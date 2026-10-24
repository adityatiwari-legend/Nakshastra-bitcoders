"""
End-to-end integration test for main.py execution.

Hermetic: all pipeline outputs are redirected into a pytest tmp directory so the
test never clobbers the live outputs/ directory used by the running web server.
"""

import sys
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import main
import config


_OUTPUT_ATTRS = [a for a in dir(config) if a.startswith("OUTPUT_")]


@pytest.fixture()
def isolated_outputs(tmp_path, monkeypatch):
    """Redirects every config.OUTPUT_* path (and OUTPUT_DIR) into tmp_path."""
    for attr in _OUTPUT_ATTRS:
        monkeypatch.setattr(config, attr, tmp_path / getattr(config, attr).name)
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)
    yield tmp_path


def test_main_pipeline_execution(isolated_outputs):
    """Verify that running main.run_pipeline end-to-end exits cleanly with code 0."""
    exit_code = main.run_pipeline(
        force_synthetic=True,
        verbose=False,
    )
    assert exit_code == 0

    # Assert all primary deliverables exist in the isolated output directory
    assert config.OUTPUT_PSR_BINARY_TIF.exists()
    assert config.OUTPUT_PSR_POLYGONS_GEOJSON.exists()
    assert config.OUTPUT_PSR_POLYGONS_SHP.exists()
    assert config.OUTPUT_SLOPE_TIF.exists()
    assert config.OUTPUT_ASPECT_TIF.exists()
    assert config.OUTPUT_ROUGHNESS_STD_TIF.exists()
    assert config.OUTPUT_ROUGHNESS_TRI_TIF.exists()
    assert config.OUTPUT_TERRAIN_HIST_PNG.exists()
    assert config.OUTPUT_HAZARD_CLASSES_TIF.exists()
    assert config.OUTPUT_HAZARD_SUMMARY_CSV.exists()
    assert config.OUTPUT_MAP_4PANEL_PNG.exists()
    assert config.OUTPUT_MAP_4PANEL_PDF.exists()
    assert config.OUTPUT_SENSITIVITY_PNG.exists()
    # The web bundle must also be exported into the isolated directory only
    assert (isolated_outputs / "web_data.json").exists()
