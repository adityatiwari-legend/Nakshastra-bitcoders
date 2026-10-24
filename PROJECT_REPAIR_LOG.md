# PROJECT REPAIR LOG — OrbisLuna

Living log maintained by the repair agent. Updated after every meaningful work batch.

---

## Phase 0 — Baseline (COMPLETE)

### Discovered architecture

- **Domain**: Lunar South Pole landing-site intelligence — PSR mapping, 5-class hazard classification, landing-site recommendation, rover traverse planning.
- **Stack**: Pure Python 3.13 stdlib + numpy/scipy/rasterio/geopandas/scikit-image/matplotlib. Web server: `http.server.ThreadingHTTPServer` (`web_server.py`, port 8050). Frontend: vanilla JS (`web/app.js` 4912 lines, `web/index.html`, `web/styles.css`) + vendored `three.min.js`/`OrbitControls.js`. No build step.
- **Pipeline** (`main.py`): ingest/align rasters → PSR clean/vectorize → terrain metrics (Horn slope, roughness) → hazard classify → 4-panel map → validation/audit → landing recommender → rover route → web bundle export. Outputs written to `outputs/`.
- **Data**:
  - `data/lola_south_pole_dem.tif` — 250×250, 240 m/px, Moon2000_spole (IAU 2015 sphere R=1737400), ±30 km. **REAL NASA PDS LOLA** (converted from `data/ldem_75s_240m.jp2`, size 10,766,928 B matches PDS archive listing; URL verified live 2026-10-18).
  - `data/lola_psr_mask.tif` — 250×250, **derived proxy** (threshold: elev < mean−900 m) generated in `prepare_lola_dataset.py`. NOT an official LOLA/LROC PSR product (no PSR product exists in the PDS GDR polar directory).
  - `data/synthetic_dem.tif` / `synthetic_psr.tif` — 200×200, 20 m/px procedural benchmark (explicitly synthetic).
  - `data/sites/*` — procedurally generated site models (shackleton, malapert, faustini, nobile, synthetic) + lola_crop (= real LOLA).
- **Tests**: pytest, 37 tests — **37 passed in 19.2s at baseline** (Windows, Python 3.13.1).

### Baseline commands & results

| Command | Result |
|---|---|
| `python -m pytest -q` | 37 passed (baseline) |
| `python web_server.py` | Starts; serves UI + API on :8050 |
| `GET /health` | 200 OK |
| `GET /api/status` | 200 — claims "REAL NASA LRO LOLA" (misleading, see BUG-003) |
| `GET /api/data` | 200 — web bundle is **synthetic-derived** (200×200) |
| `GET /api/psr-validation` | 200 — honestly reports UNLOADED (good) |
| `GET /api/psr-targets` | 200 — **elevations wrong** (mixed-grid indexing, BUG-004) |
| `GET /api/rover-route` | **CRASHES connection** (traceback in server log, BUG-001) |
| Browser load of `/` | Page loads; console traffic observed in server log |

### Root-cause cluster identified (Phase 1)

The single deepest root cause: **dataset-state inconsistency**. `outputs/` rasters are 200×200/20 m (synthetic-derived) while the raster cache blindly loads the 250×250/240 m real LOLA DEM. Every cache consumer mixes grids.

---

## Phase status

- [x] Phase 0: Baseline
- [x] Phase 1: Bug inventory (see BUG_TRACKER.md)
- [x] Phase 2: Backend root-cause fixes — **verified**
- [ ] Phase 5/6: Frontend + visualization audit (in progress)
- [ ] Phase 7-8: E2E workflows + final gate

## Batch 2 — Backend consistency fixes (COMPLETE, verified)

### Changes
1. `web_server.py` — `load_raster_cache()` rewritten: outputs-grid-matched DEM selection, shape validation, provenance fields (dataset_id/name/is_synthetic/pixel_size_m/shape); rejects mixed grids loudly.
2. `web_server.py` — `/api/status`, `/api/health`, `get_current_raster_metadata`: honest provenance from the loaded cache (was: input-file existence → false "REAL LOLA" claims over synthetic outputs).
3. `web_server.py` — `/api/rover-route`: full try/except → JSON 500 instead of connection crash.
4. `web_server.py` — `/api/validate-geotiff`: real CRS/georeferencing/nodata checks (was: fabricated `crs_valid: true`).
5. `web_server.py` — pipeline default now uses real data when available; ACTIVE_SITE_ID synced from cache at startup + after pipeline.
6. `web_server.py` — favicon route (SVG) — no more 404 noise.
7. `ml_recommender.run_mission_autonomy()` — pixel size now derived from DEM transform (was: hardcoded 20 m → 12× clearance error on LOLA 240 m data); grid-consistency guard added.
8. `prepare_lola_dataset.py` — removed hardcoded `e:\sistec\LunaSafe` path; honest PSR-proxy tags.
9. `tests/test_mapping.py` — grid-consistent DEM selection (was fragile: hardcoded synthetic DEM with live outputs).
10. `tests/test_web_server_cache.py` — NEW: 4 regression tests for cache consistency.

### Verification (executed)
- `python main.py` (real LOLA): 0 rule violations, 3 landing sites, 8.16 km route, all outputs 250×250@240 m consistent.
- `python -m pytest -q`: **41 passed** (37 baseline + 4 new).
- Live endpoints: `/health` 200; `/api/status` honest (REAL LOLA, cache=True, 250×250, 240 m); `/api/rover-route` 200 SUCCESS (14.458 km); `/api/recalculate` KPIs == hazard_summary.csv exactly; `/api/psr-targets` elevations == DEM values (5/5 exact); `/api/audit` PASSED 0 violations/62500 px; `/api/validate-geotiff` real checks pass; `/favicon.ico` 200.
- `landing_sites.json` clearances now multiples of 240 m (were 20 m — physically impossible).
- User live-session observed: site switching + recalculate all returning 200 on fixed server.

