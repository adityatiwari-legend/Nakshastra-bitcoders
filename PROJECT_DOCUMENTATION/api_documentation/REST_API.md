# REST API — Detailed JSON Reference

> Companion to [`../09_API_REFERENCE.md`](../09_API_REFERENCE.md) (route table + statuses).
> This document adds full request/response JSON shapes and field semantics, verified against
> `web_server.py` on 2026-10-17. `/api/data` payload: [`DATA_BUNDLE_SCHEMA.md`](DATA_BUNDLE_SCHEMA.md);
> landing site objects: [`LANDING_SITES_SCHEMA.md`](LANDING_SITES_SCHEMA.md).

**Base:** `http://localhost:8050` · **Encoding:** UTF-8 JSON · **CORS:** `Access-Control-Allow-Origin: *` on JSON · **Auth:** none.

---

## 1. `GET /api/status`

```jsonc
{
  "status": "ONLINE",
  "active_dataset": "SYNTHETIC DEMO",          // or "REAL NASA LRO LOLA (South Pole)"
  "is_synthetic": true,
  "pipeline_running": false,
  "crs": "Moon South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)",
  "has_outputs": true,                          // hazard_classes.tif AND 4-panel PNG exist
  "map_png_available": true, "map_pdf_available": true,
  "synthetic_ready": true, "real_lola_ready": false,
  "summary_data": {                             // parsed from outputs/hazard_summary.csv
    "safe":            {"pixel_count": 12749, "area_km2": 5.0996, "pct_valid_terrain": 34.58, "pct_total_raster": 31.87},
    "caution":         {"pixel_count": 13339, "area_km2": 5.3356, "pct_valid_terrain": 36.18, "pct_total_raster": 33.35},
    "unsafe":          {"pixel_count": 9377,  "area_km2": 3.7508, "pct_valid_terrain": 25.44, "pct_total_raster": 23.44},
    "shadowed_unknown":{"pixel_count": 1399,  "area_km2": 0.5596, "pct_valid_terrain": 3.8,   "pct_total_raster": 3.5},
    "unknown":         {"pixel_count": 3136,  "area_km2": 1.2544, "pct_valid_terrain": 0.0,   "pct_total_raster": 7.84}
    // (example values = the committed synthetic bundle, verified from hazard_summary.csv)
  },
  "raster_metadata": {
    "dataset_name": "Synthetic Crater Topography (Demo Benchmark)",
    "source": "Synthetic Procedural Lunar Crater Model",
    "crs": "Moon South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)",
    "pixel_size_m": 20.0, "grid_size": "200 × 200 px", "total_pixels": 40000,
    "nodata_val": -9999.0, "is_synthetic": true
  },
  "timestamp": 1760688000.12
}
```

Semantics: `summary_data` is file-derived (correct pixel size); `{}` if the CSV is unreadable
(errors swallowed, `:289`). `raster_metadata` reads the real DEM when both real files exist
(`:233-250`), else falls back to hard-coded dicts (`:222-232`, `:251-261`).

---

## 2. `GET /api/logs`

```jsonc
{ "running": false, "logs": ["[Phase 1/7] ...", "..."], "total_lines": 137 }
```
- `logs`: last **150** lines of the subprocess buffer (lock-guarded).
- Buffer cleared only at the start of a new `POST /api/run-pipeline`.
- Includes the final `[Server] Pipeline finished with exit code N` line.

---

## 3. `GET /api/psr-validation[?benchmark]`

**Reference present (happy path):**
```jsonc
{
  "reference_loaded": true, "status": "LOADED",
  "reference_name": "Independent Ground-Truth Altimetry Catalog",
  "is_independent": true,
  "precision": 0.91, "recall": 0.87, "iou": 0.84, "f1_score": 0.89
}
```
**No reference (normal state of this repo):**
```jsonc
{
  "status": "UNLOADED", "reference_loaded": false, "reference_source": "None",
  "provenance_note": "No independent ground-truth reference loaded. ... (Rule: Never show invented accuracy numbers).",
  "precision": null, "recall": null, "iou": null, "f1_score": null
}
```
`?benchmark` compares the candidate with `data/lola_psr_mask.tif` or `data/synthetic_psr.tif`
(same-shape check, `:692-701`) and relabels `reference_name` as a benchmark — the numbers then
measure agreement with the *input*, not truth. Client: `checkPsrValidation(benchmarkMode)`
(`app.js:3985`).

