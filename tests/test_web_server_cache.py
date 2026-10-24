"""
Regression tests for the web server raster-cache consistency guard (BUG-001..005).

The raster cache must NEVER mix rasters from different datasets: the DEM is
selected to match the outputs grid exactly, and inconsistent grids are rejected.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import from_origin

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import io_utils
import web_server


@pytest.fixture()
def cache_env(tmp_path, monkeypatch):
    """Builds an isolated outputs/ + data/ environment with controllable grids."""
    out_dir = tmp_path / "outputs"
    data_dir = tmp_path / "data"
    out_dir.mkdir()
    data_dir.mkdir()

    def write(path, arr, res=20.0):
        transform = from_origin(0.0, float(arr.shape[0] * res), res, res)
        io_utils.write_geotiff(output_path=path, data=arr, transform=transform,
                               crs=CRS.from_string(config.LUNAR_SOUTH_POLE_PROJ4),
                               nodata=None)

    monkeypatch.setattr(config, "OUTPUT_DIR", out_dir)
    monkeypatch.setattr(config, "OUTPUT_SLOPE_TIF", out_dir / "slope_deg.tif")
    monkeypatch.setattr(config, "OUTPUT_ROUGHNESS_STD_TIF", out_dir / "roughness_std_m.tif")
    monkeypatch.setattr(config, "OUTPUT_PSR_BINARY_TIF", out_dir / "psr_binary.tif")
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "REAL_DEM_PATH", data_dir / "lola_south_pole_dem.tif")
    monkeypatch.setattr(config, "REAL_PSR_PATH", data_dir / "lola_psr_mask.tif")
    monkeypatch.setattr(config, "SYNTHETIC_DEM_PATH", data_dir / "synthetic_dem.tif")
    monkeypatch.setattr(config, "SYNTHETIC_PSR_PATH", data_dir / "synthetic_psr.tif")

    # Reset the module-global cache between tests
    web_server.RASTER_CACHE.update({
        "loaded": False, "dem": None, "slope": None, "roughness": None, "psr": None,
        "transform": None, "meta": None, "dataset_id": None, "dataset_name": None,
        "is_synthetic": True, "pixel_size_m": None, "shape": None,
    })
    yield {"write": write, "out_dir": out_dir, "data_dir": data_dir}
    web_server.RASTER_CACHE.update({
        "loaded": False, "dem": None, "slope": None, "roughness": None, "psr": None,
        "transform": None, "meta": None, "dataset_id": None, "dataset_name": None,
        "is_synthetic": True, "pixel_size_m": None, "shape": None,
    })


def test_cache_rejects_mismatched_outputs_grids(cache_env):
    """slope/roughness/psr outputs of different shapes must be rejected (no mixing)."""
    w = cache_env["write"]
    w(cache_env["out_dir"] / "slope_deg.tif", np.zeros((50, 50), dtype=np.float32))
    w(cache_env["out_dir"] / "roughness_std_m.tif", np.zeros((50, 50), dtype=np.float32))
    w(cache_env["out_dir"] / "psr_binary.tif", np.zeros((40, 40), dtype=np.uint8))
    w(cache_env["data_dir"] / "synthetic_dem.tif", np.zeros((50, 50), dtype=np.float32))

    assert web_server.load_raster_cache() is False
    assert web_server.RASTER_CACHE["loaded"] is False


def test_cache_selects_dem_matching_outputs_grid(cache_env):
    """A present-but-mismatched real DEM must NOT be loaded; the grid-matching DEM wins."""
    w = cache_env["write"]
    # Outputs grid: 50x50 @ 20 m (synthetic-family)
    w(cache_env["out_dir"] / "slope_deg.tif", np.ones((50, 50), dtype=np.float32) * 2.0)
    w(cache_env["out_dir"] / "roughness_std_m.tif", np.ones((50, 50), dtype=np.float32) * 0.5)
    w(cache_env["out_dir"] / "psr_binary.tif", np.zeros((50, 50), dtype=np.uint8))
    # Real DEM present on disk but 60x60 (mismatched grid)
    w(cache_env["data_dir"] / "lola_south_pole_dem.tif", np.zeros((60, 60), dtype=np.float32))
    w(cache_env["data_dir"] / "lola_psr_mask.tif", np.zeros((60, 60), dtype=np.uint8))
    # Synthetic DEM matches the outputs grid
    w(cache_env["data_dir"] / "synthetic_dem.tif", np.zeros((50, 50), dtype=np.float32) - 2500.0)

    assert web_server.load_raster_cache() is True
    cache = web_server.RASTER_CACHE
    assert cache["loaded"] is True
    assert cache["dem"].shape == cache["slope"].shape == cache["roughness"].shape == cache["psr"].shape
    assert cache["shape"] == (50, 50)
    assert cache["pixel_size_m"] == 20.0
    # Provenance must honestly reflect the loaded DEM, not the present real inputs
    assert cache["dataset_id"] == "synthetic"
    assert cache["is_synthetic"] is True


def test_cache_labels_real_lola_dem_by_tags(cache_env):
    """A grid-matching LOLA DEM must be labeled as the real dataset."""
    w = cache_env["write"]
    w(cache_env["out_dir"] / "slope_deg.tif", np.ones((60, 60), dtype=np.float32))
    w(cache_env["out_dir"] / "roughness_std_m.tif", np.ones((60, 60), dtype=np.float32))
    w(cache_env["out_dir"] / "psr_binary.tif", np.zeros((60, 60), dtype=np.uint8))

    real_dem = cache_env["data_dir"] / "lola_south_pole_dem.tif"
    transform = from_origin(-7200.0, 7200.0, 240.0, 240.0)
    io_utils.write_geotiff(
        output_path=real_dem, data=np.zeros((60, 60), dtype=np.float32),
        transform=transform, crs=CRS.from_string(config.LUNAR_SOUTH_POLE_PROJ4),
        nodata=-9999.0, tags={"DATA_TYPE": "REAL NASA LRO LOLA"},
    )
    w(cache_env["data_dir"] / "lola_psr_mask.tif", np.zeros((60, 60), dtype=np.uint8))

    assert web_server.load_raster_cache() is True
    cache = web_server.RASTER_CACHE
    assert cache["dataset_id"] == "lola_crop"
    assert cache["is_synthetic"] is False
    assert "LOLA" in cache["dataset_name"]
    assert cache["pixel_size_m"] == 240.0


def test_cache_fails_cleanly_without_any_matching_dem(cache_env):
    """No DEM matching the outputs grid -> cache refuses to load (never mixes)."""
    w = cache_env["write"]
    w(cache_env["out_dir"] / "slope_deg.tif", np.ones((70, 70), dtype=np.float32))
    w(cache_env["out_dir"] / "roughness_std_m.tif", np.ones((70, 70), dtype=np.float32))
    w(cache_env["out_dir"] / "psr_binary.tif", np.zeros((70, 70), dtype=np.uint8))
    w(cache_env["data_dir"] / "lola_south_pole_dem.tif", np.zeros((60, 60), dtype=np.float32))
    w(cache_env["data_dir"] / "synthetic_dem.tif", np.zeros((50, 50), dtype=np.float32))

    assert web_server.load_raster_cache() is False
    assert web_server.RASTER_CACHE["loaded"] is False