### Note
Observed transient "40000 px" audit response during parallel test execution — root cause: `tests/test_main.py` regenerates outputs/ as synthetic as a side effect while a live server session was running. Not a defect of the fix; documented as known test-suite statefulness (tests mutate live outputs/). Tests were re-run sequentially with clean results.

## Batch 3 — Frontend authenticity + chart fixes + test hermeticity (COMPLETE, verified)

### Changes
1. `web/app.js` — **removed fabricated validation-tab charts** (BUG-014): `renderSensitivityCharts()` previously drew hardcoded invented numbers (safe 21.4/34.6…, curve 5.42k…). Now renders ONLY real data (server `sensitivity` from `/api/recalculate`, or client-side computation from the active dataset) with dynamic axes, data-source label, and explicit empty state.
2. `web/app.js` — **dynamic chart axes** (BUG-015): `renderSensitivityBars`/`renderSensitivityCurve` had hardcoded 16.0/12.0 km² scales (synthetic-benchmark extent); real LOLA (3600 km²) overflowed invisibly. Now `niceCeilAxis()` scales from actual data (`fmtKm2` for k-formatting). Verified via node unit tests incl. 240 m/px mock: flat 100×100 grid → 576 km² exact.
3. `web/app.js` — honest KPI chip: `'100.0% Mapped'` → computed `'% Valid Terrain'` (real coverage 81.7% on LOLA w/ nodata).
4. `export_web_data.py` — honest provenance: `_dem_provenance()` derives real-vs-model labels from **raster tags** (was: filename substring); PSR reference now the site's own mask for site bundles + shape guard (never includes mismatched references).
5. `main.py` — passes `dem_path`/`psr_reference_path` explicitly to the bundle export (eliminates stale-`active_site_dem` shadowing).
6. `web_server.py` — run-pipeline worker re-exports the bundle with the SAME dataset it launched.
7. `ml_recommender.py` — `run_mission_autonomy`: DEM auto-selected to match outputs grid + grid-consistency guard (loud error instead of silent mixing).
8. Tests made hermetic (BUG-013): `test_main` redirects all `config.OUTPUT_*` into `tmp_path`; `test_mission_autonomy_artifacts` passes explicit output paths (default args bind at import). **Proven: real 250@240 outputs survive a full pytest run unchanged.**

### Verification (executed)
- `python -m pytest -q` → **41 passed**; before: 250@240, after: 250@240 (hermeticity proof).
- `node --check web/app.js` → OK; node unit tests of chart helpers → ALL PASS.
- Wiring check: 198/198 element IDs referenced by app.js exist in index.html; 39/39 onclick handlers defined.
- 25-point API verification script → **ALL PASS** (health, honest status, bundle consistency incl. 62500-length psr_reference, KPI==CSV exact, rover route, psr-target elevations exact vs DEM, audit 0/62500, sites, validate-geotiff real checks, favicon, psr-validation honest UNLOADED).
- Site-switch E2E (script): shackleton → consistent 200×200 bundle, honest "Shackleton Crater (Procedural Site Model)" status, synced active-site id; back to lola_crop → 250×250 restored. Rover route on Shackleton returns honest `NO_PATH_FOUND` (25-32° walls > 18° rover limit — correct, no fabricated route); on LOLA returns 14.458 km SUCCESS.

## Phase status

- [x] Phase 0: Baseline
- [x] Phase 1: Bug inventory
- [x] Phase 2: Backend root-cause fixes — verified
- [x] Phase 3: Data authenticity & provenance — verified (see DATA_AND_MODEL_PROVENANCE.md)
- [x] Phase 4: ML/model audit — deterministic engines verified honest-labeled (no trained-model claims)
- [x] Phase 5: Visualization repair — verified (fabricated charts removed; dynamic axes; real data only)
- [x] Phase 6: UI audit — wiring verified; KPIs/inspector/rover/3D all data-driven
- [x] Phase 7: E2E workflows — API-level E2E verified (site switch, recalculate, rover, audit, downloads)
- [x] Phase 8: Final gate — see report

## Batch 4 — Hackathon audit: Rover Studio + Artifact Hub unblock (COMPLETE, verified)

### Phase 0 re-discovery (2026-10-21)
- Stack unchanged: Python 3.13 stdlib web server + vanilla JS; 41/41 pytest passing; all 25 API endpoints 200; JS syntax OK; 199 element IDs wired, 0 missing.
- Active dataset: REAL NASA LRO LOLA (250×250 @ 240 m/px, SITE=lola_crop). PSR = DEM-derived proxy (honestly labeled).
- **Root-cause cluster for the two "broken" features was a single HTML defect** (BUG-019): a duplicate, never-closed `landingSitesTab` div wrapped `roverStudioTab` + `exportTab`; CSS `.tab-pane{display:none}` on the parent made both tabs permanently invisible.

### Changes
1. `web/index.html` — removed the dead duplicate TAB 7 block (unclosed `landingSitesTab` + duplicate `sitesGrid`). Rover Studio and Artifacts Hub are now top-level tab panes (FINAL div depth 0, 0 unclosed, 0 duplicate ids).
2. `web/app.js` — `loadDataset` now calls `renderRoverProfileChart()` so the traverse profile renders on load from `DATA.rover_traverse` (was blank until Compute).
3. `web/app.js` — profile chart now draws the Slope curve (amber, right axis, dynamic max) promised by its legend; elevation/battery/shadow preserved.
4. `web/app.js` — `computeRoverRoute` error handling: `data.error || data.message || HTTP status`; on failure resets KPIs to `--`, empties waypoints table, renders failure message on chart, clears 2D/3D route overlays (was: stale KPIs + invisible log-only error).
5. `web/app.js` — `updateRoverTelemetryDisplay(null)` safe-reset; waypoint field guards.
6. `web/app.js` — new `findSummitRidgeGoal()`: summit-ridge goal option now picks the highest-elevation Class-1 (Safe) pixel client-side instead of silently auto-picking a shadow PSR target.
7. `web/index.html` + `web/app.js` — `artifactDatasetBanner`: Artifacts Hub now shows the active dataset name/grid/pixel-size/CRS (from `lastRasterMeta`) so downloads are always attributable.
8. `mission_report.py` — provenance now derived from active `hazard_classes.tif` tags (`SITE`/`DATA_TYPE`) instead of input-file existence (BUG-003 pattern removed from this module); fabricated fallback stats table replaced with honest empty state.
9. `web_server.py` — `/api/download/mission_report.pdf` regenerates when the PDF is older than hazard_classes/hazard_summary/map PNG (no more stale reports after dataset switch).

