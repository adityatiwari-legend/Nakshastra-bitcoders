# 05 — System Architecture

> Diagrams: [`architecture/system_architecture.mmd`](architecture/system_architecture.mmd),
> [`architecture/component_diagram.mmd`](architecture/component_diagram.mmd),
> [`architecture/data_flow_diagram.mmd`](architecture/data_flow_diagram.mmd),
> [`architecture/database_er_diagram.mmd`](architecture/database_er_diagram.mmd)

---

## 1. Architecture style (VERIFIED)

LunaSafe is a **two-process, file-mediated, layered monolith**:

| Property | Reality |
| :--- | :--- |
| Overall pattern | A deterministic **batch processing pipeline** (library of 8 flat Python modules) exposed through **two front doors**: a CLI (`main.py`) and a stdlib HTTP server (`web_server.py`) |
| Services / microservices | **None** — one interpreter, flat modules, no packages, no `__init__.py` at repo root |
| State | **None persisted in memory across restarts.** All state is (a) files in `outputs/`, (b) four module-level globals in `web_server.py:42-56` |
| Frontend/backed coupling | Loose and **file-based**: the browser never touches Python objects; it receives a pre-flattened JSON bundle (`outputs/web_data.json`) plus a few small JSON endpoints |
| Data store | **No database.** GeoTIFF + CSV + JSON + shapefile on local disk — see [`10_DATABASE_AND_DATA_MODEL.md`](10_DATABASE_AND_DATA_MODEL.md) |
| Authentication | **None** |

```
 ┌──────────────┐   subprocess    ┌──────────────────────────────────────────┐
 │ web_server.py│ ───────────────▶│ main.py → io_utils → psr → terrain →     │
 │ (Threading   │                 │ hazard → mapping → validate →            │
 │  HTTP :8050) │◀─── files ──────│ ml_recommender                            │
 └──────┬───────┘   outputs/*.tif └──────────────────────────────────────────┘
        │ JSON (web_data.json, /api/*)
        ▼
 ┌──────────────┐
 │ Browser SPA  │  web/index.html + app.js + three.js
 └──────────────┘
```

## 2. Layer responsibilities

| Layer | Files | Responsibility | Must not do |
| :--- | :--- | :--- | :--- |
| **Configuration** | `config.py` | Single source of truth for every threshold, path, colour, CRS string, and plot setting | Contain logic |
| **I/O & geodesy** | `io_utils.py` | Read/write GeoTIFF, enforce lunar CRS, align grids, generate synthetic data | Classify or compute terrain metrics |
| **Domain: shadow** | `psr.py` | Turn a raw mask into a clean binary mask + vectors + area | Invent illumination physics (it filters an input mask) |
| **Domain: terrain** | `terrain.py` | Slope, aspect, roughness, TRI, histograms | Write anything outside `outputs/` |
| **Domain: hazard** | `hazard.py` | The classification contract (`H`, hard overrides, classes) | Read files from disk (it takes arrays) |
| **Domain: autonomy** | `ml_recommender.py` | Landing ellipse ranking + boulder probability | Claim to be a trained model |
| **Quality** | `validate.py` | Re-derive the rules independently and audit; sensitivity study | Modify the classified raster |
| **Presentation (static)** | `mapping.py`, `mission_report.py` | Publication figures and PDF | Recompute scientific values (uses passed-in arrays / CSV) |
| **Orchestration** | `main.py` | Phase order, CLI flags, logging, summary | Contain scientific logic |
| **Presentation (interactive)** | `web_server.py`, `web/*` | HTTP routing, in-memory cache, UI | Duplicate scientific rules (it calls the same modules) |
| **Tooling** | `export_web_data.py`, `prepare_lola_dataset.py`, `build_interactive_ui.py` | Offline utilities | Be on any critical path |

## 3. Entry points

| Entry point | How invoked | Calls | Produces |
| :--- | :--- | :--- | :--- |
| `main.main()` — `main.py:237` | `python main.py [--dem --psr --force-synthetic --fail-on-mismatch --quiet]` | `run_pipeline()` → all 7 phases | 15 artifacts + console report |
| `web_server.__main__` — `web_server.py:858` | `python web_server.py` | `run_server(8050)` → `load_raster_cache()` → `serve_forever()` | HTTP service |
| `ml_recommender.__main__` — `ml_recommender.py:302` | `python ml_recommender.py` | `run_mission_autonomy()` with default paths | `landing_sites.json`, `boulder_hazard.tif` |
| `mission_report.__main__` — `mission_report.py:227` | `python mission_report.py` | `generate_pdf_mission_report()` | `mission_report.pdf` |
| `export_web_data.__main__` — `export_web_data.py:111` | `python export_web_data.py` | `export_data_bundle()` | `web_data.json` |
| `prepare_lola_dataset.__main__` — `prepare_lola_dataset.py:106` | `python prepare_lola_dataset.py` | `convert_real_lola_to_geotiff()` | `data/lola_*.tif` |
| `build_interactive_ui.__main__` — `build_interactive_ui.py:1130` | `python build_interactive_ui.py` | `build_dashboard()` | `dashboard.html` |

