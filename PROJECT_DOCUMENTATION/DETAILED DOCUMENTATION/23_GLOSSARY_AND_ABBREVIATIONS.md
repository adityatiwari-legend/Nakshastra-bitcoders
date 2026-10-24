# 23 — Glossary and Abbreviations

*Terms as used **in this repository** (with the file where the concept lives). General remote-sensing
definitions are standard; LunaSafe-specific usage is marked 🌙.*

---

## Mission & data

| Term | Meaning |
| :--- | :--- |
| **PSR** 🌙 | Permanently Shadowed Region — a lunar area that never receives direct sunlight (cold trap). Represented as a binary mask (`psr.py`), vector polygons (`psr_polygons.*`), and hazard **Class 4** |
| **ALSS** 🌙 | Autonomous Landing Site Selection — the landing-ellipse recommender (`ml_recommender.py`) |
| **DEM** | Digital Elevation Model — the single-band elevation raster (`data/*dem*.tif`) |
| **LOLA** 🌙 | Lunar Orbiter Laser Altimeter, instrument on NASA's LRO — source of `ldem_75s_240m.jp2` |
| **LRO** | Lunar Reconnaissance Orbiter (NASA) |
| **PDS** | NASA Planetary Data System — the archive the built-in downloader fetches from (`web_server.py:633`) |
| **JP2** | JPEG 2000 image — raw LOLA raster before georeferencing (`prepare_lola_dataset.py:23`) |
| **GeoTIFF** | TIFF with embedded georeferencing (CRS + affine transform). The only raster format used here (`io_utils.py:116`) |
| **GeoJSON** | JSON encoding of vector features (`outputs/psr_polygons.geojson`) |
| **Shapefile** | ESRI vector bundle (`.shp/.shx/.dbf/.prj/.cpg`) written alongside GeoJSON (`psr.py:247+`) |
| **cold trap** | Synonym for the coldest permanently dark pockets inside PSRs |
| **provenance** 🌙 | String describing whether data is `SYNTHETIC DEMO` or `LOLA-derived … (Reference)` (`config.py:138-139`) — project rule: never overstate it |
| **NoData** | Sentinel for missing pixels, `-9999.0` (`config.DEFAULT_NODATA_VALUE`); always hazard Class 0 |
| **ground truth** | Independent measured reference. ⚠️ LunaSafe has **none** shipped; `/api/psr-validation` says `UNLOADED` (`web_server.py:723`) |

## Coordinate systems

| Term | Meaning |
| :--- | :--- |
| **CRS** | Coordinate Reference System |
| **PROJ string** 🌙 | CRS as text — LunaSafe's only CRS: `+proj=stere +lat_0=-90 … +R=1737400 +units=m` (`config.py:62`) |
| **polar stereographic** | Projection from the pole — used for the lunar south pole (`Moon2000_spole` in `data/lola_*.tif`) |
| **R = 1 737 400 m** 🌙 | Moon's mean radius — the marker that distinguishes lunar CRS from Earth CRS (asserted by `tests/test_smoke.py:41`) |
| **Earth EPSG guard** 🌙 | Refusal to process Earth-coded data — raises at `io_utils.py:199-206` |
| **affine transform** | The 6-coefficient `gdal`/`affine` matrix mapping pixel ↔ world coordinates; compared to 1e-4 tolerance (`io_utils.py:257-285`) |
| **grid alignment** | Same shape + CRS + transform — precondition for combining two rasters |
| **offset='center'** | Reading world coordinates of a pixel's centre (used for site easting/northing, `ml_recommender.py`) |

## Terrain & hazard maths

