# 12 — Environment Configuration

> **Key finding (VERIFIED):** LunaSafe reads **zero environment variables**. A repo-wide search for
> `os.environ` / `os.getenv` / `getenv` returns only a comment (`config.py:147`). All configuration
> is (a) Python constants in `config.py`, (b) CLI flags on `main.py`, (c) HTTP body keys on two
> POST endpoints, (d) hard-coded values in the frontend. This document is the complete config surface.

---

## 1. Configuration precedence (actual, not aspirational)

```
web request body  ──(mutates module globals)──▶  config.*  ◀── default values in config.py
                                                      │
                                                      ├─ imported by every backend module
                                                      ├─ read live by main.py subprocess? NO —
                                                      │   the subprocess re-imports config.py from disk
                                                      └─ duplicated as literals in web/app.js
```

1. **Defaults:** `config.py` at import time.
2. **Runtime override (web only):** `POST /api/recalculate` and `POST /api/run-pipeline` assign new
   values to `config` attributes (`web_server.py:341-362`, `:438-446`). These persist for the
   server process lifetime and affect *every* client. There is **no reset endpoint** — the UI's
   `resetDefaults()` simply re-posts the literal defaults from `web/app.js`.
3. **CLI:** `main.py` has no threshold flags at all — CLI users are always bound to `config.py`
   values on disk.
4. **Frontend copies:** `web/app.js` contains its own fallback numbers used by the client-side
   preview (`previewReclassifyClient`) and 40 m standoff rendering. They can drift from `config.py`.

⚠️ Issue I-11: there is no way to restore `config.py` defaults without restarting the server.

---

## 2. Complete `config.py` reference (152 lines)

### 2.1 Paths (`config.py:12-49`)

| Constant | Value | Side effect |
| :--- | :--- | :--- |
| `BASE_DIR` | repo root (`Path(__file__).resolve().parent`) | — |
| `DATA_DIR` | `<root>/data` | **directory created at import** (`:18`) |
| `OUTPUT_DIR` | `<root>/outputs` | **directory created at import** (`:19`) |
| `TESTS_DIR` | `<root>/tests` | — |
| `SYNTHETIC_DEM_PATH` / `SYNTHETIC_PSR_PATH` | `data/synthetic_dem.tif`, `data/synthetic_psr.tif` | — |
| `REAL_DEM_PATH` / `REAL_PSR_PATH` | `data/lola_south_pole_dem.tif`, `data/lola_psr_mask.tif` | existence flips the whole app to "real" mode |
| 15 × `OUTPUT_*` | `outputs/<artifact>` | one constant per artifact; used by producer **and** consumers |

> Importing `config` has filesystem side effects — that is why `config` is imported first
> everywhere (`main.py:28-35`, tests, server).

### 2.2 Landing site & boulder detection (`:51-54`)

| Constant | Default | Meaning | Consumers |
| :--- | :--- | :--- | :--- |
| `LANDING_ELLIPSE_RADIUS_M` | 100.0 | minimum clearance for a candidate | `ml_recommender.py:115`, API key `landing_ellipse_radius_m` |
| `LANDING_CLEARANCE_BUFFER_M` | 40.0 | **intended** standoff from hazards | ⚠️ **never applied** in scoring (Issue I-05); only echoed in JSON/UI |
| `TOP_LANDING_SITES_COUNT` | 3 | sites returned (Alpha/Beta/Gamma) | `ml_recommender.py:230` |
| `BOULDER_RESIDUAL_THRESHOLD_STD` | 2.2 | σ-z cut for boulder probability | `ml_recommender.py:57` |

### 2.3 Lunar CRS (`:57-62`)

```python
LUNAR_SOUTH_POLE_PROJ4 = "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs"
```
This is the **only** CRS definition in the codebase (`config.py:62`); everything else derives from
it or from input rasters. Guard: `io_utils.inspect_raster` rejects 5 Earth EPSG signatures
(`io_utils.py:199-206`); `tests/test_smoke.py:39-41` asserts `EPSG:4326` is absent, `+proj=stere`
present, `+R=1737400` present.

### 2.4 Raster/DEM constants (`:64-76`)

