# 08 — Data Flow and Workflows

> Companion diagrams: [`architecture/data_flow_diagram.mmd`](architecture/data_flow_diagram.mmd),
> [`architecture/system_architecture.mmd`](architecture/system_architecture.mmd).
> This document adds the *operational* view: what a user/actor actually does, in what order,
> and what data moves at each step.

---

## 1. Data types in the system

| Kind | Formats | Examples | Invariants |
| :--- | :--- | :--- | :--- |
| **Grid / raster** | GeoTIFF (LZW), one band | `synthetic_dem.tif`, `slope_deg.tif`, `hazard_classes.tif` | Must share CRS, affine transform and shape with the DEM; verified by `check_grid_alignment` (`io_utils.py:257`) |
| **Vector** | GeoJSON + ESRI Shapefile bundle | `psr_polygons.*` | WGS84-agnostic lunar CRS written to `.prj`; GeoJSON written via `to_file` |
| **Tabular** | CSV | `hazard_summary.csv` | Exactly 5 rows (classes 1,2,3,4,0), fixed column order (`hazard.py:15-18`) |
| **Document** | PDF | `lunasafe_hazard_map.pdf`, `mission_report.pdf` | Generated only; never parsed back |
| **Image** | PNG | `lunasafe_hazard_map.png`, `terrain_histograms.png` | 300 DPI (`config.PLOT_DPI`) |
| **JSON contract** | JSON | `landing_sites.json`, `web_data.json`, every `/api/*` response | See [`api_documentation/DATA_BUNDLE_SCHEMA.md`](api_documentation/DATA_BUNDLE_SCHEMA.md) |
| **In-memory arrays** | `numpy` | `RASTER_CACHE`, handler locals | dtype preserved from disk; hazard output is `uint8` |

### Raster encoding conventions (VERIFIED across all writers)

| Convention | Value | Where enforced |
| :--- | :--- | :--- |
| NoData sentinel | `-9999.0` (float), or the DEM's own nodata | `config.NO_DATA_VALUE`; `io_utils.write_geotiff` re-tagged with input `nodata` |
| Slope/roughness on invalid pixels | `-9999.0` | `terrain.py:84-85,133,194` |
| Hazard class ids | 0 unknown · 1 safe · 2 moderate · 3 unsafe · 4 PSR | `config.hazard_class_{id,ids,name,names}` |
| PSR mask dtype | `uint8`, values {0,1} | `psr.py:73,104-107` |
| Elevation units | metres above lunar datum | `data/lola_south_pole_dem.tif` tag `UNITS=metres`, DN × 0.5 applied at ingest |
| CRS | Lunar South Pole Polar Stereographic, sphere R = 1 737 400 m | `config.LUNAR_SOUTH_POLE_PROJ4` (`config.py:62`); rejected if it matches an Earth EPSG signature |

---

## 2. Workflow A — Batch processing (CLI)

**Actor:** developer / CI-less verification. **Trigger:** `python main.py` (optionally via `run.bat`).

| # | Step | Inputs | Outputs written | Failure mode |
| :-: | :--- | :--- | :--- | :--- |
| 0 | Interpreter self-upgrade to `.venv` | none | none | silent re-exec, non-zero exit propagates |
| 1 | Input selection + dataset inspection | `data/*`, `--dem/--psr` | none (console only) | `ValueError` if `--fail-on-mismatch` + grid mismatch |
| 2 | PSR cleaning & export | PSR raster + DEM mask | `psr_binary.tif`, `psr_polygons.{geojson,shp…}`, `.zip` | no polygons → warning, exports skipped |
| 3 | Terrain metrics | DEM | `slope_deg.tif`, `aspect_deg.tif`, `roughness_std_m.tif`, `roughness_tri_m.tif`, `terrain_histograms.png` | raises on wrong shape/CRS |
| 4 | Hazard classification | slope, roughness, PSR | `hazard_classes.tif`, `hazard_summary.csv` | raises on wrong shape/CRS |
| 5 | Cartography | all of the above | `lunasafe_hazard_map.png/.pdf` | geopandas missing → maps exported without outlines |
| 6 | Validation | hazard, slope, roughness, PSR | `slope_sensitivity.png` + in-memory audit dict | audit non-zero only fails the process if `--fail-on-mismatch` |
| 7 | Autonomy (re-opens files) | DEM + written rasters | `boulder_hazard.tif`, `landing_sites.json` | graceful "no safe candidates" JSON |
| 8 | Console summary | in-memory results | none | — |

**Ordering constraint:** Phase 7 reads `outputs/` written in phases 2–4, so skipping phases
(except with `--force-synthetic`, which still runs everything) is not supported.

**Artifact count:** 15 files (asserted in `tests/test_main.py:36-37`).

---

## 3. Workflow B — Web console cold start

