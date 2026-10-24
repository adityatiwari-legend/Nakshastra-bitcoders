# 10 — Database and Data Model

> **Headline fact:** LunaSafe has **no database**. Persistence is a set of files in `data/`
> (inputs) and `outputs/` (artifacts), plus two JSON "documents" that act as the application's
> record format. This document is the complete data model: schemas, encodings, invariants,
> lifecycles, and where each field is produced/consumed.

**Diagram:** [`architecture/database_er_diagram.mmd`](architecture/database_er_diagram.mmd)

---

## 1. Why there is no DB (and what is used instead)

| Typical DB concern | LunaSafe equivalent | Evidence |
| :--- | :--- | :--- |
| Tables | One CSV (5 rows) + fixed JSON documents | `hazard_summary.csv`, `landing_sites.json` |
| Rows/entities | PSR polygon features; landing site records | GeoJSON features; `top_sites[]` |
| Queries | Whole-file reads into numpy | `io_utils.read_geotiff` (`io_utils.py:154`) |
| Transactions | None — writes are last-writer-wins | `write_geotiff` (`:115`) |
| Schema migrations | None — fields are added by editing producer code | — |
| Concurrency control | None (only a log/status lock in the web server) | `web_server.py:47` |

**No SQL/ORM/NoSQL import exists anywhere** (verified by grep over the repo). The nearest thing to
a "connection" is `RASTER_CACHE`, a plain dict held in RAM by `web_server.py:48-56`.

---

## 2. Physical schema — input datasets (`data/`)

### 2.1 `synthetic_dem.tif` — reference/procedural DEM

| Attribute | Value | Verified by |
| :--- | :--- | :--- |
| Size on disk | 141 KB (2026-10-17) | filesystem |
| Grid | 200 × 200 | `config.SYNTHETIC_DEM_SHAPE` (`config.py:68`) |
| Pixel size | 20.0 m | `config.SYNTHETIC_PIXEL_SIZE_M` (`:69`) |
| CRS | lunar south-pole polar stereographic, sphere R = 1 737 400 | `config.LUNAR_SOUTH_POLE_PROJ4` (`config.py:62`) |
| NoData | −9999.0 | `config.DEFAULT_NODATA_VALUE` (`:67`) |
| Generation | `io_utils.generate_synthetic_lunar_crater()` (`io_utils.py:416-463`): crater radius 1 200 m, depth 350 m, rim +80 m, regional base −2 500 m, seeded noise + lineated ejecta | `config.py:70-73` |
| Tags | `PROJECT=LunaSafe`, `BODY=MOON`, `DATA_TYPE=SYNTHETIC DEMO`, `DESCRIPTION=Synthetic Lunar Crater and PSR for Pipeline Validation` (verified) | `io_utils.generate_synthetic_lunar_crater` → `write_geotiff(..., tags=...)` (`io_utils.py:446-460`) |

### 2.2 `synthetic_psr.tif`

uint8 {0,1}, 200×200, aligned with the synthetic DEM; produced by
`io_utils.generate_synthetic_lunar_crater` (`:465-500`) — a central shadow disc plus a permanently
shadowed crater-floor patch.

### 2.3 `lola_south_pole_dem.tif` (real dataset)

| Attribute | Value |
| :--- | :--- |
| Size | 246 KB |
| Grid / pixel | 250 × 250 @ 240.0 m/px (≈60 km × 60 km) |
| CRS | `Moon2000_spole` / `Moon_2000_IAU_IAG` (R = 1 737 400) — confirmed by rasterio |
| Producer | `prepare_lola_dataset.convert_real_lola_to_geotiff()` (`prepare_lola_dataset.py:19-104`): centre-crop 250×250 from `ldem_75s_240m.jp2` (3 812×3 812 int16), scale `DN × 0.5` → metres, unit tags written |
| Units | metres (tag `UNITS=metres`, `:90-93`) |

### 2.4 `lola_psr_mask.tif`

uint8 {0,1}, 250×250, same grid. **Definition:** `depth < −900 m`
(`prepare_lola_dataset.py:51-56`) — a *topographic-depression heuristic*, not a published PSR
atlas (Issue I-08). The `download-lola` handler's `provenance_note` (`web_server.py:727-731`)
describes exactly this limitation.

### 2.5 `ldem_75s_240m.jp2`

Raw NASA PDS artifact (10.5 MB, 3 812×3 812 int16, no CRS until converted). Re-fetchable from
`web_server.py:633`. Not read by any code path directly except `prepare_lola_dataset.py:23`.

---

## 3. Physical schema — derived rasters (`outputs/*.tif`)

