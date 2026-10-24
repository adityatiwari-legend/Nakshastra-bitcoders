# 09 — API Reference

**Service:** `web_server.py` → `LunaSafeHandler` (`ThreadingHTTPServer`, stdlib).
**Base URL:** `http://localhost:8050` (fallback port 8080 if 8050 is occupied — `web_server.py:840-846`).
**Auth:** none. **CORS:** every JSON response carries `Access-Control-Allow-Origin: *` (`:196`).
**Content type:** all bodies `application/json` except static/attachment routes.
**Verification:** every route, status code and field below was read from source on 2026-10-17;
line numbers refer to `web_server.py`.

> **Conventions used in this document**
> `200` always unless shown otherwise; malformed JSON bodies are silently coerced to `{}` by
> `read_json_body` (`:200-208`) — the server does **not** return 400 for bad JSON.

---

## 1. Route table (complete — 7 POST + 14 GET/other handlers)

| # | Method | Path | Handler (line) | Purpose |
| :-: | :--- | :--- | :--- | :--- |
| 1 | GET | `/health`, `/api/health` | `handle_api_health` (`:210`) | Liveness/state heartbeat (UI polls every 2.5 s) |
| 2 | GET | `/api/status` | `handle_api_status` (`:263`) | Console badges, KPI CSV, raster metadata |
| 3 | GET | `/api/data` | `handle_api_data` (`:309`) | Full raster bundle (`outputs/web_data.json`) |
| 4 | GET | `/api/logs` | `handle_api_logs` (`:320`) | Last 150 pipeline log lines |
| 5 | GET | `/api/download-lola-status` | inline in `do_GET` (`:123`) | Ingestion worker progress |
| 6 | GET | `/api/psr-validation[?benchmark]` | `handle_api_psr_validation` (`:681`) | PSR metrics vs reference or explicit UNLOADED truth |
| 7 | GET | `/api/download/<filename>` | `handle_api_download` (`:789`) | Artifact attachment |
| 8 | POST | `/api/run-pipeline` | `handle_api_run_pipeline` (`:329`) | Async full pipeline in a subprocess |
| 9 | POST | `/api/recalculate` | `handle_api_recalculate` (`:411`) | Fast in-memory reclassification |
| 10 | POST | `/api/audit` | `handle_api_audit` (`:549`) | 9-rule consistency audit |
| 11 | POST | `/api/download-lola` | `handle_api_download_lola` (`:601`) | Start NASA JP2 ingestion (async) |
| 12 | POST | `/api/upload-raster` | `handle_api_upload_raster` (`:669`) | ⚠ raw byte write of a custom GeoTIFF (**unused by UI**) |
| 13 | POST | `/api/validate-geotiff` | `handle_api_validate_geotiff` (`:739`) | ⚠ file stats with hard-coded "passed" flags |
| 14 | POST | `/api/load-offline-demo` | `handle_api_load_offline_demo` (`:777`) | Reload `RASTER_CACHE` from `outputs/` |
| 15 | GET | `/`, `/index.html` | `do_GET` (`:99`) | SPA shell |
| 16 | GET | `/styles.css` | `:103` | Stylesheet (served from `web/`) |
| 17 | GET | `/app.js` | `:106` | Application JS (served from `web/`) |
| 18 | GET | `/vendor/*` | `:134` | Vendored three.js assets |
| 19 | GET | `/outputs/*` | `:143` | ⚠ any file in `outputs/` verbatim (no allowlist) |
| 20 | GET | *(everything else)* | `:152` → `SimpleHTTPRequestHandler` | ⚠ **any file under the repository root** |

---

## 2. Detailed endpoint specifications

### `GET /health` · `GET /api/health` — `:210`

```json
{
  "status": "connected",            // "running" while PIPELINE_RUNNING
  "pipeline_running": false,
  "active_dataset": "synthetic",    // "lola" only if BOTH real GeoTIFFs exist
  "timestamp": 1760688000.12
}
```
Consumer: `app.js` `startStatusHeartbeat` (≈210). Never fails.

