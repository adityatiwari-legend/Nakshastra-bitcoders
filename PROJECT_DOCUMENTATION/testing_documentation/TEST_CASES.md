# TEST_CASES — Catalog

**IDs:** `TC-AUTO-nn` (existing automated), `TC-PLAN-nn` (planned), `TC-MAN-nn` (manual release
gate). Statuses: ✅ passing (see [`TEST_EXECUTION_STATUS.md`](TEST_EXECUTION_STATUS.md)) ·
⏳ planned · 🔁 every release (manual).

> Test names/behaviours below were read from `tests/*.py` and executed on 2026-10-17 (32 passed).

---

## 1. Automated — existing suite (32)

### Smoke & config (`tests/test_smoke.py`)
| ID | Test | Asserts |
| :-- | :--- | :--- |
| TC-AUTO-01 | `test_config_constants` | thresholds, class ids, PROJ.4 CRS sanity, no `EPSG:4326` |
| TC-AUTO-02 | `test_synthetic_crater_topography` | shape/bounds/crater depression |
| TC-AUTO-03 | `test_synthetic_geotiff_roundtrip` | write→read preserves shape/CRS/nodata |

### I/O & alignment (`tests/test_preprocessing.py`)
| ID | Test | Asserts |
| :-- | :--- | :--- |
| TC-AUTO-04 | `test_inspect_raster` | stats fields, valid/nodata counts |
| TC-AUTO-05 | `test_earth_epsg_protection` | Earth-CRS rasters raise `ValueError` |
| TC-AUTO-06 | `test_grid_mismatch_detection_and_loud_failure` | both mismatches reported; `--fail-on-mismatch` raises |
| TC-AUTO-07 | `test_grid_resampling_alignment` | resampled layer lands on DEM grid |

### PSR (`tests/test_psr.py`)
| ID | Test | Asserts |
| :-- | :--- | :--- |
| TC-AUTO-08 | `test_binarize_psr_and_nodata_exclusion` | threshold + NoData→0 |
| TC-AUTO-09 | `test_clean_psr_mask_removes_tiny_components` | `<9 px` components removed |
| TC-AUTO-10 | `test_calculate_psr_area_exactness` | area = px count × px area (exact) |
| TC-AUTO-11 | `test_vectorize_psr_to_polygons` | columns, positive areas, valid geometry |
| TC-AUTO-12 | `test_process_and_export_psr_end_to_end` | GeoTIFF+GeoJSON written with tags |

### Terrain (`tests/test_terrain.py`)
| ID | Test | Asserts |
| :-- | :--- | :--- |
| TC-AUTO-13 | `test_flat_surface_terrain_metrics` | slope/roughness ≈ 0 |
| TC-AUTO-14 | `test_planar_ramp_slope_exactness` | known ramp → exact slope (Horn kernel) |
| TC-AUTO-15 | `test_nodata_preservation_in_terrain` | NoData stays −9999 everywhere |
| TC-AUTO-16 | `test_process_terrain_pipeline_end_to_end` | 4 GeoTIFFs + histogram PNG |

### Hazard (`tests/test_hazard.py`)
| ID | Test | Asserts |
| :-- | :--- | :--- |
| TC-AUTO-17 | `test_hazard_score_formula_and_normalization` | `H=.5S+.3R+.2D`, clipping |
| TC-AUTO-18 | `test_hard_overrides_trigger_class_3_unsafe` | slope≥15 or rough≥5 → 3 |
| TC-AUTO-19 | `test_shadowed_unknown_vs_unsafe_psr` | PSR→4 unless already unsafe |
| TC-AUTO-20 | `test_safe_and_caution_classification` | thresholds → 1/2 |
| TC-AUTO-21 | `test_nodata_is_never_treated_as_safe` | invalid → 0 (rule 9) |
| TC-AUTO-22 | `test_process_hazard_pipeline_end_to_end` | raster + 5-row CSV |

### Mapping / recommender / validation / pipeline
| ID | Test | File | Asserts |
| :-- | :--- | :--- | :--- |
| TC-AUTO-23 | `test_hillshade_computation` | test_mapping | hillshade values sane |
| TC-AUTO-24 | `test_generate_4panel_hazard_map_end_to_end` | test_mapping | PNG+PDF exist, size>0 |
| TC-AUTO-25 | `test_boulder_micro_hazard_detection` | test_ml_recommender | prob>0.5 at peaks, ~0 elsewhere |
| TC-AUTO-26 | `test_landing_site_recommender` | test_ml_recommender | sites returned with expected fields |
| TC-AUTO-27 | `test_mission_autonomy_artifacts` | test_ml_recommender | JSON schema + `boulder_hazard.tif` |
| TC-AUTO-28 | `test_compute_psr_metrics_exactness` | test_validate | hand-computed P/R/IoU/F1 |
| TC-AUTO-29 | `test_verify_rule_consistency_passes_on_pipeline_output` | test_validate | 0 violations on pipeline output |
| TC-AUTO-30 | `test_verify_rule_consistency_catches_deliberate_errors` | test_validate | **mutation test** trips specific rules |
| TC-AUTO-31 | `test_slope_sensitivity_analysis_execution` | test_validate | runs; safe area monotonic |
| TC-AUTO-32 | `test_main_pipeline_execution` | test_main | exit 0 + 13 artifacts exist ⚠ rewrites `outputs/` |

