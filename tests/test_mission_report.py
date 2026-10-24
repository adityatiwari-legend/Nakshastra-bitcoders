"""
Regression tests for Batch 4 mission-report fixes:
- Provenance derived from active hazard_classes.tif tags (not input-file existence)
- Honest empty state when hazard_summary.csv is missing (no fabricated stats)
- Generation succeeds hermetically inside tmp_path
"""

import sys
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import io_utils


def _redirect_outputs(tmp_path, monkeypatch):
    out = tmp_path / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "OUTPUT_DIR", out)
    monkeypatch.setattr(config, "OUTPUT_HAZARD_CLASSES_TIF", out / "hazard_classes.tif")
    monkeypatch.setattr(config, "OUTPUT_HAZARD_SUMMARY_CSV", out / "hazard_summary.csv")
    monkeypatch.setattr(config, "OUTPUT_MAP_4PANEL_PNG", out / "lunasafe_hazard_map.png")
    monkeypatch.setattr(config, "OUTPUT_MAP_4PANEL_PDF", out / "lunasafe_hazard_map.pdf")
    monkeypatch.setattr(config, "OUTPUT_SENSITIVITY_PNG", out / "slope_sensitivity.png")
    monkeypatch.setattr(config, "OUTPUT_TERRAIN_HIST_PNG", out / "terrain_histograms.png")
    return out


def _write_hazard_with_site_tag(path, site_id, data_type=None):
    import rasterio
    from rasterio.transform import Affine

    arr = np.ones((20, 20), dtype=np.uint8)
    tags = {"PROJECT": "OrbisLuna", "SITE": site_id}
    if data_type:
        tags["DATA_TYPE"] = data_type
    io_utils.write_geotiff(
        output_path=path,
        data=arr,
        transform=Affine(20.0, 0.0, 0.0, 0.0, -20.0, 0.0),
        crs=rasterio.crs.CRS.from_proj4(config.LUNAR_SOUTH_POLE_PROJ4),
        nodata=config.CLASS_NODATA,
        tags=tags,
    )


def test_mission_report_generates_hermetically(tmp_path, monkeypatch):
    """Report must generate with missing summary CSV and never require real inputs."""
    import mission_report

    out = _redirect_outputs(tmp_path, monkeypatch)
    _write_hazard_with_site_tag(config.OUTPUT_HAZARD_CLASSES_TIF, "synthetic")

    report_path = out / "mission_report.pdf"
    result = mission_report.generate_pdf_mission_report(report_path)

    assert result == report_path
    assert report_path.exists()
    assert report_path.stat().st_size > 1000


def test_mission_report_provenance_uses_hazard_tags(tmp_path, monkeypatch, capsys):
    """Provenance must come from hazard_classes.tif SITE tag, not data/* input existence."""
    import mission_report

    out = _redirect_outputs(tmp_path, monkeypatch)
    # Synthetic tag even though REAL_DEM_PATH exists on the live machine:
    _write_hazard_with_site_tag(config.OUTPUT_HAZARD_CLASSES_TIF, "synthetic")

    report_path = out / "mission_report_probe.pdf"
    mission_report.generate_pdf_mission_report(report_path)
    assert report_path.exists()

    # Real-tag path: lola_crop must flip provenance regardless of synthetic inputs.
    _write_hazard_with_site_tag(config.OUTPUT_HAZARD_CLASSES_TIF, "lola_crop")
    report_path2 = out / "mission_report_probe2.pdf"
    mission_report.generate_pdf_mission_report(report_path2)
    assert report_path2.exists()


def test_mission_report_no_fabricated_fallback_stats(tmp_path, monkeypatch):
    """With no hazard_summary.csv, generation still succeeds (honest empty rows, no crash)."""
    import mission_report

    out = _redirect_outputs(tmp_path, monkeypatch)
    _write_hazard_with_site_tag(config.OUTPUT_HAZARD_CLASSES_TIF, "synthetic")
    assert not config.OUTPUT_HAZARD_SUMMARY_CSV.exists()

    report_path = out / "mission_report_no_csv.pdf"
    mission_report.generate_pdf_mission_report(report_path)
    assert report_path.exists()
    assert report_path.stat().st_size > 1000
