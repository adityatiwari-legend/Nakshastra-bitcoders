# 01 — Project Overview (verified)

## 1. Identity

| Field | Value | Evidence |
| :--- | :--- | :--- |
| Product name | **LunaSafe** | `config.py` docstrings, `main.py:53`, GeoTIFF tag `PROJECT=LunaSafe` (`hazard.py:217`) |
| Repository | `ORBISLUNA` | `git remote -v` → `https://github.com/kushbansal2005/ORBISLUNA.git` |
| Local root | `E:\sistec\LunaSafe` | working directory |
| Origin | Hackathon **Problem Statement 02 — Lunar Landing Site Characterization** | `.agents/rules/lunasafe.md:3`, `main.py:3` |
| Target region | Lunar South Pole, 80°S–90°S | `README.md:30`, `web_server.py:242` |
| Primary users | Mission planners / hackathon judges / evaluators evaluating landing-site screening | `PITCH_SCRIPT.md`, `README_WEB.md:36` |
| Delivery form | Python package (flat modules) + static web frontend + file artifacts | repository tree |

## 2. The problem it solves

**VERIFIED problem framing** (from `.agents/rules/lunasafe.md` and `PROJECT_SPECIFICATION.md`, both
written by the project authors; the *technical* claims below are checked against code):

1. **Water ice lives in permanent shadow; landers die in permanent shadow.** PSRs are scientifically
   the highest-value targets and operationally the most dangerous places to touch down.
2. **Amateur GIS pipelines mislabel lunar data with Earth datums.** LunaSafe actively rejects Earth
   CRS strings — `io_utils.inspect_raster()` raises `ValueError` if it sees `EPSG:4326`, `EPSG:3857`,
   `EPSG:4269`, `WGS 84` or `WGS_1984` (`io_utils.py:199-206`, tested by
   `tests/test_preprocessing.py::test_earth_epsg_protection`).
3. **"Flat ground in the dark" is not "safe".** A classical classifier would call a flat crater floor
   Safe. LunaSafe forces such pixels into **Class 4 Shadowed-Unknown** (`hazard.py:111-113`,
   rule 8 in `validate.py:131-133`).

## 3. What the system actually does (implemented capabilities)

Each row is traceable to source; full matrix with tests in
[`03_FEATURES_AND_IMPLEMENTATION_STATUS.md`](03_FEATURES_AND_IMPLEMENTATION_STATUS.md).

1. **Ingest** a DEM + PSR mask (GeoTIFF), auto-generating a synthetic crater benchmark if the files are
   missing (`io_utils.load_and_align_datasets()`, `io_utils.py:380-414`).
2. **Align grids** — shape / CRS / affine transform compared; on mismatch either loud-fail
   (`--fail-on-mismatch`) or nearest-neighbour reprojection (`io_utils.py:288-377`).
3. **Delineate PSRs** — binarise, remove speckle components < 9 px, compute km², export GeoTIFF +
   GeoJSON + Shapefile with provenance strings (`psr.py:174-269`).
4. **Derive terrain metrics** — Horn slope & aspect, elevation std-dev roughness, Riley TRI,
   histogram figure (`terrain.py:293-425`).
5. **Classify hazards** into classes 0–4 with the weighted score and hard overrides
   (`hazard.py:61-134`), and export a CSV area table (`hazard.py:137-182`).
6. **Render cartography** — 4-panel 300 DPI PNG + PDF with scale bar, north arrow, legend
   (`mapping.py:149-380`).
7. **Validate** — 9-rule consistency audit, slope-threshold sensitivity study, PSR metric calculator
   (`validate.py:70-280`).
8. **Recommend landing sites** — Top-3 ellipses via distance-transform fitness optimisation, plus a
   Gaussian bandpass boulder/micro-hazard probability raster (`ml_recommender.py:18-215`).
9. **Publish a PDF mission report** on demand (`mission_report.py:22`).
10. **Serve a web Mission Control console** with 8 tabs, live recalculation, 3D WebGL terrain,
    artifacts download, LOLA downloader (`web_server.py` + `web/`).

## 4. Use cases (each maps to real code)

| # | Use case | Trigger | Entry code |
| :---: | :--- | :---| :--- |
| U1 | Batch screening of a region for a landing ellipse | `python main.py` | `main.py:237` |
| U2 | Interactive "what-if" on safety thresholds | Move slider → `POST /api/recalculate` | `web_server.py:411` |
| U3 | Judge-facing 60-second automated demo | `🏆 60s Tour` button | `web/app.js` `startJudgeTour()` (≈line 4331) |
| U4 | Offline demonstration with no network | `Load Offline Demo` button | `web_server.py:777` |
| U5 | Ingest real NASA LRO LOLA South Pole data | `Ingest` button → `POST /api/download-lola` | `web_server.py:601` |
| U6 | Download deliverables (GeoTIFF/CSV/PDF/Shapefile) | `GET /api/download/<name>` | `web_server.py:789` |
| U7 | Prove the classifier obeys its own rules | `GET/POST /api/audit` | `web_server.py:549` |
| U8 | Regenerate a self-contained legacy dashboard | `python build_interactive_ui.py` | `build_interactive_ui.py:10` |