### Verification (executed)
- `node --check web/app.js` → OK; div-depth scan → balanced (0 unclosed); wiring check → 199/199 IDs, 0 duplicate ids, 39/39 onclick handlers.
- Live server: `/health` lola; rover-route POST alpha→PSR SUCCESS 18.906 km / 70 wps; impassable POST returns NO_PATH_FOUND JSON with `error` (frontend now surfaces it).
- Mission report: PDF was 10 days older than inputs → download auto-regenerated (mtime + size updated); provenance reads SITE=lola_crop → REAL NASA LOLA.
- `python -m pytest -q` → **44 passed** (41 prior + 3 new `tests/test_mission_report.py` regressions: hermetic generation, tag-based provenance, honest empty state; caught + fixed a follow-on `IndexError` on `table_rows[2]` and a hardcoded "PASSED (0 VIOLATIONS)" claim — audit now runs real `validate.verify_rule_consistency` on active rasters).
- Live restart: `/health` lola; rover POST SUCCESS; mission_report.pdf regenerated; single `roverStudioTab`/`exportTab`/`landingSitesTab` each.

## Phase status

- [x] Phase 0: Baseline
- [x] Phase 1: Bug inventory
- [x] Phase 2: Backend root-cause fixes — verified
- [x] Phase 3: Data authenticity & provenance — verified (see DATA_AND_MODEL_PROVENANCE.md)
- [x] Phase 4: ML/model audit — deterministic engines verified honest-labeled (no trained-model claims)
- [x] Phase 5: Visualization repair — verified (fabricated charts removed; dynamic axes; real data only)
- [x] Phase 6: UI audit — wiring verified; KPIs/inspector/rover/3D all data-driven
- [x] Phase 7: E2E workflows — API-level E2E verified (site switch, recalculate, rover, audit, downloads)
- [x] Phase 8: Final gate — see report
- [x] Batch 4 (2026-10-21): Rover Studio + Artifact Hub unblocked (BUG-019..027) — verified

## Batch 5 — Rover Traverse Studio hardened into a real planning tool (COMPLETE, verified)

### Changes
1. `rover_router.py` — `compute_cost_surface(avoid_psr=...)`: PSR/Shadowed-Unknown cells become impassable (∞ cost) when enabled; friendly remediation hints on FAILED/NO_PATH_FOUND (mentions slope limit + avoid-PSR).
2. `rover_router.py` — SUCCESS responses now include `avoid_psr` flag and `hazard_breakdown` (safe/caution/unsafe/shadowed waypoint counts, %, 3D distance).
3. `web_server.py` — `/api/rover-route` accepts `avoid_psr`; when enabled and no explicit goal, auto-goal is the Class-1 pixel nearest the sunlit-safe centroid (never a cold trap).
4. `web/index.html` (Rover tab) — Avoid-PSR toggle; Reset Route + Undo Last Pick; Export GeoJSON/CSV buttons (disabled until a route exists); hazard-breakdown strip (SAFE/CAUTION/UNSAFE/SHADOW %); status banner; loading label on Compute buttons.
5. `web/app.js` — `computeRoverRoute`: loading state, avoid_psr payload, friendly NO_PATH message, hazard-breakdown render, export-button enable; custom-mode validation ("pick points first"); `resetRoverRoute`/`undoRoverRoutePick`; `exportRoverRouteGeoJSON` (LineString + start/goal Points, lunar CRS note, summary props) and `exportRoverRouteCSV` (12-column waypoint table); pending start/goal beacons drawn on the 2D map before Compute; `loadDataset` hydrates breakdown + exports from bundled route.

### Verification (executed)
- Live API: `avoid_psr=true` → SUCCESS 19.7 km, **0% shadow**, breakdown present; `avoid_psr=false` → SUCCESS 18.9 km, 20% shadow; slope 8° corridor → NO_PATH_FOUND with actionable guidance text.
- `pytest`: **47 passed** (3 new: avoid-PSR impassability, goal-in-shadow blocked-or-zero-shadow, hazard_breakdown sums to 100%±2).
- `node --check web/app.js` OK; wiring check 205/205 IDs, 0 dups, 43/43 onclick handlers.

## Batch 6 — Artifact Hub rebuilt as a manifest-driven hub (COMPLETE, verified)

### Root cause
exportTab was a static hardcoded `<div class="downloads-grid">` with 10 fixed `<a href>` cards — no manifest source, no JS, no search/filter/sort, no preview, no upload, and zero integration with Rover Traverse Studio routes.