---

### `GET /api/status` — `:263`

```json
{
  "status": "ONLINE",
  "active_dataset": "SYNTHETIC DEMO",          // or "REAL NASA LRO LOLA (South Pole)"
  "is_synthetic": true,
  "pipeline_running": false,
  "crs": "Moon South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)",
  "has_outputs": true,                          // hazard_classes.tif AND 4-panel PNG exist
  "map_png_available": true,
  "map_pdf_available": true,
  "synthetic_ready": true,
  "real_lola_ready": false,
  "summary_data": {                             // parsed from outputs/hazard_summary.csv
    "safe":  {"pixel_count": 1191, "area_km2": 0.4764, "pct_valid_terrain": 63.5, "pct_total_raster": 2.98},
    "...":   "keys = class_name lowercased: safe | caution | unsafe | shadowed_unknown | unknown"
  },
  "raster_metadata": {                          // via get_current_raster_metadata() :219
    "dataset_name": "Synthetic Crater Topography (Demo Benchmark)",
    "source": "Synthetic Procedural Lunar Crater Model",
    "crs": "...", "pixel_size_m": 20.0,
    "grid_size": "200 × 200 px", "total_pixels": 40000,
    "nodata_val": -9999.0, "is_synthetic": true
  },
  "timestamp": 1760688000.12
}
```
Notes: CSV read errors are swallowed (`:289`) → `summary_data` can be `{}`. `pixel_size_m`
default fallthrough at `:237` (`20.0 if not is_real else 240.0`) can report a wrong value when
`pixel_size_x` is missing.

---

### `GET /api/data` — `:309`

Returns `outputs/web_data.json` as-is; if missing, calls `export_web_data.export_data_bundle()`
once, then serves it; 500 if still unavailable.

Payload shape (full schema: [`api_documentation/DATA_BUNDLE_SCHEMA.md`](api_documentation/DATA_BUNDLE_SCHEMA.md)):

| Field | Type | Notes |
| :--- | :--- | :--- |
| `width`, `height` | int | grid dims of **this** bundle |
| `pixel_size_x/y` | float | metres |
| `bounds` | `{l,r,b,t}` | from the raster transform |
| `nodata` | float | |
| `defaults` | object | default thresholds sent to the sliders |
| `dem[]`, `slope[]`, `roughness[]`, `psr[]`, `psr_reference[]`, `hazard_classes[]`, `boulder_hazard[]` | number[] | length `width*height`, **flattened row-major** |
| `psr_polygons` | GeoJSON FeatureCollection | embedded vector |
| `landing_sites` | array | same objects as `landing_sites.json` |
| `boulder_points` | array | up to 30 sample points |

⚠️ Sizes ~2.2 MB for 200×200; 250×250 → ~3.4 MB. No compression, no caching headers
(`serve_file` sets `no-cache`, `:185`).

---

### `GET /api/logs` — `:320`

```json
{ "running": false, "logs": ["[Phase 1/7] …", "…"], "total_lines": 137 }
```
Lock-guarded (`PIPELINE_LOCK`); window = last 150 lines. Buffer is cleared at the start of each
run (`:336`) and never on idle.

---

### `GET /api/download-lola-status` — `:123`

Global `DOWNLOAD_STATUS` dict, mutated by the ingestion worker thread:
```json
{ "running": false, "progress": 100, "message": "…", "success": true }
```
⚠ Written from a worker thread without a lock (`:607-664`), read by request threads (`:124`).

---

### `GET /api/psr-validation[?benchmark]` — `:681`

| Case | Condition | Response |
| :--- | :--- | :--- |
| Reference available | `data/independent_psr_reference.tif` exists (default) or `?benchmark` with a same-shape reference | `{"precision","recall","iou","f1_score","reference_name","reference_loaded":true,"status":"LOADED", …}` from `validate.compute_psr_metrics` |
| No reference | always the honest path (`:723-737`) | `{"status":"UNLOADED","reference_loaded":false,"reference_source":"None","provenance_note":"…(Rule: Never show invented accuracy numbers).","precision":null,"recall":null,"iou":null,"f1_score":null}` |

