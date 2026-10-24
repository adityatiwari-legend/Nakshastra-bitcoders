# `config.py` — Central Configuration (152 lines)

> Role: **single source of truth** for every threshold, path, CRS string, class definition and plot
> setting. Imported by all 14 backend modules, the web server, the tooling scripts and every test.

**Status:** ✅ complete · **Tested by:** `tests/test_smoke.py::test_config_constants` ·
**Issues:** feeds I-02, I-04, I-05, I-11, M-08 (duplication elsewhere).

---

## 1. Contract

- Pure constants + two import side effects: `DATA_DIR.mkdir()` and `OUTPUT_DIR.mkdir()`
  (`config.py:18-19`). **Importing this module touches the filesystem.**
- No functions, no classes, no environment-variable reads (repo-wide `getenv` search: none).
- Mutable at runtime by `web_server.py` (see doc 12 §1) — the only write path besides editing the file.

## 2. Sections

| Lines | Section | Key contents |
| :--: | :--- | :--- |
| 12-19 | Base paths | `BASE_DIR`, `DATA_DIR`, `OUTPUT_DIR`, `TESTS_DIR` + dir creation |
| 22-27 | Input paths | `SYNTHETIC_DEM_PATH`, `SYNTHETIC_PSR_PATH`, `REAL_DEM_PATH`, `REAL_PSR_PATH` — **existence of the REAL pair flips the whole app to real mode** (`main.py:66-73`, `web_server.py:266`) |
| 30-49 | Output paths | 15 `OUTPUT_*` constants — one per artifact; producers *and* consumers use these names |
| 51-54 | Landing/boulder | `LANDING_ELLIPSE_RADIUS_M=100`, `LANDING_CLEARANCE_BUFFER_M=40` ⚠ unused in algo (I-05), `TOP_LANDING_SITES_COUNT=3`, `BOULDER_RESIDUAL_THRESHOLD_STD=2.2` |
| 62 | CRS | `LUNAR_SOUTH_POLE_PROJ4` — the only CRS definition in the repo |
| 67-76 | Raster/synthetic | `DEFAULT_NODATA_VALUE=-9999`, shape `(200,200)`, `SYNTHETIC_PIXEL_SIZE_M=20` ⚠ misused by web (I-02), crater geometry, `SYNTHETIC_LABEL` |
| 82-93 | Slope/roughness | safe 5/1.5 · caution 10/3 · hard 15/5 · norm caps 15/5 |
| 96 | Window | `TERRAIN_WINDOW_SIZE=3` |
| 99-106 | Score weights & limits | `.50/.30/.20`; `SCORE_SAFE_MAX=0.25`, `SCORE_UNSAFE_MIN=0.60` |
| 109-131 | Classes | `CLASS_*` ids 0-4, `CLASS_NAMES`, `CLASS_COLORS` dicts |
| 134-139 | PSR | `PSR_BINARIZE_THRESHOLD=0.5`, `PSR_MIN_SIZE_PIXELS=9`, provenance strings |
| 144-151 | Plot | `PLOT_DPI=300`, dark style, `matplotlib.use("Agg")` forced |

## 3. Design notes & landmines

1. **Duplicated thresholds:** `SLOPE_CAUTION_MAX == SLOPE_UNSAFE_MIN` (both 10) and same for
   roughness — harmless but confusing; the classifier uses only `*_SAFE_MAX`, `*_HARD_UNSAFE_MIN`
   and the score limits.
2. **`WEIGHT_SHADOW=0.20` is currently inert** because the pipeline never passes
   `shadow_fraction` (I-07) — the weight exists so the D term *can* be enabled.
3. **`LANDING_CLEARANCE_BUFFER_M` is exported but never read by the recommender** (I-05); only
   `mission_report`/UI echo it.
4. **Runtime mutation** by the web server turns these "constants" into global state (I-11); any new
   module that reads a threshold *after* a request can observe a different value than at import.
5. **No version/defaults snapshot** — T-06 proposes `DEFAULTS = {…}` captured at import.
6. `CLASS_COLORS` values are consumed by `mapping.py` **and** duplicated as hex literals in
   `web/app.js` (`PALETTE_HAZARD`) — keep them in sync manually (M-08).

## 4. How other modules use it

```python
import config                                   # module attribute access, never "from config import X"
arr = io_utils.read_geotiff(config.SYNTHETIC_DEM_PATH)
if hazard == config.CLASS_SAFE: ...
```
⚠️ Note `web_server.py` uses `from web_server`-style global access *to write*:
`config.SLOPE_SAFE_MAX = float(...)` (`:438-446`) — do not copy that pattern elsewhere.

## 5. Change checklist for this file

1. Grep the old literal repo-wide (doc 12 §7 lists every duplication site).
2. Update `web/app.js` fallbacks/labels and `web/index.html` slider attributes.
3. Update `web_server.py` rule descriptions (`:573-581`) and `mission_report.py` text (`:167-177`).
4. Update README/`PROJECT_SPECIFICATION.md` tables **only if** claims remain true (doc 19 §E).
5. Run `pytest tests/test_smoke.py tests/test_hazard.py -v`.
