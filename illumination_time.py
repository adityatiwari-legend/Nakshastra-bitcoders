"""
Analytic diurnal (lunar-day) illumination model - Phase 4 time slider.

HONESTY NOTE (see .agents/rules/lunasafe.md):
This is a MODEL, not a measured time-series product. The published datasets
(AVGVISIB cycle-average, Mazarico et al. 2011) contain no time-resolved frames.
This module computes per-frame lit/shadow from:
  1. an analytic solar position (hour angle over one lunar local day, fixed
     southern-summer declination delta = -1.54 deg = -lunar obliquity), and
  2. horizon ray-marching across the ACTIVE DEM (nearest-neighbour sampling).

The published LPSR mask (LPSR_65S_240M) remains the authoritative permanent
shadow product; this model is for visualization/screening of diurnal lighting
only and MUST be labeled "analytic model" anywhere it is shown.

Frames are uint8: 0 = modeled shadow (or NoData), 255 = modeled direct sun.
"""

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

import config

MODEL_VERSION = "analytic_solar_horizon_psr_v2"
MOON_OBLIQUITY_DEG = 1.54
# Southern-summer solstice declination: maximum solar elevation over the
# lunar south polar region. Fixed for the animation (documented simplification).
SOLAR_DECLINATION_DEG = -MOON_OBLIQUITY_DEG
MAX_RAY_KM = 24.0
HORIZON_EPS_M = 1.0
DEFAULT_FRAMES = 24

ILLUM_TIME_DIR = config.OUTPUT_DIR / "web" / "illum_time"


def solar_elevation_azimuth_deg(
    latitude_deg: float,
    hour_angle_deg: float,
    declination_deg: float = SOLAR_DECLINATION_DEG,
) -> Tuple[float, float]:
    """Solar elevation and azimuth for a lunar local-solar-time hour angle.

    Args:
        latitude_deg: observer latitude (negative = south).
        hour_angle_deg: hour angle, 0 at local noon, -180..180
                        (negative = morning, positive = afternoon).
        declination_deg: solar declination (fixed -1.54 deg for this model).

    Returns:
        (elevation_deg, azimuth_deg) - azimuth measured clockwise from north,
        normalized to [0, 360).
    """
    phi = math.radians(latitude_deg)
    delta = math.radians(declination_deg)
    H = math.radians(hour_angle_deg)

    sin_elev = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(H)
    sin_elev = max(-1.0, min(1.0, sin_elev))
    elev = math.degrees(math.asin(sin_elev))

    az = math.degrees(
        math.atan2(
            math.sin(H),
            math.cos(H) * math.sin(phi) - math.tan(delta) * math.cos(phi),
        )
    ) + 180.0
    az = az % 360.0
    return elev, az


def frame_schedule(frames: int = DEFAULT_FRAMES, latitude_deg: float = -85.0) -> Dict[str, list]:
    """Per-frame local-solar hour, elevation and azimuth for one lunar day.

    Hour spans 0..24 local solar time; hour angle H = (hour - 12) * 15 deg.
    Default latitude -85 deg guarantees both day and night frames under the
    fixed southern-summer declination (at the exact pole the sun never sets).
    """
    hours, elevs, azs = [], [], []
    for i in range(frames):
        hour = (i * 24.0) / frames
        H = (hour - 12.0) * 15.0
        elev, az = solar_elevation_azimuth_deg(latitude_deg, H)
        hours.append(round(hour, 3))
        elevs.append(round(elev, 4))
        azs.append(round(az, 3))
    return {"hours": hours, "sun_elevation_deg": elevs, "sun_azimuth_deg": azs}


# Fallback latitude for schedule previews when no site latitude is known.
_DEFAULT_LAT = -85.0