`?benchmark` deliberately falls back to comparing against the **input** mask (itself derived from
the same source) — labelled `"…Ground Truth (Benchmark)"` (`:708-713`).

---

### `GET /api/download/<filename>` — `:789`

| `filename` | Behaviour |
| :--- | :--- |
| `mission_report.pdf` | **Lazily generated** on first request via `mission_report.generate_pdf_mission_report()` (`:793-798`) |
| `psr_polygons.shp`-style names | zipped on the fly if the bundle zip is missing (`:800+`) |
| any other file present in `outputs/` | served as an attachment (`send_file_attachment`) |
| missing → | `404` (`:813-815`) |

Allowlist is effectively *whatever exists in `outputs/`* — see Issue I-13 (no name sanitisation).

---

### `POST /api/run-pipeline` — `:329`

**Request** (all keys optional):
```json
{
  "force_synthetic": true,
  "slope_safe_max": 5.0, "slope_caution_max": 10.0, "slope_hard_unsafe": 15.0,
  "rough_safe_max": 1.5, "rough_caution_max": 3.0, "rough_hard_unsafe": 5.0,
  "weight_slope": 0.5, "weight_roughness": 0.3, "weight_shadow": 0.2,
  "landing_ellipse_radius_m": 100.0, "clearance_buffer_m": 40.0
}
```
**Responses:**
- `200 {"status":"STARTED","message":"Pipeline initiated in background thread"}`
- `409 {"status":"BUSY","message":"Pipeline already running in background"}`

**Side effects:** writes every received key into the `config` module (`:341-362`) — permanent for
the process; then spawns `Popen([python, "main.py", "--force-synthetic"])` (`:369-381`).

⚠️ **The threshold keys are NOT passed to the child process** (Issue I-04); only
`force_synthetic` reaches `main.py`. After completion the worker re-exports `web_data.json` and
reloads `RASTER_CACHE` (`:395-397`).

---

### `POST /api/recalculate` — `:411`  *(hot path)*

**Request:** same key names as `/api/run-pipeline`, except `force_synthetic` is ignored; missing
keys fall back to the current `config` values (`:422-435`).

**Precondition:** `RASTER_CACHE` loaded; otherwise lazy `load_raster_cache()`, and `400
{"status":"ERROR","message":"Raster cache not ready; run pipeline once."}` (`:415-419`).

**Response (200):**
```json
{
  "status": "SUCCESS",
  "summary": {
    "safe": {"pixels": n, "area_km2": x, "pct": y},
    "caution": {...}, "unsafe": {...},
    "shadowed_unknown": {...},
    "nodata": {"pixels": n, "area_km2": x, "pct": y_of_TOTAL_pixels},
    "valid_pixels": n, "total_pixels": 40000
  },
  "landing_sites": [ /* top_sites objects, identical to landing_sites.json */ ],
  "hazard_classes_flat": [0,1,2,3,4, ...],       // length width*height, row-major
  "rule_audit": {"is_consistent": true, "total_violations": 0, "violations": {"rule1_…": 0, …}},
  "sensitivity": {
    "bars": [{"threshold":5.0,"safe_km2":…,"caution_km2":…,"unsafe_km2":…,"shadow_km2":…}, {…10.0}, {…15.0}],
    "curve": [{"slope_deg":3.0,"unsafe_km2":…,"unsafe_pct":…}, … {"slope_deg":25.0, …}]
  }
}
```

