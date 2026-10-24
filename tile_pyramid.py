"""
Multi-scale tile pyramid generator and LRU cache for OrbisLuna.

Provides hierarchical 256x256 XYZ tiles for continuous and categorical lunar layers:
- continuous layers: elevation, slope, roughness, score (downsampled via nanmean)
- categorical layers: hazard (classes 0..4, Unsafe overrides Caution overrides Safe), psr
- edge padding with NoData (not stretched)
- z = 0..maxZ where z=0 is the whole raster in one tile
  and maxZ = max(0, ceil(log2(max(W, H) / 256)))
"""

import math
import threading
from collections import OrderedDict
from typing import Dict, Optional, Tuple, Any

import numpy as np


TILE_SIZE = 256

CATEGORICAL_LAYERS = {"hazard", "hazard_classes", "psr", "psr_mask"}
CONTINUOUS_LAYERS = {"elevation", "dem", "slope", "roughness", "score", "illumination"}
ALLOWED_LAYERS = CATEGORICAL_LAYERS | CONTINUOUS_LAYERS


def compute_max_z(width: int, height: int, tile_size: int = TILE_SIZE) -> int:
    """Computes maxZ such that z=0 has dimensions <= tile_size (whole raster in one tile)."""
    max_dim = max(int(width), int(height))
    if max_dim <= tile_size:
        return 0
    return max(0, math.ceil(math.log2(max_dim / float(tile_size))))