---

## 4. `POST /api/run-pipeline`

**Request** (all optional; unknown keys ignored):
```jsonc
{
  "force_synthetic": true,
  "slope_safe_max": 5.0, "slope_caution_max": 10.0, "slope_hard_unsafe": 15.0,
  "rough_safe_max": 1.5, "rough_caution_max": 3.0, "rough_hard_unsafe": 5.0,
  "weight_slope": 0.5, "weight_roughness": 0.3, "weight_shadow": 0.2,
  "landing_ellipse_radius_m": 100.0, "clearance_buffer_m": 40.0
}
```
**Responses:**
```jsonc
200 {"status":"STARTED","message":"Pipeline initiated in background thread"}
409 {"status":"BUSY","message":"Pipeline already running in background"}
```
**Effects:** numeric keys are written into `config.*` (process-wide — I-11); child spawned as
`[PYTHON_BIN, "main.py", ("--force-synthetic",)?]` — **numbers are NOT forwarded** (I-04). On child
exit: `export_web_data.export_data_bundle()` + `load_raster_cache()`. Progress via `GET /api/logs`.

---

## 5. `POST /api/recalculate` (hot path)

**Request:** same key names as §4 (`force_synthetic` ignored). Missing key → current `config` value.
No cache → `400 {"status":"ERROR","message":"Raster cache not ready; run pipeline once."}`.

**Response:**
```jsonc
{
  "status": "SUCCESS",
  "summary": {
    "safe":            {"pixels": 12749, "area_km2": 5.0996, "pct": 34.58},   // pct of VALID pixels
    "caution":         {"pixels": 13339, "area_km2": 5.3356, "pct": 36.18},
    "unsafe":          {"pixels": 9377,  "area_km2": 3.7508, "pct": 25.44},
    "shadowed_unknown":{"pixels": 1399,  "area_km2": 0.5596, "pct": 3.8},
    "nodata":          {"pixels": 3136,  "area_km2": 1.2544, "pct": 7.84},     // pct of TOTAL pixels
    "valid_pixels": 36864, "total_pixels": 40000
  },
  "landing_sites": [ /* same objects as landing_sites.json top_sites[] */ ],
  "hazard_classes_flat": [0,1,2,3,4, "..."],   // length width*height, row-major ints
  "rule_audit": {
    "is_consistent": true, "total_violations": 0,
    "violations": {"rule1_safe_slope_exceeded":0, "rule2_safe_roughness_exceeded":0,
                   "rule3_safe_score_exceeded":0, "rule4_safe_pixel_in_psr":0,
                   "rule5_hard_slope_not_unsafe":0, "rule6_hard_roughness_not_unsafe":0,
                   "rule7_high_score_not_unsafe":0, "rule8_psr_pixel_marked_safe_or_caution":0,
                   "rule9_nodata_misclassified_as_surface":0}
  },
  "sensitivity": {
    "bars":  [{"threshold":5.0,"safe_km2":0.0,"caution_km2":0.0,"unsafe_km2":0.0,"shadow_km2":0.0},
              {"threshold":10.0,"...":"..."}, {"threshold":15.0,"...":"..."}],
    "curve": [{"slope_deg":3.0,"unsafe_km2":0.0,"unsafe_pct":0.0}, "... 10 points up to 25.0 ..."]
  }
}
```
⚠ Caveats: areas always use 20 m/px (**I-02**); sites computed with default 20 m pixel (**I-12b**);
request values mutate global config (**I-11**). Here `rule_audit.violations` uses the *emitted*
keys correctly; the `/api/audit` mapping does not (I-03).

---

## 6. `POST /api/audit`

