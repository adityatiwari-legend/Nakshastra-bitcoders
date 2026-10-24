# 24 — Cross-Reference Matrix (Traceability)

> One-stop mapping: every major concept → its documentation, source code, tests, and known issues.
> Use this to jump straight to the right place. Line numbers verified 2026-10-17
> (`web/app.js` numbers are approximate).

---

## 1. Feature → docs → code → tests → issues

| Feature | Docs | Source | Tests | Issues |
| :--- | :--- | :--- | :--- | :--- |
| Synthetic dataset generation | 08 §2, 10 §2, 12 §2.4 | `io_utils.py:416-500`, `config.py:67-76` | `test_smoke.py:20,27` | — |
| Real LOLA ingestion (auto) | 08 §5, 13 §3.2 | `prepare_lola_dataset.py:19-104` | **none** | I-08, I-15, M-03 |
| LOLA download button | 09, 08 §5 | `web_server.py:601-667` | **none** | M-03 |
| CRS guard (lunar only) | 05 §7, 10 §1 | `io_utils.py:199-206`, `config.py:62` | `test_preprocessing.py::test_earth_epsg_protection`, `test_smoke.py:39-41` | — |
| Grid alignment / reprojection | 07 §A3, 10 §3 | `io_utils.py:257-377` | `test_preprocessing.py::test_grid_*` | — |
| PSR clean + area + vector | 07 §A4, 10 §3.2 | `psr.py:30-269` | `test_psr.py` (5) | — |
| Slope/aspect (Horn) | 07 §A5, 23 | `terrain.py:21-87` | `test_terrain.py::test_planar_ramp_slope_exactness` | — |
| Roughness std / TRI | 07 §A5 | `terrain.py:90-196` | `test_terrain.py` | — |
| Terrain histograms | 08 §2 | `terrain.py:199-290` | e2e in `test_terrain.py` | — |
| Hazard score H | 07 §A6, 23 | `hazard.py:23-58` | `test_hazard.py::test_hazard_score_formula…` | I-07 (D=0) |
| 5-class surface + overrides | 07 §A6, 10 §3 | `hazard.py:61-134` | `test_hazard.py` (6) | — |
| Hazard summary CSV | 10 §3.1 | `hazard.py:137-182, 239-241` | `test_hazard.py::test_process…` | I-02 (web twin) |
| 4-panel map PNG/PDF | 07 §A7, 08 §2 | `mapping.py:149-380` | `test_mapping.py` (2) | — |
| 9-rule auditor | 07 §A8, 19, 23 | `validate.py:70-148` | `test_validate.py` (2) | **I-03** (key), M-06 |
| PSR accuracy metrics | 19 I-01, 23 | `validate.py:301-308` + `compute_psr_metrics:166+` | unit only | **I-01** |
| Slope sensitivity study | 07 §A8, 09 | `validate.py:151-280`; web mirror `web_server.py:504-530` | `test_validate.py::test_slope_sensitivity…` | I-10 (UI chart fake) |
| Landing-site recommender | 07 §A9, 10 §4.1 | `ml_recommender.py:84-215` | `test_ml_recommender.py` (3) | **I-05**, I-12b |
| Boulder detection | 07 §A9, 23 | `ml_recommender.py:18-81` | `test_ml_recommender.py::test_boulder…` | I-09 |
| CLI orchestration + summary | 07 §A1-A10 | `main.py:38-234` | `test_main.py` | M-02 |
| Mission report PDF | 15 §9, 19 | `mission_report.py:22-225` | **none** | **I-14** |
| Web data bundle | 08 §4, 10 §4.2 | `export_web_data.py:11-108` | **none** | **I-06**, T-15 |
| REST API (21 routes) | 09, `api_documentation/` | `web_server.py:95-856` | **none** | I-02/03/04/11/12/13 |
| In-memory raster cache | 05 §6, 15 §2 | `web_server.py:48-85` | **none** | I-06 (stale) |
| Fast recalculate (sliders) | 07 §B3, 08 §4 | `web_server.py:411-547` | **none** | I-02, I-11, I-12b |
| Async pipeline run | 07 §B4, 08 §5 | `web_server.py:329-409` | **none** | **I-04**, SEC-04 |
| Console log pane | 09 | `web_server.py:320-327`; `app.js` ≈1090 | **none** | M-07 |
| 2D map studio | 13 §4.3, `feature_documentation/` | `web/app.js` §§precompute/drawMap (≈40–945) | **none** | I-10 family |
| 3D terrain | 13 §4.3, `feature_documentation/` | `web/app.js` ≈1701–2746 | **none** | — |
| Landing cards / ellipse draw | `feature_documentation/` | `web/app.js` ≈3593–3608 | **none** | I-05 (40 m ring client-only) |
| Validation tab / PSR card | 09, `feature_documentation/` | `web/app.js` ≈3968, ≈4212 | **none** | I-03 visible here |
| Security posture | 16, 19-D | `web_server.py:93,134-152,196,840` | **none** | SEC-01…10 |
| Testing & QA | 14 | `tests/` | — | M-05, M-06 |
| Git / history | 18, `change_history/` | 2 commits `c3d26dd`, `fa36e99` | — | M-01 |

