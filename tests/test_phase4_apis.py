"""
Phase 4 tests: analytic illumination-time model + new API endpoints
(/api/regions, /api/tiles/*, /api/illumination-time[.bin]).

Honesty requirements under test: the illumination-time product must always be
labeled as an ANALYTIC MODEL (never as observed/derived time-series data), and
night frames must be all-dark.
"""

import json
import re
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import export_web_data
import illumination_time as it
import web_server


# ---------------------------------------------------------------------------
# Analytic solar-position model
# ---------------------------------------------------------------------------

def test_solar_noon_south_polar_points_north():
    """At local noon near the south pole the subsolar point lies north of the observer."""
    elev, az = it.solar_elevation_azimuth_deg(-85.0, 0.0)
    assert elev > 0.0
    assert az < 10.0 or az > 350.0  # azimuth ~0 deg (north)


def test_solar_morning_east_evening_west():
    _, az_morning = it.solar_elevation_azimuth_deg(-85.0, -90.0)
    _, az_evening = it.solar_elevation_azimuth_deg(-85.0, 90.0)
    assert 80.0 <= az_morning <= 100.0   # east
    assert 260.0 <= az_evening <= 280.0  # west


def test_solar_night_elevation_negative():
    elev_midnight, _ = it.solar_elevation_azimuth_deg(-85.0, 180.0)
    assert elev_midnight < 0.0


def test_frame_schedule_spans_lunar_day():
    sched = it.frame_schedule(24)
    assert len(sched["hours"]) == 24
    assert sched["hours"][0] == 0.0
    assert max(sched["sun_elevation_deg"]) > 0.0
    assert min(sched["sun_elevation_deg"]) < 0.0


# ---------------------------------------------------------------------------
# Frame computation
# ---------------------------------------------------------------------------

def _ridge_dem(size=64, ridge_m=500.0):
    """Flat DEM with a north-edge ridge: shadows should form when the sun is low south."""
    dem = np.zeros((size, size), dtype=np.float32)
    dem[0, :] = ridge_m
    return dem


def test_compute_frames_shape_dtype_and_night_all_dark():
    vol, meta = it.compute_frames(_ridge_dem(), 240.0, -85.0, frames=24)
    assert vol.shape == (24, 64, 64)
    assert vol.dtype == np.uint8
    night = [i for i, e in enumerate(meta["sun_elevation_deg"]) if e <= 0.0]
    assert night, "model must include night frames at south-polar latitudes"
    for i in night:
        assert vol[i].sum() == 0, f"night frame {i} must be fully dark"


def test_compute_frames_deterministic_and_daytime_varies():
    dem = _ridge_dem()
    vol_a, meta_a = it.compute_frames(dem, 240.0, -85.0, frames=24)
    vol_b, _ = it.compute_frames(dem, 240.0, -85.0, frames=24)
    assert np.array_equal(vol_a, vol_b)
    day = [i for i, e in enumerate(meta_a["sun_elevation_deg"]) if e > 2.0]
    assert len(day) >= 4
    distinct = {vol_a[i].tobytes() for i in day}
    assert len(distinct) > 1, "daytime frames must differ as the sun moves"


def test_compute_frames_nodata_stays_dark():
    dem = np.full((32, 32), 100.0, dtype=np.float32)
    dem[0, 0] = config.DEFAULT_NODATA_VALUE
    vol, _ = it.compute_frames(dem, 240.0, -85.0, frames=24,
                               nodata=config.DEFAULT_NODATA_VALUE)
    assert vol[:, 0, 0].sum() == 0


def test_compute_frames_psr_mask_stays_dark():
    dem = np.full((32, 32), 100.0, dtype=np.float32)
    psr = np.zeros((32, 32), dtype=np.uint8)
    psr[10:20, 10:20] = 1  # 10x10 PSR patch
    vol, meta = it.compute_frames(dem, 240.0, -85.0, frames=24, psr_mask=psr)
    assert meta["psr_constrained"] is True
    # In all frames (day and night), the PSR patch must be strictly 0 (shadow)
    assert vol[:, 10:20, 10:20].sum() == 0
    # But non-PSR flat terrain should be lit during high-sun daytime frames
    day = [i for i, e in enumerate(meta["sun_elevation_deg"]) if e > 2.0]
    assert day
    for i in day:
        assert vol[i, 0:5, 0:5].sum() > 0


