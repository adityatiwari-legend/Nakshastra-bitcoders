# 14 — Testing and Quality Assurance

*Verified 2026-10-17: `python -m pytest -q` → **`32 passed, 1 warning in 25.28s`**.*

---

## 1. Test stack

| Item | Value |
| :--- | :--- |
| Framework | `pytest==9.1.1` (pinned in `requirements.txt:12`) |
| Layout | flat `tests/` package, `tests/__init__.py` |
| Discovery | `python -m pytest` from repo root; each file starts with the `sys.path.insert(ROOT_DIR)` idiom (`tests/test_smoke.py:1-8` pattern) |
| Fixtures | **none defined** — no `conftest.py`; every test builds its own tmp files via `tmp_path` |
| Markers | **none** — no `@pytest.mark.slow`/`serial`, no `pytest.ini`/`pyproject.toml`/`setup.cfg` |
| Coverage tool | **none installed** (no `pytest-cov`, no `coverage`) |
| Linters in CI | **no CI at all** (no `.github/workflows`) |
| Lint tool available | `pyflakes==4.0.3` installed in the venv but **undeclared** in requirements (Issue I-16) |

---

## 2. Complete test inventory (32 tests)

### `tests/test_smoke.py` — 3 tests
| Test | Asserts | Guards |
| :--- | :--- | :--- |
| `test_config_constants` | threshold values, class ids, `LUNAR_SOUTH_POLE_PROJ4` contains `+proj=stere`/`+R=1737400`, no `EPSG:4326` | config drift, accidental Earth CRS |
| `test_synthetic_crater_topography` | shape, min/max sane, crater depression exists | generator maths |
| `test_synthetic_geotiff_roundtrip` | write → read preserves shape/CRS/nodata | `io_utils` I/O |

### `tests/test_preprocessing.py` — 4 tests
| Test | Asserts |
| :--- | :--- |
| `test_inspect_raster` | stats dict fields, valid/nodata counts |
| `test_earth_epsg_protection` | `ValueError` when a raster carries `EPSG:4326`-like CRS (`io_utils.py:199-206`) |
| `test_grid_mismatch_detection_and_loud_failure` | `check_grid_alignment` reports both mismatches; `--fail-on-mismatch` path raises |
| `test_grid_resampling_alignment` | reprojected PSR ends up on the DEM grid with correct transform |

### `tests/test_psr.py` — 5 tests
| Test | Asserts |
| :--- | :--- |
| `test_binarize_psr_and_nodata_exclusion` | float→threshold, NoData→0 |
| `test_clean_psr_mask_removes_tiny_components` | components `< 9 px` vanish (`config.PSR_MIN_SIZE_PIXELS`) |
| `test_calculate_psr_area_exactness` | area = count × px area (exact arithmetic, not tolerance) |
| `test_vectorize_psr_to_polygons` | GeoDataFrame columns, `area_m2 > 0`, valid geometries |
| `test_process_and_export_psr_end_to_end` | GeoTIFF + GeoJSON written, tags present |

### `tests/test_terrain.py` — 4 tests
| Test | Asserts |
| :--- | :--- |
| `test_flat_surface_terrain_metrics` | slope ≈ 0, aspect flat → 0, roughness ≈ 0 |
| `test_planar_ramp_slope_exactness` | known ramp geometry → exact expected slope value (Horn kernel correctness) |
| `test_nodata_preservation_in_terrain` | NoData cells stay `-9999` after every metric |
| `test_process_terrain_pipeline_end_to_end` | 4 GeoTIFFs + histogram PNG exist |

### `tests/test_hazard.py` — 6 tests
| Test | Pins down |
| :--- | :--- |
| `test_hazard_score_formula_and_normalization` | `H = .5S + .3R + .2D`, clipping at norm caps |
| `test_hard_overrides_trigger_class_3_unsafe` | slope ≥ 15 **or** rough ≥ 5 → 3 |
| `test_shadowed_unknown_vs_unsafe_psr` | PSR → 4 unless already unsafe (class order) |
| `test_safe_and_caution_classification` | safe thresholds → 1, else 2 |
| `test_nodata_is_never_treated_as_safe` | invalid → 0 (rule 9) |
| `test_process_hazard_pipeline_end_to_end` | raster + CSV written, 5 CSV rows |

### `tests/test_mapping.py` — 2 tests
`test_hillshade_computation`, `test_generate_4panel_hazard_map_end_to_end` (PNG+PDF exist, size > 0).

