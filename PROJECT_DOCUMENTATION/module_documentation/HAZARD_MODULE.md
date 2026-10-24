# `hazard.py` — Hazard Score & 5-Class Surface (263 lines)

> Role: **the heart of the product.** Defines the classification contract: composite score `H`,
  hard overrides, the 5-class raster, and the summary CSV. Everything else (map, audit, recommender,
  UI) consumes its output.

**Status:** ✅ · **Tested by:** `tests/test_hazard.py` (6 tests, one per rule family) ·
**Issues:** I-07 (shadow term 0 upstream); twin logic duplicated in `validate.py` and `web_server.py`.

---

## 1. The two-stage classification

### Stage 1 — score (`compute_hazard_score`, `:23-58`)

```
S = clip(slope / SLOPE_NORM_MAX(15), 0, 1)
R = clip(roughness / ROUGHNESS_NORM_MAX(5), 0, 1)
D = clip(shadow_fraction, 0, 1)                # ← always 0 in the current pipeline (I-07)
H = WEIGHT_SLOPE·S + WEIGHT_ROUGHNESS·R + WEIGHT_SHADOW·D   # .50 / .30 / .20
H[~valid] = 0
```
Returns `(H, valid_mask)`. With D=0, H ∈ [0, 0.8].

### Stage 2 — classes (`classify_hazard_surface`, `:61-134`)

Evaluation order (each step *overwrites* earlier classes — order is the semantics):

| # | Rule | Class | Line |
| :-: | :--- | :-: | :-- |
| 1 | build `valid_mask` (slope/rough ≠ −9999, not NaN) | — | 80-86 |
| 2 | start: everything = | 0 | 89 |
| 3 | score H (stage 1) | — | 93-96 |
| 4 | `hard = slope ≥ 15 | rough ≥ 5` | flag | 100-102 |
| 5 | `valid & (H ≥ 0.60 | hard)` | **3 Unsafe** | 105-106 |
| 6 | `psr==1 & not unsafe` | **4 Shadowed-Unknown** | 109-113 |
| 7 | remaining valid & non-PSR: `H<0.25 & slope<5 & rough<1.5` → **1 Safe** else **2 Caution** | 1/2 | 119-129 |
| 8 | `~valid` → | 0 | 132 |

**Why order matters:** step 5 before step 6 ⇒ a steep PSR wall is *Unsafe (3)*, while a flat PSR
floor is *Shadowed-Unknown (4)*. Swapping them breaks audit rule 8's spirit ("never Safe/Caution")
but changes the meaning of class 4. Swapping 6 and 7 would put PSR pixels at risk of class 1/2.

## 2. Summary table (`generate_hazard_summary_table`, `:137-182`)

- `class_id, class_name, pixel_count, area_m2, area_km2, pct_valid_terrain, pct_total_raster`
- areas = `count × |px_x · px_y|` — **uses the real pixel size** (unlike the web recalc, I-02)
- always 5 rows, last row class 0; written by `pandas.DataFrame.to_csv` (`:241`)

## 3. Pipeline wrapper (`process_hazard_pipeline`, `:185-263`)

validates inputs (shape/CRS/transform of slope, roughness, psr vs DEM meta) → classify →
export GeoTIFF (nodata=0, tags `PROJECT/BODY/DATA_TYPE/PRODUCT/CLASSES`, verified) →
export CSV → verbose console table → returns `(hazard_classes, score_h, metrics)`.

## 4. Where the same logic is duplicated (drift risk)

| Copy | Location | Divergence already observed |
| :--- | :--- | :--- |
| canonical | `hazard.py:61-134` | — |
| auditor re-implementation | `validate.py:103-137` | must be kept byte-equivalent in thresholds; uses config too |
| web sensitivity mirror | `web_server.py:504-530` | recomputes classes inline for 3 thresholds — uses `score_h` from the canonical call, so consistent today |
| client-side preview | `web/app.js` `previewReclassifyClient` | literals (M-08) |

Any threshold change must hit **all four** (doc 12 §7) or the UI preview/audit will disagree with
the raster. T-06 + T-01's key-parity test reduce this surface.

## 5. Test coverage

| Test | Rule pinned |
| :--- | :--- |
| `test_hazard_score_formula_and_normalization` | weights + clipping |
| `test_hard_overrides_trigger_class_3_unsafe` | step 4/5 |
| `test_shadowed_unknown_vs_unsafe_psr` | step 5-6 ordering |
| `test_safe_and_caution_classification` | step 7 |
| `test_nodata_is_never_treated_as_safe` | step 8 / rule 9 |
| `test_process_hazard_pipeline_end_to_end` | exports + 5 CSV rows |

Gaps: NaN-only inputs; `shadow_fraction` non-zero (I-07 means no test exercises D>0); class
colour/config rename.

## 6. Extension guidance

- **New class:** `config.CLASS_*` + name/colour dicts → insert into the order table (think hard
  about where relative to steps 5-7) → `validate.py` new rule → `mapping.py` legend +
  `BoundaryNorm` edges + `web/app.js` palette + `export_web_data` docs → tests → doc 03/10/23.
- **New term in H:** add weight to `config`, extend `compute_hazard_score` **and** the two mirrors,
  update `test_hazard_score_formula…` expectations and the formula strings in
  `web_server.py:573` area + UI text (`app.js:2909`).
- Never add I/O to this module — arrays in, arrays out (doc 22 §3).