---

## 2. Planned automated cases (IDs stable — do not renumber)

| ID | Target | Steps / assertion | Fixes risk | Task |
| :-- | :--- | :--- | :--- | :--- |
| TC-PLAN-01 | `web_server` boot | start on free port → `GET /health` 200 `ONLINE` | — | T-08 |
| TC-PLAN-02 | status contract | `GET /api/status` keys ⊇ documented set; `summary_data` counts sum to `total_pixels` | I-06-ish | T-08 |
| TC-PLAN-03 | bundle integrity | `web_data.json` arrays all = `width*height` | I-06 | T-08 |
| TC-PLAN-04 | **audit key contract** | `set(verify_rule_consistency()['violations'])` == keys read by `handle_audit`; assert `rule_results[3].violations` > 0 when a safe pixel sits in PSR | I-03 | T-08b |
| TC-PLAN-05 | area units | run `/api/recalculate` on a 240 m cache → reported km² uses 240² not 20² | I-02 | T-08 |
| TC-PLAN-06 | param forwarding | POST run-pipeline with `slope_safe_max=7` → child `main.py` sees 7 (or documented behaviour) | I-04 | T-08 |
| TC-PLAN-07 | stale detection | export bundle then rewrite rasters → endpoint/flag reports mismatch | I-06 | T-08 |
| TC-PLAN-08 | report honesty | extract `mission_report.pdf` text → audit table matches `POST /api/audit`, no literal `0 / PASSED` fallback | I-14 | T-03 |
| TC-PLAN-09 | traversal | `GET /api/download/..%2f..%2fconfig.py` → 404, body not source | SEC-01 | T-13 |
| TC-PLAN-10 | 409 / 404 | second `run-pipeline` while busy → 409; unknown POST → 404 | — | T-08 |
| TC-PLAN-11 | non-destructive | full suite leaves `git status` clean | T-09 | T-09 |
| TC-PLAN-12 | converter portability | `prepare_lola_dataset.py` works from any CWD | I-15 | T-18 |
| TC-PLAN-13 | recommender pixel size | LOLA-shaped cache → `req_radius_px` uses 240 m | I-12b | T-02 |
| TC-PLAN-14 | clearance semantics | `clearance_radius_m` documented/measured consistently in card + PDF | I-05-adjacent | T-12b |
| TC-PLAN-15 | lint gate | `pyflakes *.py tests\*.py` → 0 errors (or allow-list) | I-16 | T-07 |

## 3. Manual release-gate cases (from doc 14 §6, one row each)

| ID | Area | Pass condition |
| :-- | :--- | :--- |
| TC-MAN-01 | CLI | `python main.py` exit 0, `total_violations 0` |
| TC-MAN-02 | summary | `hazard_summary.csv` 5 rows; counts sum to grid size |
| TC-MAN-03 | bundle | `python export_web_data.py` after raster changes; integrity check passes |
| TC-MAN-04 | API | `/api/status` ONLINE, correct `active_dataset` |
| TC-MAN-05 | Map Studio | 7 layers render; inspector shows class + reason |
| TC-MAN-06 | sliders | areas update ≈1 s; audit chip stays 0 |
| TC-MAN-07 | pipeline | log streams; KPIs refresh; no console errors |
| TC-MAN-08 | 3D | mesh, sun-driven shadows, transect plots |
| TC-MAN-09 | downloads | 4 artifacts non-empty; report opens |
| TC-MAN-10 | offline demo | reloads cache without restart |
| TC-MAN-11 | honesty | PSR card `UNLOADED` (no fabricated %); provenance says `SYNTHETIC DEMO` |
| TC-MAN-12 | security | only intended files served (spot-check `/outputs/../config.py` blocked after T-13) |

## 4. Defect-detected-by map

| Issue | Caught by today? | Would be caught by |
| :-- | :-: | :--- |
| I-01 self-comparison | ❌ (unit only) | an e2e assertion on `psr_validation` vs independent file |
| I-02/I-03/I-04/I-11/I-12 | ❌ | TC-PLAN-04/05/06 |
| I-06 stale bundle | ❌ | TC-PLAN-03/07 |
| I-14 hard-coded report | ❌ | TC-PLAN-08 |
| SEC-01 traversal | ❌ | TC-PLAN-09 |
| I-16 dep drift | ❌ | TC-PLAN-15 + requirements sync check |