```jsonc
{
  "status": "PASSED",                    // "FAILED" when total_violations != 0
  "total_violations": 0,
  "rule_results": [
    {"rule_id": "Rule 1",
     "description": "Safe slope limit: slope must be strictly below safe threshold (< 5.0°)",
     "violations": 0, "passed": true},
    "... 9 entries in order Rule 1..Rule 9 ..."
  ],
  "total_pixels": 40000, "valid_pixels": 36864
}
```
⚠ **Rule 4 always reports 0** — lookup key `rule4_safe_in_psr` doesn't exist (I-03).
Descriptions embed live threshold values. Client: `openAuditModal:3948`, table `:3968`.

---

## 7. `POST /api/download-lola` + `GET /api/download-lola-status`

```jsonc
// POST
200 {"status":"STARTED","message":"NASA LRO LOLA ingestion initiated"}
409 {"status":"BUSY","message":"Ingestion already in progress"}

// GET status (poll)
{"running": false, "progress": 100,
 "message": "NASA LRO LOLA South Pole dataset ready (60 km x 60 km, 240 m/px)!",
 "success": true}
// failure
{"running": false, "progress": 90, "message": "Ingestion error: <exception>", "success": false}
```
Progress milestones: 0 start · 60 local JP2 converting · 60-80 download % · 90 georeferencing · 100 done.

---

## 8. `POST /api/upload-raster` (dead endpoint)

- Body: **raw bytes** (not JSON) of a GeoTIFF. Written verbatim to `data/custom_upload.tif`.
- `200 {"status":"SUCCESS","filename":"custom_upload.tif","path":"..."}` / `500 {"status":"ERROR",...}`.
- ⚠ No UI caller, no size/type validation, fixed filename (I-12a, SEC-05). Recommended: delete (T-13).

## 9. `POST /api/validate-geotiff`

```jsonc
// request
{"type": "dem", "filename": ""}      // filename optional, resolved under data/
// success (note: crs_valid/all_passed are hard-coded true — I-11b)
{"status":"SUCCESS","checks":{
  "file_readable": true, "filename": "synthetic_dem.tif",
  "dimensions": "200 × 200 pixels", "pixel_size": "20.0 m/px",
  "crs_valid": true,
  "crs_name": "Moon South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)",
  "nodata_defined": true, "nodata_value": -9999.0,
  "min_val": -2850.84, "max_val": -2402.89,     // synthetic DEM, verified
  "all_passed": true
}}
// unreadable file
400 {"status":"ERROR","message":"..."}
```

## 10. `POST /api/load-offline-demo`

```jsonc
200 {"status":"SUCCESS","message":"Offline demo dataset loaded directly from outputs/. ...","is_offline":true}
500 {"status":"ERROR","message":"..."}
```
Re-runs `load_raster_cache()`; does **not** regenerate `web_data.json`.

---

## 11. Error vocabulary (all endpoints)

| Code | Shape | When |
| :--- | :--- | :--- |
| 400 | `{"status":"ERROR","message":…}` | cache not ready; geotiff unreadable |
| 404 | HTML (stdlib) | unknown POST route; missing file |
| 409 | `{"status":"BUSY","message":…}` | pipeline or ingestion already running |
| 500 | `{"status":"ERROR"…}` or HTML | static read failure, bundle build failure, demo load failure |
| — | `{}` used as request | malformed JSON body is **silently accepted** (no 400) |

## 12. Client call map

| UI action | Endpoint | app.js |
| :--- | :--- | :--- |
| heartbeat / badges | `GET /health`, `GET /api/status` | `:108`, `:128`, `:210` |
| initial load | `GET /api/data` | `:233` |
| slider release | `POST /api/recalculate` | `:3441` |
| RUN PIPELINE | `POST /api/run-pipeline` + `GET /api/logs` | `:3690`, `:3740` |
| audit modal | `POST /api/audit` | `:3948` |
| PSR card | `GET /api/psr-validation` | `:3985` |
| NASA download | `POST /api/download-lola` + status | `:3898` |
| offline demo | `POST /api/load-offline-demo` | `:4258` |
| preflight | `POST /api/validate-geotiff` | `:4220` |
| downloads | `GET /api/download/<name>` | various |
