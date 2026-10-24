# 13 — How to Run the Project

*All commands verified working on Windows + `.venv` (Python 3.13.0) on 2026-10-17.
Run everything from the repository root `E:\sistec\LunaSafe`.*

---

## 1. Quick start (30 seconds)

```powershell
# A. Web console (recommended — this is the demo)
run_website.bat            # → http://localhost:8050, browser opens after 2 s

# B. CLI pipeline
run.bat                    # full 7-phase run on the default dataset
```

No activation, no extra steps: both launchers prefer `.venv\Scripts\python.exe`.

---

## 2. The four ways to run LunaSafe

| # | Command | What starts | Use when |
| :-: | :--- | :--- | :--- |
| 1 | `run_website.bat` | `web_server.py` on :8050 + opens browser | demos, judges, interactive work |
| 2 | `run.bat` (≡ `python main.py`) | full pipeline in the console | regenerating artifacts, CI-less verification |
| 3 | `python -m pytest -q` | 32 tests incl. one full pipeline run | after changing any backend module |
| 4 | `python -m pytest tests/test_hazard.py -v` | only one module's tests | during focused development |

### Direct invocations (no launchers)

```powershell
.\.venv\Scripts\python.exe web_server.py
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe main.py --force-synthetic --quiet
.\.venv\Scripts\python.exe main.py --dem data\lola_south_pole_dem.tif --psr data\lola_psr_mask.tif
.\.venv\Scripts\python.exe main.py --fail-on-mismatch     # strict grid checking
```

If you forget to activate the venv, `main.py:18-26` detects the missing `rasterio` and re-executes
itself under `.venv\Scripts\python.exe` automatically.

---

## 3. CLI recipes

### 3.1 Standard run and what you should see

```
python main.py
→ [Phase 1/7] ... ingest ...
→ [Phase 2/7] ... PSR ...
→ ... [PHASE 7/7] MISSION AUTONOMY ...   (printed by ml_recommender.py, phase label mismatch is cosmetic)
→ LUNASAfe PIPELINE SUMMARY: elapsed time, PSR area, total_violations, 15 artifacts
```

Exit code `0` on success. Artifacts land in `outputs/` (15 files — list in doc 06 §2).

### 3.2 Run on real NASA LOLA data

Two steps, both already done in this checkout (so this "just works"):

```powershell
# 1. obtain data  (either path)
curl.exe -L -o data\ldem_75s_240m.jp2 "<URL from web_server.py:633>"
#    …or from the UI: DOWNLOAD NASA DATA button
#    …or manual: see data\DOWNLOAD_INSTRUCTIONS.md

# 2. convert
.\.venv\Scripts\python.exe prepare_lola_dataset.py
```

Because `data/lola_south_pole_dem.tif` **and** `data/lola_psr_mask.tif` both exist, the next
`python main.py` and the web console automatically switch to the real dataset
(`main.py:66-73`, `web_server.py:266`). Force synthetic with `--force-synthetic` or by renaming the
files.

> ⚠️ `prepare_lola_dataset.py:15` hard-codes `e:\sistec\LunaSafe` — on any other checkout edit that
> line first (Issue I-15).

### 3.3 Regenerate only the UI data bundle

```powershell
.\.venv\Scripts\python.exe export_web_data.py     # rewrites outputs/web_data.json from current rasters
```
Needed whenever you changed rasters **without** running the full pipeline (or if the UI looks stale).

### 3.4 Generate the 2-page mission report

```powershell
.\.venv\Scripts\python.exe mission_report.py     # writes outputs/mission_report.pdf
```
(Also auto-generated on first `GET /api/download/mission_report.pdf` — `web_server.py:793-798`.)

### 3.5 Run only the landing-site recommender

```powershell
.\.venv\Scripts\python.exe ml_recommender.py     # reads data/ + outputs/ rasters, writes landing_sites.json
```

### 3.6 Regenerate the legacy single-file dashboard

```powershell
.\.venv\Scripts\python.exe build_interactive_ui.py   # → dashboard.html; open via view_ui.bat
```

---

## 4. Running the web console

### 4.1 Start

```powershell
run_website.bat        # or run_website.ps1, or python web_server.py
```
Banner + `LunaSafe Mission Control running on http://localhost:8050`. If 8050 is taken → port 8080
(`web_server.py:840-846`).

### 4.2 Startup data check

| Server state | Console behaviour |
| :--- | :--- |
| `outputs/` present (current repo) | everything works immediately: 2D layers, 3D, sliders, audit |
| `outputs/` empty/missing | KPI tiles show 0; **sliders return 400** until you press RUN PIPELINE or OFFLINE DEMO |

### 4.3 The 8 tabs