def test_compute_frames_meta_is_labeled_analytic_model():
    _, meta = it.compute_frames(_ridge_dem(), 240.0, -85.0, frames=8)
    assert meta["kind"] == "analytic_model_not_observed"
    assert "model" in meta["label"].lower()
    assert "LPSR" in meta["disclaimer"]  # published product stays authoritative
    assert meta["dtype"] == "uint8"
    assert meta["frames"] == 8
    assert len(meta["hours"]) == 8


def test_cache_key_depends_on_dataset_shape_lat_pixel(monkeypatch):
    k1 = it._cache_key("a", 24, (250, 250), -89.0, 240.0)
    assert k1 != it._cache_key("b", 24, (250, 250), -89.0, 240.0)
    assert k1 != it._cache_key("a", 24, (251, 250), -89.0, 240.0)
    assert k1 != it._cache_key("a", 24, (250, 250), -85.0, 240.0)
    assert k1 != it._cache_key("a", 24, (250, 250), -89.0, 20.0)
    assert k1 == it._cache_key("a", 24, (250, 250), -89.0, 240.0)


def test_compute_or_get_cache_hit(tmp_path):
    dem = _ridge_dem()
    _, meta1 = it.compute_or_get(dem, 240.0, -85.0, "unit", frames=8,
                                 cache_dir=tmp_path)
    bin2, meta2 = it.compute_or_get(dem, 240.0, -85.0, "unit", frames=8,
                                    cache_dir=tmp_path)
    assert meta1["cache_hit"] is False
    assert meta2["cache_hit"] is True
    vol = it.load_volume(bin2, meta2)
    assert vol.shape == (8, 64, 64)


