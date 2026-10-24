# 04 — Tech Stack & Dependencies

*Everything below was read from `requirements.txt`, `requirement.txt`, `.venv/Lib/site-packages` metadata,
the actual `import` statements across the source tree, and direct file inspection on 2026-10-17.*

---

## 1. Runtime

| Item | Value | Evidence |
| :--- | :--- | :--- |
| Language | **Python 3.13.0** | `.\.venv\Scripts\python.exe -V` |
| Declared support | Python 3.10 – 3.13 | `requirements.txt:2`, `README.md:73` |
| OS in use on this machine | Windows 10/11 (`win32`) | environment |
| Virtual environment | `.venv/` (self-ignoring: `.venv/.gitignore` contains `*`) | `git check-ignore -v .venv/pyvenv.cfg` |
| Package manager | `pip` 26.2.1 (inside venv) | `pip list` |
| Cross-platform claim | PARTIALLY VERIFIED — code uses `Path` and stdlib, but `main.py:19`, `web_server.py:38`, `prepare_lola_dataset.py:15` hardcode **Windows** venv/paths (`.venv/Scripts/python.exe`, `e:\sistec\...`) |

## 2. Pinned direct dependencies (`requirements.txt`)

| Package | Pinned version | Installed | Actually imported? | Purpose (where) |
| :--- | :---: | :---: | :---: | :--- |
| numpy | 2.5.3 | 2.5.3 ✅ | ✅ | All array maths — `terrain.py`, `hazard.py`, `psr.py`, `ml_recommender.py`, `validate.py`, `mapping.py`, `web_server.py` |
| scipy | 1.18.1 | 1.18.1 ✅ | ✅ | `scipy.ndimage` convolutions/filters/label/distance transform — `terrain.py:12`, `psr.py:14`, `ml_recommender.py:12` |
| rasterio | 1.5.2 | 1.5.2 ✅ | ✅ | GeoTIFF read/write, CRS, affine transforms, reprojection — `io_utils.py:14-24`, `psr.py:19-21`, `ml_recommender.py:13`, `prepare_lola_dataset.py:12` |
| geopandas | 1.2.0 | 1.2.0 ✅ | ✅ | Vector GeoDataFrame + `.to_file()` for GeoJSON/Shapefile — `psr.py:22`, `mapping.py:25`, tests |
| shapely | 2.2.0 | 2.2.0 ✅ | ✅ | Polygon geometry construction/repair — `psr.py:23` (`shapely.geometry as sg`) |
| matplotlib | 3.11.2 | 3.11.2 ✅ | ✅ | All figures; forced `Agg` backend (`config.py:148-152`, `terrain.py:13-14`, `validate.py:14-15`, `mission_report.py:14-15`) |
| pyproj | 3.8.0 | 3.8.0 ✅ | ❌ **never imported directly** | Transitively used by geopandas/rasterio for CRS handling; pinned but unused in first-party code |
| pandas | 3.0.6 | 3.0.6 ✅ | ✅ | Summary tables — `hazard.py:17`, `validate.py:13`, `mission_report.py:13` |
| scikit-image | 0.26.0 | 0.26.0 ✅ | ❌ **never imported** (verified: 0 matches for `skimage` in `*.py`/`tests/*.py`) | Listed as required by `.agents/rules/lunasafe.md:7` but unused → dead dependency (task T-12) |
| pytest | 9.1.1 | 9.1.1 ✅ | ✅ | Test runner — `tests/` |

> ⚠️ `requirement.txt` (singular) exists as a near-duplicate of `requirements.txt` (missing only the
> header comment). Both install the same pins today. Keep one; see task **T-13**.

## 3. Transitive dependencies actually present in `.venv`

`affine`, `attrs`, `certifi`, `click`, `colorama`, `contourpy`, `cycler`, `fonttools`, `ImageIO`,
`iniconfig`, `kiwisolver`, `lazy-loader`, `networkx`, `packaging`, `pillow`, `pluggy`, `Pygments`,
`pyogrio`, `pyparsing`, `python-dateutil`, `six`, `tifffile`, `tzdata`.

