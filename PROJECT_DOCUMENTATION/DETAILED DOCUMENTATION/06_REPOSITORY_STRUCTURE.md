# 06 — Repository Structure

*Annotated tree of `E:\sistec\LunaSafe` as of 2026-10-17 (branch `main`, clean tree).
Sizes/line counts verified by direct inspection. `.venv/`, `.git/`, `.pytest_cache/` internals are
excluded except where behaviourally relevant.*

**Legend:** 🧠 source (you will edit) · ⚙️ config/rules · 🧪 tests · 📦 data (inputs, committed) ·
📤 outputs (generated, committed) · 🌐 frontend · 🧰 tooling · 📄 docs (pre-existing) · 🗑️ legacy/unused · ♻️ generated cache

---

```text
LunaSafe/
│
├── 🧠 main.py                    260 L  CLI entry point; orchestrates 7 phases  (run_pipeline @38, main @237)
├── 🧠 config.py                  152 L  ALL thresholds, paths, CRS, class ids/colours, plot settings
├── 🧠 io_utils.py                464 L  GeoTIFF I/O, CRS guard, grid alignment, synthetic crater generator
├── 🧠 psr.py                     269 L  PSR binarise → despeckle → area → vectorise/export
├── 🧠 terrain.py                 425 L  Horn slope/aspect, roughness std, TRI, histograms
├── 🧠 hazard.py                  263 L  Hazard score H, 5-class surface, hard overrides, CSV summary
├── 🧠 validate.py                357 L  9-rule auditor, PSR metrics, slope sensitivity study
├── 🧠 mapping.py                 380 L  4-panel 300-DPI cartography (PNG+PDF)
├── 🧠 ml_recommender.py          303 L  ALSS Top-3 ellipses + boulder bandpass detector
├── 🧠 mission_report.py          229 L  2-page PDF mission report (on demand)
│
├── 🧠 web_server.py              864 L  ThreadingHTTPServer + REST API + in-memory raster cache
├── 🌐 web/
│   ├── index.html              ~1888 L  8-tab SPA markup, KaTeX + three.js script tags
│   ├── app.js                  ~4560 L  ALL frontend logic (canvas 2D, three.js 3D, API calls)
│   ├── styles.css              ~2282 L  dark theme + responsive breakpoints
│   └── vendor/
│       ├── three.min.js         603 KB  three.js r128 (vendored, offline)
│       └── OrbitControls.js      26 KB  r128-era controls (vendored, offline)
│
├── 🧰 export_web_data.py         112 L  Flattens rasters → outputs/web_data.json (UI data contract)
├── 🧰 prepare_lola_dataset.py    107 L  NASA JP2 → data/lola_*.tif  (⚠ hard-coded e:\sistec path @15)
├── 🧰 build_interactive_ui.py   1131 L  🗑️ generates legacy dashboard.html; not imported anywhere
│
├── 🧪 tests/
│   ├── __init__.py                 1 L  (empty package marker)
│   ├── test_smoke.py             104 L  3 tests: config constants, synthetic topography, GeoTIFF roundtrip
│   ├── test_preprocessing.py     122 L  4 tests: inspect, Earth-EPSG guard, mismatch, resample
│   ├── test_psr.py               142 L  5 tests: binarise, clean, area, vectorise, end-to-end export
│   ├── test_terrain.py           116 L  4 tests: flat surface, planar ramp exactness, NoData, pipeline
│   ├── test_hazard.py            143 L  6 tests: score formula, overrides, classes, NoData, pipeline
│   ├── test_mapping.py            71 L  2 tests: hillshade, 4-panel end-to-end
│   ├── test_ml_recommender.py     97 L  3 tests: boulders, recommender, artifact generation
│   ├── test_validate.py          132 L  4 tests: PSR metric maths, audit pass, audit catches errors, sensitivity
│   └── test_main.py               38 L  1 test: full pipeline exit code + 13 artifact assertions
│
├── 📦 data/                       (committed inputs)
│   ├── synthetic_dem.tif         141 KB  200×200 @ 20 m/px synthetic crater DEM
│   ├── synthetic_psr.tif         2.4 KB  200×200 binary synthetic PSR mask
│   ├── ldem_75s_240m.jp2         10.5 MB NASA PDS LOLA polar JP2 (3812×3812 int16)
│   ├── lola_south_pole_dem.tif   246 KB  250×250 @ 240 m/px centre crop, DN×0.5 → metres
│   ├── lola_psr_mask.tif         63 KB   250×250 uint8, depth-threshold heuristic PSR
│   └── DOWNLOAD_INSTRUCTIONS.md          manual NASA/USGS ingestion guide
│
├── 📤 outputs/                    (committed generated artifacts — 19 files)
│   ├── psr_binary.tif, psr_polygons.{geojson,shp,shx,dbf,prj,cpg}, psr_polygons_bundle.zip
│   ├── slope_deg.tif, aspect_deg.tif, roughness_std_m.tif, roughness_tri_m.tif
│   ├── terrain_histograms.png, slope_sensitivity.png
│   ├── hazard_classes.tif, hazard_summary.csv
│   ├── lunasafe_hazard_map.png (1.7 MB), lunasafe_hazard_map.pdf (636 KB)
│   ├── boulder_hazard.tif, landing_sites.json
│   ├── mission_report.pdf (1.05 MB)
│   └── web_data.json (2.2 MB)  ⚠ currently a 250×250 bundle while the rest is 200×200 (Issue I-06)
│
├── ⚙️ .agents/rules/lunasafe.md   25 L  Authoritative project rules for humans & AI agents
├── 📄 README.md                  286 L  Marketing readme (some claims overstated → cross-check doc 19)
├── 📄 README_WEB.md              138 L  Web-platform readme + Mermaid diagram
├── 📄 PROJECT_SPECIFICATION.md   350 L  Long-form feature dossier / maths
├── 📄 PITCH_SCRIPT.md            136 L  5-minute pitch + 8 judge Q&A
│
├── ⚙️ requirements.txt            12 L  Pinned deps (authoritative)
├── ⚙️ requirement.txt             11 L  🗑️ near-duplicate alias — drift risk
│
├── 🧰 run.bat                      7 L  CLI launcher (venv-aware)
├── 🧰 run_website.bat             16 L  Web launcher + browser open
├── 🧰 run_website.ps1             22 L  PowerShell web launcher
├── 🧰 view_ui.bat                  3 L  Opens 🗑️ dashboard.html
│
├── 🗑️ dashboard.html            1.3 MB  Generated single-file console (legacy, not linked)
│
└── ♻️ __pycache__/ (22 tracked .pyc!), tests/__pycache__/, .pytest_cache/, .venv/
```