| Term | Meaning |
| :--- | :--- |
| **Horn** | Horn (1981) 3×3 slope/aspect algorithm — `terrain.py:55-64` |
| **slope** 🌙 | Max gradient in degrees; safe < 5°, hard-unsafe ≥ 15° |
| **aspect** | Downslope direction, degrees clockwise from north; flat terrain forced to 0° |
| **roughness (std)** 🌙 | 3×3 rolling standard deviation of elevation (micro-relief), metres — `terrain.py:90` |
| **TRI** | Terrain Ruggedness Index (Riley et al. 1999) — RMS of neighbour elevation differences (`terrain.py:139`) |
| **H (hazard score)** 🌙 | Screening index `0.50·S + 0.30·R + 0.20·D` (`hazard.py:41-54`) |
| **S / R / D** | Normalised slope / roughness / shadow terms |
| **hard override** 🌙 | Rule that bypasses H: slope ≥ 15° or roughness ≥ 5 m ⇒ Class 3 (`hazard.py:100-102`) |
| **Class 0–4** 🌙 | 0 NoData · 1 Safe · 2 Caution · 3 Unsafe · 4 Shadowed-Unknown (`config.py:109-113`) |
| **Class 4 ≠ safe** 🌙 | The project's defining invariant (`.agents/rules/lunasafe.md`) |
| **hillshade** | Shaded-relief rendering from slope+aspect, sun az 315°/alt 45° (`mapping.py:30`) |
| **despeckle** | Removal of small connected components — `< 9 px` PSR blobs deleted (`psr.py:61-91`) |
| **binarise** | Converting a continuous mask to {0,1} at threshold 0.5 (`psr.py:30`) |
| **connected component / 8-connectivity** | Pixel blob labelling — `scipy.ndimage.label` with a 3×3 structure |
| **EDT** | Euclidean Distance Transform — clearance of a safe pixel to the nearest non-safe pixel (`ml_recommender.py:~100`) |
| **fitness** 🌙 | `0.35·clearance + 0.30·flatness + 0.20·smoothness + 0.15·science` (`ml_recommender.py:143-148`) |
| **science term** | Gaussian preference centred 250 m from PSR (`ml_recommender.py:140`) |
| **ellipse radius** 🌙 | 100 m minimum clearance for a landing candidate (`config.py:51`) |
| **standoff / clearance buffer** 🌙 | 40 m exclusion ring from hazards — *drawn in the UI, not enforced in code* (Issue I-05) |
| **high-pass residual** | DEM minus its σ=2 Gaussian trend — the boulder-detection signal (`ml_recommender.py:34-49`) |
| **sigmoid squashing** | `1/(1+e^(-1.8·(z−2.2)))` → 0…1 probability (`ml_recommender.py:57-64`) |
| **maximum filter** | Morphological local-maxima finder used to pick boulder peaks (5×5) |
| **sensitivity analysis** 🌙 | Recompute class areas at slope thresholds 5/10/15° + unsafe-vs-slope curve (`validate.py:151`) |

## Validation & rules

| Term | Meaning |
| :--- | :--- |
| **9-rule audit** 🌙 | Independent numpy re-check of the 9 classification invariants (`validate.py:70-148`) |
| **violations** | Pixel counts violating a rule; non-zero ⇒ `is_consistent: false` |
| **precision / recall / IoU / F1** | Standard mask-agreement metrics — only meaningful vs an *independent* reference (Issue I-01) |
| **benchmark mode** 🌙 | `/api/psr-validation?benchmark` compares against the input mask itself and is *labelled* as a benchmark (`web_server.py:692-713`) |

## Software & ops

| Term | Meaning |
| :--- | :--- |
| **pipeline (7 phases)** 🌙 | ingest → PSR → terrain → hazard → cartography → validation → autonomy (`main.py:85-201`) |
| **RASTER_CACHE** 🌙 | In-memory dict of DEM/slope/roughness/PSR held by `web_server.py:48-56` |
| **data bundle** 🌙 | `outputs/web_data.json` — flat arrays + metadata consumed by the UI (`export_web_data.py:11`) |
| **offscreen canvas** | Hidden canvas per UI layer, pre-rendered then composited (`web/app.js`) |
| **debounce (250 ms)** | Slider input coalescing before `POST /api/recalculate` (`web/app.js`) |
| **ThreadingHTTPServer** | Python stdlib HTTP server, one thread per connection (`web_server.py:836`) |
| **subprocess worker** 🌙 | The async `POST /api/run-pipeline` spawns `main.py` as a child process (`web_server.py:373`) |
| **three.js r128** | Vendored WebGL library (`web/vendor/three.min.js`) |
| **OrbitControls** | three.js camera controller (vendored) |
| **KaTeX** | Math renderer loaded from CDN (`web/index.html:16`) |
| **venv** | Virtual environment at `.venv/`; launchers auto-select it |
| **pytest** | Test runner (`tests/`, 32 tests) |
| **pyflakes** | Static linter — installed but undeclared (Issue I-16) |
| **LZW** | Lossless GeoTIFF compression used for every raster (`io_utils.py:145`) |
| **Agg backend** | Headless matplotlib renderer forced at import (`config.py:148-151`) |
| **procedural generation** | Deterministic synthetic crater creation with a seeded RNG (`io_utils.py:416`) |

## Issue & doc notation used in `PROJECT_DOCUMENTATION/`

| Symbol | Meaning |
| :--- | :--- |
| `I-nn` | Open issue, register in `19_CURRENT_STATUS_AND_KNOWN_ISSUES.md` |
| `T-nn` | Roadmap task, `20_ROADMAP_AND_NEXT_STEPS.md` |
| `SEC-nn` | Security finding, `16_SECURITY_AND_PRIVACY_REVIEW.md` |
| `M-nn` | Minor/hygiene issue (inside doc 19) |
| `A1…A10` | Architectural decisions (doc 05 §9) |
| `O1…O15` | Objectives (doc 02) |
| ✅ 🟠 🟡 🔴 ⚪ | complete · partial/risky · partial · broken/absent · info |
| VERIFIED / INFERRED / … | evidence labels required by the task spec |
