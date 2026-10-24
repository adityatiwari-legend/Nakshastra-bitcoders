"""
Unit and integration tests for LunaSafe Machine Learning & Mission Autonomy Module
Tests boulder micro-hazard AI detection and autonomous landing site recommender.
"""

import json
import numpy as np
import pytest
import rasterio

import config
import ml_recommender

def test_boulder_micro_hazard_detection():
    """Verify that the boulder AI detector flags high-frequency local anomalies."""
    shape = (50, 50)
    # Smooth base terrain
    dem = np.full(shape, -2500.0, dtype=np.float32)
    
    # Introduce localized sharp boulder obstacle at (25, 25)
    dem[25, 25] += 12.0  # 12-meter spike/boulder anomaly
    
    boulder_prob, boulder_points = ml_recommender.detect_boulder_micro_hazards(
        dem_data=dem,
        nodata_val=config.DEFAULT_NODATA_VALUE,
        std_threshold=2.0
    )
    
    assert boulder_prob.shape == shape
    assert boulder_prob[25, 25] > 0.7  # Boulder point must have high probability
    assert len(boulder_points) >= 1
    # Check that (25, 25) is detected among obstacle points
    detected_coords = [(p["row"], p["col"]) for p in boulder_points]
    assert (25, 25) in detected_coords

def test_landing_site_recommender():
    """Verify that the recommender selects contiguous safe zones and outputs Top-3 sites."""
    shape = (100, 100)
    # 0 = NoData, 1 = Safe, 2 = Caution, 3 = Unsafe, 4 = Shadow
    hazard_classes = np.full(shape, config.CLASS_UNSAFE, dtype=np.uint8)
    
    # Create large safe plateau in quadrant 1 (rows 20-50, cols 20-50)
    hazard_classes[20:50, 20:50] = config.CLASS_SAFE
    # Create second safe plateau in quadrant 2 (rows 60:85, cols 60:85)
    hazard_classes[60:85, 60:85] = config.CLASS_SAFE
    
    dem = np.full(shape, -2500.0, dtype=np.float32)
    slope = np.full(shape, 2.0, dtype=np.float32)
    roughness = np.full(shape, 0.5, dtype=np.float32)
    psr = np.zeros(shape, dtype=np.uint8)
    # Place PSR near edge
    psr[80:95, 10:25] = 1

    transform = rasterio.transform.from_origin(0.0, 0.0, 20.0, 20.0)

    results = ml_recommender.recommend_landing_sites(
        hazard_classes=hazard_classes,
        dem_data=dem,
        slope_data=slope,
        roughness_data=roughness,
        psr_mask=psr,
        transform=transform,
        ellipse_radius_m=100.0,
        top_k=3,
        pixel_size_m=20.0
    )

    assert results["status"] == "SUCCESS"
    top_sites = results["top_sites"]
    assert len(top_sites) >= 2  # At least 2 distinct safe plateaus found
    
    primary = top_sites[0]
    assert primary["designation"] == "Alpha"
    assert primary["suitability_pct"] > 50.0
    assert primary["mean_slope_deg"] <= config.SLOPE_SAFE_MAX
    assert primary["status"] == "APPROVED FOR DESCENT"
    
    # Verify sites are spatially separated
    if len(top_sites) >= 2:
        secondary = top_sites[1]
        dist = np.hypot(primary["row"] - secondary["row"], primary["col"] - secondary["col"])
        assert dist >= 10.0  # Spatially separated by multiple ellipse radii

def test_mission_autonomy_artifacts(tmp_path):
    """Verify that full pipeline phase generates JSON and GeoTIFF outputs.

    Hermetic: autonomy artifacts are written into tmp_path (explicit paths are
    required because run_mission_autonomy binds its default output paths at
    import time), so the live outputs/ directory is never clobbered.
    """
    if not config.SYNTHETIC_DEM_PATH.exists():
        pytest.skip("Synthetic DEM not present, skipping integration test")

    out_json = tmp_path / "landing_sites.json"
    out_boulder = tmp_path / "boulder_hazard.tif"

    ml_recommender.run_mission_autonomy(
        output_json=out_json,
        output_boulder_tif=out_boulder,
    )
    assert out_json.exists()
    assert out_boulder.exists()

    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data.get("top_sites", [])) == 3
    assert data["top_sites"][0]["designation"] == "Alpha"
