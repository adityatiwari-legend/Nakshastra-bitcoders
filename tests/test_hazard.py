"""
Unit and integration tests for Phase 4: Hazard classification
(scoring, hard overrides, class assignments, and summary table).
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import io_utils
import hazard


def test_hazard_score_formula_and_normalization():
    """Verify H = 0.50*S + 0.30*R + 0.20*D with clipping."""
    # S = 7.5 / 15 = 0.50
    # R = 2.5 / 5 = 0.50
    # D = 0.0 (binary default)
    # H = 0.50*(0.50) + 0.30*(0.50) + 0.20*(0.0) = 0.25 + 0.15 = 0.40
    slope = np.array([[7.5]], dtype=np.float32)
    roughness = np.array([[2.5]], dtype=np.float32)
    
    score = hazard.compute_hazard_score(slope=slope, roughness=roughness)
    assert score[0, 0] == pytest.approx(0.40, rel=1e-3)


def test_hard_overrides_trigger_class_3_unsafe():
    """Verify that slope >= 15 deg or roughness >= 5 m triggers Unsafe regardless of score."""
    # Case A: Slope = 16 deg, roughness = 0.0, D = 0.
    # Score H = 0.50*(1.0) = 0.50 (< 0.60), but slope >= 15 hard override applies!
    slope_a = np.array([[16.0]], dtype=np.float32)
    rough_a = np.array([[0.2]], dtype=np.float32)
    psr_a = np.array([[0]], dtype=np.uint8)
    
    classes_a, _ = hazard.classify_hazard_surface(slope=slope_a, roughness=rough_a, psr_mask=psr_a)
    assert classes_a[0, 0] == config.CLASS_UNSAFE

    # Case B: Roughness = 5.5 m, slope = 1.0 deg.
    # Score H = 0.50*(1/15) + 0.30*(1.0) = 0.033 + 0.30 = 0.333 (< 0.60), but roughness >= 5 hard override applies!
    slope_b = np.array([[1.0]], dtype=np.float32)
    rough_b = np.array([[5.5]], dtype=np.float32)
    psr_b = np.array([[0]], dtype=np.uint8)
    
    classes_b, _ = hazard.classify_hazard_surface(slope=slope_b, roughness=rough_b, psr_mask=psr_b)
    assert classes_b[0, 0] == config.CLASS_UNSAFE


def test_shadowed_unknown_vs_unsafe_psr():
    """Verify PSR rule: Class 4 for PSR pixels not already Unsafe; Class 3 for steep/rough PSR pixels."""
    # Pixel 1: Flat PSR crater floor (slope 2.0, rough 0.5, psr 1) -> Class 4 (Shadowed-Unknown)
    # Pixel 2: Steep PSR crater wall (slope 22.0, rough 3.0, psr 1) -> Class 3 (Unsafe)
    slope = np.array([[2.0, 22.0]], dtype=np.float32)
    roughness = np.array([[0.5, 3.0]], dtype=np.float32)
    psr_mask = np.array([[1, 1]], dtype=np.uint8)
    
    classes, _ = hazard.classify_hazard_surface(slope=slope, roughness=roughness, psr_mask=psr_mask)
    assert classes[0, 0] == config.CLASS_SHADOWED_UNKNOWN
    assert classes[0, 1] == config.CLASS_UNSAFE


def test_safe_and_caution_classification():
    """Verify Class 1 Safe (H<0.25, slope<5, rough<1.5) and Class 2 Caution (0.25<=H<0.60)."""
    # Pixel 1: Slope 2.0, rough 0.5 -> H = 0.5*(2/15) + 0.3*(0.5/5) = 0.067 + 0.03 = 0.097 -> Safe
    # Pixel 2: Slope 7.0, rough 1.0 -> H = 0.5*(7/15) + 0.3*(1.0/5) = 0.233 + 0.06 = 0.293 -> Caution
    # Pixel 3: Slope 4.0, rough 2.0 -> slope < 5, but rough >= 1.5 -> Caution
    slope = np.array([[2.0, 7.0, 4.0]], dtype=np.float32)
    roughness = np.array([[0.5, 1.0, 2.0]], dtype=np.float32)
    psr_mask = np.array([[0, 0, 0]], dtype=np.uint8)
    
    classes, _ = hazard.classify_hazard_surface(slope=slope, roughness=roughness, psr_mask=psr_mask)
    assert classes[0, 0] == config.CLASS_SAFE
    assert classes[0, 1] == config.CLASS_CAUTION
    assert classes[0, 2] == config.CLASS_CAUTION


def test_nodata_is_never_treated_as_safe():
    """Verify that NoData pixels strictly result in Class 0 (NoData)."""
    slope = np.array([[config.DEFAULT_NODATA_VALUE, 2.0]], dtype=np.float32)
    roughness = np.array([[config.DEFAULT_NODATA_VALUE, config.DEFAULT_NODATA_VALUE]], dtype=np.float32)
    psr_mask = np.array([[0, 0]], dtype=np.uint8)
    
    classes, _ = hazard.classify_hazard_surface(slope=slope, roughness=roughness, psr_mask=psr_mask)
    assert classes[0, 0] == config.CLASS_NODATA
    assert classes[0, 1] == config.CLASS_NODATA


def test_process_hazard_pipeline_end_to_end(tmp_path):
    """Verify end-to-end hazard classification execution, GeoTIFF, and summary CSV."""
    # Load synthetic dataset and compute terrain
    dem_path = config.SYNTHETIC_DEM_PATH
    if not dem_path.exists():
        io_utils.create_and_save_synthetic_dataset()
    dem_meta = io_utils.inspect_raster(dem_path, verbose=False)
    
    # Load aligned PSR
    psr_meta = io_utils.inspect_raster(config.SYNTHETIC_PSR_PATH, verbose=False)
    
    # Compute matching slope and roughness for synthetic DEM
    import terrain
    slope, _, _ = terrain.calculate_slope_and_aspect(
        dem_meta["data"],
        pixel_size_x=dem_meta["pixel_size_x"],
        pixel_size_y=dem_meta["pixel_size_y"],
    )
    roughness = terrain.calculate_roughness_std(dem_meta["data"])
    
    out_tif = tmp_path / "hazard_test.tif"
    out_csv = tmp_path / "hazard_test.csv"
    
    hazard_classes, score_h, df_summary = hazard.process_hazard_pipeline(
        slope=slope,
        roughness=roughness,
        psr_mask=psr_meta["data"],
        dem_meta=dem_meta,
        output_tif=out_tif,
        output_csv=out_csv,
        is_synthetic=True,
        verbose=False,
    )
    
    assert out_tif.exists()
    assert out_csv.exists()
    
    # Verify classes in raster
    unique_classes = set(np.unique(hazard_classes))
    # All non-empty classes must be valid 0, 1, 2, 3, 4
    for c in unique_classes:
        assert c in [config.CLASS_NODATA, config.CLASS_SAFE, config.CLASS_CAUTION, config.CLASS_UNSAFE, config.CLASS_SHADOWED_UNKNOWN]
        
    # Check CSV content
    df_read = pd.read_csv(out_csv)
    assert len(df_read) == 5
    assert "class_name" in df_read.columns
    assert "area_km2" in df_read.columns
    assert df_read["pixel_count"].sum() == hazard_classes.size


# ---------------------------------------------------------------------------
# Phase 5E: known-grid exact classification (hand-computed reference map)
# ---------------------------------------------------------------------------

def test_known_grid_exact_class_map():
    """A 4x4 hand-computed grid must classify to the exact expected map.

    Every cell exercises one rule path (safe, caution, hard-slope, hard-rough,
    score-based unsafe, shadow, shadow-loses-to-unsafe, nodata via slope,
    nodata via roughness). Thresholds: SLOPE_SAFE_MAX=5, ROUGHNESS_SAFE_MAX=1.5,
    SLOPE_HARD_UNSAFE_MIN=15, ROUGHNESS_HARD_UNSAFE_MIN=5, SCORE_SAFE_MAX=0.25,
    SCORE_UNSAFE_MIN=0.60, weights 0.50/0.30/0.20 with D=0 (no shadow fraction).
    """
    slope = np.array([
        [1.0,      16.0,   7.0,   1.0],
        [-9999.0,  1.0,    2.0,  16.0],
        [9.0,      0.5,    3.0,  15.0],
        [4.0,     10.0,    1.0,  14.0],
    ], dtype=np.float32)
    rough = np.array([
        [0.2,    0.2,   0.5,   0.2],
        [0.2,    6.0,   0.3,   0.2],
        [0.4,    0.1,   1.0,   0.2],
        [1.0,    0.5,   -9999.0, 4.5],
    ], dtype=np.float32)
    psr = np.array([
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 1, 0],
        [0, 0, 0, 0],
    ], dtype=np.uint8)

    expected = np.array([
        [1, 3, 2, 4],   # safe | hard-slope | caution | shadow
        [0, 3, 1, 3],   # nodata(slope) | hard-rough | safe | shadow loses to hard-slope
        [2, 1, 4, 3],   # caution | safe | shadow | hard at exactly 15 deg
        [1, 2, 0, 3],   # safe | caution | nodata(rough) | score-based unsafe (H=0.737)
    ], dtype=np.uint8)

    classes, score = hazard.classify_hazard_surface(slope, rough, psr)
    assert classes.tolist() == expected.tolist()
    # Hand-computed H for (slope=1, rough=0.2): 0.5*(1/15) + 0.3*(0.2/5) = 0.04533
    assert score[0, 0] == pytest.approx(0.04533, rel=1e-3)
    # Hand-computed H for (slope=14, rough=4.5): 0.5*(14/15) + 0.3*(4.5/5) = 0.73667 >= 0.60
    assert score[3, 3] == pytest.approx(0.73667, rel=1e-3)
    # All five classes present in the reference grid
    assert set(np.unique(classes).tolist()) == {0, 1, 2, 3, 4}
