# TEST_EXECUTION_STATUS

**Last verified run:** 2026-10-17 · **Environment:** Windows, `.venv` (Python 3.13.0),
`pytest==9.1.1` · **Command:** `.venv\Scripts\python.exe -m pytest -q` (repo root)

## 1. Result

```
32 passed, 1 warning in 25.28s
```

| File | Tests | Status |
| :--- | :-: | :-: |
| `tests/test_smoke.py` | 3 | ✅ |
| `tests/test_preprocessing.py` | 4 | ✅ |
| `tests/test_psr.py` | 5 | ✅ |
| `tests/test_terrain.py` | 4 | ✅ |
| `tests/test_hazard.py` | 6 | ✅ |
| `tests/test_mapping.py` | 2 | ✅ |
| `tests/test_ml_recommender.py` | 3 | ✅ |
| `tests/test_validate.py` | 4 | ✅ |
| `tests/test_main.py` | 1 | ✅ (⚠ destructive) |
| **Total** | **32** | **all passing** |

- The single warning originates in the third-party dependency stack (not LunaSafe code); locate
  with `pytest -q -W error`.
- Collection is stable at **32** — a different count means tests were added/renamed; update
  [`TEST_CASES.md`](TEST_CASES.md) §1 and core doc 14 §2 in the same change.

## 2. Side effects of that run (documented)

The run **modified committed files** (pipeline e2e rewrites `outputs/`):

| File | Cause | Recovery |
| :--- | :--- | :--- |
| `outputs/lunasafe_hazard_map.pdf` | binary re-encoding by matplotlib/GS | `git checkout -- outputs/lunasafe_hazard_map.pdf` |
| `outputs/psr_polygons.dbf` | GeoPackage/DBF writer re-encoding | `git checkout -- outputs/psr_polygons.dbf` |

After recovery, `git status` reported a **clean tree** (except the new, untracked
`PROJECT_DOCUMENTATION/`).

### Reproduce this check after any run
```powershell
git status --porcelain outputs/
git checkout -- outputs/            # only if the two (or more) files show as modified
git status --porcelain              # expect: only ?? PROJECT_DOCUMENTATION/
```

## 3. How to re-run

```powershell
# full suite (≈25 s; destructive → then restore outputs/, see §2)
.\.venv\Scripts\python.exe -m pytest -q

# fast loop (non-pipeline, ≈20 s)
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests\test_main.py

# single case
.\.venv\Scripts\python.exe -m pytest "tests/test_validate.py::test_compute_psr_metrics_exactness" -vv
```

## 4. Static-analysis baseline (same date, `pyflakes==4.0.3`)

```powershell
$files = (Get-ChildItem -File *.py, tests\*.py).FullName
.\.venv\Scripts\python.exe -m pyflakes @files
```
Result: **9 findings, 0 syntax errors** (pyflakes is installed but undeclared — Issue I-16):

| File:line | Finding |
| :--- | :--- |
| `web_server.py:435` | local `clearance_buf` assigned but never used ← evidence for **I-05** |
| `tests/test_hazard.py:19`, `tests/test_smoke.py:79` | unused `rasterio` import |
| `tests/test_main.py:7`, `test_mapping.py:8`, `test_terrain.py:8` | unused `pytest` import |
| `tests/test_ml_recommender.py:7` | unused `pathlib.Path` import |
| `tests/test_ml_recommender.py:90` | local `autonomy_res` assigned but never used |
| `tests/test_validate.py:53` | local `dem` assigned but never used |

This run is the suggested "zero-warning" baseline for task **T-07** (declare pyflakes, wire it
into `check.bat`/CI, burn down the list).

## 5. Known gaps at this baseline (details: core doc 14 §3)

| Gap | Count |
| :--- | :-: |
| Routes in `web_server.py` with automated tests | 0 / 20 |
| Modules with zero tests (`mission_report`, `export_web_data`, `prepare_lola_dataset`, `build_interactive_ui`, `web_server`) | 5 |
| Frontend tests | 0 (no node toolchain) |
| Coverage measurement / linter gate / CI | none |
| Non-destructive full run | ❌ |

Planned coverage additions: `TEST_CASES.md` §2 (TC-PLAN-01…15), roadmap tasks T-07…T-10,
T-16 (declare pyflakes properly), T-20 (frontend smoke).

## 6. Change log for this file

| Date | Event |
| :--- | :--- |
| 2026-10-17 | Initial verification run (32 passed, 25.28 s); side effects restored; tree clean; pyflakes baseline recorded (§4). |