| Constant | Value | Used for |
| :--- | :--- | :--- |
| `DEFAULT_NODATA_VALUE` | −9999.0 | default `nodata` in `write_geotiff`, invalid-pixel tests |
| `SYNTHETIC_DEM_SHAPE` | (200, 200) | synthetic generator |
| `SYNTHETIC_PIXEL_SIZE_M` | 20.0 | synthetic grid — ⚠️ **also misused as the area scale in `/api/recalculate`** (Issue I-02) |
| `SYNTHETIC_CRATER_RADIUS_M` | 1200.0 | generator geometry |
| `SYNTHETIC_CRATER_DEPTH_M` | 350.0 | idem |
| `SYNTHETIC_CRATER_RIM_HEIGHT_M` | 80.0 | idem |
| `SYNTHETIC_REGIONAL_ELEVATION_M` | −2500.0 | idem |
| `SYNTHETIC_LABEL` | `"SYNTHETIC DEMO"` | provenance string in tags/CSV/console |

### 2.5 Hazard thresholds (`:78-139`) — the numbers everyone tunes

| Group | Constants (defaults) | Semantics |
| :--- | :--- | :--- |
| Slope (°) | `SLOPE_SAFE_MAX=5.0`, `SLOPE_CAUTION_MAX=10.0`, `SLOPE_UNSAFE_MIN=10.0`, `SLOPE_HARD_UNSAFE_MIN=15.0`, `SLOPE_NORM_MAX=15.0` | safe `<5`; hard override `≥15`; `*_NORM_MAX` = normalisation cap for H |
| Roughness (m) | `ROUGHNESS_SAFE_MAX=1.5`, `ROUGHNESS_CAUTION_MAX=3.0`, `ROUGHNESS_UNSAFE_MIN=3.0`, `ROUGHNESS_HARD_UNSAFE_MIN=5.0`, `ROUGHNESS_NORM_MAX=5.0` | same pattern |
| Window | `TERRAIN_WINDOW_SIZE=3` | 3×3 roughness/TRI |
| Weights | `WEIGHT_SLOPE=0.50`, `WEIGHT_ROUGHNESS=0.30`, `WEIGHT_SHADOW=0.20` | must sum to 1.0 (audit rule checks the score, not the sum) |
| Score | `SCORE_SAFE_MAX=0.25`, `SCORE_CAUTION_MAX=0.60`, `SCORE_UNSAFE_MIN=0.60` | H < 0.25 → candidate safe; H ≥ 0.60 → unsafe |
| Classes | `CLASS_NODATA=0, CLASS_SAFE=1, CLASS_CAUTION=2, CLASS_UNSAFE=3, CLASS_SHADOWED_UNKNOWN=4` + `CLASS_NAMES`, `CLASS_COLORS` dicts | id contract shared with the UI |
| PSR | `PSR_BINARIZE_THRESHOLD=0.5`, `PSR_MIN_SIZE_PIXELS=9`, `PSR_PROVENANCE_PUBLISHED/SYNTHETIC` | binarisation & despeckle |

> ⚠️ `SLOPE_CAUTION_MAX` and `SLOPE_UNSAFE_MIN` are duplicates (both 10.0), likewise the roughness
> pair. The classifier uses only `*_HARD_UNSAFE_MIN`, `*_SAFE_MAX` and the score; the API exposes
> both groups under different names (`slope_caution_max` vs `slope_hard_unsafe`).

### 2.6 Plotting (`:141-152`)

| Constant | Value |
| :--- | :--- |
| `PLOT_DPI` | 300 |
| `FIGURE_STYLE` | `"dark_background"` |
| backend | `matplotlib.use("Agg")` forced at import (`:148-151`) — headless-safe, also means **plt.show() never works** |

---

## 3. CLI configuration (`main.py`)

| Flag | Type | Default | Effect |
| :--- | :--- | :--- | :--- |
| `--dem PATH` | str | `None` | overrides `REAL_DEM_PATH` for this run |
| `--psr PATH` | str | `None` | overrides `REAL_PSR_PATH` for this run |
| `--force-synthetic` | store_true | off | ignore real data, use `data/synthetic_*.tif` |
| `--fail-on-mismatch` | store_true | off | raise instead of reprojecting a misaligned PSR |
| `--quiet` | store_true | off | `verbose=False` through all phases |

There are **no** flags for thresholds, output directory, DPI, top-k, or random seed.
Note `ml_recommender.py` has its own separate `argparse` (`:302-300` area, `--dem/--psr/--out`)
used only when run directly.

---

## 4. HTTP configuration (POST bodies)

All keys optional; missing keys fall back to current `config` values.