## 1. Where to edit for a given change

| You want to… | Edit these files | Also update |
| :--- | :--- | :--- |
| Change a safety threshold | `config.py` | `.agents/rules/lunasafe.md`, `validate.py` rule descriptions, `web/app.js` fallbacks (several hard-coded copies!), `mission_report.py:167-177` text, READMEs |
| Add a hazard class | `config.py`, `hazard.py`, `validate.py` | `mapping.py` palette, `web/app.js` palette + `PALETTE_HAZARD`, `export_web_data.py` |
| Fix a bug in slope maths | `terrain.py` | `tests/test_terrain.py` (add an exactness case) |
| Change landing-site logic | `ml_recommender.py` | `tests/test_ml_recommender.py`, `outputs/landing_sites.json` regen |
| Add a REST endpoint | `web_server.py` (`do_GET`/`do_POST` at `:95`/`:154`) | `web/app.js` caller, `api_documentation/REST_API.md` |
| Change the UI layout | `web/index.html` | `web/styles.css`, `web/app.js` |
| Change what the 2D map draws | `web/app.js` §§3 (`precomputeAllLayers`, `drawMap`) | `web/styles.css` |
| Change the 3D terrain | `web/app.js` (3D section, ≈1670–2746) | vendor three.js — do **not** upgrade casually |
| Add a dependency | `requirements.txt` **and** `requirement.txt` | `04_TECH_STACK_AND_DEPENDENCIES.md` |
| Add a test | `tests/test_<module>.py` | `14_TESTING_AND_QUALITY_ASSURANCE.md` |
| Change PDF report content | `mission_report.py` | consider reading real audit values instead of the hard-coded table |