**Self-bootstrapping detail (VERIFIED):** `main.py:18-26` and `web_server.py:38-39` look for
`.venv\Scripts\python.exe` and, if the current interpreter cannot `import rasterio`, silently
re-exec the same command under the venv. This is Windows-specific.

## 4. The two execution paths compared

| Concern | CLI path (`main.py`) | Web path (`web_server.py`) |
| :--- | :--- | :--- |
| Process model | Single process, sequential | Thread-per-request + 2 background worker threads |
| Which dataset | `--dem/--psr` → real files → synthetic fallback (`main.py:60-80`) | DEM chosen by file existence (`web_server.py:62`, `:220-221`) |
| Terrain metrics | Computed in-process (`main.py:116`) | **Read from `outputs/*.tif`** — the web path does not recompute slope |
| Reclassification | Full phase 4 | `hazard.classify_hazard_surface` on cached arrays (`web_server.py:455`) |
| Thresholds | Read once from `config.py` at import | Mutated at runtime from request bodies (`web_server.py:341-362`, `:438-446`) |
| Audit | `validate.process_validation_pipeline` | `validate.verify_rule_consistency` (`web_server.py:496`, `:563`) |
| Full re-run | The whole pipeline | `subprocess` of `main.py` (`web_server.py:373`) — **a separate interpreter** |
| Outputs | Always written to `outputs/` | Written only by the subprocess; the "fast" path writes nothing |

## 5. Communication contracts

| From → To | Mechanism | Contract |
| :--- | :--- | :--- |
| Browser → server | HTTP/1.1, JSON bodies | [`09_API_REFERENCE.md`](09_API_REFERENCE.md) |
| Server → browser | HTTP/200 JSON + static files | same |
| Server → pipeline | `subprocess.Popen([python, "main.py", ...])` | stdout is captured line-by-line into `PIPELINE_LOGS` (`web_server.py:383-387`) |
| Server → rasters | Direct `rasterio` reads at startup and after each run (`load_raster_cache`, `web_server.py:59`) | `RASTER_CACHE` dict |
| Browser → rasters | Never directly — always via `web_data.json` or `/api/recalculate` | see [`api_documentation/DATA_BUNDLE_SCHEMA.md`](api_documentation/DATA_BUNDLE_SCHEMA.md) |
| Pipeline → NASA PDS | One `urllib.request` GET | `web_server.py:633-648` (only if neither local GeoTIFFs nor the JP2 exist) |

## 6. State management

There is **no** database and **no** session state. The mutable state is:

| Symbol | Location | Guard | Lifetime | Risk |
| :--- | :--- | :--- | :--- | :--- |
| `PIPELINE_RUNNING` | `web_server.py:43` | `PIPELINE_LOCK` | process | Boolean race is handled; but set False only in `finally` (`:404`) |
| `PIPELINE_LOGS` | `web_server.py:44` | `PIPELINE_LOCK` | process | Unbounded until next run clears it (`:336`) |
| `DOWNLOAD_STATUS` | `web_server.py:45` | **unguarded** | process | Written by worker thread, read by request thread (`:602`, `:124`) — benign in CPython but not formally safe |
| `RASTER_CACHE` | `web_server.py:48-56` | **unguarded** | process | Replaced wholesale; readers may see a partially updated dict during a reload |
| `config.<THRESHOLD>` | module attributes | **none** | process | `POST /api/recalculate` and `/api/run-pipeline` **overwrite module globals permanently** (`web_server.py:438-446`). There is no "reset to defaults" server endpoint — the UI's `resetDefaults()` simply re-sends the default numbers |

## 7. Error and failure paths