All written by `io_utils.write_geotiff` (`io_utils.py:116-151`), which:
- builds a single-band `GTiff` profile with `compress="lzw"` (untiled), caller-supplied
  `nodata` (default `config.DEFAULT_NODATA_VALUE = -9999.0`, but every caller overrides it —
  see the column below), `crs` and `transform`;
- writes **only** the `tags` dict passed by the caller (`dst.update_tags(**tags)` at `:150-151`) —
  there is no automatic tag injection;
- always ends up with rasterio's `AREA_OR_POINT=Area`.

Tags below were read back from the committed files with `rasterio.open(...).tags()` on 2026-10-17.

| File | dtype | Value domain | Units | Producer | Actual tags (verified) | `nodata` written |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `psr_binary.tif` | uint8 | {0,1} | — | `psr.process_and_export_psr` (`psr.py:219-233`) | `PROJECT=LunaSafe`, `DATA_TYPE`, `PSR_PROVENANCE`, `PSR_AREA_KM2`, `PSR_PIXELS` | `None` |
| `slope_deg.tif` | float32 | 0…90 or −9999 | degrees | `terrain.calculate_slope_and_aspect` (`terrain.py:348`) | `PROJECT`, `BODY=MOON`, `DATA_TYPE`, `METRIC=SLOPE`, `UNITS=DEGREES` | −9999.0 |
| `aspect_deg.tif` | float32 | 0…360 or −9999 | degrees (N-clockwise, flat=0) | `terrain.py:358` | …`METRIC=ASPECT`, `UNITS=DEGREES_FROM_NORTH` | −9999.0 |
| `roughness_std_m.tif` | float32 | ≥0 or −9999 | metres | `terrain.calculate_roughness_std` (`terrain.py:368`) | …`METRIC=ROUGHNESS_STD`, `UNITS=METERS`, `WINDOW_SIZE=3` | −9999.0 |
| `roughness_tri_m.tif` | float32 | ≥0 or −9999 | metres | `terrain.calculate_roughness_tri` (`terrain.py:378`) | …`METRIC=ROUGHNESS_TRI`, `UNITS=METERS` | −9999.0 |
| `hazard_classes.tif` | uint8 | {0,1,2,3,4} | class id | `hazard.process_hazard_pipeline` (`hazard.py:216-230`) | `PROJECT`, `BODY=MOON`, `DATA_TYPE`, `PRODUCT=HAZARD_CLASSIFICATION`, `CLASSES=0=NoData,1=Safe,2=Caution,3=Unsafe,4=Shadowed-Unknown` | **0** (`CLASS_NODATA`) |
| `boulder_hazard.tif` | float32 | 0…1 | probability | `ml_recommender.run_mission_autonomy` (`ml_recommender.py:259-270`) | `HAZARD_TYPE=Boulder/Crater Micro-Hazard Probability`, `MODEL=Lunar High-Pass Residual AI` — **no `PROJECT`/`BODY`** | −9999.0 |

Input tags for comparison (also verified): `data/synthetic_*.tif` →
`PROJECT, BODY, DATA_TYPE=SYNTHETIC DEMO, DESCRIPTION`; `data/lola_*.tif` →
`PROJECT, BODY, DATA_TYPE=REAL NASA LRO LOLA, DESCRIPTION, MISSION=LRO, INSTRUMENT=LOLA`.

**Cross-raster invariants** (each enforced by a test, see doc 14):
`shape` equal · `crs` equal · `transform` equal · NoData = −9999 on float metric rasters ·
every class ∈ {0,1,2,3,4} · class 1 ⊂ PSR=0 (audit rule 4) · class 0 ⇔ NoData (audit rule 9).

### 3.1 `hazard_summary.csv` — the only "table"

Columns, fixed order (`hazard.py:15-18`):

```
class_id,class_name,pixel_count,area_m2,area_km2,pct_valid_terrain,pct_total_raster
1,Safe,...        5 rows, last row is class 0 (Unknown / NoData)
```

- Written by `hazard.generate_hazard_summary_table` → `hazard.py:239-241`.
- Areas = `pixel_count × |pixel_size_x × pixel_size_y|` (correct, unlike the web recalc — Issue I-02).
- Read back by `web_server.handle_api_status` (`:276-288`), `mission_report.py` (page-2 table),
  and the UI's KPI tiles. Lower-cased `class_name` becomes the JSON key.

### 3.2 Vector output — `psr_polygons.*`

| Field | Type | Source |
| :--- | :--- | :--- |
| `poly_id` | int | 1-based enumeration (`psr.py:152`) |
| `feature` | str | `"Permanently Shadowed Region"` |
| `area_m2`, `area_km2` | float | shapely `.area` |
| `perim_m` | float | shapely `.length` |
| `provenance` | str | from `config.PSR_PROVENANCE_*` |