**Caveats (verified):**
- `area_km2` uses `config.SYNTHETIC_PIXEL_SIZE_M` (20 m) regardless of the dataset (`:470`) → Issue I-02.
- All new thresholds are written into `config` (`:438-446`) → process-wide state (Issue I-11).
- `landing_sites` recomputed without `pixel_size_m`, so clearance uses 20 m/px (Issue I-12).
- `hazard_classes_flat` is the only way the browser gets updated classes; on a 250×250 grid that
  is 62 500 integers per slider tick.

---

### `POST /api/audit` — `:549`

Re-classifies from cache and runs `validate.verify_rule_consistency`.

```json
{
  "status": "PASSED",                 // "FAILED" if total_violations != 0
  "total_violations": 0,
  "rule_results": [
    {"rule_id": "Rule 1", "description": "Safe slope limit: slope must be strictly below safe threshold (< 5.0°)", "violations": 0, "passed": true},
    {"rule_id": "Rule 4", "description": "Safe PSR exclusion: safe landing zone strictly outside permanent shadow", "violations": 0, "passed": true},
    "… Rules 2,3,5,6,7,8,9 …"
  ],
  "total_pixels": 40000,
  "valid_pixels": 15000
}
```
⚠️ **Rule 4 reads `detailed.get("rule4_safe_in_psr", 0)` (`:576`) but the validator emits
`rule4_safe_pixel_in_psr`** (`validate.py:117`) → Rule 4 always reports 0 violations (Issue I-03).
Descriptions embed the current thresholds at request time (`:573-581`).

---

### `POST /api/download-lola` — `:601`

- `409 {"status":"BUSY","message":"Ingestion already in progress"}` if `DOWNLOAD_STATUS["running"]`.
- `200 {"status":"STARTED","message":"NASA LRO LOLA ingestion initiated"}`, worker thread does
  one of three things (`:612-658`):
  1. both GeoTIFFs exist → immediate success;
  2. local `data/ldem_75s_240m.jp2` > 5 MB → `prepare_lola_dataset.convert_real_lola_to_geotiff()`;
  3. otherwise `urllib` GET from PDS (`:633`, 30 s timeout, `Content-Length`-driven progress to
     80 %) then convert.
- Failure → `DOWNLOAD_STATUS.message = "Ingestion error: …", success=false` (`:660-663`).
- Poll with `GET /api/download-lola-status`.

⚠️ Endpoint uses `config.DATA_DIR / 'ldem_75s_240m.jp2'`; the manual doc
(`data/DOWNLOAD_INSTRUCTIONS.md:23`) cites a different URL — document-level inconsistency.

---

### `POST /api/upload-raster` — `:669`

Reads `Content-Length` bytes verbatim and writes them to `data/custom_upload.tif` (fixed name).
`200 {"status":"SUCCESS","filename":"custom_upload.tif","path":"…"}` or `500`.

⚠️ **Dead endpoint:** no reference in `web/app.js`. No size cap, no MIME/CRS validation, fixed
filename → any client can overwrite the file (Issue I-12b). A malformed body writes a corrupt
`.tif` that later stages may pick up.

---

### `POST /api/validate-geotiff` — `:739`

**Request:** `{"type": "dem"|"psr", "filename": "optional_name.tif"}` (relative to `data/`,
empty ⇒ dataset default).

```json
{"status":"SUCCESS","checks":{
  "file_readable": true, "filename": "synthetic_dem.tif",
  "dimensions": "200 × 200 pixels", "pixel_size": "20.0 m/px",
  "crs_valid": true, "crs_name": "Moon South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)",
  "nodata_defined": true, "nodata_value": -9999.0,
  "min_val": -1234.5, "max_val": 987.6,
  "all_passed": true
}}
```
⚠️ `crs_valid`, `crs_name` and `all_passed` are **hard-coded constants** (`:765-771`) — the CRS
is never actually checked, and `all_passed` is always `true` (Issue I-11b/I-11c → tracked as I-11
companion). Only unreadable files return `400 {"status":"ERROR","message":…}`.

---

### `POST /api/load-offline-demo` — `:777`