### Changes
1. `web_server.py` — Artifact Hub backend:
   - `ARTIFACT_CATALOG` (curated title/type/tags for 17 known products) + heuristic fallback; `ARTIFACT_INTERNAL_SKIP` (web_data.json, active_site_dem.tif, artifacts.json) and sidecar skip (.shx/.dbf/.prj/.cpg/.aux/.xml/.ovr).
   - `_artifact_active_dataset_label()` — provenance from `hazard_classes.tif` SITE/DATA_TYPE tags, falls back to RASTER_CACHE dataset_id.
   - `build_artifacts_manifest()` — scans `outputs/` + `outputs/saved_routes/`, builds entries (id/title/type/dataset/date/size/tags/preview_kind/thumbnail_url/download_url/saved), persists `outputs/artifacts.json`; mission_report.pdf keeps the auto-regen download URL.
   - `GET /api/artifacts` → manifest; `POST /api/artifacts/save-route` (SUCCESS-only routes, sanitized label, `_hub` metadata); `POST /api/artifacts/upload` (extension allow-list json/geojson/csv/txt/pdf/png, 20 MB cap, sanitized filename, no-overwrite suffixing).
2. `web/index.html` — exportTab rebuilt: hero PDF card kept; toolbar (search, type filter, dataset filter, sort, Refresh, Upload); loading/error/empty state blocks; dynamic `#artifactGrid`; preview modal; `#artifactHubStatus`. Rover Studio got "Save Route to Artifact Hub" (`#btnSaveRouteToHub`).
3. `web/app.js` — `loadArtifactManifest`/`populateArtifactFilters`/`renderArtifactHub` (search + type/dataset filter + 5 sort modes, PNG thumbnails, type/dataset/saved badges, tags, per-card Preview/Download/Open); `openArtifactPreview` (image, PDF iframe, GeoJSON/JSON with feature-count summary, CSV first-100-rows table, info fallback); `openArtifactOnMap` (routes load into `activeRoverRoute` overlay then 2D Studio; images preview; rasters/vectors open 2D Studio); `saveRouteToHub` (POSTs activeRoverRoute); `uploadArtifactFile` (arrayBuffer→base64→POST, hub status feedback, manifest refresh); `switchTab('exportTab')` triggers `loadArtifactManifest(true)`; `updateRoverExportButtons` also toggles save button; `escHtml()` on all manifest strings.

### Verification (executed)
- Live manifest: 18 artifacts, dataset=lola_crop, 3 PNG thumbnails, types map/raster/vector/data/report/chart/route populated, sidecars + web_data.json + active_site_dem.tif excluded.
- Route round-trip: avoid-PSR route (68 wps) → save-route SUCCESS `route_alpha_to_sunlit_20261022_001508.json` → re-fetch shows `saved=True`, dataset lola_crop, curated title honored.
- Upload: CSV SUCCESS (typed `data`); `.exe` rejected 400; FAILED-status route save rejected 400.
- `pytest`: **50 passed** (3 new: manifest scan + skip rules, saved-route `_hub` metadata, sidecar rejection).
- `node --check web/app.js` OK; wiring 221/221 IDs, 0 dups (reported missing `if` is a false positive from inline `onclick="if(event.target===this)…"` guard).

## Known remaining (documented, non-blocking)
- Accessibility is minimal (1 aria attribute in index.html) — P3 improvement, not regression.
- Browser-level automation (Playwright) not installed; UI verified via static analysis + wiring checks + live session observation instead.
- `dashboard.html` is an unreferenced legacy artifact (regenerable via `python build_interactive_ui.py`); not served in the app flow.
- Test suite mutates `data/sites/*` rasters when site-switch tests run — observed in git status from the user's live session; regenerating site rasters is by-design behavior of `select-site`.
- ~~PSR mask for LOLA remains a DEM-derived proxy (no official PDS PSR product exists in the LOLA GDR polar archive — verified 2026-10-18); labeled honestly everywhere.~~ **RESOLVED this batch**: published Mazarico et al. (2011) LPSR product now used as primary PSR source (BUG-031); DEM-threshold proxy no longer written for real-data paths.

---

## Batch 7 — Phase 3: Real Public Lunar Datasets, Artemis III Regions & Preprocessing Pipeline (2026-10-22)

### Bugs fixed (BUG-030 through BUG-034)
| ID | Sev | Summary |
|---|---|---|
| BUG-030 | **P0** | ~98% of real LOLA terrain labeled Unsafe (roughness thresholds not resolution-aware) |
| BUG-031 | P1 | Stale `outputs/psr_binary.tif` caused 1,835 phantom audit violations |
| BUG-032 | P2 | All nine artemis_* real crops mislabeled "Procedural Site Model" |
| BUG-033 | P3 | Data Sources panel static; Diviner/PRADAN/MoonTrek/LROC + checksums + Artemis regions invisible |
| BUG-034 | P3 | `data/DOWNLOAD_INSTRUCTIONS.md` referenced dead USGS URL + wrong product names |

### 1. Reproducible preprocessing pipeline (`preprocess_lunar_data.py`)
- `ensure_download()` — checksum-verified (SHA-256 pinned in config) downloads from NASA PDS Geosciences + MIT imbrium.mit.edu; `--skip-download` offline mode.
- `crop_dem_roi()` — LDEM_75S_240M JP2 → 250×250 @ 240 m south-pole crop, DN×0.5 → meters rel. to R=1737.4 km.
- `align_raster_to_grid()` — reads JP2 array explicitly (never `rasterio.band`, which silently ignores src_crs override) then bilinear/nearest reprojects onto DEM grid; LPSR empirical alignment resolved to lon_0=0 (label says 180 — verified via terrain/PSR co-location).
- `derive_psr_from_lpsr()` — **published** Mazarico et al. (2011) LPSR product (DN>0=PSR), replaces DEM-threshold proxy for real-data paths.
- `derive_illumination_fraction()` — AVGVISIB DN×0.00004 → [0,~0.93] visibility fraction.
- Terrain (Horn slope, 3×3 local std roughness, TRI) + hazard classification (resolution-scaled) + hazard_classes.tif + summary CSV.
- Web assets: compact float32 XYZ `.f32` tiles + meta.json, `cost_grid.json`, `artemis_iii_regions.geojson`, illumination_frac array in bundle.
- `prepare_lola_dataset.convert_real_lola_to_geotiff()` now a thin backward-compatible wrapper over the pipeline (server download-lola endpoint keeps working unchanged).

