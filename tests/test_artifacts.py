"""Regression tests for Artifact Hub manifest + save-route (Phase 2)."""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import web_server


def _redirect_outputs(tmp_path, monkeypatch):
    out = tmp_path / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "OUTPUT_DIR", out)
    monkeypatch.setattr(config, "OUTPUT_HAZARD_CLASSES_TIF", out / "hazard_classes.tif")
    monkeypatch.setattr(web_server, "ARTIFACT_SAVED_ROUTES_DIR", out / "saved_routes")
    return out


def test_manifest_scans_outputs_and_skips_internals(tmp_path, monkeypatch):
    out = _redirect_outputs(tmp_path, monkeypatch)
    (out / "hazard_summary.csv").write_text("class_id,pixel_count\n1,10\n", encoding="utf-8")
    (out / "lunasafe_hazard_map.png").write_bytes(b"\x89PNG\r\n\x1a\n fake")
    (out / "web_data.json").write_text("{}", encoding="utf-8")   # must be skipped
    (out / "active_site_dem.tif").write_bytes(b"II*\x00")          # must be skipped
    (out / "psr_polygons.prj").write_text("PROJ", encoding="utf-8")  # sidecar, skipped
    (out / "custom_thing.tif").write_bytes(b"II*\x00")            # uncatalogued -> raster

    manifest = web_server.build_artifacts_manifest()

    assert manifest["status"] == "SUCCESS"
    ids = {a["id"] for a in manifest["artifacts"]}
    assert "hazard_summary.csv" in ids
    assert "lunasafe_hazard_map.png" in ids
    assert "custom_thing.tif" in ids
    assert "web_data.json" not in ids
    assert "active_site_dem.tif" not in ids
    assert "psr_polygons.prj" not in ids

    png = next(a for a in manifest["artifacts"] if a["id"] == "lunasafe_hazard_map.png")
    assert png["type"] == "map"
    assert png["thumbnail_url"] == "/outputs/lunasafe_hazard_map.png"
    assert png["preview_kind"] == "image"
    assert png["title"] == "4-Panel Hazard Publication Map"
    assert png["tags"]

    tif = next(a for a in manifest["artifacts"] if a["id"] == "custom_thing.tif")
    assert tif["type"] == "raster"
    assert tif["preview_kind"] == "info"

    csv = next(a for a in manifest["artifacts"] if a["id"] == "hazard_summary.csv")
    assert csv["preview_kind"] == "csv"
    assert csv["size_bytes"] > 0
    assert csv["date"]

    # manifest persisted to disk
    assert (out / "artifacts.json").exists()
    saved = json.loads((out / "artifacts.json").read_text(encoding="utf-8"))
    assert saved["count"] == manifest["count"]


def test_manifest_includes_saved_routes_with_hub_metadata(tmp_path, monkeypatch):
    out = _redirect_outputs(tmp_path, monkeypatch)
    sr = out / "saved_routes"
    sr.mkdir()
    route = {
        "status": "SUCCESS",
        "waypoints": [{"index": 0, "row": 1, "col": 1}],
        "_hub": {
            "title": "My Custom Traverse",
            "dataset": "lola_crop",
            "date": "2026-10-22T00:00:00",
            "tags": ["rover", "custom"],
        },
    }
    (sr / "route_test_20261022.json").write_text(json.dumps(route), encoding="utf-8")

    manifest = web_server.build_artifacts_manifest()
    entry = next(a for a in manifest["artifacts"] if a["id"] == "saved_routes/route_test_20261022.json")
    assert entry["type"] == "route"
    assert entry["saved"] is True
    assert entry["title"] == "My Custom Traverse"
    assert entry["dataset"] == "lola_crop"
    assert "custom" in entry["tags"]


def test_artifact_entry_rejects_sidecars_and_bad_extensions(tmp_path, monkeypatch):
    out = _redirect_outputs(tmp_path, monkeypatch)
    for name in ("x.dbf", "x.shx", "x.aux.xml", "x.ovr"):
        (out / name).write_text("x", encoding="utf-8")
    manifest = web_server.build_artifacts_manifest()
    assert manifest["count"] == 0