| Failure | Handling | Where |
| :--- | :--- | :--- |
| Missing DEM/PSR file | Silent fallback to synthetic, logged with `[INFO]` | `io_utils.py:392-404` |
| Earth EPSG detected | `ValueError` with explicit message | `io_utils.py:203-206` |
| Grid mismatch, `--fail-on-mismatch` | `ValueError` printing both transforms/shapes | `io_utils.py:309-318` |
| Grid mismatch, default | nearest-neighbour reprojection | `io_utils.py:339-348` |
| Non-overlapping extents | `ValueError` "SPATIAL EXTENT ERROR" | `io_utils.py:330-333` |
| `rasterio`/`geopandas`/`shapely` missing | `ImportError` with explicit message at call time; modules import lazily | `io_utils.py:14-24`, `psr.py:19-27` |
| Pipeline already running | HTTP 409 `{"status":"BUSY"}` | `web_server.py:332-334` |
| Raster cache not loaded | HTTP 400 | `web_server.py:415-419`, `:553-555` |
| Unknown POST route | HTTP 404 "Endpoint not found" | `web_server.py:172-173` |
| Missing download artifact | HTTP 404 | `web_server.py:813-815` |
| LOLA download error | `DOWNLOAD_STATUS["message"] = f"Ingestion error: {e}"`, `success=False` | `web_server.py:660-663` |
| Malformed JSON body | **Swallowed → `{}`** (no 400) | `web_server.py:200-208` |
| Generic file read error | HTTP 500 | `web_server.py:188-189`, `:830-831` |
| Port 8050 busy | Fall back to 8080, else `OSError` propagates | `web_server.py:840-846` |

**Observation (VERIFIED):** scientific code raises exceptions loudly (good), while the web layer
often degrades silently (`except Exception: pass` at `web_server.py:207`, `:289`, `mission_report.py:48`).
This is the opposite of the rule in `.agents/rules/lunasafe.md:13` and is tracked as **I-15**.

## 8. Security boundaries (summary — full review in doc 16)

| Boundary | Status |
| :--- | :--- |
| Network exposure | Server binds `""` (all interfaces) — `web_server.py:840`. Anyone on the LAN can run the pipeline |
| Authentication / authorisation | **None** |
| CORS | `Access-Control-Allow-Origin: *` on every JSON response (`web_server.py:196`) |
| Static file scope | `SimpleHTTPRequestHandler` rooted at the **repository root** (`:93`) → `.py`, `requirements.txt`, `data/*` are all downloadable via plain GET |
| Input validation | Minimal — numbers are `float()`-cast without range checks; upload writes raw body to a fixed path with no size/type check (`:669-679`) |
| Secrets | **None in the repository** (verified: no `API_KEY`/`SECRET`/`TOKEN`/`PASSWORD` strings; no `.env` file) |

## 9. Architectural decisions (with evidence)

| # | Decision | Evidence | Consequence |
| :---: | :--- | :--- | :--- |
| A1 | No web framework; stdlib HTTP server | `web_server.py:22` | Zero extra deps; also no routing middleware, no CSRF protection, no uploads API |
| A2 | All thresholds in `config.py`, imported as a **module** and mutated at runtime | `config.py`; `web_server.py:341-362` | Enables live sliders, but creates process-wide hidden state (Issue I-11) |
| A3 | Arrays in, arrays out for the science core (`hazard.classify_hazard_surface` takes ndarrays) | `hazard.py:61-67` | Easy to unit test without files; forces the web layer to hold rasters in RAM |
| A4 | Web "fast path" re-derives hazard from **cached** slope/roughness rather than recomputing terrain | `web_server.py:448-459` | ~ms latency, but slider changes cannot affect terrain metrics (by design) |
| A5 | Full pipeline re-run is a **subprocess**, not an in-process call | `web_server.py:373-381` | Isolation, but configuration changes do not propagate (Issue I-04) |
| A6 | Synthetic fallback rather than a hard failure | `io_utils.py:392-404` | Demo always works; can hide a bad `--dem` path |
| A7 | Class 4 exists to separate "unknown" from "safe" | `hazard.py:111-113` | The project's central safety idea; enforced by audit rule 8 |
| A8 | Auditor **re-implements** the classifier logic instead of importing the decision function | `validate.py:103-137` | True independence, but the two implementations can drift (web rule-4 key bug is exactly this class of drift) |
| A9 | Frontend is a single 4.5k-line JS file with no build step | `web/app.js` | Trivial to run; hard to test or tree-shake |
| A10 | Artifacts are committed to git | `git ls-files` shows `outputs/*` and `data/*` | Reviewable demo without a run; binary churn in diffs |

## 10. Architecture limitations (honest list)

1. **Single-machine, single-user.** No locking around `outputs/`; two concurrent pipeline runs corrupt artifacts.
2. **Whole region in RAM.** `RASTER_CACHE` and `web_data.json` hold full flattened arrays; a 4k×4k DEM would produce a >100 MB JSON.
3. **No tiling/pyramids.** 2D canvas redraws `ImageData` per pixel (`web/app.js` `precomputeAllLayers`).
4. **Web cannot recompute terrain.** Changing DEM requires a full subprocess re-run.
5. **Configuration is global.** Any threshold change in the web process affects every subsequent request.
6. **The auditor and the classifier can drift** (already have: Issue I-03).
7. **No observability** — no structured logging, no metrics, no request log (beyond the pipeline log buffer).
8. **No packaging.** Flat modules + `sys.path` hacks; not installable as a package.