### 2. Resolution-aware roughness thresholds (`config.scaled_roughness_thresholds`)
- Reference: `REFERENCE_ROUGHNESS_PIXEL_M = 20.0`; linear baseline scaling (local 3×3 std grows with pixel size).
- At 240 m/px: Safe <18 m, Caution <36 m, hard-Unsafe ≥60 m (vs 1.5/3/5 m at 20 m reference).
- Slope thresholds (angular: 5/10/15°) deliberately unchanged; `HLS_LANDING_SLOPE_MAX_DEG = 8.0` added as documented reference constant (our Safe band is stricter than the published HLS bound).
- `hazard.classify_hazard_surface`, `compute_hazard_score`, `validate.verify_rule_consistency` all accept optional `pixel_size_m`; default None preserves the 20 m reference behavior for synthetic/tests.
- Every caller passes the active pixel size: `web_server.py` (recalculate, audit, select-site, psr-targets, rover-route), `mission_report.py`, `preprocess_lunar_data.py`, `rover_router.compute_cost_surface` (roughness cost normalization), `ml_recommender.recommend_landing_sites` (smoothness score).
- `export_web_data.py` bundle `defaults` now carries scaled `rough_safe_max`/`rough_caution_max`/`rough_hard_unsafe`/`rough_norm_max` + `rough_scale_factor` + `pixel_size_m`.
- Frontend: `TH` object synced from `DATA.defaults` on every `loadDataset`; client-side classification, plain-language inspector text, Nominal-Baseline slider preset, and resetDefaults all use scaled values.

### 3. Official Artemis III candidate regions (9, NASA Oct 28 2024 down-select)
- `config.ARTEMIS_III_REGIONS` — real CLS coordinates (Wueller et al. 2026 Table A1 means): Peak near Cabeus B, Haworth, Malapert Massif, Mons Mouton, Mons Mouton Plateau, Nobile Rim 1, Nobile Rim 2, de Gerlache Rim 2, Slater Plain.
- `lunar_catalog.LUNAR_SITES` extended with `artemis_*` entries (category "Official Artemis III Candidate Region (NASA Oct 2024)", `is_real_data: true`).
- `_crop_real_region()` — pyproj Moon2000 geographic→stereographic transform + rasterio Window crop from LDEM JP2 + matching LPSR window (binary PSR from published product).
- `generate_site_terrain('artemis_*')` returns real crop (250×250 @ 240 m); `save_site_dataset` persists to `data/sites/artemis_*/`; `handle_api_select_site` recomputes terrain/hazard with `is_synthetic=False` for lola_crop + artemis_*.

### 4. Public dataset registry + Data Sources panel
- `config.PUBLIC_DATASETS` — 7 entries (LDEM, LPSR, AVGVISIB downloaded; Diviner, Chandrayaan-2 PRADAN, Moon Trek, LROC NAC_POLE_PSR documented-only) each with publisher/url/license/citation/status/role/access_notes.
- `GET /api/data-sources` — serves registry with live `local_exists`/`local_size_bytes`/`sha256_short` per file + Artemis-region list + active hazard thresholds.
- `web/index.html` methodTab card replaced with dynamic containers (`#dataSourceList`, `#artemisRegionList`, `#hazardThresholdNote`); `loadDataSourcePanel()` in app.js renders status-colored cards with citations, URLs, local-file info, and access_notes.
- `data/DOWNLOAD_INSTRUCTIONS.md` rewritten: exact PDS/MIT URLs + SHA-256 checksums + PowerShell commands + manual steps for Diviner (PDS PPI browse), PRADAN (registration required), Moon Trek (portal only), LROC shapefile (403 to scripts — browser download only).

### 5. Supporting fixes
- Pipeline writes published PSR to both `data/lola_psr_mask.tif` and canonical `outputs/psr_binary.tif` (BUG-031).
- `RASTER_CACHE`/`_describe_dem` provenance extended to artemis_* (BUG-032).
- Audit endpoint Rule 2/Rule 6 descriptions now show active resolution-scaled thresholds.
- `config.py` added `from typing import Dict` (NameError in scaled_roughness_thresholds type hint).
- `lunar_catalog._crop_real_region` uses `@` matmul instead of deprecated `*` for Affine transforms.

### Verification (executed)
- Pipeline run: checksums verified (3/3), DEM crop 250×250 valid=62494/62500 elev −3418..1955 m; published LPSR 9335/62500 PSR px (14.94%); mean illumination 0.1775; hazard: Safe 2.91%, Caution 36.03%, Unsafe 55.96%, Shadowed-Unknown 5.11%, NoData 0.01%.
- `pytest`: **61 passed** (11 new in `tests/test_phase3_datasets.py`: scaled-threshold math, classification outcome change at 240 m, audit consistency, registry integrity, checksums pinned, 9 Artemis regions, real-elevation-range crop, published-LPSR provenance, pipeline wrapper delegation).
- `node --check web/app.js` OK; wiring 224 IDs, 0 dups.
- Live probes (server restart): health OK; `/api/data-sources` SUCCESS 7 datasets (3 downloaded w/ checksums, 4 documented-only w/ access notes) + 9 Artemis regions; `/api/sites` 15 total (9 artemis); select-site artemis_mons_mouton → SUCCESS, real 250×250 crop (elev −1925..6986 m, 3816 PSR px), `is_synthetic=False`, px=240.0; select-site artemis_haworth → status "REAL NASA LRO LOLA — Haworth (Artemis III Candidate)", audit 0 violations; select-site lola_crop → audit 0 violations, Rule 2 text shows "18.0 m (resolution-scaled)".
- web_data.json: defaults rough_safe_max=18.0, rough_hard_unsafe=60.0, scale_factor=12.0, pixel_size_m=240.0; illumination array 62500 values populated.
- Deliberate decision logged: slope thresholds kept at 5/10/15° (established, tests assert exact values, frontend ~20 sites, stricter than HLS 8° bound); `HLS_LANDING_SLOPE_MAX_DEG = 8.0` documented as reference only — not swapped into classification rules.

