# `ml_recommender.py` — Landing-Site Autonomy & Boulder Detection (303 lines)

> Role: the **ALSS** — ranks the Top-3 landing ellipses inside safe terrain, and produces a
  boulder/crater micro-hazard probability raster. Despite the module name, everything here is
  **deterministic signal processing + multi-criteria scoring** — no trained model exists (I-09).

**Status:** 🟠 works, two correctness issues · **Tested by:** `tests/test_ml_recommender.py` (3) ·
**Issues:** **I-05** (40 m buffer unused), **I-12b** (pixel size default 20 m), I-09 (labelling).

---

## 1. Boulder micro-hazard (`detect_boulder_micro_hazards`, `:18-81`)

```
1. fill NoData with mean of valid pixels
2. macro  = gaussian_filter(dem, sigma=2)            # smoothed trend
3. micro  = |dem - macro|                             # high-pass residual
4. z      = (micro - mean) / std over valid pixels
5. prob   = sigmoid(1.8 * (z - 2.2))                 # 2.2 = config.BOULDER_RESIDUAL_THRESHOLD_STD
6. peaks  = local maxima of z in 5×5 window where prob > 0.5 → boulder points (cap 150)
```
Returns `(probability_float32, points_list)`; points carry
`x, y, z, dx, dy, sigma, dz, residual_z, probability`.

Export: `outputs/boulder_hazard.tif` (tags `HAZARD_TYPE`, `MODEL=Lunar High-Pass Residual AI`,
nodata −9999) — see `run_mission_autonomy:259-270`.

⚠️ Labeling: tag + README say "AI"; the maths is a bandpass + logistic squash (I-09/T-12a).

## 2. Landing-site ranking (`recommend_landing_sites`, `:84-215`)

**Signature:** `(hazard_classes, dem_data, slope_data, roughness_data, psr_mask, transform,
ellipse_radius_m=None, pixel_size_m=None, top_k=None)` → `{"top_sites":[…], …}`

| Step | Lines | Detail |
| :-: | :-- | :--- |
| 1 | 96-101 | `safe_mask = (hazard == CLASS_SAFE)`; invalid pixels excluded |
| 2 | 103-107 | `dist = distance_transform_edt(safe_mask)` → pixels → metres via `pixel_size_m` (**default 20.0 — I-12b**) |
| 3 | 115-121 | candidates: `dist_m ≥ ellipse_radius_m` (100); if none, relax to `0.85 × max` and warn |
| 4 | 133-141 | per-candidate stats: mean/max slope, mean roughness, distance to PSR, elevation |
| 5 | 140-148 | `fitness = .35·clearance_norm + .30·flatness + .20·smoothness + .15·science`<br>`science` = Gaussian preference for ~250 m from PSR |
| 6 | 154-157 | `suitability_pct = fitness × 100` |
| 7 | 163-207 | greedy arg-max: pick best, zero all pixels within `2.5 × ellipse_radius`, repeat `top_k` |
| 8 | 170-200 | each site: world coords via `rasterio.transform.xy(..., offset="center")`, mission role assignment (`Primary/Relay/Survey`) |
| 9 | 214-216 | status `SUCCESS` / `SUCCESS_NO_SITE` when zero candidates |

⚠️ **`LANDING_CLEARANCE_BUFFER_M` (40 m) is never applied** (I-05) — the constraint is
`dist ≥ ellipse_radius` only. The 40 m ring the UI draws is decorative.

## 3. Orchestration (`run_mission_autonomy`, `:218-300`)

- **Re-opens files from disk** (`:238-253`): DEM (data/), PSR/slope/roughness/hazard (outputs/) —
  does not reuse `main.py`'s in-memory arrays. Requires phases 2-4 to have written files first.
- Runs boulder detection → recommender → writes `landing_sites.json` + `boulder_hazard.tif`.
- JSON top-level: `status, top_sites[3], total_sites_identified, target_ellipse_radius_m,
  evaluation_crs (= config.LUNAR_SOUTH_POLE_PROJ4), boulder_obstacles_detected,
  boulder_points_sample[≤30]` (slice `boulder_obstacles[:30]`, `:282`).
- ⚠️ `pixel_size_m=config.SYNTHETIC_PIXEL_SIZE_M` hard-coded at `:278` → real-LOLA pixel size
  ignored (I-12b); sites' pixel-index maths assume 20 m.
- Standalone CLI: `python ml_recommender.py [--dem --psr --out]` (`:302+`).

## 4. Site record schema (consumers: UI cards, PDF, bundle)

Emitted at `:180-202` — `rank, name ("Site Alpha (Primary)"), designation ("Alpha"), row, col,
easting_m, northing_m, elevation_m, suitability_pct, clearance_radius_m (MEASURED distance to
nearest risk, `:177,190` — not the configured radius), ellipse_semi_major_m (radius×1.1),
ellipse_semi_minor_m (radius×0.9), ellipse_radius_m, mean_slope_deg, max_slope_deg,
mean_roughness_m, dist_to_psr_m, status ("APPROVED FOR DESCENT", constant), mission_role
(rank 1/2/3).`
(→ keep `api_documentation/LANDING_SITES_SCHEMA.md` in sync on any change)

## 5. Test coverage

| Test | Guards |
| :--- | :--- |
| `test_boulder_micro_hazard_detection` | known bumps → probability > 0.5 at peaks, ~0 elsewhere |
| `test_landing_site_recommender` | safe island → returns sites with expected fields |
| `test_mission_autonomy_artifacts` | JSON + GeoTIFF written, schema present |

**Gaps:** no test for `pixel_size_m` scaling (would catch I-12b); no test for buffer enforcement
(could catch I-05); no `SUCCESS_NO_SITE` path test; no suppression-radius test (two nearby islands).

## 6. Fix guidance

```python
# I-05 (T-12b): enforce the standoff
min_clear = ellipse_radius + config.LANDING_CLEARANCE_BUFFER_M
candidates = dist_m >= min_clear
# I-12b (T-02): caller passes real size
px = abs(RASTER_CACHE["transform"].a)
ml_recommender.recommend_landing_sites(..., pixel_size_m=px)
```
Both fixes need a regression test (see doc 20 T-02/T-12b).

## 7. Naming / honesty (I-09)

Options: (a) rename module/description to `ls_recommender`/`deterministic scorer` and fix
README/pitch/spec wording; or (b) actually train a small model (T-12c). Either way the GeoTIFF tag
`MODEL=Lunar High-Pass Residual AI` should be updated or removed.
