# 15 — Debugging and Troubleshooting

> Symptom → cause → fix format. Every entry cites the code that causes it, so you can patch rather
> than guess. Related: [`19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](19_CURRENT_STATUS_AND_KNOWN_ISSUES.md)
> for the permanent issue list.

---

## 0. First triage (30 seconds)

```powershell
# 1. What state is the system in?
curl.exe http://localhost:8050/api/status          # ONLINE? has_outputs? active_dataset?
curl.exe http://localhost:8050/api/health          # running vs connected

# 2. Do artifacts exist and agree?
Get-ChildItem outputs | Select Name, Length, LastWriteTime

# 3. Does the core still pass?
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests\test_main.py

# 4. Did I dirty the repo?
git status --short
```

Decision table:

| Observation | Go to |
| :--- | :--- |
| Server won't start | §1 |
| Browser loads but layers are empty | §2 |
| Sliders return errors | §3 |
| Numbers look wrong | §4 |
| Pipeline crashes | §5 |
| Tests fail | §6 |
| Real LOLA data issues | §7 |
| UI/performance issues | §8 |
| PDF/figure issues | §9 |
| Git/output noise | §10 |

---

## 1. Server / startup problems

| Symptom | Root cause | Fix |
| :--- | :--- | :--- |
| `'rasterio' is not found` immediately then the process restarts | venv auto-switch (`main.py:18-26`) re-exec under `.venv` | expected; if it loops, the venv lacks `rasterio` → reinstall `requirements.txt` |
| `OSError: [WinError 10048] ... address in use` | 8050 occupied | server auto-falls back to **8080** (`web_server.py:840-846`) — read the banner, or `netstat -ano \| findstr :8050` and kill the old PID |
| `FileNotFoundError: web/index.html` | launched from another cwd | run from repo root (launchers do `cd /d "%~dp0"`); the server resolves `ROOT_DIR` from its own path (`web_server.py:26-31`) |
| PowerShell blocks `run_website.ps1` | execution policy | use `run_website.bat` instead |
| Server starts, terminal prints nothing else | normal — it only logs on requests | verify with `curl /api/health` |
| Browser: "This site can't be reached" after 2 s | slow start (raster cache load) | wait/refresh; check the terminal for the port banner |

---

## 2. Console loads but is empty / no data

| Symptom | Root cause | Fix |
| :--- | :--- | :--- |
| KPI tiles all 0, badge "NO OUTPUTS" | `outputs/` missing key files (`web_server.py:270`) | `run.bat` (or RUN PIPELINE), then `python export_web_data.py` |
| 2D canvas blank, 3D shows nothing | `/api/data` failed → check DevTools Network tab | 500 = "Unable to load or export raster web data bundle" (`:318`) → run `python export_web_data.py` |
| Layers render but colours look swapped | stale `currentHazardArray` after a pipeline run | reload the page (the bundle is fetched once at startup) |
| UI shows old data after editing Python code | `RASTER_CACHE` + bundle are snapshots; nothing is file-watched | **restart `web_server.py`** and hard-refresh the browser (Ctrl+F5) |
| KaTeX boxes show raw `\frac{}` text | offline / CDN blocked | cosmetic only; app is fully functional (`web/index.html:16`) |

---

## 3. Sliders / POST endpoints failing

| Symptom | Root cause | Code | Fix |
| :--- | :--- | :--- | :--- |
| Slider shows "Raster cache not ready; run pipeline once." (400) | `outputs/slope_deg.tif` or `psr_binary.tif` missing at first recalc | `web_server.py:415-419` | run the pipeline once, or press OFFLINE DEMO (`:777`) |
| Slider updates pixels but areas are nonsense | **20 m/px assumed** regardless of dataset | `web_server.py:470` (Issue I-02) | temporary: read areas from `/api/status.summary_data` (CSV-based, correct); fix: replace `config.SYNTHETIC_PIXEL_SIZE_M` with the actual transform pixel size from `RASTER_CACHE["transform"]` |
| Rule 4 always 0 violations even for bad data | key mismatch `rule4_safe_in_psr` vs emitted `rule4_safe_pixel_in_psr` | `web_server.py:576` / `validate.py:117` (Issue I-03) | change the lookup key to `rule4_safe_pixel_in_psr` |
| Changed thresholds don't apply to RUN PIPELINE output | subprocess re-imports `config.py` from disk | `web_server.py:369-381` (Issue I-04) | pass thresholds as `main.py` CLI args (requires adding flags) or write a temp config; for now expect defaults |
| Thresholds "stick" across sessions / weird values for other users | request bodies mutate global `config` | `web_server.py:341-362,438-446` (Issue I-11) | restart the server to reset; UI `resetDefaults()` re-posts defaults |
| 409 `BUSY` when pressing RUN PIPELINE | previous run still going, or a crashed worker left the flag set | `web_server.py:331-335`, `:402-404` | wait; if stuck, restart the server |
| POST returns HTML instead of JSON | wrong path (404 from `send_error`) | `web_server.py:173` | check DevTools; only the 7 documented POST routes exist |
| Malformed JSON silently acts like "no options" | `read_json_body` swallows exceptions → `{}` | `web_server.py:207` (Issue I-15 companion) | validate the body client-side; consider raising 400 |

---

## 4. Wrong scientific numbers

| Symptom | Root cause | Code | Fix |
| :--- | :--- | :--- | :--- |
| PSR precision/recall/IoU always 1.0 from the batch pipeline | mask compared to itself | `validate.py:301-308` (Issue I-01) | pass a genuinely independent reference: `compute_psr_metrics(psr_mask, independent_ref)` — the web endpoint `/api/psr-validation?benchmark` already does a proper (labelled) comparison |
| Report says `rule-audit 0 / PASSED` even on a failing run | hard-coded text | `mission_report.py:167-177` (Issue I-14) | read `process_validation_pipeline()["rule_audit"]` instead |
| `H` never exceeds 0.8; "weight_shadow" slider has no effect | shadow term D is 0 in the pipeline (no `shadow_fraction` passed) | `main.py:137`, Issue I-07 | compute an illumination mask and pass `shadow_fraction=...` to `compute_hazard_score`, **or** stop advertising the third weight |
| Areas differ between CLI CSV and web KPIs | CSV uses real pixel size; web recalc uses 20 m | `hazard.py:160` vs `web_server.py:470` | see I-02 |
| Clearance/standoff not respected by ranked sites | 40 m buffer never applied; ranking uses `ellipse_radius_m` only | `ml_recommender.py:115-116` (Issue I-05) | apply `LANDING_CLEARANCE_BUFFER_M` as an additional `dist_m ≥ ellipse + buffer` gate |
| Boulder probability looks like noise | high-pass residual picks up every DEM ripple | `ml_recommender.py:18-81` | tune `BOULDER_RESIDUAL_THRESHOLD_STD` (2.2) upward; σ=2 Gaussian trend |
| Slope map has streaks along NoData edges | NoData filled with global median before convolution | `terrain.py:46-49` | expected; ignore values within 1 px of NoData, or fill via nearest-neighbour |
| Flat pixels show random aspect | aspect undefined on flat terrain | `terrain.py:70-74` | by design aspect forced to 0 when slope < 0.01° |

---

## 5. Pipeline (CLI) failures

| Symptom | Root cause | Code | Fix |
| :--- | :--- | :--- | :--- |
| `ValueError: Earth-like CRS detected...` | input carries an Earth EPSG | `io_utils.py:199-206` | intentional guard (project rule) — reproject source to the lunar PROJ string at `config.py:62` **only if you truly have lunar data**; otherwise you are holding Earth data |
| `ValueError: SPATIAL EXTENT ERROR` | PSR and DEM bounding boxes don't overlap | `io_utils.py:330-333` | wrong file pair; check `--dem/--psr` |
| `ValueError: GRID MISMATCH ... use --fail-on-mismatch` | shapes/transforms differ | `io_utils.py:309-318` | default behaviour silently nearest-reprojects; pass `--fail-on-mismatch` to investigate |
| `FileNotFoundError` on `e:\sistec\...` | hard-coded root | `prepare_lola_dataset.py:15` (Issue I-15) | edit line 15 to your checkout path (or make it `Path(__file__).resolve().parent`) |
| Import errors when running a single script | flat-module layout | every entry point | run from repo root; the `sys.path.insert` idiom in each file handles the rest |
| `[PHASE 7/7]` printed while main says 6 phases | label mismatch | `ml_recommender.py` banner vs `main.py:196` | cosmetic — ignore or normalise labels |
| Output file locked (`PermissionError`) | PDF/PNG open in a viewer | `write_geotiff`/savefig | close the file; Windows locks open PDFs |

### Fast isolation recipe
```powershell
$env:PYTHONVERBOSE = "0"
.\.venv\Scripts\python.exe main.py --force-synthetic --fail-on-mismatch 2>&1 | Tee-Object run.log
# then bisect: comment out phases in main.py? No — run the modules individually instead:
.\.venv\Scripts\python.exe -c "import io_utils,config; print(io_utils.inspect_raster(config.SYNTHETIC_DEM_PATH))"
```

---

## 6. Test failures

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'tests'` | run from a subdirectory | always `python -m pytest` from repo root |
| End-to-end tests fail with missing artifacts | a previous phase raised but the error surfaced late | run `python main.py --force-synthetic` directly to see the real traceback |
| Tests rewrite `outputs/` and dirty git | by design (`test_main.py:19`) | `git checkout -- outputs/` after; see doc 14 §4 |
| New test can't find modules | forgot the `sys.path` header | copy `tests/test_smoke.py:1-8` |
| 1 warning reported | third-party deprecation | `pytest -q -W error` to attribute it |

---

## 7. Real NASA LOLA dataset problems

| Symptom | Cause | Code | Fix |
| :--- | :--- | :--- | :--- |
| Download button does nothing / `Ingestion error` | PDS URL moved or offline | `web_server.py:633` (Issue: URL differs from `data/DOWNLOAD_INSTRUCTIONS.md:23`) | fetch manually per `data/DOWNLOAD_INSTRUCTIONS.md`, drop `ldem_75s_240m.jp2` into `data/`, press the button again (local JP2 path takes precedence at `:621-630`) |
| Converter runs on another machine and fails | hard-coded `e:\sistec\LunaSafe` | `prepare_lola_dataset.py:15` (I-15) | edit the line |
| After switching to LOLA, UI shows odd shapes/units | committed `web_data.json` is the old 250×250/200×200 mismatch | Issue I-06 | `python export_web_data.py`, restart server, hard-refresh |
| Areas look 144× too big/small | web uses 20 m/px on 240 m data | Issue I-02 | see §3 |
| "Is this PSR actually published?" | mask = depth < −900 m heuristic | `prepare_lola_dataset.py:51-56` (I-08) | label it honestly in UI/reports; a true atlas needs an external PSR product |
| Regression: everything flipped back to SYNTHETIC | one of the two GeoTIFFs renamed/missing | `web_server.py:266` | both files must exist for "real" mode |

---

## 8. UI / performance

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| Slider feels laggy on LOLA (62 500 px) | response includes full flattened hazard array each tick | expect ~200-400 ms; consider diff-only payloads (roadmap T-05) |
| Browser tab freezes when toggling layers | full `ImageData` repaints per layer change at `drawMap` | reduce layer count, or decimate the display grid |
| 3D tab black | WebGL unavailable / three.js failed to load | check DevTools; `web/vendor/three.min.js` must be served (route `:134`) |
| 3D terrain flat (no relief) | vertical exaggeration slider at 0 or DEM all-equal | raise `Y-EXAGGERATION` in the 3D panel |
| Minimap/inspector coordinates wrong | bounds come from the bundle; stale bundle = stale coords | regenerate `web_data.json` |
| Fonts differ from screenshots | CDN blocked → system fallback | cosmetic |

Memory: the server holds one full copy of each raster in RAM (`RASTER_CACHE`); a 4k×4k DEM would
need ~250 MB per float32 band — the architecture ceiling (doc 05 §10).

---

## 9. Figures & PDFs

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `lunasafe_hazard_map.pdf` differs from PNG only in size | both rendered at `PLOT_DPI=300` | expected |
| Map legend missing PSR outlines | `geopandas`/`shapely` import failed (optional path) | check `python -c "import geopandas"` |
| Report PDF contains zeros / "0 / PASSED" | hard-coded fallback stats + audit table | Issue I-14 — patch `mission_report.py:51-58,167-177` |
| Report timestamp wrong timezone but labelled UTC | local time formatted as UTC | `mission_report.py:71` |
| Fonts missing in PDF | matplotlib DejaVu fallback | cosmetic; `matplotlib` bundled fonts are used |
| Can't open PDF while testing | Windows file lock | close viewer before re-running |

---

## 10. Git / repository hygiene

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| Every run diffs `outputs/*.pdf`, `*.dbf` | binaries regenerated with new encodings | `git checkout -- outputs/`; decide in T-14 whether outputs stay tracked |
| `.pyc` files keep appearing as modified | 22 `__pycache__` files are **tracked** | add root `.gitignore` + `git rm -r --cached __pycache__` (T-11) |
| `git status` clean but `.venv` exists | `.venv/.gitignore` contains `*` | fine; still add a root `.gitignore` for outputs/cache |
| Untracked junk after experiments | no root ignore rules | `git clean -nxd` first, always |

---

## 11. Debugging tooling that exists / doesn't

| Tool | Status | How to use |
| :--- | :-: | :--- |
| `print()` tracing | ✅ | every phase prints banners; `--quiet` silences |
| Pipeline log buffer (web) | ✅ | `GET /api/logs` / the console pane — only for the *subprocess* run |
| Request logging | ❌ | `BaseHTTPRequestHandler` default stderr logging only |
| `pyflakes` | ✅ installed, ⚠ undeclared | `python -m pyflakes main.py web_server.py …` |
| `pdb`/breakpoints | ✅ | `python -m pdb main.py` (venv interpreter) |
| Coverage | ❌ | not installed |
| Structured logs / metrics | ❌ | none |
| Browser DevTools network tab | ✅ | the most useful tool for API debugging |

### Handy inspection one-liners

```powershell
# raster summary
.\.venv\Scripts\python.exe -c "import rasterio,numpy as np;s=rasterio.open('outputs/hazard_classes.tif');a=s.read(1);print(s.shape,s.nodata,dict(zip(*np.unique(a,return_counts=True))))"

# compare bundle grid vs raster grid (catches Issue I-06)
.\.venv\Scripts\python.exe -c "import json,rasterio;d=json.load(open('outputs/web_data.json'));print(d['width'],d['height']);print(rasterio.open('outputs/hazard_classes.tif').shape)"

# live audit
curl.exe -X POST http://localhost:8050/api/audit
```