### Honest data provenance summary (what is downloaded vs documented-only)
| Dataset | Local file? | Status |
|---|---|---|
| LDEM_75S_240M V2.1 (NASA PDS) | Yes (`data/ldem_75s_240m.jp2`, SHA verified) | Downloaded + processed |
| LPSR_65S_240M V1.05 (MIT/GSFC, Mazarico 2011) | Yes (`data/external/`, SHA verified) | Downloaded + used as primary PSR |
| AVGVISIB_65S_240M V1.05 (MIT/GSFC) | Yes (`data/external/`, SHA verified) | Downloaded + used for illumination fraction |
| Diviner polar temperatures (NASA PDS PPI) | **No** | Documented-only (access steps in registry) |
| Chandrayaan-2 OHRC/TMC-2 (ISRO PRADAN) | **No** | Documented-only (registration required) |
| Moon Trek basemap tiles (NASA GSFC) | **No** | Documented-only (portal, not bulk API) |
| LROC NAC_POLE_PSR shapefile | **No** | Documented-only (403 to scripts; MIT LPSR used instead) |

---

## Batch 8 — Phase 4: Dynamic Website — illumination, lunar-day time slider, comparison, URL state (2026-10-22)

### Bugs fixed (BUG-035, BUG-036)
| ID | Sev | Summary |
|---|---|---|
| BUG-035 | **P0** | `/api/data` served `NaN` literals → browser JSON.parse died → entire dashboard dataset load dead (introduced by Phase 3 illumination export, caught by Phase 4 headless-Edge smoke) |
| BUG-036 | P1 | AOI-aware `computeSensitivityData` called `.has()` on a legacy numeric `validPx` → `loadDataset` crash even after BUG-035 |

### 1. Analytic lunar-day illumination model (`illumination_time.py`)
- `solar_elevation_azimuth_deg(lat, hour_angle_deg, decl)` — standard spherical solar position (azimuth +180 convention); `frame_schedule(frames, latitude_deg=-85.0)` spreads frames over the 29.53-day lunar day as hour angles.
- Latitude honesty note: with fixed southern-summer declination (−1.54°) the sun **never sets** at the pole (constant +1.54°) and stays above horizon at −89°; schedules/tests use −85° so night frames exist.
- `compute_frames(dem, pixel_size_m, latitude_deg, frames, nodata)` — uint8 volume (0 = modeled shadow/NoData, 255 = lit), nearest-neighbour ray-march toward the sun (≤24 km, 1 m eps), night frames all dark.
- Disk cache: `outputs/web/illum_time/{key}.bin` + `.meta.json`, key = sha256(dataset_id|frames|HxW|lat|px|MODEL_VERSION)[:24], atomic `.part` write, size-validated hits; `MODEL_VERSION = "analytic_solar_horizon_v1"`.

### 2. New API endpoints (`web_server.py`)
- `GET /api/regions` — 9 Artemis III candidate regions (Wueller et al. 2026 Table A1) + `geojson_url`, used by the dynamic region-jump chips.
- `GET /api/tiles/{layer}/meta.json` and `GET /api/tiles/{layer}/{z}/{x}/{y}` — layer whitelist `{hazard, illumination}`, z=0, 256×256 float32 row-major `.f32` + meta.json; bad layer → 404, bad coords → 400.
- `GET /api/illumination-time[.bin]?frames=` — meta (sun elevations per frame, schedule, honesty labels, disclaimer) and raw uint8 binary; `frames` clamped 8–48, latitude from `LUNAR_SITES`, 503 without an active dataset, `Cache-Control: max-age=3600`.
- `GET /api/data` now serves strict JSON: stale on-disk bundles containing `NaN`/`Infinity` tokens are sanitized to `null` on the fly (BUG-035 defense-in-depth; clean files keep the raw fast path).

### 3. Frontend (`web/app.js`, `web/index.html`, `web/styles.css`)
- **Illumination layer + time overlay**: `mapLayers.illumination`/`timeillum` with offscreen ramps (AVGVISIB + analytic frame tint, nodata gray), composite steps 4b (base illumination) and 7b (time overlay above PSR outlines); layer-stack row with visibility/opacity.
- **Lunar-day time slider** (2D Studio sidebar): frame slider, play/stop (220 ms), overlay checkbox, per-frame label ("Lunar local time 00:00 — Sun 1.7° below horizon (night) — azimuth 180° — frame 1/24"), `ANALYTIC MODEL` badge + explicit disclaimer (not observed data; published LPSR stays authoritative), stale-load generation guard (`illumTimeGen`), grid-mismatch guard, `.bin` uint8 decode.
- **Landing-site comparison** (Candidate Screening tab): up to 3 picks from recommended sites or arbitrary map pixels, 100 m ellipse metrics (mean slope/roughness, illumination %, PSR %, hazard classes, composite `S`), ranked table + verdict with documented formula, A/B/C dashed rings on the map, keyboard `s`/`p` shortcuts.
- **URL/app state sync**: `buildAppState`/`writeUrlState` (push for tab/tool/site, throttled replace otherwise) + `applyUrlStateOnBoot`/popstate — params `tab, site, tool, ly, z, cx, cy, sel, sw, swp, t, to, cmp` fully round-trip (deep links, refresh, back/forward).
- **Polish**: animated KPI/legend counters (rAF eased, 700 ms), AOI-aware sensitivity charts (Set-based AOI restriction, source label), loading skeletons (map, lists, data-source panel), global error boundary + fatal toast, ARIA roles/labels (`tablist`/`tab`/`tabpanel`, aria-live announcer) and keyboard shortcuts (Esc, arrows pan, +/− zoom, 1–4 tools), dynamic region-jump chips from `/api/regions`.