- `pyogrio` is the default GeoDataFrame engine used by `gdf.to_file(...)` (`psr.py:246,250`).
- `networkx`, `imageio`, `pillow`, `tifffile`, `lazy-loader` are **scikit-image's** requirements — they
  exist only because scikit-image is pinned, even though scikit-image itself is never used.

## 4. Packages present but NOT pinned in `requirements.txt`

| Package | Version | Why it matters |
| :--- | :---: | :--- |
| `pyflakes` | 4.0.3 | Installed manually (Required-by: *nothing*). Suggests someone ran a linter ad-hoc. No config file exists, so linting is not part of any workflow |
| `pip` | 26.2.1 | Tooling only |

**Consequence:** a fresh `pip install -r requirements.txt` will **not** install `pyflakes`.
That is fine today because no script invokes it, but it means "works on my machine" risk if someone
adds a lint step without pinning it.

## 5. Frontend stack (`web/`)

| Technology | Version | Load path | Purpose |
| :--- | :---: | :--- | :--- |
| HTML5 | — | `web/index.html` (≈1,888 lines) | 8-tab single-page layout |
| CSS (vanilla) | — | `web/styles.css` (≈2,282 lines) | Dark "mission control" theme, responsive breakpoints at 1920/1366/390 px |
| JavaScript (vanilla, no build step) | — | `web/app.js` (≈4,560 lines) | All UI logic; **no bundler, no `package.json`, no npm** |
| three.js | **r128** | local `web/vendor/three.min.js` (603 KB), CDN fallback pinned to `r128` / `0.128.0` at `web/index.html:25-26` | 3D terrain mesh, lighting, raycasting |
| OrbitControls | r128-era | `web/vendor/OrbitControls.js` (26 KB), CDN fallback `three@0.128.0/examples/js/controls/OrbitControls.js` | 3D camera control |
| KaTeX | 0.16.8 | CDN only — `web/index.html:16-17` (`cdn.jsdelivr.net`) | Renders the hazard-score formula |
| Google Fonts | — | `web/index.html:9-11` (`fonts.googleapis.com`) | `Inter`, `Outfit`, `JetBrains Mono` |

**Offline implications (VERIFIED from code):** the page itself, the CSS, the JS and three.js all load
locally from the server, so the console works without internet **except** KaTeX and the webfonts,
which fall back to system fonts / plain-HTML formulas when unreachable
(`renderKatexFormula` in `web/app.js` has an HTML fallback).

## 6. Server stack

| Component | Choice | Evidence |
| :--- | :--- | :--- |
| HTTP framework | **None** — Python standard library | `from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler` (`web_server.py:22`) |
| Concurrency | Thread-per-request (`ThreadingHTTPServer`) + background `threading.Thread` for pipeline/download workers | `web_server.py:406-407`, `:666`, `:841` |
| Shared state | Two module-level globals guarded by one `threading.Lock` | `web_server.py:42-45` (`PIPELINE_LOCK`, `PIPELINE_RUNNING`, `PIPELINE_LOGS`, `DOWNLOAD_STATUS`) plus `RASTER_CACHE` (`:48-56`) |
| JSON | stdlib `json` | `web_server.py:14` |
| Outbound HTTP | stdlib `urllib.request` (NASA download) | `web_server.py:19,633-648` |
| Static file serving | `SimpleHTTPRequestHandler` rooted at the **repo root** | `web_server.py:93` (`directory=str(ROOT_DIR)`), fallback `:152` |
| Pipeline execution | `subprocess.Popen` of `main.py` | `web_server.py:373-381` |
| Process bootstrap | auto-relaunch under `.venv` if deps missing | `main.py:18-26`, `web_server.py:38-39` |

No Flask, no FastAPI, no Django, no ASGI, no websockets — **VERIFIED by import list**.

## 7. Data / file formats

