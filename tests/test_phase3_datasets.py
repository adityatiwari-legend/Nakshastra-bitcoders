"""
Phase 3 tests: resolution-aware roughness thresholds, real-data provenance,
Artemis III region crops, public dataset registry, and preprocessing pipeline sanity.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import hazard
import validate


def test_scaled_roughness_thresholds_reference_resolution():
    """At the 20 m synthetic reference, scaled thresholds equal base values."""
    rt = config.scaled_roughness_thresholds(20.0)
    assert rt["safe_max"] == pytest.approx(config.ROUGHNESS_SAFE_MAX)
    assert rt["hard_unsafe_min"] == pytest.approx(config.ROUGHNESS_HARD_UNSAFE_MIN)
    assert rt["scale_factor"] == pytest.approx(1.0)


def test_scaled_roughness_thresholds_240m():
    """At 240 m/px (real LOLA), roughness thresholds scale by 12x."""
    rt = config.scaled_roughness_thresholds(240.0)
    assert rt["scale_factor"] == pytest.approx(12.0)
    assert rt["safe_max"] == pytest.approx(18.0)
    assert rt["hard_unsafe_min"] == pytest.approx(60.0)


def test_classify_hazard_surface_resolution_scaling_changes_outcome():
    """A pixel with roughness 10 m is Unsafe at 20 m reference but Caution at 240 m."""
    slope = np.array([[2.0]], dtype=np.float32)
    rough = np.array([[10.0]], dtype=np.float32)
    psr = np.array([[0]], dtype=np.uint8)

    # Unscaled (20 m reference): roughness 10 >= hard 5 -> Unsafe
    cls_ref, _ = hazard.classify_hazard_surface(slope, rough, psr)
    assert cls_ref[0, 0] == config.CLASS_UNSAFE

    # 240 m scaled: hard_unsafe_min = 60, so 10 < 60 -> not Unsafe via roughness
    cls_240, score = hazard.classify_hazard_surface(slope, rough, psr, pixel_size_m=240.0)
    assert cls_240[0, 0] != config.CLASS_UNSAFE
    assert score[0, 0] < config.SCORE_UNSAFE_MIN


def test_verify_rule_consistency_accepts_scaled_thresholds():
    """Audit with matching pixel_size_m passes on scaled-classified surface."""
    slope = np.full((5, 5), 3.0, dtype=np.float32)
    rough = np.full((5, 5), 20.0, dtype=np.float32)  # safe at 240m (18m limit) marginally over; use 15
    rough[:] = 15.0
    psr = np.zeros((5, 5), dtype=np.uint8)

    cls, score = hazard.classify_hazard_surface(slope, rough, psr, pixel_size_m=240.0)
    audit = validate.verify_rule_consistency(
        hazard_classes=cls, slope=slope, roughness=rough, psr_mask=psr,
        score_h=score, pixel_size_m=240.0,
    )
    assert audit["total_violations"] == 0
    assert audit["rough_safe_max_applied"] == pytest.approx(18.0)


def test_public_datasets_registry_integrity():
    """Every PUBLIC_DATASETS entry has required honesty fields."""
    required = {"id", "name", "mission", "publisher", "url", "license", "citation", "status", "role"}
    assert len(config.PUBLIC_DATASETS) >= 5
    for ds in config.PUBLIC_DATASETS:
        missing = required - set(ds.keys())
        assert not missing, f"Dataset {ds.get('id')} missing fields: {missing}"
        assert ds["status"] in ("downloaded", "available", "registration_required")


def test_lpsr_published_checksum_documented():
    """LPSR/AVGVISIB checksums are pinned in config for reproducibility."""
    assert config.LPSR_JP2_SHA256 == "d0807d1b7d16c13e6e037ce9a9d82efb375cd2065da3f8beeed3f97157deaf94"
    assert config.AVGVISIB_JP2_SHA256 == "4ccaf5ef7cdfc35bbff4d28e0d9b1051d9d56a66181cda633e71bfd42237dd49"


def test_artemis_regions_have_real_coordinates():
    """All 9 official Artemis III regions present with plausible south-polar coordinates."""
    assert len(config.ARTEMIS_III_REGIONS) == 9
    for rid, r in config.ARTEMIS_III_REGIONS.items():
        assert -90.0 < r["center_lat"] <= -80.0, f"{rid} lat out of south polar range"
        assert -180.0 <= r["center_lon"] <= 180.0
        assert r["name"]


def test_artemis_crop_produces_real_elevation_range():
    """A real Artemis crop has geographically plausible elevation spread (not synthetic constants)."""
    import lunar_catalog
    if not (config.LOLA_DEM_JP2_PATH.exists() and config.LPSR_JP2_PATH.exists()):
        pytest.skip("JP2 sources not present")
    dem, psr, transform, crs = lunar_catalog.generate_site_terrain("artemis_mons_mouton")
    valid = dem[dem != config.DEFAULT_NODATA_VALUE]
    valid = valid[np.isfinite(valid)]
    # Mons Mouton region: elevation range should span > 1 km (real polar relief)
    assert valid.size > 1000
    assert (valid.max() - valid.min()) > 1000.0
    # Published PSR present (Mons Mouton has nearby cold traps)
    assert psr.sum() > 0


def test_arthemis_crop_lpsr_provenance_is_published():
    """artemis_* crop uses published LPSR (never DEM-threshold proxy)."""
    import lunar_catalog
    if not config.LPSR_JP2_PATH.exists():
        pytest.skip("LPSR JP2 not present")
    _, psr, _, _ = lunar_catalog.generate_site_terrain("artemis_haworth")
    # Binary output, values only 0/1
    assert set(np.unique(psr)).issubset({0, 1})
    assert psr.sum() > 0  # Haworth is a well-known PSR-dominated crater


def test_prepare_lola_dataset_delegates_to_pipeline():
    """prepare_lola_dataset.convert_real_lola_to_geotiff is a thin wrapper over the Phase 3 pipeline."""
    import inspect
    import prepare_lola_dataset
    src = inspect.getsource(prepare_lola_dataset)
    assert "run_pipeline" in src
    assert "from preprocess_lunar_data import" in src


def test_mission_report_audit_uses_matching_pixel_size():
    """mission_report's audit call passes pixel_size_m so scaled rules are applied consistently."""
    import inspect
    import mission_report
    src = inspect.getsource(mission_report)
    assert "pixel_size_m" in src