### Verification (executed)
- `pytest`: **79 passed** (18 in `tests/test_phase4_apis.py`: solar-position sanity, schedule coverage, night-all-dark, determinism, nodata darkness, meta honesty labels, cache-key/cache-hit, live ephemeral-port tests for regions/tiles/illumination meta+bin+clamping, strict-JSON `/api/data`, `_finite_round`).
- `node --check web/app.js` OK; wiring check: 245 IDs referenced, 0 missing (only known `onclick="if(...)"` false positive).
- Live probes (server restarted): health OK; `/api/regions` 9 regions (selected `artemis_haworth`); hazard tile meta + 262,144 B bin, unknown layer 404; `/api/illumination-time?frames=24` computed 4.17 s → cached, `.bin` = 1,500,000 B (24×250×250).
- Headless-Edge smoke (`--headless --dump-dom` with `?tab=mapStudioTab&tool=inspect&ly=hazard:1:1.00,illumination:1:0.80`): **0 page error lines**; dataset loaded (skeleton removed, KPI 350.41 km², REAL NASA LOLA — Haworth); time slider enabled with populated frame label + ANALYTIC MODEL badge; 5 compare chips; 9 region chips; tab/`ly` restored from URL (illum opacity 80%); ARIA `tablist`/`tab` roles injected; sensitivity charts mounted; no console errors (only CDN tracking-prevention warnings).

---

## Batch 9 — Phase 5: Performance & Quality (2026-10-22)

Goal (user brief): lazy-load heavy components, Web Worker for heavy compute, memoization, tile
caching, fast first load with Lighthouse before/after report, tests for the hazard classifier and
pathfinder (known grid, expected route), dead code removal + lint fixes, `npm run build` passing.

### 5A - Lighthouse baseline (headless Edge, npx lighthouse@12)
- Performance 0.36 | FCP 8.0 s | LCP 21.3 s | TBT 30 ms | CLS 0.484 | TTI 21.3 s | weight 5,472 KiB
  | a11y 0.78 | best-practices 0.96. Opportunities: 4,365 KiB compressible text, 6,250 ms
  render-blocking, 485 KiB unused JS (three.min.js 603,445 B), 67 KiB unminified JS, 36 KiB unused CSS.

### 5B - Server (`web_server.py`)
- HTTP/1.1 keep-alive (all Content-Length framed), gzip for text-like types >1 KiB
  (`Vary: Accept-Encoding`, bounded 64-entry cache), ETag + `If-None-Match` -> 304.
- Cache policies: app.js/styles.css `max-age=60`, vendor 86400, outputs 60, tiles 3600, index no-cache.
- `GET /api/data?parts=core` (drops illumination+boulder_hazard, adds `deferred_parts` marker) and
  `?parts=extras` (illumination+boulder only); both gzip+ETag keyed; strict-JSON NaN sanitizer kept.
- Wire results: index 131,281 -> 25,863 B; app.js 256,967 -> 61,967 B (304 -> 0 B); styles 10,625 B;
  `/api/data` 2,557,550 -> 559,743 B; parts=core 408,164 B (28% smaller than full-wire); keep-alive PASS.

### 5C - Frontend (`web/app.js`, `web/index.html`, `web/hazard_core.js` NEW, `web/worker.js` NEW, `web/styles.css`)
- Lazy Three.js: removed head `<script>` vendor tags + `document.write` CDN fallback; boot no longer
  calls `init3DScene()`; `ensureThreeJs()` (local vendor -> CDN fallback, promise-cached) wired into
  `switchTab('terrain3dTab')` and `retry3dContext()`; raycaster/mouse3d now `let`, created in
  `init3DScene()` (BUG-037); non-blocking Google Fonts + KaTeX CSS (`preload` + noscript).
- Web Worker preview: `hazard_core.js` (pure `sensitivity` + `previewAll`, DOM-free, shared by app,
  worker, Node tests) + `worker.js` (init/ready/preview protocol, zero-copy hazard transfer, params
  echo per BUG-038); `previewReclassifyClient` = param memo -> worker dispatch -> shared
  `applyPreviewResults`; stale responses dropped by request id; sync fallback on any worker error;
  worker + memos reset on dataset load (`stateVersion`).
- Deferred rasters: `loadDataset` fetches `?parts=core` (full-bundle fallback) then background
  `?parts=extras` merge rebuilds the illumination offscreen + repaints.
- Memoization: preview params (incl. stateVersion), `buildAoiIndexSet` (cap 32),
  `computeCompareMetrics` (cap 64); `computeSensitivityData` now a thin HazardCore wrapper;
  dead `computeAndRenderClientSensitivity` removed.
- CLS: `font-variant-numeric: tabular-nums` on KPI values/chips/deltas (BUG-040).
- Server routes added for `/hazard_core.js` + `/worker.js` (BUG-039).

### 5D - Lint, dead code, build tooling
- pyflakes 4.0.3 clean over 34 Python files (11 findings fixed: unused imports in lunar_catalog,
  mission_report, 8 test files; unused locals in test_ml_recommender/test_validate).
- New dependency-free `package.json` + `scripts/build.js`: `npm run lint` (JS syntax + pyflakes),
  `npm run build` (lint + index.html local-asset integrity + hazard_core-before-app.js ordering +
  lazy-Three head check), `npm test` (node protocol tests + pytest).

### 5E - New tests (6 pytest + 5 Node)
- `test_hazard.py::test_known_grid_exact_class_map` — hand-computed 4x4 grid, exact 5-class map,
  score spot checks (0.04533 / 0.73667), all five classes present.