Written as GeoJSON **and** shapefile (`.shp/.shx/.dbf/.prj/.cpg`), plus a zipped bundle. The `.prj`
contains an unnamed `PROJCS["unknown", SPHEROID[…,1737400,…]]` — lunar, but many GIS tools display
it as "unknown CRS". Encodings: GeoJSON `UTF-8`, shapefile `UTF-8` via `.cpg`.

---

## 4. Document schemas — the JSON records

### 4.1 `outputs/landing_sites.json` (written by `ml_recommender.run_mission_autonomy`, `:284-286`)

```jsonc
{
  "status": "SUCCESS",                  // or "SUCCESS_NO_SITE" (ML module :214-216)
  "top_sites": [
    {
      "rank": 1, "name": "Site Alpha (Primary)", "designation": "Alpha",
      "row": 114, "col": 103,           // raster indices (0-based)
      "easting_m": 70.0, "northing_m": -290.0,    // rasterio.transform.xy offset='center'
      "elevation_m": -2846.86,          // DEM value at (row, col)
      "suitability_pct": 94.3,          // fitness × 100 (0-100)
      "clearance_radius_m": 240.0,      // MEASURED distance-to-nearest-risk at the centre
                                        // (ml_recommender.py:177,190) — not the configured radius
      "ellipse_semi_major_m": 110.0,    // ellipse_radius_m × 1.1  (:191)
      "ellipse_semi_minor_m": 90.0,     // ellipse_radius_m × 0.9  (:192)
      "ellipse_radius_m": 100.0,        // requested radius        (:193)
      "mean_slope_deg": 1.24, "max_slope_deg": 3.2,   // stats inside ellipse mask (:171-175)
      "mean_roughness_m": 0.44,
      "dist_to_psr_m": 240.0,
      "status": "APPROVED FOR DESCENT",                 // constant (:198)
      "mission_role": "Primary Targeted Landing Zone"   // rank 1/2/3 (:199-201)
    }
    // … up to TOP_LANDING_SITES_COUNT (3)
  ],
  "total_sites_identified": 3,
  "target_ellipse_radius_m": 100.0,
  "evaluation_crs": config.LUNAR_SOUTH_POLE_PROJ4,
  "boulder_obstacles_detected": 150,
  "boulder_points_sample": [
    {"row": 4, "col": 64, "probability": 1.0, "estimated_diameter_m": 8.0, "severity": "High"}
    // slice [:30] of the full list (ml_recommender.py:282); full list capped at 150 (:79)
  ]
}
```
Field-by-field derivation: [`api_documentation/LANDING_SITES_SCHEMA.md`](api_documentation/LANDING_SITES_SCHEMA.md).
**No `clearance_buffer_m` (40 m) field appears — the standoff is never applied** (Issue I-05).

### 4.2 `outputs/web_data.json` (written by `export_web_data.export_data_bundle`, `export_web_data.py:11-108`)

```jsonc
{
  "width": 200, "height": 200,            // from the DEM actually embedded (nx, ny :34)
  "pixel_size_x": 20.0, "pixel_size_y": 20.0,
  "bounds": {"left": …, "right": …, "bottom": …, "top": …},   // keys verified :73-78
  "nodata": -9999.0,                      // config.DEFAULT_NODATA_VALUE
  "defaults": {                           // exactly 10 keys (:90-101), no clearance_buffer_m
    slope_safe_max, slope_caution_max, slope_hard_unsafe,
    rough_safe_max, rough_caution_max, rough_hard_unsafe,
    weight_slope, weight_roughness, weight_shadow, landing_ellipse_radius_m
  },
  "dem": [/* width*height numbers, row-major, rounded to 2 dp */],
  "slope": [], "roughness": [],           // 2 dp floats; slope slope-from-output is used as-is
  "psr": [], "psr_reference": [],         // ints
  "hazard_classes": [],                   // ints (from hazard_classes.tif :44-47)
  "boulder_hazard": [],                   // floats 2 dp (:66)
  "psr_polygons": { /* GeoJSON FeatureCollection or null */ },
  "landing_sites": [],                    // = landing_sites.json top_sites (:88)
  "boulder_points": []                    // = landing_sites.json boulder_points_sample ≤30 (:89)
}
```
Grid selection logic (`:25-50`): if `data/lola_south_pole_dem.tif` exists **and** its shape matches
the current rasters, real DEM/PSR reference arrays are embedded; otherwise synthetic.
⚠️ **Staleness is silent** — the file is only rebuilt when a pipeline run or an explicit
`export_data_bundle()` call happens (Issue I-06). The committed bundle is 250×250 @240 m (LOLA-era,
62 500-element arrays) while the committed rasters are 200×200 @20 m — verified 2026-10-17.
⚠️ **Derived hazard (VERIFIED by code reading, `export_web_data.py:34`):** `width/height` are
re-taken from the chosen DEM while `slope/psr/...` come from `outputs/` without a shape check —
if DEM and outputs ever disagree, the bundle ships mismatched array lengths.

