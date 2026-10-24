"""
Smoke test for Phase 0: scaffold, configuration, and synthetic DEM / PSR generator.
"""

import sys
from pathlib import Path
import numpy as np

# Ensure root directory is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import io_utils


def test_config_constants():
    """Verify all required threshold and classification constants exist."""
    assert config.SLOPE_SAFE_MAX == 5.0
    assert config.SLOPE_CAUTION_MAX == 10.0
    assert config.SLOPE_HARD_UNSAFE_MIN == 15.0
    
    assert config.ROUGHNESS_SAFE_MAX == 1.5
    assert config.ROUGHNESS_CAUTION_MAX == 3.0
    assert config.ROUGHNESS_HARD_UNSAFE_MIN == 5.0
    
    assert config.WEIGHT_SLOPE == 0.50
    assert config.WEIGHT_ROUGHNESS == 0.30
    assert config.WEIGHT_SHADOW == 0.20
    
    assert config.CLASS_NODATA == 0
    assert config.CLASS_SAFE == 1
    assert config.CLASS_CAUTION == 2
    assert config.CLASS_UNSAFE == 3
    assert config.CLASS_SHADOWED_UNKNOWN == 4
    
    # Assert Lunar CRS is defined and does NOT contain Earth EPSG (e.g. EPSG:4326 or EPSG:3857)
    assert "EPSG:4326" not in config.LUNAR_SOUTH_POLE_PROJ4
    assert "+proj=stere" in config.LUNAR_SOUTH_POLE_PROJ4
    assert "+R=1737400" in config.LUNAR_SOUTH_POLE_PROJ4


def test_synthetic_crater_topography():
    """Verify synthetic crater DEM and PSR mask generation."""
    shape = (100, 100)
    dem, psr, valid = io_utils.generate_synthetic_crater_topography(
        shape=shape,
        pixel_size=20.0,
        radius=600.0,
        depth=200.0,
        rim_height=50.0,
        base_elevation=-2500.0,
    )
    
    assert dem.shape == shape
    assert psr.shape == shape
    assert valid.shape == shape
    
    # Check NoData assignment
    assert np.any(dem == config.DEFAULT_NODATA_VALUE)
    assert np.all(dem[~valid] == config.DEFAULT_NODATA_VALUE)
    
    # Check valid elevation range inside crater vs base
    valid_elevations = dem[valid]
    assert valid_elevations.min() < -2600.0  # Crater depth Depression
    assert valid_elevations.max() > -2480.0  # Rim peak
    
    # Check PSR binary values
    unique_psr = np.unique(psr)
    for val in unique_psr:
        assert val in (0, 1)
    assert 1 in unique_psr  # Permanent shadow present
    assert 0 in unique_psr  # Lit surface present


def test_synthetic_geotiff_roundtrip(tmp_path):
    """Verify writing and reading GeoTIFF with Lunar CRS."""
    test_dem_path = tmp_path / "test_synthetic_dem.tif"
    test_psr_path = tmp_path / "test_synthetic_psr.tif"
    
    io_utils.create_and_save_synthetic_dataset(
        dem_path=test_dem_path,
        psr_path=test_psr_path,
        shape=(60, 60),
        pixel_size=25.0,
    )
    
    assert test_dem_path.exists()
    assert test_psr_path.exists()
    
    # Read back and verify
    dem_info = io_utils.read_geotiff(test_dem_path)
    assert dem_info["shape"] == (60, 60)
    assert dem_info["pixel_size_x"] == 25.0
    assert dem_info["pixel_size_y"] == 25.0
    assert dem_info["nodata"] == config.DEFAULT_NODATA_VALUE
    assert "MOON" in str(dem_info["tags"].get("BODY", ""))
    
    psr_info = io_utils.read_geotiff(test_psr_path)
    assert psr_info["shape"] == (60, 60)
    assert np.isin(psr_info["data"], [0, 1]).all()


def test_legacy_dashboard_location():
    """Verify legacy dashboard.html is housed under legacy/ and not left orphaned in root."""
    root_dashboard = ROOT_DIR / "dashboard.html"
    legacy_dashboard = ROOT_DIR / "legacy" / "dashboard.html"
    legacy_readme = ROOT_DIR / "legacy" / "README.md"

    assert not root_dashboard.exists(), "dashboard.html should be moved to legacy/"
    assert legacy_dashboard.exists(), "legacy/dashboard.html must exist"
    assert legacy_readme.exists(), "legacy/README.md must document legacy artifact"
    assert "web/index.html" in legacy_readme.read_text(encoding="utf-8")

