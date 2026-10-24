# 11 — Setup and Installation

*Environment of record: Windows 11, Python **3.13.0** inside `.venv`, verified 2026-10-17.*

---

## 1. Prerequisites

| Requirement | Minimum | Notes |
| :--- | :--- | :--- |
| OS | Windows 10/11 (primary) | `.bat` launchers and the venv auto-switch are Windows-only (`main.py:18-26`). Linux/macOS work only if you activate the venv yourself and invoke `python main.py` directly |
| Python | 3.10+ (header of `requirements.txt:2`); **3.13.0 used here** | wheels exist for all pinned deps on 3.13 |
| Disk | ≈ 600 MB | deps ≈ 450 MB, `data/` ≈ 11 MB, `outputs/` ≈ 6 MB, vendored three.js 0.6 MB |
| RAM | ≥ 1 GB free | full rasters cached twice (disk + `RASTER_CACHE`) |
| GPU | **not required** | three.js 3D uses WebGL in the browser; the pipeline is pure CPU numpy |
| Network | **optional** | only for (a) `pip install`, (b) NASA JP2 download, (c) optional CDN KaTeX/fonts (page degrades without them) |
| GIS install | **not required** | GDAL comes bundled inside the `rasterio` wheel; QGIS is never invoked |

---

## 2. Clean install (from a fresh clone)

```powershell
# 1. Clone
git clone https://github.com/kushbansal2005/ORBISLUNA.git
cd ORBISLUNA

# 2. Virtual environment (Python 3.13)
py -3.13 -m venv .venv
#    …or:  python -m venv .venv

# 3. Activate
.\.venv\Scripts\Activate.ps1        # PowerShell
#   .venv\Scripts\activate.bat      # cmd.exe
#   If PowerShell blocks scripts:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 4. Install pinned deps
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Expected: all 10 pins resolve cleanly (verified by `pip install -r requirements.txt` on 2026-10-17 —
`Requirement already satisfied` for every line).

### Shortcut: no activation needed

Both launchers and both entry points are **venv-aware**:

| Mechanism | Effect |
| :--- | :--- |
| `run.bat` / `run_website.bat` | Prefer `.venv\Scripts\python.exe` if present (`run.bat:3-7`) |
| `main.py:18-26` | If `rasterio` is missing in the current interpreter, silently re-exec under `.venv\Scripts\python.exe` |
| `web_server.py:38-39` | Sets `PYTHON_BIN` to the venv interpreter for subprocess runs |
| `run_website.ps1` | Same idea, PowerShell edition |

So `py -3.13 -m venv .venv` + `pip install -r requirements.txt` + **any** of the launchers works
without ever calling `activate`.

---

## 3. Dependency inventory

### 3.1 Declared (`requirements.txt` — authoritative, fully pinned)

```
numpy==2.5.3        scipy==1.18.1      rasterio==1.5.2   scikit-image==0.26.0
geopandas==1.2.0    shapely==2.2.0     matplotlib==3.11.2
pyproj==3.8.0       pandas==3.0.6      pytest==9.1.1
```

| Package | Used by | Imported? (verified) |
| :--- | :--- | :--- |
| `numpy` | every module | ✅ |
| `scipy` | `terrain` (`convolve`, `uniform_filter`), `psr` (`ndimage.label`), `ml_recommender` (`distance_transform_edt`, `gaussian_filter`, `maximum_filter`) | ✅ |
| `rasterio` | `io_utils`, `prepare_lola_dataset` | ✅ |
| `geopandas` | `psr` (GeoDataFrame), `mapping` (map outlines) | ✅ (optional in `mapping`, guarded) |
| `shapely` | `psr` (geometry) | ✅ |
| `matplotlib` | `terrain`, `mapping`, `validate`, `mission_report` | ✅ |
| `pyproj` | transitively needed by geopandas/rasterio CRS objects | ✅ (not imported directly by LunaSafe code) |
| `pandas` | **not imported anywhere in `*.py`** — pulled in by geopandas | ⚠️ declared but unused directly |
| `pytest` | `tests/` | ✅ |
| `scikit-image` | **never imported** | ⚠️ declared but unused (Issue I-16) |

### 3.2 Undeclared / drift

| Observation | Detail |
| :--- | :--- |
| `requirement.txt` (singular) | A near-duplicate of `requirements.txt` with **different content** (11 vs 12 lines) → anyone editing the wrong file silently loses a pin (Issue I-16) |
| `pyflakes==4.0.3` | **Installed in the venv but not in any requirements file** (verified via `pip list`) |
| `colorama` | Installed transitively (Windows console colors); unused by LunaSafe code |
| No lock file / hashes | Pins are exact-version, but there is no `pip-compile`/`--require-hashes` supply-chain lock |

### 3.3 Transitive packages actually installed (34 total)

`affine, attrs, certifi, click, colorama, contourpy, cycler, fonttools, geopandas, ImageIO,
iniconfig, kiwisolver, lazy-loader, matplotlib, networkx, numpy, packaging, pandas, pillow, pip,
pluggy, pyflakes, Pygments, pyogrio, pyparsing, pyproj, pytest, python-dateutil, rasterio,
scikit-image, scipy, shapely, six, tifffile, tzdata`

> `pyogrio` is the default geopandas IO engine; `ImageIO`+`tifffile` come from `scikit-image`.
> Do not prune them — they are required by the pinned versions above.

---

## 4. Offline / air-gapped setup

1. On a connected machine: `pip download -r requirements.txt -d wheels\`
2. Copy `wheels\` + repo to the offline machine: `pip install --no-index --find-links=wheels -r requirements.txt`
3. Everything else (three.js, dashboard) is already vendored in-repo; only KaTeX/Google Fonts are CDN
   (`web/index.html:16-17`) and the app still works without them.

---

## 5. Verifying the installation

```powershell
# 1. Interpreter & deps present
.\.venv\Scripts\python.exe -c "import rasterio, scipy, geopandas, shapely, matplotlib, pytest; print('deps OK')"

