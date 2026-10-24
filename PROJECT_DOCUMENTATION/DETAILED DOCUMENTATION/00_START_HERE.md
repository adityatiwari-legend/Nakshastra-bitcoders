# 00 — START HERE: First-Day Onboarding Guide

*Audience: a developer who has never seen this repository before.*
*Time to read: ~25 minutes. Time to complete the checklist: ~3–4 hours.*

---

## 1. What does this project do, in plain words?

Imagine you want to land a spacecraft near the Moon's South Pole. Some areas are flat and safe; others
are steep, rocky, or sitting in permanent darkness where you cannot see what you are landing on.

**LunaSafe takes two map files of the lunar surface and answers three questions, pixel by pixel:**

1. *How steep is it?* (slope)
2. *How rough is it?* (small bumps and dips — boulders, micro-craters)
3. *Is it in permanent shadow?* (a "PSR" — Permanently Shadowed Region)

It then combines those three answers into a single safety verdict per pixel:

| Class | Name | Meaning |
| :---: | :--- | :--- |
| 0 | NoData | No elevation data — **never** considered safe |
| 1 | Safe | Flat, smooth, sunlit |
| 2 | Caution | Borderline |
| 3 | Unsafe | Steep or rough — hard override |
| 4 | Shadowed-Unknown | Inside permanent shadow and *not* obviously steep — **we cannot see it, so we do not call it safe** |

Finally it draws the result as a map, recommends the 3 best landing ellipses, and writes a PDF report.

## 2. Why was it created?

It is a hackathon entry for **"Problem Statement 02 — Lunar Landing Site Characterization"**
(see [`../.agents/rules/lunasafe.md`](../.agents/rules/lunasafe.md) and the problem framing in
[`02_PROBLEM_STATEMENT_AND_OBJECTIVES.md`](02_PROBLEM_STATEMENT_AND_OBJECTIVES.md)).

Two design rules shape everything:

- **Geodetic honesty** — lunar data must keep a lunar coordinate system
  (`+R=1737400`, see `config.py:62`). Using Earth's WGS84 on Moon data silently distorts distances.
- **Never call darkness "safe"** — that is the origin of Class 4 (`Shadowed-Unknown`), which is the
  project's signature idea (see `hazard.py:111-113`).

## 3. What must you understand first?

Read these five concepts before touching code:

1. **Raster vs vector.** A *raster* is a grid of numbers (an image with coordinates); a *vector* is
   shapes/outlines (`.geojson`, `.shp`). LunaSafe works mostly with rasters and produces both.
2. **CRS (Coordinate Reference System).** The rule set for turning grid cells into real-world
   metres. LunaSafe uses *Moon South Pole Polar Stereographic, R = 1,737,400 m*.
3. **NoData.** A special value (`-9999.0`, `config.py:67`) meaning "no measurement". It must never be
   treated as terrain.
4. **The pipeline.** `main.py` runs 7 sequential phases; each phase is a separate Python module.
5. **The web console.** `web_server.py` re-uses the *same* Python modules but keeps rasters in RAM so
   slider changes re-classify instantly.

## 4. Which documents to read, in order

| # | Read | Takes |
| :---: | :--- | :---: |
| 1 | this file | 25 min |
| 2 | [`01_PROJECT_OVERVIEW.md`](01_PROJECT_OVERVIEW.md) | 15 min |
| 3 | [`05_SYSTEM_ARCHITECTURE.md`](05_SYSTEM_ARCHITECTURE.md) + [`architecture/system_architecture.mmd`](architecture/system_architecture.mmd) | 25 min |
| 4 | [`06_REPOSITORY_STRUCTURE.md`](06_REPOSITORY_STRUCTURE.md) | 15 min |
| 5 | [`11_SETUP_AND_INSTALLATION.md`](11_SETUP_AND_INSTALLATION.md) + [`13_HOW_TO_RUN_THE_PROJECT.md`](13_HOW_TO_RUN_THE_PROJECT.md) | 45 min (hands-on) |
| 6 | [`07_CODEBASE_DEEP_DIVE.md`](07_CODEBASE_DEEP_DIVE.md) | 40 min |
| 7 | One module doc for the module you will touch first (see [`module_documentation/`](module_documentation/)) | 30 min |
| 8 | [`14_TESTING_AND_QUALITY_ASSURANCE.md`](14_TESTING_AND_QUALITY_ASSURANCE.md) | 20 min |
| 9 | [`19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](19_CURRENT_STATUS_AND_KNOWN_ISSUES.md) | 20 min |

Do **not** start with `PROJECT_SPECIFICATION.md` or `README.md` — they are promotional and contain a
few claims that the code does not support (catalogued in [`19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](19_CURRENT_STATUS_AND_KNOWN_ISSUES.md)).

## 5. How to set up and run (summary — full detail in docs 11/13)

```powershell
# from the repository root, Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Headless pipeline
python main.py                 # writes 15 artifacts into outputs/

# Web console
python web_server.py           # then open http://localhost:8050/
```

> **VERIFIED** in this environment: `.\.venv\Scripts\python.exe -m pytest -q` → `32 passed, 1 warning in 25.28s`.

## 6. Where is the entry point?

There are **two** entry points — do not confuse them:

| Entry point | Command | What happens |
| :--- | :--- | :--- |
| `main.py` (`main()` at `main.py:237`, `run_pipeline()` at `main.py:38`) | `python main.py` | Runs 7 phases in a **subprocess-friendly single process** and prints a 15-artifact summary |
| `web_server.py` (`run_server()` at `web_server.py:834`, `__main__` at `web_server.py:858`) | `python web_server.py` | Starts a `ThreadingHTTPServer` on port 8050 (falls back to 8080, `web_server.py:840-846`) |