# ---------------------------------------------------------------------------
# Live endpoint tests (ephemeral port)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def server():
    httpd = ThreadingHTTPServer(("", 0), web_server.OrbisLunaHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def _get(url, expect_binary=False, timeout=60):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read()
            code = resp.status
    except urllib.error.HTTPError as e:
        body = e.read()
        code = e.code
    if expect_binary or (code == 200 and b"status" not in body[:64] and b"{" not in body[:8]):
        return code, body
    return code, json.loads(body.decode("utf-8"))


def test_regions_endpoint(server):
    code, data = _get(f"{server}/api/regions")
    assert code == 200
    assert data["status"] == "SUCCESS"
    regions = data["regions"]
    assert len(regions) == len(config.ARTEMIS_III_REGIONS) == 9
    for r in regions:
        assert r["is_real_data"] is True
        assert -90.0 < r["center_lat"] <= -80.0
        assert "Wueller" in data["source"] or "Table A1" in data["source"]
    geojson_path = ROOT_DIR / data["geojson_url"].lstrip("/")
    assert geojson_path.exists()


def test_tiles_meta_and_binary(server):
    code, meta = _get(f"{server}/api/tiles/hazard/meta.json")
    assert code == 200
    assert meta["dtype"] == "float32"
    assert "tileSize" in meta and meta["tileSize"] == 256
    assert "maxZ" in meta
    n_tiles = meta["tiles_x"] * meta["tiles_y"]
    assert n_tiles >= 1

    # Also test /api/tiles/<layer>/meta without .json
    code_raw_meta, meta_raw = _get(f"{server}/api/tiles/hazard/meta")
    assert code_raw_meta == 200
    assert meta_raw["tileSize"] == 256
    assert "maxZ" in meta_raw
    assert "width" in meta_raw
    assert "height" in meta_raw

    code, blob = _get(f"{server}/api/tiles/hazard/0/0/0", expect_binary=True)
    assert code == 200
    assert len(blob) == 256 * 256 * 4
    arr = np.frombuffer(blob, dtype=np.float32)
    assert arr.min() >= 0.0  # hazard class codes 0..4, NoData never Safe


def test_tiles_reject_unknown_layer_and_bad_coords(server):
    # Unknown layer must return 400
    code, data = _get(f"{server}/api/tiles/nope/0/0/0")
    assert code == 400
    code, data = _get(f"{server}/api/tiles/unknown_layer/meta")
    assert code == 400

    # Non-integer coordinates must return 400
    code, data = _get(f"{server}/api/tiles/hazard/0/x/0")
    assert code == 400

    # Malformed URL must return 404
    code, data = _get(f"{server}/api/tiles/hazard")
    assert code == 404

    # Out-of-range z/x/y must return 404
    code, data = _get(f"{server}/api/tiles/hazard/0/99/0")
    assert code == 404
    code, data = _get(f"{server}/api/tiles/hazard/99/0/0")
    assert code == 404



def test_illumination_time_meta_endpoint(server):
    code, meta = _get(f"{server}/api/illumination-time?frames=8", timeout=120)
    assert code == 200
    assert meta["status"] == "SUCCESS"
    assert meta["frames"] == 8
    assert meta["kind"] == "analytic_model_not_observed"
    assert "LPSR" in meta["disclaimer"]
    assert len(meta["hours"]) == 8
    assert meta["width"] > 0 and meta["height"] > 0
    assert meta["bin_url"].endswith("frames=8")

    # Second call must come from cache
    code, meta2 = _get(f"{server}/api/illumination-time?frames=8", timeout=120)
    assert code == 200
    assert meta2["cache_hit"] is True


def test_illumination_time_binary_frames(server):
    code, meta = _get(f"{server}/api/illumination-time?frames=8", timeout=120)
    assert code == 200
    code, blob = _get(f"{server}/api/illumination-time.bin?frames=8", expect_binary=True,
                      timeout=120)
    assert code == 200
    expected = meta["frames"] * meta["width"] * meta["height"]
    assert len(blob) == expected
    vol = np.frombuffer(blob, dtype=np.uint8).reshape(
        meta["frames"], meta["height"], meta["width"])
    # Every night frame all dark; at least one day frame partially lit
    night = [i for i, e in enumerate(meta["sun_elevation_deg"]) if e <= 0.0]
    for i in night:
        assert vol[i].sum() == 0
    day_lit = [i for i, e in enumerate(meta["sun_elevation_deg"]) if e > 0.0]
    assert day_lit, "model must include sun-above-horizon frames"
    assert any(vol[i].sum() > 0 for i in day_lit)
    psr = web_server.RASTER_CACHE.get("psr")
    if psr is not None and (psr > 0).any():
        for i in range(meta["frames"]):
            assert vol[i][psr > 0].sum() == 0, f"Frame {i} must have zero illumination on PSR pixels"


def test_illumination_frames_invalid_value_clamped(server):
    code, meta = _get(f"{server}/api/illumination-time?frames=9999", timeout=120)
    assert code == 200
    assert meta["frames"] == 48


def test_api_data_is_strict_json(server):
    """/api/data must never emit NaN/Infinity literals (browser JSON.parse rejects them)."""
    code, raw = _get(f"{server}/api/data", expect_binary=True)
    assert code == 200
    text = raw.decode("utf-8")
    assert re.search(r"\bNaN\b|\b-Infinity\b|\bInfinity\b", text) is None

    def _reject(constant):
        raise ValueError(f"non-standard JSON constant: {constant}")

    json.loads(text, parse_constant=_reject)


def test_export_finite_round_maps_nan_to_null():
    assert export_web_data._finite_round(float("nan"), 4) is None
    assert export_web_data._finite_round(float("inf"), 2) is None
    assert export_web_data._finite_round(-float("inf"), 2) is None
    assert export_web_data._finite_round(0.123456, 4) == 0.1235


# ---------------------------------------------------------------------------
# Phase 5E: /api/data split endpoints (parts=core / parts=extras)
# ---------------------------------------------------------------------------

def test_api_data_parts_core_excludes_deferred_rasters(server):
    """parts=core must ship first-paint rasters only and mark the deferred ones."""
    code, core = _get(f"{server}/api/data?parts=core")
    assert code == 200
    assert "illumination" not in core
    assert "boulder_hazard" not in core
    assert core["deferred_parts"] == ["illumination", "boulder_hazard"]
    assert core["dem"] is not None
    assert core["slope"] is not None
    assert core["psr"] is not None
    assert len(core["dem"]) == core["width"] * core["height"]


def test_api_data_parts_extras_returns_only_deferred_rasters(server):
    """parts=extras carries illumination + boulder and no first-paint rasters."""
    code, extras = _get(f"{server}/api/data?parts=extras")
    assert code == 200
    assert extras["illumination"] is not None
    assert extras["boulder_hazard"] is not None
    assert "dem" not in extras
    assert "slope" not in extras


def test_api_data_parts_core_is_strict_json(server):
    """The smaller core bundle must keep the strict-JSON guarantee (no NaN)."""
    code, raw = _get(f"{server}/api/data?parts=core", expect_binary=True)
    assert code == 200
    text = raw.decode("utf-8")
    assert re.search(r"\bNaN\b|\b-Infinity\b|\bInfinity\b", text) is None

    def _reject(constant):
        raise ValueError(f"non-standard JSON constant: {constant}")

    json.loads(text, parse_constant=_reject)


def test_api_recalculate_sensitivity_is_real_and_scaled(server):
    """BUG-041: sensitivity bars/curve must use resolution-scaled roughness
    thresholds (same math as classify_hazard_surface).

    Before the fix the charts mixed the scaled score_h with RAW 20 m-reference
    roughness gates — at 240 m/px nearly every pixel satisfies roughness >= 5.0,
    so the curve was a flat line (~3533.70 km2 at every threshold) and the three
    bars were identical, while the summary in the same response was sane.
    """
    payload = json.dumps({
        "slope_safe_max": 5.0,
        "slope_caution_max": 10.0,
        "slope_hard_unsafe": 15.0,
        "rough_safe_max": 1.5,
        "rough_hard_unsafe": 5.0,
        "weight_slope": 0.5,
        "weight_roughness": 0.3,
        "weight_shadow": 0.2,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{server}/api/recalculate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    assert data["status"] == "SUCCESS"

    curve = data["sensitivity"]["curve"]
    bars = data["sensitivity"]["bars"]
    summary = data["summary"]

    # 1. The curve is a real descending response, not a flat line.
    vals = [p["unsafe_km2"] for p in curve]
    assert len(vals) == 10
    assert max(vals) - min(vals) > 50.0
    assert vals[0] > vals[-1]

    # 2. The 15-degree curve point encodes exactly the classify rule set
    #    (H >= 0.60 | slope >= 15 | rough >= scaled hard) -> matches summary.
    c15 = next(p["unsafe_km2"] for p in curve if p["slope_deg"] == 15.0)
    unsafe = summary["unsafe"]["area_km2"]
    assert abs(c15 - unsafe) <= max(0.05, 0.005 * unsafe)

    # 3. Bars show strong scenario variation (was: three identical columns).
    u = [b["unsafe_km2"] for b in bars]
    assert u[0] > u[1] > u[2]

    # 4. Cross-chart consistency: bars[t].unsafe == curve point at t
    #    (t=5 and t=15 are sampled by both; t=10 must sit between curve 9 and 11).
    c5 = next(p["unsafe_km2"] for p in curve if p["slope_deg"] == 5.0)
    c9 = next(p["unsafe_km2"] for p in curve if p["slope_deg"] == 9.0)
    c11 = next(p["unsafe_km2"] for p in curve if p["slope_deg"] == 11.0)
    assert abs(bars[0]["unsafe_km2"] - c5) <= 0.01
    assert abs(bars[2]["unsafe_km2"] - c15) <= 0.01
    assert c9 > bars[1]["unsafe_km2"] > c11

    # 5. Safe segment is independent of t and equals the classify Safe area.
    safe = summary["safe"]["area_km2"]
    for b in bars:
        assert abs(b["safe_km2"] - safe) <= 0.05

    # 6. Every bar partitions the valid area exactly (stacked composition).
    valid = sum(summary[k]["area_km2"]
                for k in ("safe", "caution", "unsafe", "shadowed_unknown"))
    for b in bars:
        total = (b["safe_km2"] + b["caution_km2"]
                 + b["unsafe_km2"] + b["shadow_km2"])
        assert abs(total - valid) < 0.3