# 2. Data + config self-check
.\.venv\Scripts\python.exe -c "import config; print(config.BASE_DIR, config.LUNAR_SOUTH_POLE_PROJ4)"

# 3. Full test suite (runs the whole pipeline — see warning below!)
.\.venv\Scripts\python.exe -m pytest -q
```

**Expected result (2026-10-17):** `32 passed, 1 warning in 25.28s`.

> ⚠️ **`pytest` is destructive to `outputs/`.** `tests/test_main.py:19` executes the real pipeline
> and rewrites 15 artifacts (a known diff on `outputs/lunasafe_hazard_map.pdf` and
> `outputs/psr_polygons.dbf` was observed and reverted). After running tests:
> ```powershell
> git status            # inspect
> git checkout -- outputs/   # if you want the committed versions back
> ```

### Quick smoke checks (non-destructive)

```powershell
# Web server (terminal 1)
.\.venv\Scripts\python.exe web_server.py
# → "LunaSafe Mission Control running on http://localhost:8050"

# Health (terminal 2)
curl.exe http://localhost:8050/api/status
```

---

## 6. Platform-specific notes

| Topic | Detail |
| :--- | :--- |
| PowerShell execution policy | `run_website.ps1` may be blocked; use `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` or just use the `.bat` |
| Path with spaces | Launchers quote paths (`run.bat:4`); `sys.path` inserts are `str()`-safe. But `prepare_lola_dataset.py:15` hard-codes `e:\sistec\LunaSafe` → breaks on any other checkout (Issue I-15) |
| Long paths | `data/ldem_75s_240m.jp2` is fine; enable Win32 long paths if you move data deeper |
| Non-Windows | Not supported out of the box: no `.sh` launchers, `main.py:18-26` venv logic references `\Scripts\python.exe`, `PYTHON_BIN` in `web_server.py` likewise. Workaround: activate a venv manually — the code itself is POSIX-friendly |
| Python > 3.13 | Untested; pinned wheels (e.g. `pandas==3.0.6`) may not exist yet for newer versions |
| Conda users | Not supported/tested; `rasterio`'s wheel and conda-forge GDAL can conflict. Prefer the venv route |

---

## 7. Uninstall / reset

```powershell
Remove-Item -Recurse .venv                 # environment only
Remove-Item -Recurse .pytest_cache         # test cache
git clean -nxd                              # DRY RUN — show every untracked file
git clean -xdf                              # deletes untracked outputs/data additions too — review first
```

Deleting `outputs/` is safe (regenerated by `python main.py --force-synthetic`), but deleting
`data/synthetic_*.tif` removes the only fallback dataset unless you regenerate it via
`io_utils.generate_synthetic_lunar_crater()` (no standalone CLI exists for that).

---

## 8. Troubleshooting installation

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `'rasterio' is not recognized` / ImportError in plain `python` | venv not used | use a launcher, or activate, or `main.py` will auto-switch |
| `Cannot open clipboard` / `permission denied` writing `.pyc` | read-only checkout | `pip install -r requirements.txt` after fixing permissions |
| `pip install rasterio==1.5.2` fails to find a wheel | Python version too new/old | use Python 3.10–3.13 |
| `FileNotFoundError: ...\web\index.html` | run from another directory | launchers `cd /d "%~dp0"` first — or run from repo root |
| `Port 8050 in use` → falls back to 8080 | another instance | `netstat -ano | findstr :8050` and kill, or edit `web_server.py:835` |
| Tests create huge diffs | pipeline rewrites artifacts | see §5 warning; `git checkout -- outputs/` |