**Actor:** end user / judge / demo presenter. **Trigger:** `run_website.bat` → `http://localhost:8050`.

```
run_website.bat
  └─ python web_server.py
       ├─ load_raster_cache()            needs outputs/{slope_deg,psr_binary}.tif
       │    ├─ none → lazy-load on first request; recalculate returns 400 until a run
       │    └─ present → RASTER_CACHE = {dem, slope, roughness_std, psr} + profile/transform
       ├─ ThreadingHTTPServer(("",8050))
       └─ background: none at startup

browser opens /
  ├─ GET /            → web/index.html   (reads app.js inline via <script src>)
  ├─ GET /app.js, /styles.css, /vendor/*, CDN KaTeX/fonts
  ├─ GET /api/status  → config echo + hazard_summary.csv KPIs + latest audit counts
  ├─ GET /api/data    → 2.2 MB JSON bundle (built by export_web_data.export_data_bundle if absent)
  └─ GET /health      → 200 every 2.5 s   (liveness heartbeat)
```

**First-run scenario (no `outputs/`):** `/api/status` still answers with zeros and config values;
`POST /api/recalculate` answers `{"error": "Raster cache not loaded"}` 400 until either a pipeline
run happens or `load_offline_demo` succeeds.

---

## 4. Workflow C — Interactive reclassification (the signature feature)

**Actor:** user dragging SLOPE/ROUGHNESS/ELIGIBLE-classification sliders.

| T | Event | Where | Network | Result visible after |
| :-: | :--- | :--- | :--- | :--- |
| 0 | `input` on a slider | `onParamChange()` | none yet | client-side `previewReclassifyClient()` preview on canvas |
| 1 | +250 ms debounce | `recalculateFast()` | `POST /api/recalculate` (step 7 above) | wait |
| 2 | 200 OK | `app.js` handler | — | `currentHazardArray` replaced; `drawMap()`; 3D texture rebuilt; KPI delta chips; `rule_audit` chip; landing cards refreshed |
| 3 | drag again <250 ms | debounce resets | — | only the local preview updates |

Server-side work in step 2 (all in RAM, no disk writes):
`classify_hazard_surface` → class histogram → `verify_rule_consistency` → `recommend_landing_sites`
→ sensitivity + threshold-curve arrays → JSON with a **full flattened hazard array**.

⚠️ Two caveats (documented in doc 19):
- The stored thresholds are written into `config` module globals (Issue I-11) — they persist for
  *all* sessions and are **not** applied to the subprocess path (Issue I-04).
- Areas use a fixed 20 m pixel (Issue I-02) → wrong km² on the real dataset.

---

## 5. Workflow D — Full pipeline run from the UI

**Actor:** user pressing **RUN PIPELINE**.

1. UI posts `{force_synthetic, slope_threshold, roughness_threshold, safety_threshold, ...}`.
2. Server rejects with 409 if `PIPELINE_RUNNING` (`web_server.py:331`), else mutates `config`,
   clears `PIPELINE_LOGS`, starts `worker()`.
3. `worker()` → `Popen([venv_python, "main.py", "--force-synthetic"|"--dem", "--psr", ...])`.
   ⚠️ The slider values posted in step 2 are **not** passed to the child (Issue I-04).
4. Every stdout line appends to `PIPELINE_LOGS` under `PIPELINE_LOCK`.
5. UI polls `GET /api/logs` → the DOM log pane, auto-scrolling.
6. Exit code 0 → `export_data_bundle()` then `load_raster_cache()` → subsequent `/api/data`
   and `/api/recalculate` reflect the new files.
7. `finally` clears `PIPELINE_RUNNING`.

**Concurrency:** only one run at a time; there is **no** lock on `outputs/` itself, so a user
running `python main.py` in a terminal at the same time is unsafe.

---

## 6. Workflow E — NASA LOLA ingestion

Two independent, **non-interchangeable** paths exist — a known documentation hazard:

| Path | Trigger | Code | Result |
| :--- | :--- | :--- | :--- |
| **Built-in downloader** | `POST /api/download-lola` (or `GET /api/download-lola-status` polling) | `web_server.py:606-667` → URL at `:633` | `data/ldem_75s_240m.jp2` only (≤100 MB guard); status JSON |
| **Manual ingestion** | `python prepare_lola_dataset.py` | `prepare_lola_dataset.py:15` hard-coded `e:\sistec\LunaSafe` | JP2 → `data/lola_south_pole_dem.tif` (centre crop, DN×0.5, unit tags) + `data/lola_psr_mask.tif` (depth < −900 m heuristic) |

After ingestion, existence of the two GeoTIFFs flips every dataset choice (CLI and web) to
**real LOLA**. Nothing invalidates the existing `outputs/` automatically → stale-artifact risk
(Issue I-06 in its current form).

