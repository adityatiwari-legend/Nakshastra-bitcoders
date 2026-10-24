# 03 — Features & Implementation Status

**Legend for Status column**

| Status | Meaning |
| :--- | :--- |
| ✅ **Implemented & verified** | Code path reviewed **and** exercised by an executed test or by direct observation in this run |
| 🟡 **Partially implemented** | Works for some inputs/paths, or key sub-claim is missing |
| 🟠 **UI-only / placeholder** | The UI or label exists but the underlying work is cosmetic, hard-coded, or missing |
| 🔴 **Broken / unverified** | Evidence of incorrect behaviour, or the claim cannot be reproduced |
| ⚪ **Planned / not found** | No implementation in the repository |

**Test column** refers to tests that exist in `tests/` and were **executed** in this run
(`32 passed`), not to tests that merely look plausible.

---

## A. Data & geodesy

| Feature | Status | Evidence in code | Dependencies | Tests | Limitations |
| :--- | :---: | :--- | :--- | :--- | :--- |
| Synthetic crater DEM + PSR generator | ✅ | `io_utils.py:27-113`, `create_and_save_synthetic_dataset()` `io_utils.py:417-464` | numpy, rasterio | `test_smoke.py:44,77` | Deterministic (fixed `RandomState(42..45)`) — good for tests, not representative of real terrain |
| GeoTIFF read/write with lunar CRS | ✅ | `io_utils.py:116-188` | rasterio | `test_smoke.py:77`, `test_preprocessing.py:22` | LZW only; single band assumed everywhere (`src.read(1)`) |
| Earth-EPSG rejection sentinel | ✅ | `io_utils.py:199-206` | — | `test_preprocessing.py:48` | String-match based (5 signatures); exotic Earth CRS (e.g. `+ellps=WGS84`) would slip through |
| Grid alignment check (shape/CRS/transform) | ✅ | `io_utils.py:257-285` | — | `test_preprocessing.py:65` | Tolerance fixed at `1e-4` (`io_utils.py:260`) |
| Auto-resample PSR onto DEM grid | ✅ | `io_utils.py:288-377` | rasterio.warp | `test_preprocessing.py:92` | Nearest-neighbour only; bilinear option mentioned in README is **NOT FOUND** |
| Auto-fallback to synthetic when data missing | ✅ | `main.py:60-80`, `io_utils.py:392-404` | — | indirect (`test_main.py:19` uses `force_synthetic`) | Silent fallback can mask a wrong `--dem` path |
| NASA JP2 → GeoTIFF converter | 🟡 | `prepare_lola_dataset.py:19-104` | rasterio | **none** | Hard-coded `ROOT_DIR = Path(r"e:\sistec\LunaSafe")` (`:15`); PSR mask is a depth heuristic, not a published PSR product (`:51-56`) |
| Auto-download LOLA JP2 from NASA PDS | 🟡 | `web_server.py:601-667` (URL at `:633`) | urllib (stdlib) | **none** | No retry/resume/checksum; URL differs from the one recommended in `data/DOWNLOAD_INSTRUCTIONS.md:23` |
| Custom GeoTIFF upload | 🔴 | Server: `web_server.py:669-679`. Frontend: **never calls it** (`web/app.js` has no `/api/upload-raster`) | — | none | Dead endpoint; frontend "UPLOADED" badge is cosmetic (`web/app.js` `handleFileSelected`, ≈line 4207) |

## B. Terrain & PSR analysis