Third, **rarely used** entry points (VERIFIED, low priority):
- `export_web_data.py:111` — rebuilds `outputs/web_data.json`
- `prepare_lola_dataset.py:106` — converts NASA JP2 → GeoTIFF
- `mission_report.py:227` — regenerates `outputs/mission_report.pdf`
- `ml_recommender.py:302` — runs only the autonomy phase
- `build_interactive_ui.py:1130` — regenerates the legacy `dashboard.html`

## 7. Trace one feature end-to-end: "why is this pixel Class 3 (Unsafe)?"

Use this as your mental model; follow the files in order.

1. **Input.** `data/synthetic_dem.tif` is read by `io_utils.read_geotiff()` (`io_utils.py:154`).
2. **Slope.** `terrain.calculate_slope_and_aspect()` (`terrain.py:21`) applies Horn's 3×3 kernel.
3. **Roughness.** `terrain.calculate_roughness_std()` (`terrain.py:90`) — local elevation std-dev.
4. **PSR.** `psr.process_and_export_psr()` (`psr.py:174`) binarises + despeckles the shadow mask.
5. **Score.** `hazard.compute_hazard_score()` (`hazard.py:23`) → `H = 0.50·S + 0.30·R + 0.20·D`.
6. **Verdict.** `hazard.classify_hazard_surface()` (`hazard.py:61`) applies hard overrides:
   `slope ≥ 15°` **or** `roughness ≥ 5 m` → Class 3 (`hazard.py:100-106`).
7. **Proof.** `validate.verify_rule_consistency()` (`validate.py:70`) audits all 9 rules and would
   flag any cell that breaks them (`validate.py:103-137`).
8. **Display.** `mapping.generate_4panel_hazard_map()` (`mapping.py:149`) draws it red
   (`#e74c3c`, `config.py:127`); the web UI re-draws it in `web/app.js` (`rebuildOffscreenHazard`).

For the same trace through the **web** path, see [`08_DATA_FLOW_AND_WORKFLOWS.md`](08_DATA_FLOW_AND_WORKFLOWS.md) Workflow W3.

## 8. What NOT to change until you understand the architecture

| Do not touch yet | Why |
| :--- | :---|
| `config.py` thresholds | The whole test suite, the maps, the PDF, and the web UI colours are calibrated to them |
| The lunar CRS string (`config.py:62`) | Every GeoTIFF, the `.prj`, and all coordinates derive from it |
| `hazard.classify_hazard_surface()` ordering of rules | `validate.py` re-implements the same logic; a divergence = rule violations |
| `validate.verify_rule_consistency()` | It is the safety contract of the project |
| Anything inside `outputs/` by hand | `tests/test_main.py:19` regenerates them; hand edits are lost |
| Committed binaries (`data/*.tif`, `*.jp2`) | Large, unreviewable diffs; there is no `.gitignore` discipline in this repo |

Safe first changes: fix a UI string, add a test, correct a documented number, improve a doc.

## 9. First-day checklist (both members)

- [ ] Read `00_START_HERE.md`, `01_PROJECT_OVERVIEW.md`, `05_SYSTEM_ARCHITECTURE.md`.
- [ ] `git log --oneline` shows the 2 commits; `git status` is clean.
- [ ] `python -m venv .venv` + `pip install -r requirements.txt` succeeded.
- [ ] `python main.py --force-synthetic` prints "LUNASAFE PIPELINE EXECUTION SUCCESSFUL" and `outputs/` has 16 files.
- [ ] `python -m pytest -q` → **32 passed**. *(Remember: this overwrites `outputs/` — see the warning below.)*
- [ ] `python web_server.py` → browser opens `http://localhost:8050/` and the header shows a provenance badge.
- [ ] In the web console, open **📊 Validation & Metrics** and see the 9-rule audit table.
- [ ] Identify the entry point and one feature trace **without** looking at this document.
- [ ] Restore any changed output files: `git checkout -- outputs/` (see warning).

> ⚠️ **Side effect you must know (VERIFIED):** running the test suite executes the *full* pipeline
> (`tests/test_main.py:19-22`), which **rewrites files in `outputs/`**. On the generation machine this
> modified `outputs/lunasafe_hazard_map.pdf` and `outputs/psr_polygons.dbf`; both were restored with
> `git checkout -- outputs/`. If you want a pristine tree after testing, run the same command.
> Recommended improvement: make the test write to `tmp_path` — tracked as task **T-07** in
> [`20_ROADMAP_AND_NEXT_STEPS.md`](20_ROADMAP_AND_NEXT_STEPS.md).

## 10. Glossary of the 10 terms you will see constantly

Full glossary: [`23_GLOSSARY_AND_ABBREVIATIONS.md`](23_GLOSSARY_AND_ABBREVIATIONS.md).

| Term | Meaning |
| :--- | :--- |
| DEM | Digital Elevation Model — grid of surface heights in metres |
| PSR | Permanently Shadowed Region — never sees the Sun |
| Horn (1981) | The 3×3 slope algorithm used in `terrain.py:55-64` |
| TRI | Terrain Ruggedness Index (Riley et al. 1999), `terrain.py:139` |
| NoData | Missing measurement, sentinel `-9999.0` |
| ALSS | Autonomous Landing Site Selection — `ml_recommender.py:84` |
| Hazard score `H` | Weighted 0.50/0.30/0.20 sum of normalised slope, roughness, shadow |
| CRS | Coordinate Reference System |
| GeoTIFF | Image file that carries coordinates (`.tif`) |
| Verifier | `validate.verify_rule_consistency()` — the 9-rule auditor |