---

## 2. Module → documentation map

| Module | Dedicated doc | Also discussed in |
| :--- | :--- | :--- |
| `config.py` | `module_documentation/CONFIG_MODULE.md` | 12, 05 §4 |
| `main.py` | `module_documentation/MAIN_PIPELINE.md` | 07 §A, 08 §2 |
| `io_utils.py` | `module_documentation/IO_UTILS_MODULE.md` | 07 §A3, 10 §2-3 |
| `psr.py` | `module_documentation/PSR_MODULE.md` | 07 §A4, 10 §3.2 |
| `terrain.py` | `module_documentation/TERRAIN_MODULE.md` | 07 §A5, 08 §2 |
| `hazard.py` | `module_documentation/HAZARD_MODULE.md` | 07 §A6, 10 §3.1, 23 |
| `validate.py` | `module_documentation/VALIDATE_MODULE.md` | 07 §A8, 19 I-01/I-03 |
| `mapping.py` | `module_documentation/MAPPING_MODULE.md` | 07 §A7 |
| `ml_recommender.py` | `module_documentation/ML_RECOMMENDER_MODULE.md` | 07 §A9, 10 §4.1, 19 I-05/I-12b |
| `mission_report.py` | `module_documentation/MISSION_REPORT_MODULE.md` | 19 I-14 |
| `web_server.py` | `module_documentation/WEB_SERVER_MODULE.md` | 07 §B, 09, 16 |
| `export_web_data.py` + `prepare_lola_dataset.py` + `build_interactive_ui.py` | `module_documentation/TOOLING_MODULES.md` | 08 §5, 19 I-15 |
| `web/app.js` + `index.html` + `styles.css` | `feature_documentation/` (per tab) | 07 §B5-B7 |
| `tests/*` | `testing_documentation/` | 14 |

---

## 3. Endpoint → docs → client call site → issues

| Endpoint | Spec | Handler | Client (app.js ≈) | Issue |
| :--- | :--- | :--- | :--- | :--- |
| `GET /health` | 09 §2 | `:210` | 210 | — |
| `GET /api/status` | 09 | `:263` | 128 | — |
| `GET /api/data` | 09 + `DATA_BUNDLE_SCHEMA.md` | `:309` | 233 | I-06 |
| `GET /api/logs` | 09 | `:320` | 1090 | M-07 |
| `GET /api/download-lola-status` | 09 | `:123` | 1291 | — |
| `GET /api/psr-validation` | 09 | `:681` | 4212 | I-01 (client side) |
| `GET /api/download/<f>` | 09 | `:789` | 3750+ | SEC-01 |
| `POST /api/run-pipeline` | 09 | `:329` | 1014 | **I-04**, I-11, SEC-04 |
| `POST /api/recalculate` | 09 | `:411` | 834 | **I-02**, I-11, I-12b |
| `POST /api/audit` | 09 | `:549` | 1149 | **I-03** |
| `POST /api/download-lola` | 09 | `:601` | 1291 | M-03 |
| `POST /api/upload-raster` | 09 | `:669` | **(none)** | I-12a, SEC-05 |
| `POST /api/validate-geotiff` | 09 | `:739` | ≈1450 | I-11b |
| `POST /api/load-offline-demo` | 09 | `:777` | 1401 | — |
| static `/vendor/*`, `/outputs/*`, fallback | 09 §3 | `:134-152` | n/a | **SEC-01/02** |

