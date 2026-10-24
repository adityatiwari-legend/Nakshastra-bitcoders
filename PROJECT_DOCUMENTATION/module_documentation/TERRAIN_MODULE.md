# `terrain.py` — Terrain Attribute Computation (425 lines)

> Role: derives slope, aspect, roughness (std) and TRI from the DEM, exports them as GeoTIFFs, and
  renders the terrain histogram figure. Pure numpy/scipy — no file handles beyond `write_geotiff`.

**Status:** ✅ · **Tested by:** `tests/test_terrain.py` (4, incl. an exactness test on a planar ramp) ·
**Issues:** none in-module (known quirks below are by design).

---

## 1. Functions

| Function | Line | Algorithm | Output |
| :--- | :-: | :--- | :--- |
| `calculate_slope_and_aspect(dem, transform, nodata)` | 21 | **Horn (1981)** 3×3 kernels | `(slope_deg, aspect_deg, valid_mask)` |
| `calculate_roughness_std(dem, transform, nodata, window=3)` | 90 | rolling std via three `uniform_filter` passes | `(roughness_std, valid_mask)` |
| `calculate_roughness_tri(dem, transform, nodata)` | 139 | Riley TRI: `√(Σ(neighbour−centre)² / count)` | `(tri, valid_mask)` |
| `generate_terrain_histograms(...)` | 199 | matplotlib 2×2 figure, dark theme, 300 DPI | `terrain_histograms.png` |
| `process_terrain_pipeline(dem, dem_meta, output_paths, verbose)` | 293 | runs all three + exports + stats | dict of arrays + metrics |

## 2. Algorithm details worth knowing

**Slope/aspect (`:21-87`)**
1. valid mask = `dem != nodata & ~isnan`.
2. **NoData cells are filled with the global valid median** before convolution (`:46-49`) so the
   kernel never sees `NaN`/`-9999` spikes. → side effect: bands of "median terrain" appear within
   1 px of NoData edges (documented quirk, doc 15 §4).
3. Horn kernels (`:55-64`) convolved with `mode="nearest"`.
4. `slope = degrees(arctan(√(gx²+gy²)))`; pixel-size normalisation comes from the transform.
5. `aspect = (90 − degrees(atan2(dz/dy, −dz/dx))) % 360`; flat (< 0.01°) forced to `0`
   (avoids random compass directions on crater floors).
6. NoData re-applied to both outputs (`:84-85`); output dtype `float32`, nodata `-9999`.

**Roughness std (`:90-136`)** — an efficient identity:
`var = E[z²] − (E[z])²` with three `uniform_filter` passes giving count / Σz / Σz² per window;
variance clipped at 0 (float cancellation), needs **≥3 valid samples**, else NoData.
Much faster than per-window `np.std`.

**TRI (`:139-196`)** — 8 explicit shifted arrays; `count` = number of valid neighbours, so edge
pixels average over fewer neighbours (no dilation bias).

## 3. Exported tags (verified on disk)

`terrain.py:342-378` → `PROJECT=LunaSafe, BODY=MOON, DATA_TYPE, METRIC=SLOPE|ASPECT|ROUGHNESS_STD|ROUGHNESS_TRI,
UNITS=DEGREES|DEGREES_FROM_NORTH|METERS, WINDOW_SIZE=3 (std only)`, nodata `-9999`.

## 4. Metrics returned by the pipeline (`:293+`)

```
slope, aspect, roughness_std, roughness_tri, valid_mask,
slope_stats {min, max, mean, median, p95}, roughness_stats {...},
histogram_path
```
Consumed by `hazard` (score), `mapping` (panel B + hillshade), `validate` (rules 1,2,5,6),
`ml_recommender` (fitness), `export_web_data` (UI layers).

## 5. Test coverage & gaps

Covered: flat surface → ~0 slope & aspect 0; **planar ramp exactness** (catches Horn sign/unit
bugs); NoData preservation; end-to-end exports.
Gaps: `aspect` wrap-around at 0°/360°; all-NoData input; non-square pixels (transform `e ≠ a`);
roughness std on single-valid-sample windows.

## 6. Design notes

1. **Median fill instead of zero-padding** — avoids artificial cliffs at NoData borders, at the cost
   of the 1-px halo. Alternative (masked convolution) would need `np.ma` plumbing through scipy —
   not worth it at this scale.
2. **Aspect convention** = azimuth of *downslope* direction, degrees clockwise from north, which is
   what `mapping.compute_hillshade` expects (`mapping.py:30-56`). Changing either side alone breaks
   the hillshade lighting.
3. **Units are metres/degrees** because the CRS is metric (lunar stereographic) — do not use these
   functions on lat/lon grids without first projecting.
4. Everything is `float32` — sufficient for these metrics and halves memory vs float64.

## 7. Change checklist

- Touching kernels → run `test_planar_ramp_slope_exactness` first, then regenerate `outputs/` and
  compare the 4-panel map (visual regression by eye).
- Changing the NoData fill → update the histogram PNG expectations and this doc §2.
- Adding a metric (e.g. curvature): follow the pattern
  `compute → valid_mask fixup → write_geotiff(tags=…) → summary print → test → update doc 06/08`.
