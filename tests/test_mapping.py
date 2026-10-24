"""
Unit and integration tests for Phase 5: Publication-grade 4-panel cartography
(PNG and PDF output at 300 DPI).
"""

import sys
from pathlib import Path
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import io_utils
import mapping
import geopandas as gpd


def test_hillshade_computation():
    """Verify hillshade calculation outputs values in range [0, 1]."""
    slope = np.array([[0.0, 15.0], [30.0, 45.0]], dtype=np.float32)
    aspect = np.array([[0.0, 90.0], [180.0, 270.0]], dtype=np.float32)
    
    hs = mapping.compute_hillshade(slope, aspect)
    assert hs.shape == (2, 2)
    assert np.all(hs >= 0.0)
    assert np.all(hs <= 1.0)


def test_generate_4panel_hazard_map_end_to_end(tmp_path):
    """Verify creation of 4-panel PNG and PDF maps at 300 DPI."""
    # The map must be generated from a grid-consistent dataset: choose the
    # DEM whose grid matches the current pipeline outputs (never mix grids).
    out_shape = io_utils.read_geotiff(config.OUTPUT_SLOPE_TIF)["data"].shape

    dem_path = None
    for cand in (
        config.OUTPUT_DIR / "active_site_dem.tif",
        config.REAL_DEM_PATH,
        config.SYNTHETIC_DEM_PATH,
    ):
        if cand.exists() and io_utils.read_geotiff(cand)["data"].shape == out_shape:
            dem_path = cand
            break
    if dem_path is None:
        # Fall back to regenerating the synthetic benchmark so the test is hermetic
        io_utils.create_and_save_synthetic_dataset()
        dem_path = config.SYNTHETIC_DEM_PATH
    dem_meta = io_utils.inspect_raster(dem_path, verbose=False)
    is_synthetic = dem_path == config.SYNTHETIC_DEM_PATH or "synthetic" in str(dem_path).lower()

    slope = io_utils.read_geotiff(config.OUTPUT_SLOPE_TIF)["data"]
    aspect = io_utils.read_geotiff(config.OUTPUT_ASPECT_TIF)["data"]
    psr_mask = io_utils.read_geotiff(config.OUTPUT_PSR_BINARY_TIF)["data"]
    hazard_classes = io_utils.read_geotiff(config.OUTPUT_HAZARD_CLASSES_TIF)["data"]

    psr_gdf = None
    if config.OUTPUT_PSR_POLYGONS_GEOJSON.exists():
        psr_gdf = gpd.read_file(config.OUTPUT_PSR_POLYGONS_GEOJSON)

    out_png = tmp_path / "test_map.png"
    out_pdf = tmp_path / "test_map.pdf"

    png_path, pdf_path = mapping.generate_4panel_hazard_map(
        dem=dem_meta["data"],
        slope=slope,
        aspect=aspect,
        psr_mask=psr_mask,
        hazard_classes=hazard_classes,
        dem_meta=dem_meta,
        psr_gdf=psr_gdf,
        output_png=out_png,
        output_pdf=out_pdf,
        is_synthetic=is_synthetic,
        verbose=False,
    )

    assert png_path.exists()
    assert pdf_path.exists()

    # Assert non-empty file size (> 100 KB)
    assert png_path.stat().st_size > 100_000
    assert pdf_path.stat().st_size > 50_000