---

## 4. Issue → fix task → owning doc

| Issue | Task | Primary doc to update when fixed |
| :--- | :--- | :--- |
| I-01 PSR self-comparison | T-04 | 19, 07 §A8 |
| I-02 20 m area scale | T-02 | 19, 09 (recalculate spec) |
| I-03 rule-4 key | T-01 | 19, 09 (audit spec) |
| I-04 config vs subprocess | T-06 (+flags) | 19, 12 §1 |
| I-05 40 m buffer | T-12b | 19, 10 §4.1, 12 §2.2 |
| I-06 stale bundle | T-10 | 19, 10 §4.2, 18 |
| I-07 shadow term 0 | T-12a/b | 19, 07 §A6 |
| I-08 PSR heuristic | T-23 | 19, 10 §2.4 |
| I-09 ML wording | T-12a | 19, 23 (glossary) |
| I-10 fake charts | T-17 | 19, feature docs |
| I-11 global config | T-06 | 19, 12 §1 |
| I-11b validate-geotiff | T-08 scope | 19, 09 |
| I-12 upload/pixel size | T-02 (b) + T-13 (a) | 19, 09 |
| I-13 security | T-13 | 16, 19-D |
| I-14 report hard-coding | T-03 | 19, `MISSION_REPORT_MODULE.md` |
| I-15 hard-coded path | T-18 | 19, `TOOLING_MODULES.md` |
| I-16 dependency drift | T-16 | 19, 04, 11 §3 |
| M-01…M-08 | T-07, T-09, T-11, T-18 | 18, 14, 19 |
| SEC-01…10 | T-13 | 16 |

---

## 5. Audience → reading paths

| You are… | Path |
| :--- | :--- |
| **New teammate (day 1)** | 00 → 01 → 06 → your module's doc → 19 → 20 |
| **Frontend dev** | 00 → 09 → `feature_documentation/` → 07 §B → `WEB_SERVER_MODULE.md` → 22 |
| **Backend/science dev** | 01/02 → 07 → `HAZARD/VALIDATE/…_MODULE.md` → 14 → 19 → 20 |
| **Reviewer/judge** | 01 → 03 → 09 (API reality) → 19 §E (claims vs reality) → 16 §4 (privacy) |
| **Maintainer/ops** | 11 → 13 → 15 → 17 → 18 |
| **Security reviewer** | 16 → 19-D → `WEB_SERVER_MODULE.md` §routes |
| **QA** | 14 → `testing_documentation/` → 19 (gaps) → 20 (T-08/09) |

---

## 6. Artifact → producer → consumer

| Artifact | Producer (doc §) | Consumer (doc §) |
| :--- | :--- | :--- |
| `psr_binary.tif` | 07 §A4 | 07 §A6-A9, `RASTER_CACHE` (05 §6) |
| `slope/roughness*.tif` | 07 §A5 | 07 §A6, 08 §3 |
| `hazard_classes.tif` | 07 §A6 | 07 §A7-A9, `/api/status` (09) |
| `hazard_summary.csv` | 10 §3.1 | KPIs (09), PDF (19 I-14) |
| `psr_polygons.*` | 07 §A4 | map C panel, bundle (10 §4.2) |
| `landing_sites.json` | 07 §A9 | ALSS tab, PDF, bundle |
| `web_data.json` | 08 §4, 10 §4.2 | `GET /api/data` → whole UI |
| `mission_report.pdf` | 07, 19 I-14 | download button |
| `lunasafe_hazard_map.png/pdf` | 07 §A7 | download buttons, judging |