def compute_frames(
    dem: np.ndarray,
    pixel_size_m: float,
    latitude_deg: float,
    frames: int = DEFAULT_FRAMES,
    nodata: Optional[float] = None,
    psr_mask: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Computes modeled lit/shadow frames over one lunar local day.

    Args:
        dem: 2D float elevation array (meters).
        pixel_size_m: grid spacing in meters (assumed square).
        latitude_deg: site latitude for the solar-position model.
        frames: number of frames spanning one 24 h lunar day.
        nodata: NoData elevation value (those pixels stay dark in all frames).
        psr_mask: optional 2D binary/integer array matching DEM where >0 indicates
            an authoritative Permanently Shadowed Region (PSR). By astronomical
            definition, PSRs never receive direct solar illumination and are kept
            in permanent shadow (value 0) across all frames.

    Returns:
        (volume, meta): volume is uint8 [frames, H, W]; meta describes schedule,
        model version and honesty labeling.
    """
    dem = np.asarray(dem, dtype=np.float32)
    if dem.ndim != 2:
        raise ValueError(f"dem must be 2D, got shape {dem.shape}")
    H, W = dem.shape
    px = float(pixel_size_m)
    if px <= 0:
        raise ValueError("pixel_size_m must be positive")

    valid = np.isfinite(dem)
    if nodata is not None:
        valid &= (dem != nodata)

    psr_flat = None
    if psr_mask is not None:
        psr_arr = np.asarray(psr_mask)
        if psr_arr.shape == (H, W):
            psr_flat = (psr_arr > 0).reshape(-1)

    n_steps = max(4, int(round(MAX_RAY_KM * 1000.0 / px)))
    t = (np.arange(1, n_steps + 1, dtype=np.float32) * px)  # (S,)

    # Pixel-center world coordinates (Moon2000 polar stereographic: x east, y north;
    # raster transform origin is top-left with negative y-step).
    cols = np.arange(W, dtype=np.float32)
    rows = np.arange(H, dtype=np.float32)
    # World coords assume identity-position grid; caller passes arrays whose
    # raster geometry is regular. Absolute position does not matter for shadow
    # geometry, only relative layout — use grid indices scaled by pixel size.
    X = cols * px          # east meters
    Y = (H - 1 - rows) * px  # north meters (row 0 = north edge)
    Xg, Yg = np.meshgrid(X, Y)          # (H, W)
    Xf = Xg.reshape(-1)                 # (P,)
    Yf = Yg.reshape(-1)
    Zf = dem.reshape(-1)                # (P,)
    validf = valid.reshape(-1)

    volume = np.zeros((frames, H, W), dtype=np.uint8)
    hours, elevs, azs = [], [], []

    for i in range(frames):
        hour = (i * 24.0) / frames
        H_ang = (hour - 12.0) * 15.0
        elev, az = solar_elevation_azimuth_deg(latitude_deg, H_ang)
        hours.append(round(hour, 3))
        elevs.append(round(elev, 4))
        azs.append(round(az, 3))

        if elev <= 0.0:
            continue  # local night: everything dark

        az_rad = math.radians(az)
        dx = math.sin(az_rad)   # east component of sun direction
        dy = math.cos(az_rad)   # north component
        tan_e = math.tan(math.radians(elev))

        # Sample positions along the sun ray for every pixel: (P, S)
        Xs = Xf[:, None] + t[None, :] * dx
        Ys = Yf[:, None] + t[None, :] * dy
        sc = np.clip((Xs / px).astype(np.int32), 0, W - 1)
        sr = np.clip(((H - 1) - Ys / px).astype(np.int32), 0, H - 1)

        sampled = dem[sr, sc]                     # (P, S)
        horizon = Zf[:, None] + t[None, :] * float(tan_e) + HORIZON_EPS_M
        blocked = np.any(sampled > horizon, axis=1)  # (P,)
        # Samples clipped from outside the grid cannot obstruct (documented).
        lit = validf & ~blocked
        if psr_flat is not None:
            lit &= ~psr_flat

        frame = lit.reshape(H, W)
        volume[i][frame] = 255

    if psr_flat is not None and np.any(psr_flat):
        psr_2d = psr_flat.reshape(H, W)
        volume[:, psr_2d] = 0

    meta = {
        "model": MODEL_VERSION,
        "kind": "analytic_model_not_observed",
        "label": "Analytic diurnal illumination model (solar position + DEM horizon ray-trace + PSR constraint)",
        "disclaimer": (
            "Computed model, not a time-resolved measurement. The published LPSR mask "
            "(Mazarico et al. 2011) remains the authoritative permanent-shadow product. "
            "Pixels within authoritative PSR boundaries are strictly constrained to 0% direct solar illumination."
        ),
        "psr_constrained": bool(psr_flat is not None and np.any(psr_flat)),
        "declination_deg": SOLAR_DECLINATION_DEG,
        "moon_obliquity_deg": MOON_OBLIQUITY_DEG,
        "max_ray_km": MAX_RAY_KM,
        "latitude_deg": float(latitude_deg),
        "pixel_size_m": px,
        "width": W,
        "height": H,
        "frames": frames,
        "dtype": "uint8",
        "encoding": "0=modeled shadow/NoData/PSR, 255=modeled direct sun",
        "hours": hours,
        "sun_elevation_deg": elevs,
        "sun_azimuth_deg": azs,
    }
    return volume, meta


def _cache_key(dataset_id: str, frames: int, shape: Tuple[int, int], lat: float,
               pixel_size_m: float, has_psr: bool = False) -> str:
    raw = (f"{dataset_id}|{frames}|{shape[0]}x{shape[1]}|{round(lat,4)}"
           f"|{round(float(pixel_size_m),4)}|{MODEL_VERSION}|psr={has_psr}")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def compute_or_get(
    dem: np.ndarray,
    pixel_size_m: float,
    latitude_deg: float,
    dataset_id: str,
    frames: int = DEFAULT_FRAMES,
    nodata: Optional[float] = None,
    psr_mask: Optional[np.ndarray] = None,
    cache_dir: Optional[Path] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """Compute frames with an on-disk cache keyed by dataset + model version.

    Returns:
        (bin_path, meta) where bin_path holds frames*H*W raw uint8 bytes.
    """
    cache_dir = Path(cache_dir) if cache_dir else ILLUM_TIME_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    has_psr = psr_mask is not None and bool(np.any(np.asarray(psr_mask) > 0))
    key = _cache_key(dataset_id, frames, np.asarray(dem).shape, float(latitude_deg),
                     float(pixel_size_m), has_psr=has_psr)
    bin_path = cache_dir / f"{key}.bin"
    meta_path = cache_dir / f"{key}.meta.json"

    if bin_path.exists() and meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            expected = int(meta["frames"]) * int(meta["height"]) * int(meta["width"])
            if bin_path.stat().st_size == expected:
                meta["cache_hit"] = True
                return bin_path, meta
        except Exception:
            pass  # regenerate on any inconsistency

    volume, meta = compute_frames(
        dem=dem, pixel_size_m=pixel_size_m, latitude_deg=latitude_deg,
        frames=frames, nodata=nodata, psr_mask=psr_mask,
    )
    meta["dataset_id"] = dataset_id
    meta["cache_key"] = key
    tmp = bin_path.with_suffix(".bin.part")
    with open(tmp, "wb") as f:
        f.write(volume.tobytes())
    tmp.replace(bin_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)
    meta["cache_hit"] = False
    return bin_path, meta


def load_volume(bin_path: Path, meta: Dict[str, Any]) -> np.ndarray:
    """Memory-maps/reads the cached frame volume back into [frames, H, W] uint8."""
    frames = int(meta["frames"])
    H = int(meta["height"])
    W = int(meta["width"])
    raw = Path(bin_path).read_bytes()
    return np.frombuffer(raw, dtype=np.uint8).reshape(frames, H, W)