### `tests/test_ml_recommender.py` — 3 tests
`test_boulder_micro_hazard_detection`, `test_landing_site_recommender`,
`test_mission_autonomy_artifacts` (JSON fields + `boulder_hazard.tif`).

### `tests/test_validate.py` — 4 tests
| Test | Asserts |
| :--- | :--- |
| `test_compute_psr_metrics_exactness` | hand-computed precision/recall/IoU/F1 on a tiny synthetic confusion case |
| `test_verify_rule_consistency_passes_on_pipeline_output` | `total_violations == 0` on real pipeline output |
| `test_verify_rule_consistency_catches_deliberate_errors` | **mutations** of a class array trip specific rules — the anti-tautology test |
| `test_slope_sensitivity_analysis_execution` | runs + safe area is monotonically non-decreasing across thresholds |

### `tests/test_main.py` — 1 test
`test_main_pipeline_execution` → `main.main()` with `--force-synthetic`, asserts exit code and
**13 artifact paths** exist.

---

## 3. Quality gates that actually exist

| Gate | Exists? | Evidence |
| :--- | :-: | :--- |
| Unit tests for all 8 backend modules | ✅ | 9 test files |
| End-to-end pipeline test | ✅ | `test_main.py` |
| CRS/lunar-safety regression test | ✅ | `test_smoke.py:39-41`, `test_preprocessing.py::test_earth_epsg_protection` |
| Auditor self-test (catches deliberate errors) | ✅ | `test_validate.py` mutation test |
| Threshold-monotonicity test | ✅ | sensitivity monotonic assertion |
| Tests for `web_server.py` | ❌ | no file; every REST route untested (Issue: coverage gap) |
| Tests for `mission_report.py`, `export_web_data.py`, `prepare_lola_dataset.py`, `build_interactive_ui.py` | ❌ | — |
| Frontend tests (JS) | ❌ | no node/npm at all |
| Type checking (`mypy`) | ❌ | no annotations beyond a few `Path` hints |
| Linter in CI | ❌ | no CI; `pyflakes` installed but unused |
| Coverage measurement | ❌ | — |
| Non-destructive test run | ❌ | `test_main.py` + end-to-end tests rewrite `outputs/` |

---

## 4. ⚠️ The destructive-test problem (documented side effect)

`tests/test_main.py:19` calls the real `main.main()`, which overwrites `outputs/*`. A verification
run on 2026-10-17 changed two committed files:

- `outputs/lunasafe_hazard_map.pdf` (binary re-encoding)
- `outputs/psr_polygons.dbf` (writer re-encoding)

**Recovery used:** `git checkout -- outputs/lunasafe_hazard_map.pdf outputs/psr_polygons.dbf`,
then `git status` confirmed a clean tree.

**Recommendations (tasks T-09/T-10):**
1. In tests, redirect `config.OUTPUT_DIR` to `tmp_path` (monkeypatch) — one-line change per test
   module, since all producers take paths from `config`.
2. Mark the heavy tests `@pytest.mark.pipeline` and default to `-m "not pipeline"` for fast loops.
3. Or accept the churn and add `outputs/` regeneration to a `run.bat --refresh` script.

---

## 5. How to run tests (verified commands)

```powershell
# everything (≈25 s, destructive to outputs/)
.\.venv\Scripts\python.exe -m pytest -q

# fast subset (excludes the pipeline end-to-end)
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests\test_main.py

# one module
.\.venv\Scripts\python.exe -m pytest tests\test_validate.py -v

# single test + live output
.\.venv\Scripts\python.exe -m pytest "tests/test_hazard.py::test_hard_overrides_trigger_class_3_unsafe" -vv -s

# keyword filter
.\.venv\Scripts\python.exe -m pytest -k "nodata" -v

# show warnings
.\.venv\Scripts\python.exe -m pytest -q -W error::DeprecationWarning
```

The single observed warning in the suite was **located on 2026-10-17** by re-running the
non-pipeline subset with `-W error`: `tests/test_preprocessing.py::test_earth_epsg_protection`
raises `rasterio.errors.NotGeoreferencedWarning` (its fixture writes with
`from_origin(0, 0, 1, 1)`, a matrix GDAL considers identity — `test_preprocessing.py:55`).
Run the same command to confirm: `pytest -q --ignore=tests\test_main.py -W error`
→ expected `1 failed, 30 passed` (the "failure" is just the warning promoted to error).
Optional fix: give the fixture a non-identity origin or `@pytest.mark.filterwarnings`.