## 5. Expected outputs

`main.py:216-230` prints exactly **15** artifacts; `mission_report.pdf` is a 16th produced on demand
by the web server (`web_server.py:793-798`). Actual files present in `outputs/` at documentation time
(VERIFIED by directory listing):

`psr_binary.tif`, `psr_polygons.geojson`, `psr_polygons.shp/.shx/.dbf/.prj/.cpg`,
`psr_polygons_bundle.zip`, `slope_deg.tif`, `aspect_deg.tif`, `roughness_std_m.tif`,
`roughness_tri_m.tif`, `terrain_histograms.png`, `hazard_classes.tif`, `hazard_summary.csv`,
`lunasafe_hazard_map.png`, `lunasafe_hazard_map.pdf`, `slope_sensitivity.png`,
`landing_sites.json`, `boulder_hazard.tif`, `mission_report.pdf`, `web_data.json`.

## 6. System boundaries

**Inside the boundary (implemented):** local file I/O, in-process numeric computation, local HTTP
server on `0.0.0.0:8050` (binds all interfaces — `web_server.py:840`), one optional outbound HTTP GET
to NASA PDS for a ~10 MB JP2 (`web_server.py:633`), optional Google Fonts / KaTeX / cdnjs requests
from the browser (`web/index.html:9-26`).

**Outside the boundary (does not exist):**
- No database, no ORM, no migrations — [`10_DATABASE_AND_DATA_MODEL.md`](10_DATABASE_AND_DATA_MODEL.md).
- No user accounts, sessions, or authentication — [`16_SECURITY_AND_PRIVACY_REVIEW.md`](16_SECURITY_AND_PRIVACY_REVIEW.md).
- No deployment pipeline, container, or hosting config — [`17_DEPLOYMENT_AND_RELEASE_GUIDE.md`](17_DEPLOYMENT_AND_RELEASE_GUIDE.md).
- No trained/serialized ML model anywhere in the repository (search for `.pkl`/`.joblib`/`.h5`/`.onnx` → NOT FOUND).
- No message queue, no cache server, no async framework — state is two module-level globals in
  `web_server.py:42-56`.

## 7. Assumptions the code makes

| Assumption | Where encoded | Consequence if wrong |
| :--- | :--- | :--- |
| Pixel size drives all physical thresholds; 3×3 window ≈ lander-scale roughness | `config.TERRAIN_WINDOW_SIZE = 3` (`config.py:96`) | On 240 m/px LOLA data a 3×3 window spans 720 m — roughness is not lander-scale |
| Binary PSR ⇒ shadow fraction `D = 0` in score `H` | `hazard.py:46-48` | The 0.20 shadow weight is inert in the default pipeline (VERIFIED — `main.py:137` never passes `shadow_fraction`) |
| 100 m radius ellipse + 40 m standoff represents Artemis dispersion | `config.py:51-52` | 40 m standoff is **not enforced in the recommender** — see Issue **I-05** in [`19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](19_CURRENT_STATUS_AND_KNOWN_ISSUES.md) |
| Pixel size = 20 m when computing web areas | `web_server.py:470` | Areas wrong by 144× on the 240 m/px dataset — Issue **I-02** |

## 8. Known limitations (summary)

Detailed, ranked in [`19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](19_CURRENT_STATUS_AND_KNOWN_ISSUES.md).

1. The "PSR segmentation benchmark" in the pipeline compares the mask **to itself**, so
   IoU/Precision/Recall/F1 are always 1.0 (`validate.py:301-308`) — Issue **I-01**.
2. Web audit endpoint never reports Rule 4 violations (wrong dict key, `web_server.py:576`) — Issue **I-03**.
3. Thresholds sent to `POST /api/run-pipeline` are silently ignored by the child process — Issue **I-04**.
4. The "real data" PSR mask is not a published PSR atlas; it is derived by depth thresholding
   (`prepare_lola_dataset.py:51-56`) — Issue **I-08**.
5. `outputs/web_data.json` is stale (250×250 LOLA bundle) while the rest of `outputs/` is a 200×200
   synthetic run — Issue **I-06**.
6. Validation-tab sensitivity charts in the browser display hard-coded numbers — Issue **I-10**.

## 9. Objectives vs. reality

The original objective list is in [`02_PROBLEM_STATEMENT_AND_OBJECTIVES.md`](02_PROBLEM_STATEMENT_AND_OBJECTIVES.md).
Honest status:

- **Fully met:** deterministic 5-class surface, Class 4 innovation, geodetic enforcement, rule audit,
  cartography, reproducibility on synthetic data, 32-test suite.
- **Met with caveats:** web console (works in code, not browser-tested in this run), real LOLA path
  (files exist; PSR derivation is a heuristic), "AI" boulder detector (deterministic filtering, not ML).
- **Not met / not present:** independent PSR accuracy benchmark, deployment, auth, CI, boulders
  resolved below DEM resolution, regolith bearing-capacity modelling (explicitly disclosed in
  `mission_report.py:211-218`).