⚠️ Neither path produces a *published* PSR atlas: the mask is a depth heuristic
(`prepare_lola_dataset.py:51-56`, Issue I-08).

---

## 7. Workflow F — Validation & audit (two entry points)

| Entry point | Function | Used by | Scope |
| :--- | :--- | :--- | :--- |
| `validate.verify_rule_consistency` | 9 numpy boolean reductions (`validate.py:70-148`) | `POST /api/audit`, `/api/recalculate`, `/api/run-pipeline` | in-memory arrays supplied by caller |
| `validate.process_validation_pipeline` | PSR metric + audit + sensitivity (`:283-357`) | `main.py:172-186` | re-reads class + slope + roughness from `outputs/` |

Both share the 9 rules; only the batch path also computes PSR precision/recall/IoU/F1 — and only
those numbers are currently meaningless (Issue I-01).

**Reading the result:** `{"audit": {"is_consistent", "total_violations", "audited_pixels",
"detailed_violations": {"rule1_...": n, ...}}}`. Non-zero any counter = FAILED check.

---

## 8. Workflow G — Export & download

| Artifact | Produced by | Served by | UI button |
| :--- | :--- | :--- | :--- |
| `lunasafe_hazard_map.png/.pdf` | phase 5 | `GET /api/download/lunasafe_hazard_map.png` | DOWNLOAD buttons |
| `hazard_summary.csv` | phase 4 | `GET /api/download/hazard_summary.csv` | EXPORT |
| `landing_sites.json` | phase 7 | `GET /api/download/landing_sites.json` | EXPORT |
| `psr_polygons.geojson` | phase 2 | `GET /api/download/psr_polygons.geojson` | EXPORT |
| `mission_report.pdf` | `mission_report.py` **lazily on first request** | `GET /api/download/mission_report.pdf` (`web_server.py:793`) | MISSION REPORT |
| 2D canvas snapshot | client | none (canvas → dataURL → `<a download>`) | SNAPSHOT |
| 3D view PNG | client | none (renderer `toDataURL`) | 3D screenshot |
| `web_data.json` | `export_web_data.py` | `GET /api/data` | (not exposed as a download) |

Anything outside `outputs/` → 404 (`web_server.py:813-815`).

---

## 9. End-to-end trace for one landing site

```
data/synthetic_dem.tif ──read──▶ dem[200,200] float32
data/synthetic_psr.tif ──align─▶ psr[200,200] uint8
        │
        ├──terrain.py──▶ slope_deg[200,200], roughness_std_m[200,200]
        │
        ├──hazard.py───▶ hazard_classes[200,200] uint8  (rule order, doc 07 §A6)
        │
        ├──ml_recommender.recommend_landing_sites
        │       safe_mask = (hazard==1)
        │       dist = distance_transform_edt(safe_mask) × 20 m   ← Issue I-12
        │       candidates = dist ≥ 100 m
        │       fitness = .35·clearance + .30·flatness + .20·smoothness + .15·science
        │       greedy argmax + 250 m suppression
        │       ──▶ landing_sites.json → top_sites[0..2]
        │             {rank, row, col, easting_m, northing_m, elevation_m,
        │              suitability_pct, clearance_radius_m, mean_slope_deg, ...}
        │
        └──export_web_data──▶ web_data.json {landing_sites: [same objects], boulder_points}
                                  │
                                  └──GET /api/data──▶ app.js renderLandingSitesCards()
                                                       └──plot Site #1..#3 on canvas + 3D
```

Downstream consumers of that one record: the landing cards (§≈4100 `app.js`), the 2D ellipse +
40 m standoff ring (client-only geometry), the 3D marker at easting/northing, and — after a run —
page 2 of `mission_report.pdf` (which reads the JSON file, not the API).

---

## 10. Data lifecycle & regeneration

| File | Regenerated by | Destroyed/replaced by |
| :--- | :--- | :--- |
| `outputs/*.tif` (7 rasters) | `python main.py` (phases 2-4, 7) | next full run; `pytest tests/test_main.py` |
| `outputs/lunasafe_hazard_map.*` | phase 5 | full run |
| `outputs/web_data.json` | `export_web_data.py` or the pipeline worker | any UI pipeline run |
| `outputs/mission_report.pdf` | first `GET .../mission_report.pdf` | not automatically — rebuilt per request (`mission_report.py:22` called at `web_server.py:796`) |
| `data/lola_*.tif` | `prepare_lola_dataset.py` | manual only |
| `dashboard.html` | `build_interactive_ui.py` | manual only |
| `RASTER_CACHE` | server start, post-run reload | server restart |

**Rule of thumb:** if you need trustworthy outputs after editing any module, run
`python main.py --force-synthetic` **and** `python export_web_data.py`, then restart
`web_server.py` (RAM cache is not watched for changes).
