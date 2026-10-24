"""
Unit and integration tests for Phase 3: Terrain analysis
(slope, aspect, roughness standard deviation, TRI, and histogram generation).
"""

import sys
from pathlib import Path
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import io_utils
import terrain
import rasterio


def test_flat_surface_terrain_metrics():
    """Verify flat surface produces 0 deg slope and 0 m roughness."""
    dem = np.full((30, 30), fill_value=-2000.0, dtype=np.float32)
    
    slope, aspect, valid = terrain.calculate_slope_and_aspect(
        dem=dem, pixel_size_x=20.0, pixel_size_y=20.0, nodata_val=config.DEFAULT_NODATA_VALUE
    )
    rough_std = terrain.calculate_roughness_std(dem, window_size=3, nodata_val=config.DEFAULT_NODATA_VALUE)
    rough_tri = terrain.calculate_roughness_tri(dem, nodata_val=config.DEFAULT_NODATA_VALUE)
    
    # Interior pixels (away from borders)
    interior = slice(3, 27), slice(3, 27)
    np.testing.assert_allclose(slope[interior], 0.0, atol=1e-5)
    np.testing.assert_allclose(rough_std[interior], 0.0, atol=1e-5)
    np.testing.assert_allclose(rough_tri[interior], 0.0, atol=1e-5)


def test_planar_ramp_slope_exactness():
    """Verify a 45-degree slope (rise = run) yields exactly 45.0 degrees."""
    # z increases by 10m for every 10m in x
    dx = 10.0
    dy = 10.0
    x = np.arange(40) * dx
    y = np.arange(40) * dy
    xx, yy = np.meshgrid(x, y)
    dem = xx.astype(np.float32) # dz/dx = 1.0, dz/dy = 0.0 -> tan(slope) = 1.0 -> 45 deg
    
    slope, aspect, valid = terrain.calculate_slope_and_aspect(
        dem=dem, pixel_size_x=dx, pixel_size_y=dy, nodata_val=config.DEFAULT_NODATA_VALUE
    )
    
    # Interior pixels should be 45 degrees
    interior = slice(5, 35), slice(5, 35)
    np.testing.assert_allclose(slope[interior], 45.0, atol=0.1)


def test_nodata_preservation_in_terrain():
    """Verify NoData pixels are strictly preserved as NoData in all terrain outputs."""
    dem = np.full((20, 20), fill_value=100.0, dtype=np.float32)
    # Add NoData in corner and border
    dem[:5, :5] = config.DEFAULT_NODATA_VALUE
    
    slope, aspect, valid = terrain.calculate_slope_and_aspect(
        dem=dem, pixel_size_x=10.0, pixel_size_y=10.0, nodata_val=config.DEFAULT_NODATA_VALUE
    )
    rough_std = terrain.calculate_roughness_std(dem, window_size=3, nodata_val=config.DEFAULT_NODATA_VALUE)
    rough_tri = terrain.calculate_roughness_tri(dem, nodata_val=config.DEFAULT_NODATA_VALUE)
    
    # NoData cells must equal DEFAULT_NODATA_VALUE
    assert np.all(slope[:5, :5] == config.DEFAULT_NODATA_VALUE)
    assert np.all(aspect[:5, :5] == config.DEFAULT_NODATA_VALUE)
    assert np.all(rough_std[:5, :5] == config.DEFAULT_NODATA_VALUE)
    assert np.all(rough_tri[:5, :5] == config.DEFAULT_NODATA_VALUE)


def test_process_terrain_pipeline_end_to_end(tmp_path):
    """Verify end-to-end terrain processing and output file generation."""
    # Ensure synthetic DEM is available
    dem_path = config.SYNTHETIC_DEM_PATH
    if not dem_path.exists():
        io_utils.create_and_save_synthetic_dataset()
    dem_meta = io_utils.inspect_raster(dem_path, verbose=False)
    
    out_slope = tmp_path / "test_slope.tif"
    out_aspect = tmp_path / "test_aspect.tif"
    out_rstd = tmp_path / "test_rstd.tif"
    out_rtri = tmp_path / "test_rtri.tif"
    out_hist = tmp_path / "test_hist.png"
    
    metrics = terrain.process_terrain_pipeline(
        dem=dem_meta["data"],
        dem_meta=dem_meta,
        output_slope=out_slope,
        output_aspect=out_aspect,
        output_rough_std=out_rstd,
        output_rough_tri=out_rtri,
        output_hist=out_hist,
        is_synthetic=True,
        verbose=False,
    )
    
    # Verify file creation
    assert out_slope.exists()
    assert out_aspect.exists()
    assert out_rstd.exists()
    assert out_rtri.exists()
    assert out_hist.exists()
    
    # Verify raster properties
    with rasterio.open(out_slope) as src:
        assert src.shape == dem_meta["shape"]
        assert src.nodata == config.DEFAULT_NODATA_VALUE
        assert src.tags().get("METRIC") == "SLOPE"
        
    assert metrics["slope_mean"] > 0.0
    assert metrics["rough_std_mean"] > 0.0