## 2. Files that are safe to regenerate (do not hand-edit)

Everything in `outputs/` except… nothing: **all** of `outputs/` is regenerated by
`python main.py --force-synthetic` (15 artifacts) plus `mission_report.pdf` (on-demand) and
`web_data.json` (on-demand). Hand edits are lost the next time the pipeline or
`tests/test_main.py` runs.

`dashboard.html` is regenerated by `python build_interactive_ui.py`.

## 3. Files that are committed but should not be

| Path | Why it is a problem | Suggested fix |
| :--- | :--- | :--- |
| `__pycache__/*.pyc` (12 files) and `tests/__pycache__/*.pyc` (10 files) — **22 tracked binary files** | Binary noise in every commit; stale bytecode can shadow source on some Python versions | Add a root `.gitignore` and `git rm -r --cached __pycache__` (task T-11) |
| `outputs/*.tif`, `*.png`, `*.pdf`, `web_data.json` (~5 MB of binaries) | Every pipeline run creates a diff that cannot be reviewed | Either (a) keep only `hazard_summary.csv` + `landing_sites.json` in git, or (b) accept them as demo assets but add a regeneration script (team decision, task T-14) |
| `data/ldem_75s_240m.jp2` (10.5 MB) | Upstream data can be re-downloaded by the built-in downloader | Optional — keeping it makes the demo reproducible offline |

## 4. Import graph (verified by grepping `import`/`from` statements)

```
config.py            → (nothing first-party)
io_utils.py          → config
psr.py               → config, io_utils
terrain.py           → config, io_utils
hazard.py            → config, io_utils
mapping.py           → config, (+ geopandas optional)
validate.py          → config, hazard
ml_recommender.py    → config, io_utils
mission_report.py    → config
export_web_data.py   → config, io_utils
main.py              → config, io_utils, psr, terrain, hazard, mapping, validate, ml_recommender
web_server.py        → config, io_utils, hazard, ml_recommender, validate, export_web_data
                       (+ mission_report and prepare_lola_dataset imported lazily inside handlers)
prepare_lola_dataset.py → config (after sys.path.insert of a hard-coded root)
build_interactive_ui.py → config, export_web_data
tests/*              → config, io_utils, + the module under test, (+ main for test_main)
```

There are **no circular imports** and **no relative imports**; every module is loaded as a
top-level module thanks to `sys.path.insert(0, ROOT_DIR)` in `main.py:14-16`,
`web_server.py:27-29`, `prepare_lola_dataset.py:15-16` and each test file.

## 5. Hidden / easy-to-miss items

| Item | Detail |
| :--- | :--- |
| `.venv/.gitignore` | Contains `*` — that is why `git status` is clean despite `.venv/` existing. There is **no** repo-root `.gitignore` |
| `.pytest_cache/` | Self-ignoring; not tracked |
| `web/vendor/three.min.js` | 603 KB vendored; `web/index.html:20` loads it first and only falls back to CDN if `THREE` is undefined (`:22-28`) |
| `outputs/psr_polygons.prj` | Contains a `PROJCS["unknown"…SPHEROID[…,1737400,…]]` — lunar, correct, but "unknown" naming means some GIS tools show an unnamed CRS |
| `data/lola_south_pole_dem.tif` CRS | `Moon2000_spole` / `Moon_2000_IAU_IAG` spheroid R=1737400 — genuinely lunar (VERIFIED via rasterio) |
| `dashboard.html` over HTTP | No route, but reachable at `http://localhost:8050/dashboard.html` because static serving is rooted at the repo |