---

## 6. Manual QA checklist (what cannot be automated today)

**Backend**
- [ ] `python main.py` prints `total_violations 0` and exit code 0
- [ ] `outputs/hazard_summary.csv` has 5 rows; `safe+caution+unsafe+shadow+unknown = 40000` (or 62500)
- [ ] `python export_web_data.py` after every rasters change

**Web console**
- [ ] `/api/status` → `ONLINE`, `has_outputs: true`, correct `active_dataset`
- [ ] Map Studio: all 7 layers render; inspector shows class name + reason text
- [ ] Slider drag: areas change within ~1 s; audit chip stays 0 violations
- [ ] RUN PIPELINE: log streams; KPIs refresh; no browser console errors
- [ ] 3D tab: mesh visible, shadows move with sun slider, transect plots
- [ ] Downloads: 4 artifacts arrive non-empty
- [ ] OFFLINE DEMO reloads cache without restart

**Scientific honesty (project rule)**
- [ ] PSR validation card shows `UNLOADED` + explanation when no independent reference exists —
      never a fabricated percentage
- [ ] Provenance strings say `SYNTHETIC DEMO` when running synthetic data

---

## 7. Coverage assessment (by inspection — no tool installed)

| Area | Estimate | Rationale |
| :--- | :-: | :--- |
| `config.py` | high | constants asserted directly |
| `io_utils.py` | medium-high | inspect/align/CRS guard covered; downloader path & `generate_synthetic_*` only indirectly |
| `psr.py` | high | 5 tests incl. exactness |
| `terrain.py` | high | exactness + NoData + e2e |
| `hazard.py` | high | 6 tests, one per rule family |
| `mapping.py` | medium | e2e exists, no legend/text assertions |
| `ml_recommender.py` | medium | happy path only; no test for "no safe candidates" |
| `validate.py` | high | incl. mutation test |
| `main.py` | medium | one e2e run; no flag-parsing tests |
| `mission_report.py` | **none** | hard-coded stats bug undetected (I-14) |
| `web_server.py` | **none** | 20 routes untested (I-03/I-11/I-12 bugs live here) |
| `export_web_data.py` | **none** | bundle schema drift undetected |
| `prepare_lola_dataset.py` | **none** | hard-coded path (I-15) undetected |
| `web/*.js` | **none** | — |

---

## 8. Recommended QA improvements (mapped to roadmap tasks)

| Priority | Improvement | Task |
| :-: | :--- | :--- |
| P0 | Test harness for `web_server.py` (start server on a random port, `urllib` calls; ~10 tests covering health/status/data/audit/recalculate/409/404) | T-08 |
| P0 | Make test runs non-destructive (redirect `OUTPUT_DIR` to `tmp_path`) | T-09 |
| P1 | Assert the *audit key names* emitted by `validate.py` match those read by `web_server.py` — would have caught Issue I-03 automatically | T-08b |
| P1 | `pytest-cov` + a floor (start at 50 % on backend modules) | T-08c |
| P1 | `pyflakes` on the repo as a pseudo-CI script (`python -m pyflakes *.py tests\*.py`) | T-07 |
| P2 | GitHub Actions workflow: install → pyflakes → pytest → upload `outputs/` as artifact | T-07 |
| P2 | Split heavy tests behind a `pipeline` marker | T-09 |
| P2 | Frontend smoke test (playwright against the running server) | T-20 |

---

## 9. Known false confidence risks

1. **`test_compute_psr_metrics_exactness` passes while the pipeline's own PSR comparison is broken** —
   the unit function is correct; `process_validation_pipeline` simply never calls it with the right
   two arguments (Issue I-01). Unit green ≠ system correct.
2. **Rule 4 audit always "passes"** because the key mismatch yields 0 (Issue I-03); the
   `test_verify_rule_consistency_passes_on_pipeline_output` test also passes because it counts a
   key that is never incremented. Only `test_verify_rule_consistency_catches_deliberate_errors`
   partially compensates — verify which keys its mutations actually trip when touching `validate.py`.
3. **`test_main_pipeline_execution` cannot detect stale-data bugs** (Issue I-06): it only checks
   that files exist, not that `web_data.json` matches their dimensions.