Full contract + consumer map:
[`api_documentation/DATA_BUNDLE_SCHEMA.md`](api_documentation/DATA_BUNDLE_SCHEMA.md).

### 4.3 API envelopes

| Endpoint family | Envelope |
| :--- | :--- |
| health/status/logs | flat object, always `200` |
| recalculate | `{status, summary, landing_sites, hazard_classes_flat, rule_audit, sensitivity}` |
| audit | `{status, total_violations, rule_results[9], total_pixels, valid_pixels}` |
| errors | `{"status":"ERROR","message":…}` (400/500) or HTML `send_error` (404/409) |

---

## 5. Data-quality rules (from `.agents/rules/lunasafe.md`)

| Rule | How it appears in the model |
| :--- | :--- |
| "Never overwrite authoritative NASA files" | `prepare_lola_dataset` writes new `.tif`s; the `.jp2` is never modified; downloaded bytes only create the JP2 if absent |
| "All PSR polygons must be valid lunar CRS" | vectors inherit the raster CRS via `rasterio.features.shapes`; shapely `buffer(0)` repair (`psr.py:145`) |
| "Never publish invented accuracy numbers" | `/api/psr-validation` returns `null`s + explanation when no independent reference exists (`web_server.py:723-737`) |
| "Never label something as prediction… if derived from deterministic input" | provenance strings in §2/§3 tags say `SYNTHETIC DEMO` / `LOLA-derived … (Reference)` |
| "Class 4 exists to separate 'unknown' from 'safe'" | `CLASS_SHADOWED_UNKNOWN = 4` (`config.py:113`) + audit rule 8 |

---

## 6. Entity → producer → consumer matrix

| Entity | Produced by | Consumed by |
| :--- | :--- | :--- |
| `synthetic_dem.tif` | `io_utils.generate_synthetic_lunar_crater` (or committed) | `main.py` default, `export_web_data`, tests |
| `lola_south_pole_dem.tif` | `prepare_lola_dataset` / downloader | dataset auto-selection in CLI + web |
| `psr_binary.tif` | phase 2 | phase 4/6/7, `RASTER_CACHE["psr"]`, audit |
| `slope/roughness*.tif` | phase 3 | phase 4/6, `RASTER_CACHE`, map panels B/D |
| `hazard_classes.tif` | phase 4 | phase 5/6/7, map panel D, `/api/status` `has_outputs` |
| `hazard_summary.csv` | phase 4 | `/api/status`, `mission_report`, UI KPI tiles |
| `psr_polygons.*` | phase 2 | map panel C, `/api/data` embed, `mission_report` figure |
| `landing_sites.json` | phase 7 | `/api/download/landing_sites.json`, `mission_report`, `/api/data` |
| `web_data.json` | `export_web_data` / pipeline worker | `GET /api/data` → entire 2D/3D UI |
| `mission_report.pdf` | on first download request | the user (attachment) |
| `RASTER_CACHE` | `load_raster_cache` at start & post-run | `/api/recalculate`, `/api/audit` |

---

## 7. Volume & performance envelope

| Dataset | Pixels | `web_data.json` | `hazard_classes_flat` in `/api/recalculate` | Notes |
| :--- | :--- | :--- | :--- | :--- |
| synthetic 200×200 | 40 000 | ~2.2 MB | 40 000 ints | current default |
| LOLA 250×250 | 62 500 | ~3.4 MB | 62 500 ints | real data |
| hypothetical 4k×4k | 16.7 M | >1 GB — **does not work** | 16.7 M ints | architecture ceiling (doc 05 §10) |

There is no tiling, no paginated API, no lazy raster access, and no caching headers, so realistic
ceiling is ≈ 1 000 × 1 000 (≈ 1 M pixels).

---

## 8. Schema change process (there is none — recommended)

1. Producer and consumer must be edited together (they are in different files/languages).
2. Add a key test asserting the field exists (`tests/` currently covers `landing_sites.json`
   field presence only via `test_ml_recommender.py:73-87`).
3. Bump nothing — no version field exists. **Recommendation (T-15):** add
   `"schema_version": 1` to both JSON documents and to `/api/data` so the UI can fail fast on a
   stale bundle instead of crashing on a `undefined` index.