| Feature | Status | Evidence in code | Dependencies | Tests | Limitations |
| :--- | :---: | :--- | :--- | :--- | :--- |
| Horn (1981) slope | ✅ | `terrain.py:21-87` (kernels `:55-64`) | scipy.ndimage | `test_terrain.py:38` (exact planar ramp) | NoData filled with global median before convolution (`:46-49`) → edge values are approximations |
| Aspect (0–360° from N) | ✅ | `terrain.py:74-80` | scipy | `test_terrain.py:21` (flat ⇒ 0) | Flat pixels forced to 0° (`:79`) |
| Roughness = local elevation std-dev (3×3) | ✅ | `terrain.py:90-136` | scipy uniform_filter | `test_terrain.py:21,76` | Requires ≥3 valid samples per window (`:120`); window spans 60 m @20 m/px, **720 m @240 m/px** |
| Riley TRI | ✅ | `terrain.py:139-196` | numpy | `test_terrain.py:76` | Pure-python 8-shift loop (slow on large rasters) |
| Terrain histograms (4-panel) | ✅ | `terrain.py:199-290` | matplotlib Agg | `test_terrain.py:76` | — |
| PSR binarisation (bool/uint8/float) | ✅ | `psr.py:30-58` | numpy | `test_psr.py:24` | NoData forced to 0 (`:56`) — correct per rule O3 |
| 8-connected speckle removal (<9 px) | ✅ | `psr.py:61-91` | scipy.ndimage | `test_psr.py:38` | Threshold `PSR_MIN_SIZE_PIXELS=9` (`config.py:136`) is uncalibrated to resolution |
| PSR area in m²/km² | ✅ | `psr.py:94-112` | numpy | `test_psr.py:61` (exactness) | — |
| Vectorisation → GeoJSON + Shapefile | ✅ | `psr.py:115-171`, export `:244-250` | geopandas, shapely, rasterio.features | `test_psr.py:74,100` | Invalid geometries repaired with `buffer(0)` (`:143`) |
| Provenance tagging (synthetic vs published) | ✅ | `psr.py:215`, `config.py:138-139` | — | partly (`test_psr.py:100`) | — |

## C. Hazard classification

| Feature | Status | Evidence in code | Dependencies | Tests | Limitations |
| :--- | :---: | :--- | :--- | :--- | :--- |
| Weighted score `H` | ✅ | `hazard.py:23-58` | numpy | `test_hazard.py:22` | Shadow term `D` is always 0 in the real pipeline (see Issue I-07) |
| Hard overrides (15° / 5 m) | ✅ | `hazard.py:100-106` | numpy | `test_hazard.py:35` | — |
| 5-class surface (0–4) | ✅ | `hazard.py:61-134` | numpy | `test_hazard.py:56,69,84` | — |
| NoData never Safe | ✅ | `hazard.py:89,132` | numpy | `test_hazard.py:84` | — |
| CSV area summary | ✅ | `hazard.py:137-182` | pandas | `test_hazard.py:95` | Percentages computed against total raster incl. NoData (`:164`) |
| GeoTIFF export of classes with tags | ✅ | `hazard.py:214-230` | rasterio | `test_hazard.py:95` | — |
| Live web reclassification | ✅ (code) | `web_server.py:411-547` | numpy | **none** | Hardcodes 20 m/px for areas (`:470`) — Issue I-02 |

## D. Mission autonomy (the "AI" layer)

| Feature | Status | Evidence in code | Dependencies | Tests | Limitations |
| :--- | :---: | :--- | :--- | :--- | :--- |
| Top-3 landing ellipse recommender (ALSS) | 🟡 | `ml_recommender.py:84-215` | scipy.ndimage, rasterio | `test_ml_recommender.py:37` | `pixel_size_m` defaults to `config.SYNTHETIC_PIXEL_SIZE_M` (`:93`) and the web caller never overrides it (`web_server.py:484-493`) → wrong metres on 240 m data |
| 40 m hazard standoff / clearance buffer | 🔴 | Config exists (`config.py:52`), used by `web_server.py:361-362` **only to store**; `recommend_landing_sites` uses `ellipse_radius_m` as the clearance (`ml_recommender.py:115-116`) and never reads `LANDING_CLEARANCE_BUFFER_M` | — | none | The 40 m claim appears in UI overlay (`web/app.js` `drawLandingSitesOverlay`) and `mission_report.py:218` but is **not enforced server-side** |
| Science-proximity scoring (250 m bell curve) | ✅ (code) | `ml_recommender.py:140` | numpy | none | Magic number 250/200 not in `config.py` (rule O2 violation) |
| Spatial separation suppression (2.5× radius) | ✅ | `ml_recommender.py:154-155,205-207` | numpy | `test_ml_recommender.py:37` | — |
| Boulder / micro-hazard probability raster | 🟡 | `ml_recommender.py:18-81` (Gaussian bandpass `:43-44`, sigmoid `:56`) | scipy.ndimage | `test_ml_recommender.py:15` | Deterministic signal processing, **not** a trained model; "estimated diameter" `clip(residual*1.8, 1, 8)` (`:68`) is a heuristic with no calibration |
| Boulder point list export (top 150) | ✅ | `ml_recommender.py:77-79`, sample of 30 in JSON (`:282`) | json | `test_ml_recommender.py:85` | — |
| `landing_sites.json` + `boulder_hazard.tif` artifacts | ✅ | `ml_recommender.py:259-286` | rasterio | `test_ml_recommender.py:85` | — |
| Serialized/loaded ML model | ⚪ | no `.pkl`/`.joblib`/`.onnx`/`.h5` in repo | — | — | README's "Boulder AI" wording overstates this (Issue I-09) |

