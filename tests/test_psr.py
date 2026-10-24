"""
Unit and integration tests for Phase 2: PSR binarization, small-component filtering,
area calculation in km2, and vector polygon export.
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
import psr
import rasterio
import geopandas as gpd
from rasterio.transform import from_origin
from rasterio.crs import CRS


def test_binarize_psr_and_nodata_exclusion():
    """Verify binarization of different types and strict NoData exclusion."""
    raw_float = np.array([[0.0, 0.4, 0.6], [0.8, 1.0, 0.2]], dtype=np.float32)
    binary = psr.binarize_psr(raw_float, threshold=0.5)
    expected = np.array([[0, 0, 1], [1, 1, 0]], dtype=np.uint8)
    np.testing.assert_array_equal(binary, expected)

    # Test with NoData mask
    nodata_mask = np.array([[False, False, True], [False, False, False]], dtype=bool)
    binary_masked = psr.binarize_psr(raw_float, threshold=0.5, nodata_mask=nodata_mask)
    # Even though pixel (0,2) had value 0.6, it is NoData and must be 0!
    assert binary_masked[0, 2] == 0


def test_clean_psr_mask_removes_tiny_components():
    """Verify removal of isolated speckles smaller than min_size."""
    mask = np.zeros((20, 20), dtype=np.uint8)
    
    # 1. An isolated single pixel (size 1)
    mask[2, 2] = 1
    # 2. A 2-pixel speckle (size 2)
    mask[5, 5] = 1
    mask[5, 6] = 1
    # 3. A large solid component 4x4 (size 16)
    mask[10:14, 10:14] = 1

    cleaned = psr.clean_psr_mask(mask, min_size_pixels=9)
    
    # Tiny components must be removed
    assert cleaned[2, 2] == 0
    assert cleaned[5, 5] == 0
    assert cleaned[5, 6] == 0
    # Large component must be preserved
    assert np.all(cleaned[10:14, 10:14] == 1)
    assert np.sum(cleaned) == 16


def test_calculate_psr_area_exactness():
    """Verify mathematical exactness of area calculations."""
    mask = np.zeros((10, 10), dtype=np.uint8)
    mask[0:5, 0:5] = 1 # 25 pixels
    
    metrics = psr.calculate_psr_area(mask, pixel_size_x=20.0, pixel_size_y=20.0)
    
    assert metrics["pixel_count"] == 25
    assert metrics["pixel_area_m2"] == 400.0
    assert metrics["area_m2"] == 10000.0  # 25 * 400
    assert metrics["area_km2"] == 0.01    # 10,000 / 1,000,000


def test_vectorize_psr_to_polygons():
    """Verify conversion of raster components to valid GeoDataFrame vector polygons."""
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[5:15, 5:15] = 1  # 10x10 block = 100 pixels
    
    transform = from_origin(0, 200, 10.0, 10.0)
    lunar_crs = CRS.from_string(config.LUNAR_SOUTH_POLE_PROJ4)
    
    gdf = psr.vectorize_psr_to_polygons(
        binary_psr=mask,
        transform=transform,
        crs=lunar_crs,
        min_size_pixels=9,
        provenance=config.PSR_PROVENANCE_SYNTHETIC,
    )
    
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) == 1
    assert gdf.iloc[0]["feature"] == "PSR"
    assert gdf.iloc[0]["area_m2"] == pytest.approx(10000.0, rel=1e-2)
    assert gdf.iloc[0]["area_km2"] == pytest.approx(0.01, rel=1e-2)
    assert gdf.iloc[0]["geometry"].is_valid
    import pyproj
    assert pyproj.CRS(gdf.crs).equals(pyproj.CRS(lunar_crs))


def test_process_and_export_psr_end_to_end(tmp_path):
    """Verify full PSR pipeline and file export (GeoTIFF, GeoJSON, Shapefile)."""
    # Load synthetic dataset
    dem_path = config.SYNTHETIC_DEM_PATH
    if not dem_path.exists():
        io_utils.create_and_save_synthetic_dataset()
    dem_meta = io_utils.inspect_raster(dem_path, verbose=False)
    
    psr_path = config.SYNTHETIC_PSR_PATH
    raw_psr_data = io_utils.read_geotiff(psr_path)["data"]
    
    out_tif = tmp_path / "psr_test.tif"
    out_geojson = tmp_path / "psr_test.geojson"
    out_shp = tmp_path / "psr_test.shp"
    
    cleaned_psr, metrics, gdf = psr.process_and_export_psr(
        raw_psr=raw_psr_data,
        dem_meta=dem_meta,
        output_tif=out_tif,
        output_geojson=out_geojson,
        output_shp=out_shp,
        is_synthetic=True,
        verbose=False,
    )
    
    assert out_tif.exists()
    assert out_geojson.exists()
    assert out_shp.exists()
    
    assert metrics["pixel_count"] > 0
    assert metrics["area_km2"] > 0.0
    assert len(gdf) > 0
    
    # Read back exported GeoTIFF and verify
    with rasterio.open(out_tif) as src:
        assert src.shape == dem_meta["shape"]
        assert np.isin(src.read(1), [0, 1]).all()
        assert "PSR_AREA_KM2" in src.tags()
        
    # Read back exported GeoJSON
    gdf_read = gpd.read_file(out_geojson)
    assert len(gdf_read) == len(gdf)
    assert gdf_read.iloc[0]["feature"] == "PSR"