Calls `load_raster_cache()`; `200 {"status":"SUCCESS","message":"Offline demo dataset loaded …","is_offline":true}`
or `500 {"status":"ERROR","message":…}`. Does **not** regenerate `web_data.json`.

---

## 3. Static & file-serving routes

| Route | Source directory | Notes |
| :--- | :--- | :--- |
| `/`, `/index.html` | `web/index.html` | special-cased at `:99-101` |
| `/styles.css` | `web/styles.css` | `:103` |
| `/app.js` | `web/app.js` | `:106` |
| `/vendor/<f>` | `web/vendor/<f>` | path-prefix strip at `:136-137` |
| `/outputs/<f>` | `<repo>/outputs/<f>` | no allowlist (`:143-148`) |
| *any other* | `<repo>/<f>` via `SimpleHTTPRequestHandler` | **directory listing + arbitrary file download** (`:93`, `:152`) |

`serve_file` always returns `Cache-Control: no-cache, no-store, must-revalidate` (`:185`).
`serve_file_attachment` sets `Content-Disposition: attachment` for downloads.

---

## 4. Error contract summary

| Code | Raised when | Body |
| :--- | :--- | :--- |
| 400 | raster cache unavailable (`:418`, `:554`); `validate-geotiff` unreadable file (`:775`) | `{"status":"ERROR","message":…}` |
| 404 | unknown POST route (`:173`); missing static/download file (`:177`, `:815`) | HTML error page (stdlib `send_error`) |
| 409 | pipeline already running (`:333`); ingestion already running (`:603`) | `{"status":"BUSY","message":…}` |
| 500 | static read failure (`:189`); `/api/data` cannot build a bundle (`:318`); `load-offline-demo` exception (`:787`); `upload-raster` exception (`:679`) | `{"status":"ERROR",…}` or HTML |
| *(none)* | malformed JSON body | coerced to `{}` → defaults used |

## 5. Known API-level issues (cross-reference: `19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`)

| Issue | Endpoint(s) | Effect |
| :--- | :--- | :--- |
| I-02 | `POST /api/recalculate` | Areas always computed with 20 m/px → 144× error on LOLA (240 m) |
| I-03 | `POST /api/audit` | Rule 4 counter reads a key the validator never emits → always 0 |
| I-04 | `POST /api/run-pipeline` | Config mutated in-process but the subprocess re-reads `config.py` from disk |
| I-11 | `POST /api/recalculate`, `/api/run-pipeline` | Thresholds become global, session-wide, non-resettable (no defaults endpoint) |
| I-11b/c | `POST /api/validate-geotiff` | `crs_valid`/`all_passed` always `true` |
| I-12 | `POST /api/upload-raster` | Dead, unvalidated, fixed-path raw write |
| I-13 | all GET routes | No auth; repo-root static serving; `*` CORS |

## 6. Client call sites (for UI work)

| UI action | Call | `web/app.js` (≈ line) |
| :--- | :--- | :--- |
| startup heartbeat | `GET /health` @ 2.5 s | 210 |
| badge/KPI refresh | `GET /api/status` @ 5 s | 128 |
| initial dataset load | `GET /api/data` | 233 |
| slider release (250 ms debounce) | `POST /api/recalculate` | 834 `recalculateFast` |
| RUN PIPELINE button | `POST /api/run-pipeline` | 1014 `runPipeline` |
| log pane | `GET /api/logs` @ 1.5 s while running | 1090 |
| RULE AUDIT panel | `POST /api/audit` | 1149 `verifyRuleAudit` |
| DOWNLOAD NASA DATA | `POST /api/download-lola` + status poll | 1291 |
| OFFLINE DEMO button | `POST /api/load-offline-demo` | 1401 |
| EXPORT/MAP/PDF buttons | `window.open('/api/download/…')` | 3750+ |
| PSR validation tab | `GET /api/psr-validation` | 4212 |

*(line numbers approximate — single-file frontend, see `feature_documentation/` for per-feature maps)*
