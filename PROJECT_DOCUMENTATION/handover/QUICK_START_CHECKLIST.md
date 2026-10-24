# QUICK_START_CHECKLIST — first 60 minutes for a new team member

> Order matters: verify **before** you change anything, so you know what "already broken" looks
> like. Commands were executed successfully on 2026-10-17 (Windows, repo root = `E:\sistec\LunaSafe`).

## 0. Mindset (2 min)
- Read `.agents/rules/lunasafe.md` (project rules: no Earth CRS, no invented accuracy, Class 4
  never presented as safe) and [`../00_START_HERE.md`](../00_START_HERE.md).
- The **README is marketing**; verified truth lives in `PROJECT_DOCUMENTATION/` and the issue
  register doc 19.

## 1. Environment (10 min)
```powershell
py -3.13 -m venv .venv                       # or use the existing .venv as-is
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import rasterio, geopandas, matplotlib; print('deps ok')"
```
- ⚠ Two requirement files exist (`requirements.txt` ✅ vs `requirement.txt` ❌ drift — I-16).
  Use **`requirements.txt`**.

## 2. Prove the baseline (15 min)
```powershell
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests\test_main.py   # fast: expect 31 passed
.\.venv\Scripts\python.exe -m pytest -q                                 # full: 32 passed, ≈25 s
git status --porcelain outputs/                                        # ⚠ tests rewrite outputs/
git checkout -- outputs/                                               # restore if dirty
```
Expected exactly: **32 passed, 1 warning**. Different → stop and compare with
[`../testing_documentation/TEST_EXECUTION_STATUS.md`](../testing_documentation/TEST_EXECUTION_STATUS.md).

## 3. See the product (10 min)
```powershell
.\run_website.bat          # → http://localhost:8050 (falls back to 8080)
```
Walk the 8 tabs once (Control, Map Studio, 3D, ALSS, Report, Validation, Prediction, Aesthetic),
then: `Ctrl+C` to stop. Keep [`../testing_documentation/TEST_CASES.md`](../testing_documentation/TEST_CASES.md)
§3 (TC-MAN-01…12) open — that's your release gate.

## 4. Know the landmines (5 min — read doc 19 before fixing anything)
| Landmine | Consequence if you miss it |
| :--- | :--- |
| Tests overwrite `outputs/` | dirty git tree; binary diffs; I-06 gets worse |
| `config.py` is mutated at runtime by the server | thresholds bleed across requests (I-11) |
| Audit key names | producer/consumer mismatch already exists (I-03) — don't copy that pattern |
| `web_data.json` may be stale (250×250 vs 200×200) | UI "two truths" (I-06) — regenerate before judging visuals |
| Issue/task IDs are stable | never renumber `I-/M-/T-/SEC-/A` IDs, only append |

## 5. Pick your first task (3 min)
- Open [`../handover/OPEN_TASKS.md`](../handover/OPEN_TASKS.md) → start with **M-A** (T-01…T-04).
- Definition of Done for every task: doc 20 §"Definition of Done" (test that fails→passes,
  green suite, clean `git status`, doc 19 updated).

## 6. Before your first commit (5 min)
```powershell
.\.venv\Scripts\python.exe -m pyflakes @((Get-ChildItem -File *.py, tests\*.py).FullName)  # baseline: 9 findings
git status --short
git log --oneline -3          # style today: short free text; recommended: <type>: <summary> (I-ID)
```
- Commit docs/code/artifacts in **separate** commits; never mix (doc 18 §7).