- `test_rover_router.py::test_known_grid_exact_route_single_channel` — sealed grid, only row 2 open:
  waypoints EXACTLY `[(2,1) ... (2,7)]`.
- `test_rover_router.py::test_known_grid_route_forced_through_single_gap` — wall at col 4 with sole
  gap (3,4): path crosses col 4 exactly once at the gap; start/goal present; wall never entered.
- `test_phase4_apis.py` — 3 live-endpoint tests: parts=core (marker list, no illumination/boulder,
  core rasters present), parts=extras (deferred only, no dem/slope), parts=core strict-JSON (no NaN).
- `tests/js/worker_proto.test.js` — simulated worker globals: pre-init error, ready, params echo,
  zero-copy exact-size transfer, hand-computed 16-px class map, sequential ids.

### 5F - Lighthouse after + deliverables
- After: **perf 0.80** | FCP **2.0 s** | LCP **2.5 s** | TBT 140 ms | CLS **0.297** | SI 2.0 s |
  weight **2,373 KiB** | a11y 0.78 | bp 0.96 (identical flags to baseline).
- Docs: FINDINGS_REPORT.md (Phase 0 findings + fix status + final state), README §10 architecture
  (mermaid), §11 judges demo script (5-min table), §12 limitations/next steps + before/after table,
  README test counts 79 -> 85, BUG_TRACKER BUG-037..040.

### Verification (executed)
- `npm run build` PASSED; `npm run lint` PASSED (34 py files clean); `npm test`: 5/5 Node + **85/85 pytest**.
- HTTP probe 24/24 (new routes, gzip, parts endpoints, keep-alive, strict JSON).
- Headless-Edge interaction smoke (temp same-origin harness): boot KPIs via core bundle, deferred
  extras merge log, worker preview path (`previewRequestSeq=1`, hazard 62,500 px applied), memo skip
  (repeat params -> seq unchanged), lazy 3D (THREE + initialized + canvas + raycasters), 0 console errors.
- pyflakes clean; `node --check` on app.js/hazard_core.js/worker.js OK; wire check clean.

---

## Batch 10 — Real-time sensitivity charts (BUG-041, 2026-10-22)

User report: "In the Mission Command dashboard the graphs are looking like a picture;
apply real graphs so that it can change real-time changes efficiently."

### Root cause (evidence, not guesswork)
- One POST to `/api/recalculate` returned `summary.unsafe = 1565.63 km² (43.49%)` while
  the SAME response's `sensitivity.curve` read `3533.70 km²` at all 10 thresholds and all
  three bars were identical (4.4/37.6/3533.7) — sensitivity mixed the scaled `score_h`
  with RAW 20 m-reference roughness gates; 61,350/62,500 px pass `roughness >= 5.0` at
  240 m/px, which mathematically forces a flat line.
- The client preview path (hazard_core) had the identical raw-threshold defect, so live
  drag frames showed ~98% Unsafe until the server response overwrote the KPIs — and the
  server overwrite re-rendered the already-degenerate charts (screenshot state).
- `validate.run_slope_sensitivity_analysis` (slope_sensitivity.png) also used raw
  `config.ROUGHNESS_*`; Reset-to-Baseline and the nominal preset pushed TH's effective
  18/60 m values into raw-range sliders (clamped to max 3.0/8.0).

### Fixes
- `web_server.py` sensitivity: effective thresholds via `config.scaled_roughness_thresholds(px)`;
  bar scenario semantics changed so `t` is the hard-unsafe slope limit → exact invariant
  `bars[t].unsafe_km2 == curve[t]`; safe gate uses the live `slope_safe` param (constant
  across bars, equals classify Safe).
- `web/hazard_core.js`: optional `rNorm` divisor (explicit scaled callers win; omission
  falls back to `rHard` = legacy bit-identical); bars predicate aligned with server;
  sensitivity sampling switched from 2x subsample to full-grid exact (charts now match
  KPIs to the decimal; compute runs in the worker).
- `web/app.js`: `roughScale()`/`scaledRoughParams()` bridge raw slider meters → effective
  (uses `DATA.defaults.rough_scale_factor`, fallback px/20) in `previewReclassifyClient`
  and `computeSensitivityData`; worker drag coalescing (`previewInFlight` + trailing
  `previewQueuedRaw` flushed via `flushQueuedPreview()`, resets on worker death/switch);
  reset/preset convert TH roughness with `/ roughScale()`.
- `web/index.html`: "Simulated impact…" subtitle replaced with live-recompute wording;
  Validation-tab bar title corrected to the real 5°/10°/15° series.
- `validate.py`: scenario analysis uses scaled `norm_max`/`hard_unsafe_min`/`safe_max`.

### Verification (executed)
- Live POST: curve 3345.98 → 1565.63 km² (range 1780.35; plateau == summary.unsafe),
  bars 3075.96 / 2016.00 / 1565.63 with safe 383.21 constant == summary; bar/curve
  cross-equality at 5° and 15° exact; every bar totals 3600.00 km².
- Node client-vs-server: 383.04/1379.46/1566.03/271.47 vs 383.21/1379.69/1565.63/271.47
  (residual 0.17 km² = float32-vs-float64 at the H=0.60 boundary; KPI ribbon shows server
  values after the authoritative recalc).
- Headless-Edge page load: 0 uncaught errors; KPI ribbon 383.21 / 1565.63; chart target 15.0.
- `npm run build` PASSED (34 py files pyflakes-clean); `npm test`: **10/10 Node + 86/86 pytest**
  (new `test_api_recalculate_sensitivity_is_real_and_scaled` — flatline, descent, summary
  parity, bar/curve equality, safe parity, stacked totals; new `tests/js/hazard_core_rnorm.test.js`
  — 5 tests for the rNorm divisor + bar/curve predicate parity).
- Docs: README + FINDINGS_REPORT counts 85 → 86; BUG_TRACKER BUG-041.