def downsample_continuous(a: np.ndarray) -> np.ndarray:
    """Downsample continuous 2D raster by 2x2 blocks using nanmean.
    
    Pads to even dimensions with NaN so edge pixels are not dropped.
    """
    h_orig, w_orig = a.shape
    h = (h_orig + 1) // 2 * 2
    w = (w_orig + 1) // 2 * 2
    p = np.full((h, w), np.nan, dtype=np.float32)
    p[:h_orig, :w_orig] = a
    blocks = p.reshape(h // 2, 2, w // 2, 2)
    with np.errstate(all='ignore'):
        out = np.nanmean(blocks, axis=(1, 3))
    return out.astype(np.float32)


def downsample_hazard(c: np.ndarray) -> np.ndarray:
    """Downsample hazard classes preserving safety overrides.
    
    Hazard classes: 0 NoData, 1 Safe, 2 Caution, 3 Unsafe, 4 Shadowed-Unknown.
    Tie-break order: (1, 2, 4, 3) where Unsafe overrides everything, then Shadowed-Unknown,
    then Caution, then Safe. All-NoData blocks remain NoData (0).
    """
    h_orig, w_orig = c.shape
    h = (h_orig + 1) // 2 * 2
    w = (w_orig + 1) // 2 * 2
    p = np.zeros((h, w), dtype=c.dtype)
    p[:h_orig, :w_orig] = c
    b = p.reshape(h // 2, 2, w // 2, 2).transpose(0, 2, 1, 3).reshape(h // 2, w // 2, 4)
    out = np.zeros(b.shape[:2], dtype=c.dtype)
    for cls in (1, 2, 4, 3):
        out[(b == cls).any(axis=2)] = cls
    return out


def downsample_psr(psr: np.ndarray) -> np.ndarray:
    """Downsample PSR mask (0 = lit, 1 = shadow).
    
    If any subpixel is in shadow, the coarse cell is marked in shadow (1).
    """
    h_orig, w_orig = psr.shape
    h = (h_orig + 1) // 2 * 2
    w = (w_orig + 1) // 2 * 2
    p = np.zeros((h, w), dtype=psr.dtype)
    p[:h_orig, :w_orig] = psr
    b = p.reshape(h // 2, 2, w // 2, 2).transpose(0, 2, 1, 3).reshape(h // 2, w // 2, 4)
    out = np.zeros(b.shape[:2], dtype=psr.dtype)
    out[(b == 1).any(axis=2)] = 1
    return out


def build_pyramid(base_array: np.ndarray, layer_name: str, tile_size: int = TILE_SIZE) -> Tuple[int, Dict[int, np.ndarray]]:
    """Builds multi-scale pyramid levels from maxZ down to 0."""
    norm_layer = layer_name.lower().strip()
    h, w = base_array.shape[:2]
    max_z = compute_max_z(w, h, tile_size)

    # Determine downsampler
    if norm_layer in ("hazard", "hazard_classes"):
        downsampler = downsample_hazard
        clean_base = base_array.copy()
    elif norm_layer in ("psr", "psr_mask"):
        downsampler = downsample_psr
        clean_base = base_array.copy()
    else:
        downsampler = downsample_continuous
        # Replace non-finite or extreme nodata values with np.nan for nanmean
        clean_base = np.array(base_array, dtype=np.float32, copy=True)
        clean_base[~np.isfinite(clean_base)] = np.nan
        clean_base[clean_base <= -9000] = np.nan

    levels: Dict[int, np.ndarray] = {max_z: clean_base}
    current = clean_base
    for z in range(max_z - 1, -1, -1):
        current = downsampler(current)
        levels[z] = current

    return max_z, levels


def slice_tile(arr: np.ndarray, x: int, y: int, is_continuous: bool, tile_size: int = TILE_SIZE) -> Optional[np.ndarray]:
    """Slices a 256x256 tile at (x, y) with NoData padding at boundaries.
    
    Returns None if x or y is out of range.
    """
    h, w = arr.shape[:2]
    tiles_x = max(1, math.ceil(w / float(tile_size)))
    tiles_y = max(1, math.ceil(h / float(tile_size)))

    if x < 0 or x >= tiles_x or y < 0 or y >= tiles_y:
        return None

    r0 = y * tile_size
    r1 = min(h, (y + 1) * tile_size)
    c0 = x * tile_size
    c1 = min(w, (x + 1) * tile_size)

    sub = arr[r0:r1, c0:c1]

    if is_continuous:
        tile = np.full((tile_size, tile_size), np.nan, dtype=np.float32)
    else:
        tile = np.zeros((tile_size, tile_size), dtype=np.float32)

    tile[:sub.shape[0], :sub.shape[1]] = sub.astype(np.float32)
    return tile


class TilePyramidCache:
    """Thread-safe in-memory LRU cache for multi-scale layer tile pyramids."""

    def __init__(self, max_tiles: int = 1024):
        self.max_tiles = max_tiles
        self._lock = threading.Lock()
        self._tile_cache: OrderedDict[Tuple[str, int, int, int], bytes] = OrderedDict()
        self._pyramids: Dict[str, Tuple[int, Dict[int, np.ndarray]]] = {}

    def clear(self):
        """Invalidates all cached tile pyramids and raw byte tiles."""
        with self._lock:
            self._tile_cache.clear()
            self._pyramids.clear()

    def get_pyramid(self, layer_name: str, base_array: np.ndarray) -> Tuple[int, Dict[int, np.ndarray]]:
        norm_layer = layer_name.lower().strip()
        with self._lock:
            if norm_layer in self._pyramids:
                return self._pyramids[norm_layer]
        # Build without holding the lock to avoid blocking other layers
        max_z, levels = build_pyramid(base_array, norm_layer, TILE_SIZE)
        with self._lock:
            self._pyramids[norm_layer] = (max_z, levels)
            return max_z, levels

    def get_meta(self, layer_name: str, base_array: np.ndarray) -> Dict[str, Any]:
        norm_layer = layer_name.lower().strip()
        h, w = base_array.shape[:2]
        max_z, levels = self.get_pyramid(norm_layer, base_array)
        level_0 = levels[0]
        tiles_x = max(1, math.ceil(level_0.shape[1] / float(TILE_SIZE)))
        tiles_y = max(1, math.ceil(level_0.shape[0] / float(TILE_SIZE)))

        return {
            "status": "SUCCESS",
            "layer": norm_layer,
            "tileSize": TILE_SIZE,
            "maxZ": max_z,
            "width": w,
            "height": h,
            "dtype": "float32",
            "tiles_x": tiles_x,
            "tiles_y": tiles_y,
        }

    def get_tile(self, layer_name: str, base_array: np.ndarray, z: int, x: int, y: int) -> Optional[bytes]:
        norm_layer = layer_name.lower().strip()
        key = (norm_layer, z, x, y)
        with self._lock:
            if key in self._tile_cache:
                self._tile_cache.move_to_end(key)
                return self._tile_cache[key]

        max_z, levels = self.get_pyramid(norm_layer, base_array)
        if z < 0 or z > max_z:
            return None

        arr_z = levels[z]
        is_continuous = norm_layer not in CATEGORICAL_LAYERS
        tile = slice_tile(arr_z, x, y, is_continuous=is_continuous, tile_size=TILE_SIZE)
        if tile is None:
            return None

        tile_bytes = tile.astype(np.float32).tobytes()
        with self._lock:
            self._tile_cache[key] = tile_bytes
            if len(self._tile_cache) > self.max_tiles:
                self._tile_cache.popitem(last=False)
        return tile_bytes


# Global singleton instance
TILE_CACHE = TilePyramidCache()