## E. Validation & reporting

| Feature | Status | Evidence in code | Dependencies | Tests | Limitations |
| :--- | :---: | :--- | :--- | :--- | :--- |
| 9-rule consistency auditor | ✅ | `validate.py:70-148` | numpy | `test_validate.py:51,73` | Rule keys differ from the web endpoint's expectations (Issue I-03) |
| Slope sensitivity study (5 scenarios) | ✅ | `validate.py:151-280` | matplotlib, pandas | `test_validate.py:104` | Recomputes `H` **without** the shadow term (`:196`) — consistent with pipeline, but differs from `hazard.compute_hazard_score` |
| PSR IoU/precision/recall/F1 calculator | ✅ (function) / 🔴 (pipeline usage) | `validate.py:22-67`; **self-comparison** at `validate.py:301-308` | numpy | `test_validate.py:20` (function maths verified with distinct arrays) | CLI always reports 1.0 because candidate == reference |
| Honest "no reference loaded" response | ✅ | `web_server.py:722-737` | — | none | Good pattern; contradicts the CLI's always-1.0 metrics |
| 4-panel 300 DPI map (PNG+PDF) | ✅ | `mapping.py:149-380` | matplotlib, geopandas | `test_mapping.py:21,32` | Scale bar assumes a fixed 1 km length (`mapping.py:71`) regardless of actual extent |
| PDF mission report | 🟡 | `mission_report.py:22-225` | matplotlib PdfPages | **none** | **Rule-audit table is hard-coded** "0 / PASSED" (`:167-177`); fallback statistics hard-coded (`:51-58`); "UTC" label uses local time (`:71`) |
| 9-point audit printed in CLI | ✅ | `validate.py:332-341` | — | indirect | — |

## F. Web Mission Control