| Tab | What to do | Depends on |
| :--- | :--- | :--- |
| **Mission Control** | KPIs, rule-audit chips, console log, RUN PIPELINE | `/api/status`, `/api/logs` |
| **Map Studio** | 7 toggleable layers, pan/zoom, pixel inspector, export PNG | `/api/data` |
| **3D Terrain** | tilt/orbit, sun angle, transect tool, raycast inspect | same + WebGL |
| **ALSS / Landing Sites** | Top-3 ellipse cards, boulder map | `landing_sites` in the bundle |
| **Mission Report** | generate/download PDF | `/api/download/mission_report.pdf` |
| **Validation** | 9-rule table, PSR metrics card | `/api/audit`, `/api/psr-validation` |
| **Sensitivity/Charts** | threshold sliders → area breakdown | `/api/recalculate` |
| **Prediction/Aesthetic** | boulder probability layer, styling | bundle arrays |

*(Exact tab ids/line refs: see `feature_documentation/`.)*

### 4.4 Typical demo script (≈90 s)

1. Open `http://localhost:8050` → badges say **SYNTHETIC DEMO / ONLINE**.
2. Map Studio: toggle PSR + hazard layers; hover a pixel → plain-language reason.
3. Drag **SLOPE SAFE MAX** 5°→8° → watch safe area + audit chip update (250 ms debounce).
4. Landing Sites tab → Site Alpha card + ellipse in the 2D/3D view.
5. Validation tab → 9 rules PASSED; note PSR metrics card honestly says `UNLOADED` if no reference.
6. Press **RUN PIPELINE** → live log streams → KPIs refresh (subprocess runs ~8-10 s).
7. Download → `lunasafe_hazard_map.pdf` and `mission_report.pdf`.

### 4.5 Switching between real LOLA and synthetic in the UI

The choice is **file-existence based**, not a UI toggle: presence of
`data/lola_south_pole_dem.tif` + `data/lola_psr_mask.tif` flips `/api/status.active_dataset`.
To go back to synthetic in the UI run, press RUN PIPELINE with *force synthetic* checked (the only
key that reaches the child process — Issue I-04).

---

## 5. Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q                 # 32 passed, ~25 s
.\.venv\Scripts\python.exe -m pytest -v                 # per-test names
.\.venv\Scripts\python.exe -m pytest tests/test_terrain.py -k ramp -v
.\.venv\Scripts\python.exe -m pytest --tb=short         # concise tracebacks
```

> ⚠️ **Full runs rewrite `outputs/`.** `tests/test_main.py:19` executes the real pipeline. After a
> test run: `git status` → `git checkout -- outputs/` if you want the committed artifacts back.

---

## 6. Server API smoke checks (optional)

```powershell
curl.exe http://localhost:8050/api/status
curl.exe http://localhost:8050/api/health
curl.exe -X POST http://localhost:8050/api/audit
curl.exe -X POST http://localhost:8050/api/recalculate -H "Content-Type: application/json" -d "{\"slope_safe_max\":6.0}"
curl.exe -o map.pdf http://localhost:8050/api/download/lunasafe_hazard_map.pdf
```

---

## 7. Day-to-day development loop

```powershell
# 1. edit source
# 2. focused tests (fast, mostly non-destructive)
.\.venv\Scripts\python.exe -m pytest tests\test_hazard.py -q
# 3. full suite when the module is stable
.\.venv\Scripts\python.exe -m pytest -q
# 4. restore artifacts if you don't want them in the diff
git checkout -- outputs/
# 5. regenerate what the UI reads, then restart the server
.\.venv\Scripts\python.exe export_web_data.py
# (restart web_server.py — RASTER_CACHE is not watched)
```

---

## 8. Common situations

| Goal | Command(s) |
| :--- | :--- |
| Everything from scratch | `run.bat` then `run_website.bat` |
| UI looks stale after code changes | `python export_web_data.py` → restart server |
| Show real NASA data in the demo | ensure `data/lola_*.tif` exist, restart server |
| Compare synthetic vs real outputs | `git stash` / `git stash pop` around runs, or archive `outputs/` |
| Check the 9 safety rules only | `POST /api/audit` or Validation tab |
| Regenerate the big map figure only | full `python main.py` (no single-phase CLI exists) |
| Port already in use | `netstat -ano \| findstr :8050`, kill the PID, or read the :8080 banner |
| Clean everything untracked | `git clean -nxd` first (dry run!) |

---

## 9. Expected healthy output

| Check | Healthy signal |
| :--- | :--- |
| `python main.py` | `[X] OPERATIONAL` summary, `total_violations 0`, exit 0 |
| `pytest -q` | `32 passed` |
| `GET /api/status` | `"status": "ONLINE"`, `"has_outputs": true` |
| `GET /api/audit` | `"status": "PASSED"`, `total_violations 0` (⚠ Rule 4 is always 0 — Issue I-03) |
| Browser console | three.js + KaTeX loaded, no red errors |
| 3D tab | terrain mesh visible, shadows respond to sun sliders |

## 10. Where things go wrong

Symptom-driven fixes: [`15_DEBUGGING_AND_TROUBLESHOOTING.md`](15_DEBUGGING_AND_TROUBLESHOOTING.md).
Installation failures: [`11_SETUP_AND_INSTALLATION.md`](11_SETUP_AND_INSTALLATION.md) §8.
