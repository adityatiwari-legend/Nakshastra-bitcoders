# `psr.py` — Permanent Shadow Region Processing (269 lines)

> Role: turn a raw PSR mask into a **clean binary mask + georeferenced vectors + area metrics**,
  and stamp honest provenance onto the products.

**Status:** ✅ · **Tested by:** `tests/test_psr.py` (5 tests, incl. exact area arithmetic) ·
**Issues:** none in-module; provenance wording ties to I-08 (input quality).

---

## 1. Pipeline (`process_and_export_psr`, `psr.py:174-269`)

```
raw PSR + dem_meta
 1. NoData mask from the DEM          (:192-200)  — PSR over invalid elevation is discarded
 2. binarize_psr                      (:30-58)    — bool | float>0.5 | int>0 ; nodata→0
 3. clean_psr_mask                    (:61-91)    — 8-connected labeling, drop components < 9 px
 4. calculate_psr_area                (:94-112)   — count × |px_x·px_y|
 5. vectorize_psr_to_polygons         (:115-171)  — rasterio.features.shapes(connectivity=8)
 6. write GeoTIFF + GeoJSON + Shapefile + zip
```

Inputs: `binary_psr` array, `dem_meta` (transform/crs/pixel sizes), `dem_nodata_mask`, output paths.

## 2. Key functions

| Function | Line | Contract | Edge cases handled |
| :--- | :-: | :--- | :--- |
| `binarize_psr(psr_array, threshold=0.5, nodata_mask=None)` | 30 | float/int/bool → uint8 {0,1} | float uses `> threshold`; int uses `>0`; nodata forced 0; NaN → 0 |
| `clean_psr_mask(mask, min_size=9)` | 61 | connected-component despeckle | `scipy.ndimage.label` with 3×3 structure (8-connectivity); sizes via `np.bincount(labels)`; empty mask returns as-is |
| `calculate_psr_area(mask, px_x, px_y)` | 94 | exact area dict `pixel_count, area_m2, area_km2` | works for all-False mask (zeros) |
| `vectorize_psr_to_polygons(binary_psr, transform, crs, min_size, provenance)` | 115 | GeoDataFrame | `buffer(0)` repair for invalid rings; columns `poly_id, feature, area_m2, area_km2, perim_m, provenance`; returns **empty** GDF cleanly if no shapes |
| `process_and_export_psr(...)` | 174 | orchestrates 1-6, returns dict of metrics | `is_synthetic` selects provenance string (`:215`); warnings when 0 polygons |

## 3. Provenance strings (honesty-critical)

| Dataset | Tag value | Source |
| :--- | :--- | :--- |
| synthetic | `SYNTHETIC DEMO PSR Mask` | `config.PSR_PROVENANCE_SYNTHETIC` |
| real | `Published / LOLA-derived PSR Mask (Reference)` | `config.PSR_PROVENANCE_PUBLISHED` |

Written to GeoTIFF tag `PSR_PROVENANCE` + each vector feature's `provenance` property + console.
⚠️ With the current real mask being a depth heuristic (I-08), "Published / …" is the strongest
wording in the codebase — it is *not* a claim of independently published PSR science, but it reads
close. T-23 (real reference atlas) or a reword to "LOLA-derived proxy" would remove ambiguity.

GeoTIFF tags actually written (`:219-225`): `PROJECT, DATA_TYPE, PSR_PROVENANCE, PSR_AREA_KM2,
PSR_PIXELS` with `nodata=None`.

## 4. Testing coverage

| Test | Guards |
| :--- | :--- |
| `test_binarize_psr_and_nodata_exclusion` | threshold semantics + nodata |
| `test_clean_psr_mask_removes_tiny_components` | `min_size=9` boundary |
| `test_calculate_psr_area_exactness` | arithmetic is exact, not approximate |
| `test_vectorize_psr_to_polygons` | schema + geometry validity |
| `test_process_and_export_psr_end_to_end` | all file outputs exist with tags |

**Not covered:** NaN inputs in `binarize_psr`; reprojection-fed masks; `min_size=0`.

## 5. Downstream dependencies

- `hazard.py` receives the cleaned mask (rule 8/PSR class assignment).
- `mapping.py` panel C draws the GeoDataFrame.
- `validate.py` rule 4/8 audit it; `compute_psr_metrics` compares it (see I-01).
- `ml_recommender.py` uses it for the science term + clearance.
- `export_web_data.py` embeds both the mask and the GeoJSON.

Changing any column name or tag breaks `web_data.json`, the map legend, the report and the API —
update docs 10 §3.2 + `DATA_BUNDLE_SCHEMA.md` together.

## 6. Gotchas

1. **`nodata=None` on output** — downstream code must not assume `-9999`.
2. **Vector CRS is inherited, not validated** — if someone feeds an Earth raster *past*
   `inspect_raster`, polygons get an Earth CRS silently (the guard lives one layer up).
3. **Area is planar** (`|px_x·px_y|`) — correct for polar-stereographic metres, ignores any
   projection distortion at 80-90°S (negligible at this scale, but say "grid area" not "true area"
   in papers).
4. Labels use 8-connectivity while `TERRAIN_WINDOW_SIZE` windows are 4/8-neighbour agnostic —
   mismatch here can split a diagonal shadow line at the 9-px filter.
