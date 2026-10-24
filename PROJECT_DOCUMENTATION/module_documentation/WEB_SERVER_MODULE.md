# `web_server.py` — Mission Control HTTP Service (864 lines)

> Role: everything interactive. Stdlib `ThreadingHTTPServer` + a custom handler with 21 routes,
  an in-memory raster cache, an async pipeline worker, and static file serving.

**Status:** 🟠 functional, security/integration issues · **Tested by:** **none** (M-06) ·
**Issues:** I-02, I-03, I-04, I-11, I-11b, I-12, I-13, SEC-01…06/10, M-07.

---

## 1. Process anatomy

```
python web_server.py
 ├─ sys.path bootstrap (:27-29), PYTHON_BIN = .venv interpreter (:38-39)
 ├─ module globals (:42-56)
 │    PIPELINE_RUNNING : bool     guarded by PIPELINE_LOCK
 │    PIPELINE_LOGS    : list     capped display at 150 lines (:324), unbounded storage (M-07)
 │    DOWNLOAD_STATUS  : dict     unguarded (worker writes, requests read)
 │    RASTER_CACHE     : dict     {"loaded", "dem","slope","roughness","psr","profile","transform"}
 ├─ __main__ (:858) → run_server(8050)
 │    load_raster_cache() (:59-85)   needs outputs/{slope_deg,psr_binary}.tif else loaded=False
 │    ThreadingHTTPServer(("", 8050), LunaSafeHandler)   → on OSError retry :8080 (:840-846)
 └─ serve_forever()   (thread-per-request; 2 ad-hoc daemon threads for pipeline/download)
```

Handler init (`:91-93`) roots `SimpleHTTPRequestHandler` at the **repo root** — the root cause of
SEC-02.

## 2. Routing summary

- **GET** (`do_GET`, `:95-152`): static (`/`, `/styles.css`, `/app.js`), health, status, data,
  logs, download-lola-status, psr-validation, `/api/download/<f>`, `/vendor/*`, `/outputs/*`, then
  **fallback `super().do_GET()`** (arbitrary repo files + directory listings).
- **POST** (`do_POST`, `:154-173`): `run-pipeline`, `recalculate`, `audit`, `download-lola`,
  `upload-raster`, `validate-geotiff`, `load-offline-demo`; else 404.
- Full specs, request/response JSON: **[`09_API_REFERENCE.md`](../09_API_REFERENCE.md)**.

## 3. Core handlers (behavioural notes)

| Handler | Lines | Critical behaviour |
| :--- | :-: | :--- |
| `serve_file` | 175-189 | `no-cache` headers; 404/500 paths |
| `send_json` | 191-198 | sets `Access-Control-Allow-Origin: *` on **every** response (SEC-03) |
| `read_json_body` | 200-208 | all errors → `{}` (no 400) |
| `handle_api_health` | 210 | `running`/`connected` + dataset probe |
| `get_current_raster_metadata` | 219-261 | reads the **actual DEM** for px/grid, with two hard-coded fallback dicts |
| `handle_api_status` | 263-307 | parses `hazard_summary.csv` (errors swallowed) → KPI payload |
| `handle_api_data` | 309-318 | builds `web_data.json` on the fly if absent |
| `handle_api_logs` | 320-327 | last 150 lines under lock |
| `handle_api_run_pipeline` | 329-409 | 409 if busy → **mutates config** → `Popen(main.py)` worker → log pump → post-run bundle+cache refresh → `finally` clears flag |
| `handle_api_recalculate` | 411-547 | lazy cache → **mutates config** → classify → areas with **20 m** (I-02) → recommender (default 20 m, I-12b) → audit → sensitivity → JSON incl. full flattened class array |
| `handle_api_audit` | 549-599 | re-classify + `verify_rule_consistency` + `rules_meta` descriptions (**rule4 key bug**, I-03) |
| `handle_api_download_lola` | 601-667 | 409 if running → worker: existing GeoTIFFs → local JP2 (>5 MB) → PDS GET (`:633`, 30 s) → convert; status dict |
| `handle_api_upload_raster` | 669-679 | **dead** (no UI caller), raw write to `data/custom_upload.tif` (I-12a, SEC-05) |
| `handle_api_psr_validation` | 681-737 | reference present → real metrics; else honest `UNLOADED` + nulls |
| `handle_api_validate_geotiff` | 739-775 | real stats, **hard-coded** `crs_valid`/`all_passed` (I-11b) |
| `handle_api_load_offline_demo` | 777-787 | re-runs `load_raster_cache()` |
| `handle_api_download` | 789-864 | mission_report generated on demand (`:793-798`); shapefile zip; attachment serving; **no filename sanitisation** (SEC-01) |

## 4. State & concurrency model

| Guarded by `PIPELINE_LOCK` | NOT guarded |
| :--- | :--- |
| `PIPELINE_RUNNING` transitions | `DOWNLOAD_STATUS` dict (worker ↔ requests) |
| `PIPELINE_LOGS` append/clear/read | `RASTER_CACHE` wholesale replacement |
| | all `config.*` threshold writes (I-11 — cross-request interference) |

`ThreadingHTTPServer` means **simultaneous POSTs race on `config`** — two clients dragging sliders
interleave assignments (`:438-446`). CPython's GIL makes each assignment atomic, but the
*sequence* is not: a request can classify with half-old/half-new thresholds.

## 5. Dataset selection logic (three different probes!)

| Site | Rule |
| :--- | :--- |
| `load_raster_cache:62` | real DEM only (ignores PSR presence) |
| `handle_api_health:215`, `handle_api_status:266` | both real files must exist |
| `main.py:66-73` | `--force-synthetic` → files → fallback ladder |

Mismatch → the health badge and the cache can disagree in edge cases (e.g. DEM present, PSR missing).

## 6. Security-relevant lines (see doc 16 for PoCs)

`:93` root dir · `:134-140` vendor join (traversal) · `:143-149` outputs join (traversal) ·
`:129-131` download name (traversal) · `:152` fallback (listings) · `:196` CORS `*` ·
`:369-381` subprocess (fixed argv) · `:669-679` upload · `:840` bind all interfaces.

## 7. Testing plan (task T-08)

Suggested `tests/test_server.py`:

1. boot `ThreadingHTTPServer(("",0))` in a thread with `RASTER_CACHE` primed from synthetic outputs;
2. `GET /health`, `/api/status` → shapes;
3. `GET /api/data` → `width*height == len(dem)`;
4. `POST /api/audit` → 9 `rule_results`, and **key parity with `validate`** (catches I-03);
5. `POST /api/recalculate` with `slope_safe_max` → summary changes; then `{}` → equals defaults
   (catches I-11 once T-06 lands);
6. `POST /api/run-pipeline` twice → second is 409 (worker stubbed);
7. traversal probes `/vendor/../config.py`, `/outputs/../requirements.txt`,
   `/api/download/../config.py` → 404 (must fail before T-13, pass after);
8. bad JSON body → 400 (after T-13) / `{}` behaviour documented (today).

## 8. When editing

- New route → `do_GET`/`do_POST` dispatch + handler + doc 09 row + `api_documentation/REST_API.md` +
  §7 tests + security review (auth? traversal? range checks?).
- Never add `config.X = …` writes without considering I-11/T-06 (prefer local overrides dict).
- Keep response `status` field vocabulary consistent: `ONLINE/SUCCESS/PASSED/BUSY/ERROR/STARTED/UNLOADED`.
