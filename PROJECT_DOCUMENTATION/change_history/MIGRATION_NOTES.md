# MIGRATION Notes — what any refactor must preserve

Audience: whoever does T-19…T-24 (framework, DB, CI, JS split). **Do not break these contracts
without updating the linked docs in the same change.**

---

## 1. Stability tiers

| Tier | Meaning | Examples |
| :--- | :--- | :--- |
| 🔴 **Hard contract** | external consumers / committed data depend on it | REST routes+JSON shapes, artifact filenames, class IDs |
| 🟡 **Soft contract** | internal, but tests or docs pin it | `config.*` names, function signatures used across modules |
| 🟢 **Free to change** | presentation / docs / legacy | dashboard.html, README text, chart colours |

## 2. 🔴 Hard contracts

### Filesystem layout
| Path | Consumer |
| :--- | :--- |
| `outputs/` artifact names (`hazard_classes.tif`, `slope_deg.tif`, `aspect_deg.tif`, `roughness_std_m.tif`, `roughness_tri_m.tif`, `psr_binary.tif`, `psr_polygons.geojson` + shapefile set + bundle zip, `hazard_summary.csv`, `landing_sites.json`, `boulder_hazard.tif`, `lunasafe_hazard_map.png/.pdf`, `slope_sensitivity.png`, `terrain_histograms.png`, `mission_report.pdf`, `web_data.json`) | `web_server.py` download routes, UI, docs 09/10, tests (`test_main.py` asserts 13 of them) |
| `data/` inputs (`synthetic_dem.tif`, `synthetic_psr.tif`, `lola_south_pole_dem.tif`, `lola_psr_mask.tif`, `ldem_75s_240m.jp2`) | pipeline fallback ladder (`main.py:60-80`), ingestion |

### REST API (docs 09 + `api_documentation/REST_API.md`)
- Route paths and verbs (20 + static fallback); **409-busy** and **404-HTML** semantics.
- JSON keys of `/api/status`, `/api/logs`, `/api/data`, `/api/recalculate` (`summary`,
  `landing_sites`, `hazard_classes_flat`, `rule_audit`, `sensitivity`), `/api/audit`
  (`rule_results[]` with `rule_id/description/violations/passed`), `/api/psr-validation`
  (`UNLOADED` + `provenance_note` when no reference — **honesty behaviour, keep it**).
- Error envelope `{"status": "ERROR"|"BUSY"|"SUCCESS", "message": ...}`.
- Port scheme 8050 → 8080 fallback; `/health` vs `/api/status` duality (UI heartbeats use both).

### Scientific value semantics
- Class IDs 0-4 and names `NoData/Safe/Caution/Unsafe/Shadowed-Unknown` (config) — CSV keys are
  **lowercased class names**, UI chips and PDF depend on them.
- CRS: `config.LUNAR_SOUTH_POLE_PROJ4` (IAU sphere R=1 737 400 m) and the **Earth-CRS guard**
  (`io_utils.py:199-206`) — never reintroduce `EPSG:4326`.
- Audit rule keys emitted by `validate.py` (`rule4_safe_pixel_in_psr`, …) — I-03 exists because a
  consumer used a different name; any rename must update producer, consumer, tests
  (TC-PLAN-04) and docs 09/10/19 together.
- Units: areas in km² from `pixel_size`, slopes in degrees, roughness in metres, distances in
  metres — web must stop assuming 20 m (I-02) when migrating.

### `outputs/web_data.json` keys
The 17 top-level keys of `api_documentation/DATA_BUNDLE_SCHEMA.md` (incl. `bounds.left/right/
bottom/top`, `defaults`' 10 keys). Frontend `loadDataset()`/offscreen layer builders hard-code them.

### Landing-site schema
`api_documentation/LANDING_SITES_SCHEMA.md` — UI cards, PDF, bundle all read these field names.

## 3. 🟡 Soft contracts

- `config.py` as the single threshold/paths source (A2). If thresholds move to a config file or
  DB, update the 7 duplicate default sites listed in doc 12 §7 **and** `defaults` in the bundle.
- Module signatures used by `main.py` phases (`io_utils.load_and_align_datasets`,
  `psr.process_and_export_psr`, `terrain.process_terrain_pipeline`,
  `hazard.process_hazard_pipeline`, `mapping.generate_4panel_hazard_map`,
  `validate.process_validation_pipeline`, `ml_recommender.run_mission_autonomy`).
- Array-in/array-out core (A3) — the only reason unit tests are hermetic; don't couple science
  functions to file paths.
- Test suite shape: 32 tests / 9 files; IDs `TC-AUTO-01…32` in `testing_documentation/TEST_CASES.md`.
- Issue/task ID namespaces: `I-01…I-16`, `M-01…M-08`, `T-01…T-24`, `SEC-01…SEC-10`, `A1…A10` —
  **append only, never renumber.**
- Launchers: `run.bat`, `run_website.bat/.ps1`, `view_ui.bat` keep working with a fresh venv.

## 4. 🟢 Safe to change

`dashboard.html` + `build_interactive_ui.py` (legacy, T-14 decision), README marketing copy,
chart hard-coding (until I-10 is fixed), `__pycache__` tracking (remove), vendored three.js
version (re-test `init3DScene`), colour palette.

## 5. Migration playbooks (short)

**Add a web framework (T-19):** keep `GET /api/data` payload byte-compatible first; move route
handlers one-by-one behind the same URLs; port the state globals (`RASTER_CACHE`,
`PIPELINE_*`, `DOWNLOAD_STATUS`, `PARAM_OVERRIDES`) to an app-scoped store (this kills I-11);
add auth last, but before exposing beyond localhost (SEC register, doc 16).

**Add a database (T-20):** the app has **no DB** by design; if introduced, only *derived* results
(summaries, audit runs, site lists) belong there — rasters stay files. Bundle regeneration must
remain a single call (`export_web_data.export_data_bundle`).

**Split the frontend (T-21):** `app.js` (≈4.5k lines) is one file with implicit ordering —
`initEventListeners` (`:88`) must run after DOM ids exist; layer builders (`:452-710`) share
`DATA`/offscreen canvases. Extract by tab, keep global `DATA` shape first.

**CI (T-22):** must run the *fast* subset by default (full suite rewrites `outputs/`, doc 14 §4)
and restore `outputs/` if the pipeline job is included.

## 6. Regression checklist after any migration

1. `pytest -q --ignore=tests\test_main.py` → 31 green; then full 32.
2. Bundle integrity command (`api_documentation/DATA_BUNDLE_SCHEMA.md` §6) → no mismatched arrays.
3. Manual QA gate (`testing_documentation/TEST_CASES.md` §3, TC-MAN-01…12).
4. Docs touched: routes (09 + REST_API), keys (10 + schemas), issues (19), tasks (20).
