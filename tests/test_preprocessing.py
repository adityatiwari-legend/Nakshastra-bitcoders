"""
Unit and integration tests for Phase 1: Data loading, raster inspection,
and grid alignment / mismatch detection.
"""

import sys
from pathlib import Path
import pytest
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import io_utils
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS


def test_inspect_raster(capsys):
    """Verify raster inspection prints CRS, pixel size, extent, dtype, NoData."""
    # Ensure synthetic dataset exists
    dem_path = config.SYNTHETIC_DEM_PATH
    if not dem_path.exists():
        io_utils.create_and_save_synthetic_dataset()
        
    summary = io_utils.inspect_raster(dem_path, verbose=True)
    captured = capsys.readouterr().out
    
    # Assert all required metadata fields are printed
    assert "CRS:" in captured
    assert "Pixel Size:" in captured
    assert "Dimensions:" in captured
    assert "Extent [Bounds]:" in captured
    assert "Data Type:" in captured
    assert "NoData Value:" in captured
    assert "Pixel Breakdown:" in captured
    assert "SYNTHETIC DEMO" in captured
    
    assert summary["pixel_size_x"] == config.SYNTHETIC_PIXEL_SIZE_M
    assert summary["pixel_size_y"] == config.SYNTHETIC_PIXEL_SIZE_M
    assert summary["shape"] == config.SYNTHETIC_DEM_SHAPE
    assert summary["nodata"] == config.DEFAULT_NODATA_VALUE


def test_earth_epsg_protection(tmp_path):
    """Verify pipeline rejects Earth EPSG on lunar data with a loud ValueError."""
    fake_tif = tmp_path / "earth_dem.tif"
    data = np.ones((50, 50), dtype=np.float32)
    # Earth EPSG:4326 WGS84
    transform = from_origin(0, 0, 1, 1)
    
    with rasterio.open(
        fake_tif, "w", driver="GTiff", height=50, width=50, count=1,
        dtype=data.dtype, crs=CRS.from_epsg(4326), transform=transform
    ) as dst:
        dst.write(data, 1)
        
    with pytest.raises(ValueError, match="LUNAR CRS VIOLATION"):
        io_utils.inspect_raster(fake_tif)


def test_grid_mismatch_detection_and_loud_failure(tmp_path):
    """Verify that differing grids fail loudly when fail_on_mismatch=True."""
    # Create base DEM (100x100, 20m)
    dem_path = tmp_path / "base_dem.tif"
    dem_data = np.zeros((100, 100), dtype=np.float32)
    t_dem = from_origin(-1000, 1000, 20.0, 20.0)
    lunar_crs = CRS.from_string(config.LUNAR_SOUTH_POLE_PROJ4)
    io_utils.write_geotiff(dem_path, dem_data, t_dem, lunar_crs, nodata=config.DEFAULT_NODATA_VALUE)
    
    dem_meta = io_utils.inspect_raster(dem_path, verbose=False)
    
    # Create PSR with differing resolution and shape (50x50, 40m)
    psr_path = tmp_path / "mismatched_psr.tif"
    psr_data = np.ones((50, 50), dtype=np.uint8)
    t_psr = from_origin(-1000, 1000, 40.0, 40.0)
    io_utils.write_geotiff(psr_path, psr_data, t_psr, lunar_crs, nodata=None)
    
    # Should FAIL LOUDLY when fail_on_mismatch=True
    with pytest.raises(ValueError, match="GRID MISMATCH ERROR"):
        io_utils.align_psr_to_dem(
            psr_path=psr_path,
            dem_meta=dem_meta,
            fail_on_mismatch=True,
            verbose=False,
        )


def test_grid_resampling_alignment(tmp_path):
    """Verify that a coarser or shifted PSR mask is cleanly aligned to the DEM grid."""
    # Base DEM: 100x100 at 20m/pixel (footprint -1000 to +1000)
    dem_path = tmp_path / "dem.tif"
    dem_data = np.zeros((100, 100), dtype=np.float32)
    t_dem = from_origin(-1000, 1000, 20.0, 20.0)
    lunar_crs = CRS.from_string(config.LUNAR_SOUTH_POLE_PROJ4)
    io_utils.write_geotiff(dem_path, dem_data, t_dem, lunar_crs, nodata=config.DEFAULT_NODATA_VALUE)
    dem_meta = io_utils.inspect_raster(dem_path, verbose=False)
    
    # Coarser PSR: 50x50 at 40m/pixel
    psr_path = tmp_path / "coarse_psr.tif"
    psr_data = np.zeros((50, 50), dtype=np.uint8)
    psr_data[10:30, 10:30] = 1 # Sub-region marked as PSR
    t_psr = from_origin(-1000, 1000, 40.0, 40.0)
    io_utils.write_geotiff(psr_path, psr_data, t_psr, lunar_crs, nodata=None)
    
    aligned_data, aligned_meta = io_utils.align_psr_to_dem(
        psr_path=psr_path,
        dem_meta=dem_meta,
        fail_on_mismatch=False,
        verbose=False,
    )
    
    # Must now match DEM dimensions and transform exactly
    assert aligned_data.shape == dem_meta["shape"]
    assert aligned_meta["pixel_size_x"] == dem_meta["pixel_size_x"]
    assert aligned_meta["pixel_size_y"] == dem_meta["pixel_size_y"]
    assert np.isin(aligned_data, [0, 1]).all()
    # Check that shadow pixels were preserved
    assert np.sum(aligned_data == 1) > 0
