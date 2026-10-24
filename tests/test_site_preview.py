"""
Unit tests for the 3D Lunar Site Preview API (/api/site-preview)
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import web_server


class DummyHandler(web_server.LunaSafeHandler):
    """Subclass of LunaSafeHandler for isolated in-memory unit testing."""
    def __init__(self):
        self.sent_json = None
        self.sent_error = None
        self._site_preview_cache = {}

    def send_json(self, data, status=200):
        self.sent_json = data
        self.sent_status = status

    def send_error(self, code, message=None):
        self.sent_error = (code, message)


def test_site_preview_shackleton():
    handler = DummyHandler()
    handler.handle_api_site_preview({"site_id": ["shackleton"]})
    assert handler.sent_error is None
    assert handler.sent_json is not None
    res = handler.sent_json
    assert res["status"] == "SUCCESS"
    assert res["site_id"] == "shackleton"
    assert "Shackleton" in res["name"]
    assert res["grid_w"] > 0
    assert res["grid_h"] > 0
    assert len(res["dem"]) == res["grid_h"]
    assert res["max_elev"] > res["min_elev"]
    assert res["relief_m"] > 0


def test_site_preview_artemis_haworth():
    handler = DummyHandler()
    handler.handle_api_site_preview({"site_id": ["artemis_haworth"]})
    assert handler.sent_error is None
    assert handler.sent_json is not None
    res = handler.sent_json
    assert res["status"] == "SUCCESS"
    assert "Haworth" in res["name"]
    assert res["center_lat"] < -80.0
    assert len(res["dem"]) > 0


def test_site_preview_caching():
    handler = DummyHandler()
    handler.handle_api_site_preview({"site_id": ["malapert"]})
    assert "malapert" in handler._site_preview_cache
    first_res = handler.sent_json

    # Second call should return from cache
    handler.sent_json = None
    handler.handle_api_site_preview({"site_id": ["malapert"]})
    assert handler.sent_json == first_res