| Feature | Status | Evidence in code | Dependencies | Tests | Limitations |
| :--- | :---: | :--- | :--- | :--- | :--- |
| Static server + REST routing | ✅ (code) | `web_server.py:95-173` | stdlib http.server | **none** | No auth; whole repo root is statically served (`:93,:152`) |
| `GET /health`, `/api/status`, `/api/data`, `/api/logs` | ✅ (code) | `web_server.py:111-125,210-327` | — | none | `/api/data` may serve a stale bundle (Issue I-06) |
| `POST /api/recalculate` (<20 ms in-memory) | 🟡 | `web_server.py:411-547` | numpy | none | Mutates global `config` permanently (`:438-446`); area math hardcoded 20 m/px (`:470`); "20 ms" claim unbenchmarked |
| `POST /api/run-pipeline` with live log streaming | 🟡 | `web_server.py:329-409` | subprocess, threading | none | Thresholds sent in the body are **not** inherited by the child `main.py` process (Issue I-04) |
| `POST /api/audit` | 🔴 | `web_server.py:549-599` | — | none | Reads `rule4_safe_in_psr` but the key is `rule4_safe_pixel_in_psr` → Rule 4 always 0 (Issue I-03) |
| `GET /api/psr-validation` | ✅ (code) | `web_server.py:681-737` | — | none | Correctly returns `null` metrics when no independent reference exists |
| `POST /api/validate-geotiff` (pre-flight) | 🔴 | `web_server.py:739-775` | — | none | Returns `crs_valid: true` and `all_passed: true` unconditionally (`:760-772`) — no CRS check performed |
| `POST /api/load-offline-demo` | ✅ (code) | `web_server.py:777-787` | — | none | Only reloads the in-memory cache |
| `GET /api/download/<artifact>` | ✅ (code) | `web_server.py:789-818` | zipfile | none | `mission_report.pdf` generated on demand (`:793-798`) |
| `POST /api/upload-raster` | 🔴 | `web_server.py:669-679` | — | none | Never invoked by the frontend; unvalidated raw-body write to `data/custom_upload.tif` |
| 2D canvas studio (layers, swipe, AOI, inspector) | 🟡 | `web/app.js` §§3–7 (≈lines 264–1668) | canvas | none | Not browser-tested in this run; DEM & PSR-reference layers have no UI toggle (dead layer entries) |
| 3D WebGL terrain + transect + sun | 🟡 | `web/app.js` (≈lines 1670–2746) | three.js r128 (vendored) | none | Not browser-tested; CDN fallback requires internet |
| 60-second judge tour | 🟠 | `web/app.js` (≈lines 4279–4474) | — | none | Step 3 inspects a hard-coded pixel (120,110); demo-driven, not data-driven |
| Validation-tab sensitivity charts | 🔴 | `web/app.js` `renderSensitivityCharts()` (≈4041) | — | none | **Hard-coded arrays** plotted as if measured (Issue I-10) — contradicts the project's own "never invent results" rule |
| Real-time log viewer | 🟡 | polling every 500 ms (`web/app.js` ≈3768) | — | none | Each poll wipes the terminal, discarding locally appended lines |
| KaTeX formula rendering | 🟡 | `web/index.html:16-17` (CDN 0.16.8) | internet on first load | none | Offline mode degrades to HTML fallback (`renderKatexFormula`) |
| Header provenance badge / raster metadata strip | ✅ (code) | `web_server.py:219-261`, `web/app.js` ≈146 | — | none | Fallback metadata hardcodes "250 × 250 px" guesses (`:257-258`) |

## G. Legacy / auxiliary

| Feature | Status | Evidence | Notes |
| :--- | :---: | :--- | :--- |
| `dashboard.html` (1.3 MB single-file console) | 🟠 legacy | Generated by `build_interactive_ui.py:1123`; opened by `view_ui.bat` | Not linked from `web/index.html`; no dedicated route, but reachable at `http://localhost:8050/dashboard.html` through the static fallback |
| `build_interactive_ui.py` | 🟠 unused | Not imported by any module (repo search) | Regenerates `dashboard.html` from `outputs/web_data.json` |
| `requirement.txt` | ⚠️ duplicate | Byte-different copy of `requirements.txt` (one comment line missing) | Drift risk: `pip install -r requirement.txt` also works today |
| `run.bat` / `run_website.bat` / `run_website.ps1` | ✅ | Contents inspected | Windows-only launchers; `.venv` preferred, falls back to global `python` |
| `.agents/rules/lunasafe.md` | ✅ | Read | The authoritative constraint list for AI/agent-assisted development |

## H. Cross-cutting gaps

| Gap | Status | Notes |
| :--- | :---: | :--- |
| Automated tests for `web_server.py` | ⚪ | No test imports `web_server` (verified by grep over `tests/`) |
| Automated tests for `mission_report.py`, `export_web_data.py`, `prepare_lola_dataset.py`, `build_interactive_ui.py` | ⚪ | none |
| Frontend tests (unit/e2e) | ⚪ | No `package.json`, no test runner |
| Linter / formatter configuration | ⚪ | No `ruff`/`flake8`/`black`/`pyproject.toml`. `pyflakes` 4.0.3 is installed in `.venv` (transitive) but never configured |
| CI | ⚪ | No `.github/workflows` |
| `.gitignore` | ⚪ | Not present; 22 `__pycache__`/`.pyc` files are tracked |
| Code coverage measurement | ⚪ | No `pytest-cov`; no coverage number exists anywhere |
