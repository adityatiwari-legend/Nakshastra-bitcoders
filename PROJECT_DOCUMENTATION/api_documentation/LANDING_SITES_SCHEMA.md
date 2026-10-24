# Landing Sites Schema — `outputs/landing_sites.json`

**Producer:** `ml_recommender.run_mission_autonomy()` (`ml_recommender.py:218-300`, write at `:284-286`).
**Consumers:** UI ALSS cards (`app.js:3588`), mission report (⚠ uses hard-coded names, I-14),
`web_data.json → landing_sites` (`export_web_data.py:88`).
**Companions:** [`../10_DATABASE_AND_DATA_MODEL.md`](../10_DATABASE_AND_DATA_MODEL.md) §4.1,
[`../module_documentation/ML_RECOMMENDER_MODULE.md`](../module_documentation/ML_RECOMMENDER_MODULE.md).

> All field semantics below were verified against `ml_recommender.py:180-202` and the committed
> `outputs/landing_sites.json` on 2026-10-17.

---

## 1. Top level

| Key | Type | Semantics |
| :--- | :--- | :--- |
| `status` | `"SUCCESS"` \| `"SUCCESS_NO_SITE"` | no-candidate path at `:214-216` |
| `top_sites` | site[ ] ≤ `TOP_LANDING_SITES_COUNT` (3) | rank-ordered candidates |
| `total_sites_identified` | int | count of accepted candidates |
| `target_ellipse_radius_m` | float | `config.LANDING_ELLIPSE_RADIUS_M` (100.0) |
| `evaluation_crs` | string | `config.LUNAR_SOUTH_POLE_PROJ4` (PROJ.4, not WKT) |
| `boulder_obstacles_detected` | int | `len(boulder_obstacles)` (`:281`) — full list capped at **150** (`:79`) |
| `boulder_points_sample` | object[ ] ≤ **30** | `boulder_obstacles[:30]` (`:282`) |

## 2. Site object (emitted `:180-202`)

| Field | Type | Derivation (code) |
| :--- | :--- | :--- |
| `rank` | int 1-based | loop index (`:181`) |
| `name` | string | `"Site Alpha (Primary)"` etc. (`:182`) |
| `designation` | `"Alpha"\|"Beta"\|"Gamma"\|"Site-N"` | `:183` |
| `row`, `col` | int | 0-based raster indices of the site centre |
| `easting_m`, `northing_m` | float, m | `rasterio.transform.xy(..., offset='center')` (`:167`) |
| `elevation_m` | float | DEM value at the centre (`:178`) |
| `suitability_pct` | float 0-100 | fitness × 100 (`:189`); fitness = `0.35·clearance + 0.30·slope + 0.20·roughness + 0.15·science` (`:143-148`), science = Gaussian bell centred on 250 m from PSR (`:140`) |
| `clearance_radius_m` | float, m | **measured** distance-to-nearest-risk at the centre (`dist_m[r,c]`, `:177,190`) — *not* a configured radius |
| `ellipse_semi_major_m` | float | `ellipse_radius_m × 1.1` (`:191`) |
| `ellipse_semi_minor_m` | float | `ellipse_radius_m × 0.9` (`:192`) |
| `ellipse_radius_m` | float | requested radius, 100.0 (`:193`) |
| `mean_slope_deg`, `max_slope_deg` | float | stats inside circular ellipse mask of `req_radius_px` (`:171-174`) |
| `mean_roughness_m` | float | same mask (`:175`) |
| `dist_to_psr_m` | float | distance-to-PSR field at the centre (`:176`) |
| `status` | `"APPROVED FOR DESCENT"` | **constant string** (`:198`) — not derived from any rule check |
| `mission_role` | rank 1/2/3 role | `:199-201` |

Verified sample (fresh run, synthetic DEM): `rank 1, suitability_pct 94.3, clearance_radius_m 240.0,
elevation_m -2846.86, dist_to_psr_m 240.0`.

## 3. Boulder sample object (emitted `:69-75`)

```jsonc
{"row": 4, "col": 64, "probability": 1.0, "estimated_diameter_m": 8.0, "severity": "High"}
```
- `probability` 0-1 (3 dp) from the micro-hazard map; `severity` = `High` if >0.8 else `Moderate`.
- `estimated_diameter_m` = clipped `micro_residual × 1.8` into `[1.0, 8.0]` (`:68`).

## 4. Known defects in this schema's semantics

| ID | What | Where |
| :-- | :--- | :--- |
| I-05 | 40 m clearance buffer never part of the constraint or the output (`min_clearance = ellipse_radius_m`) | `:115-116` |
| I-12b | `pixel_size_m=config.SYNTHETIC_PIXEL_SIZE_M` (20 m) hard-coded regardless of dataset | `:278` |
| — | `status` always `"APPROVED FOR DESCENT"` even when eligibility was relaxed (`:118`) | `:198` |
| I-14 | PDF renders *sample* names/roles, not these fields | `mission_report.py:51-77` |
| I-06 | stale bundles embed older site values (bundle: `suitability_pct 79.3`, fresh: `94.3`) | `web_data.json` |

## 5. Tests

`test_ml_recommender.py`: `test_landing_site_recommender` (field presence on a safe-island fixture),
`test_mission_autonomy_artifacts` (JSON written, schema present). **No test asserts field values**
against config → suggest asserting `clearance_radius_m` ≥ `landing_ellipse_radius_m` and
`ellipse_semi_major_m == radius×1.1`.

## 6. Versioning note

Any field added/renamed here must be updated in: `10_DATABASE_AND_DATA_MODEL.md` §4.1,
`module_documentation/ML_RECOMMENDER_MODULE.md` §4, `architecture/database_er_diagram.mmd`,
`feature_documentation/FEATURE_06_LANDING_SITES.md`, and the UI card renderer `app.js:3588`.