| Format | Reader | Writer | Role |
| :--- | :--- | :--- | :--- |
| GeoTIFF (`.tif`) | `io_utils.read_geotiff` (`:154`) | `io_utils.write_geotiff` (`:116`, LZW, single band) | DEM, PSR, all derivative rasters |
| JPEG2000 (`.jp2`) | rasterio (NASA LOLA) | — | `data/ldem_75s_240m.jp2` (10.7 MB) |
| GeoJSON | geopandas / `json` | `psr.py:246` | PSR polygons |
| ESRI Shapefile | — | `psr.py:250` (`.shp/.shx/.dbf/.prj/.cpg`) | GIS interchange |
| CSV | stdlib `csv` / pandas | `hazard.py:241` | Class area summary |
| JSON (bundle) | stdlib `json` | `export_web_data.py:105` | `outputs/web_data.json` — the web UI's data contract |
| JSON (telemetry) | stdlib `json` | `ml_recommender.py:285` | `landing_sites.json` |
| PNG / PDF (figures) | matplotlib | matplotlib `savefig` at 300 DPI | maps, histograms, sensitivity chart |
| PDF (report) | matplotlib `PdfPages` | `mission_report.py:60` | 2-page mission report |
| HTML | — | `build_interactive_ui.py` | legacy `dashboard.html` |

## 8. Test stack

| Item | Value |
| :--- | :--- |
| Runner | `pytest` 9.1.1 invoked as `python -m pytest` |
| Config file | **None** — no `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`, or `conftest.py` (NOT FOUND) |
| Import bootstrap | Each test file manually inserts the repo root into `sys.path` (e.g. `tests/test_main.py:9-11`) |
| Fixtures used | `tmp_path`, `capsys` (stdlib pytest) |
| Coverage tool | **NOT FOUND** (`pytest-cov` not installed) |
| Lint/format tool config | **NOT FOUND** |

## 9. Why these technologies appear — evidence-based reading

> ⚠️ Per the evidence rules, the motivations below are **INFERRED** from code and rules files unless
> a source document states them explicitly.

| Technology | Documented reason | Actual reason visible in code |
| :--- | :--- | :--- |
| rasterio/geopandas/shapely | Required by `.agents/rules/lunasafe.md:7` (AUTHOR STATED) | Needed to keep a real CRS on outputs and to emit `.shp`/`.geojson` (`psr.py:244-250`) |
| scipy | Required by `.agents/rules/lunasafe.md:7` | `ndimage.convolve/uniform_filter/label/distance_transform_edt/gaussian_filter` replace ~400 lines of hand-written kernels |
| matplotlib Agg | rule: "headless plotting" (`config.py:147`) | Must render figures without a display so CI/servers work |
| stdlib `http.server` | NOT FOUND (no stated reason) | INFERRED: zero-dependency demo convenience for a hackathon |
| three.js r128 (2021) | NOT FOUND | INFERRED: last version with the classic global `THREE.OrbitControls` API used at `web/app.js:1790` |
| No frontend build tooling | NOT FOUND | INFERRED: keeps the demo one-command (`python web_server.py`) |

## 10. Compatibility & risk notes

| Risk | Detail | Severity |
| :--- | :--- | :--- |
| Extremely new pins | `numpy==2.5.3`, `pandas==3.0.6`, `pytest==9.1.1`, `scipy==1.18.1` are very recent majors; older Python (3.10) wheels may not exist for all of them → the "3.10+ supported" claim is **PARTIALLY VERIFIED** (only 3.13 exercised here) | Medium |
| Windows-only paths | `.venv/Scripts/python.exe` (`main.py:19`, `web_server.py:38`) breaks auto-relaunch on Linux/macOS; `main.py` still runs, just without the venv-switch convenience | Medium |
| Hard-coded absolute path | `prepare_lola_dataset.py:15` → `Path(r"e:\sistec\LunaSafe")` | High on other machines |
| Unused pins | `scikit-image`, (effectively) `pyproj` add ~40 MB and install time | Low |
| Duplicated requirements file | `requirement.txt` vs `requirements.txt` | Low (drift risk) |
| Vendored 2021 three.js | r128 has known advisories upstream; it is a **local static file**, not fetched at runtime (CDN is only a fallback) | Low for a local demo |
| CDN dependency | KaTeX + Google Fonts need internet; degrade gracefully | Low |
| No lockfile beyond `requirements.txt` | Transitive versions unpinned (e.g. `pyogrio 0.13.0`) | Medium for reproducibility |