| JSON key | `config` attribute | Endpoint(s) |
| :--- | :--- | :--- |
| `slope_safe_max` | `SLOPE_SAFE_MAX` | `recalculate`, `run-pipeline` |
| `slope_caution_max` | `SLOPE_CAUTION_MAX` | idem |
| `slope_hard_unsafe` | `SLOPE_HARD_UNSAFE_MIN` | idem |
| `rough_safe_max` | `ROUGHNESS_SAFE_MAX` | idem |
| `rough_caution_max` | `ROUGHNESS_CAUTION_MAX` | idem |
| `rough_hard_unsafe` | `ROUGHNESS_HARD_UNSAFE_MIN` | idem |
| `weight_slope` | `WEIGHT_SLOPE` | idem |
| `weight_roughness` | `WEIGHT_ROUGHNESS` | idem |
| `weight_shadow` | `WEIGHT_SHADOW` | idem |
| `landing_ellipse_radius_m` | `LANDING_ELLIPSE_RADIUS_M` | idem |
| `clearance_buffer_m` | `LANDING_CLEARANCE_BUFFER_M` | idem (⚠️ value only echoed, never applied — I-05) |
| `force_synthetic` | — (becomes `--force-synthetic`) | `run-pipeline` only |
| `type`, `filename` | — | `validate-geotiff` |

Not settable at runtime: pixel size, class ids/colours, PSR thresholds, top-k, DPI, paths, CRS.

---

## 5. Ports, addresses, timeouts

| Setting | Value | Where to change |
| :--- | :--- | :--- |
| HTTP port | **8050**, fallback **8080** | `web_server.py:835, 843` |
| Bind address | `""` (all interfaces) | `web_server.py:840` — ⚠️ LAN-exposed (Issue I-13) |
| Health poll | 2 500 ms | `web/app.js` `startStatusHeartbeat` (≈210) |
| Status poll | 5 000 ms | idem |
| Log poll | 1 500 ms (while running) | `app.js` log pane |
| Slider debounce | 250 ms | `app.js` `onParamChange` |
| NASA download timeout | 30 s | `web_server.py:635` |
| Static caching | `no-cache, no-store, must-revalidate` | `web_server.py:185` |

---

## 6. External/network dependencies at runtime

| Dependency | Required? | Behaviour offline |
| :--- | :--- | :--- |
| `pds-geosciences.wustl.edu` JP2 | optional | `/api/download-lola` fails gracefully → `DOWNLOAD_STATUS.success=false` |
| `cdnjs` KaTeX 0.16.8 | optional | math renders as raw LaTeX source (`web/index.html:16`) |
| Google Fonts | optional | falls back to system font stack (`styles.css`) |
| CDN three.js | **never** — vendored file loads first | `web/index.html:20-28` |
| Localhost:8050 | required | console unusable |

No API keys, tokens, licence keys, or `.env` files exist (verified).

---

## 7. Configuration duplication map (the project's #1 maintenance risk)

| Value | Locations (verified) |
| :--- | :--- |
| Slope 5/10/15, roughness 1.5/3/5 | `config.py:82-93`; API defaults (`web_server.py:422-428`); UI fallbacks + slider attrs (`web/index.html`, `app.js`); rule description strings (`web_server.py:573-581`); `validate.py` docstrings; `mission_report.py:167-177`; `README.md` tables; `PROJECT_SPECIFICATION.md` |
| H = 0.50/0.30/0.20 | `config.py:99-101`; `hazard.py` docstring + `web_server.py:513` mirror logic; UI text; specs |
| Class 0–4 ids/names/colours | `config.py:109-131`; `web/app.js` `PALETTE_HAZARD` + name arrays; `mapping.py` legend; `mission_report.py` |
| 20 m/px | `config.py:69`; `web_server.py:470` (bug I-02); `ml_recommender` default (bug I-12); UI assumption |
| 40 m standoff | `config.py:52`; UI dashed ring; docs — but **not** in the algorithm (bug I-05) |

**Rule for contributors:** change `config.py` first, then grep the repo for the old literal
(`grep -rn "15.0"`-style) before declaring a change done. Doc 20 task **T-06** proposes a
`get_defaults()` + config-echo endpoint to remove the frontend copies.

---

## 8. What is *not* configurable (by design or omission)

- Output directory (fixed `outputs/`), file names.
- Any class count/colour beyond editing source.
- Logging level/format (prints only; no `logging` module use).
- Concurrency (thread-per-request is fixed).
- Dataset tile size — real LOLA path is hard-coded to a 250×250 centre crop
  (`prepare_lola_dataset.py:51-56`).
- Shadow (D) term input: the pipeline never supplies `shadow_fraction`
  (`main.py:137` → always 0, Issue I-07).
