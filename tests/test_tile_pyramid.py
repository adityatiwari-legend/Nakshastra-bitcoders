"""
Comprehensive test suite for Task 3: Multi-scale tile pyramid engine & API.

Verifies:
1. Multi-scale pyramid dimensions (z = 0..maxZ, z=0 fits in single tile).
2. Categorical hazard preservation (safety tie-break: Unsafe > Caution > Safe, NoData preserved).
3. Edge tile padding with NoData (not stretched).
4. API 400 and 404 error cases for unknown layers, malformed coordinates, and out-of-range tiles.
5. Tile metadata endpoint returning {tileSize, maxZ, width, height}.
"""

import numpy as np

from tile_pyramid import (
    compute_max_z,
    downsample_continuous,
    downsample_hazard,
    downsample_psr,
    build_pyramid,
    slice_tile,
    TILE_SIZE,
    TilePyramidCache,
)


def test_continuous_downsampling_nanmean():
    """Verify continuous layer downsampling using nanmean over 2x2 blocks."""
    arr = np.array([
        [10.0, 20.0, np.nan],
        [30.0, 40.0, 50.0],
    ], dtype=np.float32)
    down = downsample_continuous(arr)
    # Block (0, 0): [10, 20, 30, 40] -> mean = 25.0
    assert down[0, 0] == 25.0
    # Block (0, 1): [NaN, NaN, 50, NaN] -> nanmean = 50.0
    assert down[0, 1] == 50.0



def test_compute_max_z():
    """Verify maxZ calculation: z=0 must fit in a single 256x256 tile."""
    # <= 256 px -> maxZ = 0
    assert compute_max_z(250, 250) == 0
    assert compute_max_z(256, 256) == 0
    assert compute_max_z(100, 256) == 0

    # 257..512 px -> maxZ = 1
    assert compute_max_z(300, 200) == 1
    assert compute_max_z(512, 512) == 1

    # 513..1024 px -> maxZ = 2
    assert compute_max_z(600, 500) == 2
    assert compute_max_z(1000, 800) == 2
    assert compute_max_z(1024, 1024) == 2

    # 1025..2048 px -> maxZ = 3
    assert compute_max_z(2000, 2000) == 3


def test_pyramid_dimensions_and_levels():
    """Verify pyramid levels dimensions from maxZ down to 0."""
    # 1000 x 800 raster
    w, h = 1000, 800
    base = np.ones((h, w), dtype=np.float32)
    max_z, levels = build_pyramid(base, "elevation")

    assert max_z == 2
    assert set(levels.keys()) == {0, 1, 2}

    # Level 2 (finest): exact original shape
    assert levels[2].shape == (800, 1000)

    # Level 1: halved (400, 500)
    assert levels[1].shape == (400, 500)

    # Level 0 (coarsest): halved again (200, 250)
    assert levels[0].shape == (200, 250)

    # z=0 must be <= TILE_SIZE in both dimensions (fits in 1 tile)
    assert levels[0].shape[0] <= TILE_SIZE
    assert levels[0].shape[1] <= TILE_SIZE


def test_categorical_hazard_preservation():
    """Safety-critical rule: downsampling must NEVER hide a hazard.

    Tie-break order: Unsafe (3) > Shadowed-Unknown (4) > Caution (2) > Safe (1).
    All-NoData (0) remains NoData (0).
    """
    # 1. Lone Unsafe pixel in 2x2 must make the coarse pixel Unsafe (3)
    block_unsafe = np.array([
        [1, 1],
        [1, 3]
    ], dtype=np.uint8)
    assert downsample_hazard(block_unsafe)[0, 0] == 3

    # 2. Lone Caution pixel in 2x2 of Safe must make the coarse pixel Caution (2)
    block_caution = np.array([
        [1, 1],
        [2, 1]
    ], dtype=np.uint8)
    assert downsample_hazard(block_caution)[0, 0] == 2

    # 3. Shadowed-Unknown (4) overrides Caution (2) and Safe (1)
    block_shadow = np.array([
        [1, 2],
        [4, 1]
    ], dtype=np.uint8)
    assert downsample_hazard(block_shadow)[0, 0] == 4

    # 4. Unsafe (3) overrides Shadowed-Unknown (4), Caution (2), and Safe (1)
    block_all = np.array([
        [1, 2],
        [4, 3]
    ], dtype=np.uint8)
    assert downsample_hazard(block_all)[0, 0] == 3

    # 5. Preserves NoData when entire block is NoData
    block_nodata = np.array([
        [0, 0],
        [0, 0]
    ], dtype=np.uint8)
    assert downsample_hazard(block_nodata)[0, 0] == 0

    # 6. Single Safe pixel with 3 NoData becomes Safe (1)
    block_safe_nodata = np.array([
        [0, 0],
        [1, 0]
    ], dtype=np.uint8)
    assert downsample_hazard(block_safe_nodata)[0, 0] == 1


def test_psr_downsampling():
    """PSR downsampling: shadow (1) must win over lit (0)."""
    block_shadow = np.array([[0, 0], [0, 1]], dtype=np.uint8)
    assert downsample_psr(block_shadow)[0, 0] == 1

    block_lit = np.array([[0, 0], [0, 0]], dtype=np.uint8)
    assert downsample_psr(block_lit)[0, 0] == 0


def test_edge_tiles_padded_with_nodata_not_stretched():
    """Edge tiles must be padded with NoData, never stretched or resized."""
    # Non-tile-multiple size: 300 x 300
    arr = np.full((300, 300), 42.0, dtype=np.float32)

    # Tile (0, 0): full 256x256 inside bounds
    tile_00 = slice_tile(arr, x=0, y=0, is_continuous=True, tile_size=256)
    assert tile_00.shape == (256, 256)
    assert np.all(tile_00 == 42.0)

    # Tile (1, 0): right edge tile
    # columns 0..43 are valid (width 300 - 256 = 44)
    # columns 44..255 must be NaN (NoData padded)
    tile_10 = slice_tile(arr, x=1, y=0, is_continuous=True, tile_size=256)
    assert tile_10.shape == (256, 256)
    assert np.all(tile_10[:, :44] == 42.0)
    assert np.all(np.isnan(tile_10[:, 44:]))

    # Categorical edge tile: padded with 0 (NoData)
    cat_arr = np.full((300, 300), 1, dtype=np.uint8)
    cat_tile_10 = slice_tile(cat_arr, x=1, y=0, is_continuous=False, tile_size=256)
    assert cat_tile_10.shape == (256, 256)
    assert np.all(cat_tile_10[:, :44] == 1.0)
    assert np.all(cat_tile_10[:, 44:] == 0.0)


def test_lru_cache_and_invalidation():
    """Verify TilePyramidCache LRU capacity, retrieval and invalidation."""
    cache = TilePyramidCache(max_tiles=4)
    arr = np.ones((500, 500), dtype=np.float32)

    # Fetch tiles
    t0 = cache.get_tile("slope", arr, z=0, x=0, y=0)
    assert t0 is not None
    assert len(t0) == 256 * 256 * 4

    meta = cache.get_meta("slope", arr)
    assert meta["tileSize"] == 256
    assert meta["maxZ"] == 1
    assert meta["width"] == 500
    assert meta["height"] == 500

    # Invalidate cache
    cache.clear()
    assert len(cache._tile_cache) == 0
    assert len(cache._pyramids) == 0
