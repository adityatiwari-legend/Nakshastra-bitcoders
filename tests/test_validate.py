"""
Unit and integration tests for Phase 6: Validation, rule-consistency audit,
and slope-threshold sensitivity analysis.
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
import validate


def test_compute_psr_metrics_exactness():
    """Verify exact mathematical calculation of Precision, Recall, and IoU."""
    # 10x10 grid (100 pixels)
    cand = np.zeros((10, 10), dtype=np.uint8)
    ref = np.zeros((10, 10), dtype=np.uint8)
    
    # TP: pixels (0 to 4, 0 to 4) = 25 pixels
    cand[0:5, 0:5] = 1
    ref[0:5, 0:5] = 1
    
    # FP: candidate has 5 extra pixels
    cand[5, 0:5] = 1
    
    # FN: reference has 10 extra pixels
    ref[6:8, 0:5] = 1
    
    # TP = 25, FP = 5, FN = 10
    # Precision = 25 / (25 + 5) = 25 / 30 = 0.8333
    # Recall = 25 / (25 + 10) = 25 / 35 = 0.7143
    # IoU = 25 / (25 + 5 + 10) = 25 / 40 = 0.6250
    metrics = validate.compute_psr_metrics(cand, ref, reference_name="Synthetic Reference Test")
    
    assert metrics["true_positives"] == 25
    assert metrics["false_positives"] == 5
    assert metrics["false_negatives"] == 10
    assert metrics["precision"] == pytest.approx(25.0 / 30.0, rel=1e-3)
    assert metrics["recall"] == pytest.approx(25.0 / 35.0, rel=1e-3)
    assert metrics["iou"] == pytest.approx(0.625, rel=1e-3)
    assert "provenance_note" in metrics


def test_verify_rule_consistency_passes_on_pipeline_output():
    """Verify that LunaSafe generated hazard raster exhibits ZERO rule violations."""
    slope_info = io_utils.read_geotiff(config.OUTPUT_SLOPE_TIF)
    slope = slope_info["data"]
    roughness = io_utils.read_geotiff(config.OUTPUT_ROUGHNESS_STD_TIF)["data"]
    psr_mask = io_utils.read_geotiff(config.OUTPUT_PSR_BINARY_TIF)["data"]
    hazard_classes = io_utils.read_geotiff(config.OUTPUT_HAZARD_CLASSES_TIF)["data"]
    
    px = float(abs(slope_info.get("pixel_size_x", 20.0)))
    audit = validate.verify_rule_consistency(
        hazard_classes=hazard_classes,
        slope=slope,
        roughness=roughness,
        psr_mask=psr_mask,
        nodata_val=config.DEFAULT_NODATA_VALUE,
        pixel_size_m=px,
    )
    
    assert audit["is_consistent"] is True
    assert audit["total_violations"] == 0
    for rule, count in audit["detailed_violations"].items():
        assert count == 0, f"Violation detected in {rule}: {count}"


def test_verify_rule_consistency_catches_deliberate_errors():
    """Verify that the auditor catches violations if rogue classifications are injected."""
    hazard_classes = io_utils.read_geotiff(config.OUTPUT_HAZARD_CLASSES_TIF)["data"].copy()
    slope_info = io_utils.read_geotiff(config.OUTPUT_SLOPE_TIF)
    slope = slope_info["data"]
    roughness = io_utils.read_geotiff(config.OUTPUT_ROUGHNESS_STD_TIF)["data"]
    psr_mask = io_utils.read_geotiff(config.OUTPUT_PSR_BINARY_TIF)["data"]
    
    # Deliberate violation 1: Mark a steep pixel (slope > 20 deg) as Safe (Class 1)
    steep_idx = np.where(slope > 20.0)
    if len(steep_idx[0]) > 0:
        r, c = steep_idx[0][0], steep_idx[1][0]
        hazard_classes[r, c] = config.CLASS_SAFE
        
    # Deliberate violation 2: Mark a NoData border pixel as Safe (Class 1)
    nodata_idx = np.where(slope == config.DEFAULT_NODATA_VALUE)
    if len(nodata_idx[0]) > 0:
        nr, nc = nodata_idx[0][0], nodata_idx[1][0]
        hazard_classes[nr, nc] = config.CLASS_SAFE
        
    px = float(abs(slope_info.get("pixel_size_x", 20.0)))
    audit = validate.verify_rule_consistency(
        hazard_classes=hazard_classes,
        slope=slope,
        roughness=roughness,
        psr_mask=psr_mask,
        nodata_val=config.DEFAULT_NODATA_VALUE,
        pixel_size_m=px,
    )
    
    assert audit["is_consistent"] is False
    assert audit["total_violations"] >= 2


def test_slope_sensitivity_analysis_execution(tmp_path):
    """Verify slope sensitivity test computes monotonicity and creates chart."""
    dem = io_utils.read_geotiff(config.SYNTHETIC_DEM_PATH)["data"]
    dem_meta = io_utils.inspect_raster(config.SYNTHETIC_DEM_PATH, verbose=False)
    slope = io_utils.read_geotiff(config.OUTPUT_SLOPE_TIF)["data"]
    roughness = io_utils.read_geotiff(config.OUTPUT_ROUGHNESS_STD_TIF)["data"]
    psr_mask = io_utils.read_geotiff(config.OUTPUT_PSR_BINARY_TIF)["data"]
    
    out_chart = tmp_path / "test_sensitivity.png"
    
    df, chart_path = validate.run_slope_sensitivity_analysis(
        dem=dem,
        slope=slope,
        roughness=roughness,
        psr_mask=psr_mask,
        dem_meta=dem_meta,
        output_png=out_chart,
        is_synthetic=True,
        verbose=False,
    )
    
    assert chart_path.exists()
    assert chart_path.stat().st_size > 50_000
    assert len(df) == 5
    
    # Safe area must increase monotonically as slope threshold is relaxed from 3 to 15 deg
    safe_areas = df["Safe_km2"].values
    for i in range(len(safe_areas) - 1):
        assert safe_areas[i] <= safe_areas[i + 1]
