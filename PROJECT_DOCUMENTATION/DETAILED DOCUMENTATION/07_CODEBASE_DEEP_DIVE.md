# 07 — Codebase Deep Dive

> This document walks the two real execution paths from process start to rendered result, citing
> files, functions and line numbers. Module-level detail lives in
> [`module_documentation/`](module_documentation/); this is the *connective tissue*.

---

## PART A — CLI pipeline (`python main.py`)

### A0. Process bootstrap (`main.py:1-36`)

1. `main.py:14-16` — insert the repo root into `sys.path` so flat modules import.
2. `main.py:18-26` — **venv auto-switch**: if `.venv\Scripts\python.exe` exists and the current
   interpreter cannot `import rasterio`, re-exec the same argv under the venv and exit with its
   return code. This is why `python main.py` works even before activation (Windows only).
3. `main.py:28-35` — import the 8 domain modules. Importing `config` (`config.py:17-19`) also
   **creates** `data/` and `outputs/` directories as a side effect.

### A1. Argument parsing (`main.py:237-256`)

| Flag | Effect | Downstream |
| :--- | :--- | :--- |
| `--dem PATH` | Override DEM | `run_pipeline(dem_path=...)` → `main.py:66-71` |
| `--psr PATH` | Override PSR mask | `main.py:73-78` |
| `--force-synthetic` | Ignore real files | `main.py:61-63` |
| `--fail-on-mismatch` | Loud failure instead of resampling | `io_utils.py:309-318` |
| `--quiet` | `verbose=False` suppresses per-phase banners | every module takes `verbose` |

### A2. Input selection (`main.py:60-80`) — the fallback ladder

```
force_synthetic?  ──yes──▶ data/synthetic_{dem,psr}.tif
        │no
        ▼
--dem given and exists? ──yes──▶ that file
        │no
        ▼
data/lola_south_pole_dem.tif exists? ──yes──▶ real dataset
        │no
        ▼
data/synthetic_dem.tif
```
`is_synthetic` is then decided by a **substring check**: `"synthetic" in str(dem_target).lower()`
(`main.py:80`). ⚠️ Consequence: a user-supplied file whose path contains "synthetic" is mislabelled;
a real file placed at another path is labelled real.

### A3. Phase 1 — Ingest (`main.py:85-93` → `io_utils.load_and_align_datasets`, `:380-414`)

- `inspect_raster(dem_path)` (`io_utils.py:191-254`):
  - `read_geotiff` (`:154-188`) returns a dict with `data`, `crs`, `transform`, `nodata`, `bounds`,
    `pixel_size_x/y`, `shape`, `dtype`, `profile`, `tags`.
  - **Earth-EPSG sentinel** (`:199-206`): string-matches 5 Earth signatures against `str(crs)`;
    raises `ValueError` on hit.
  - Computes valid/nodata counts, min/max, prints a banner.
- `align_psr_to_dem` (`:288-377`):
  - `check_grid_alignment` (`:257-285`) compares shape, CRS object, and the 6 affine coefficients
    within `tol=1e-4`.
  - If aligned → return as-is. Else → either raise (`--fail-on-mismatch`) or `rasterio.warp.reproject`
    with `Resampling.nearest` onto the DEM transform (`:339-348`), after a bounding-box overlap check
    (`:324-333`).
- Returns `(dem, raw_psr, dem_meta, psr_meta)`.

### A4. Phase 2 — PSR (`main.py:98-109` → `psr.process_and_export_psr`, `psr.py:174-269`)

1. Build a NoData mask from the **DEM** (`psr.py:192-200`) — shadow pixels over NoData elevation are discarded.
2. `binarize_psr` (`:30-58`) — bool / float(threshold 0.5) / int(>0) paths; then `binary[nodata]=0`.
3. `clean_psr_mask` (`:61-91`) — `scipy.ndimage.label` with a 3×3 (8-connectivity) structure,
   `np.bincount` sizes, zero everything `< PSR_MIN_SIZE_PIXELS` (9).
4. `calculate_psr_area` (`:94-112`) — `count × |px_x·px_y|`.
5. `vectorize_psr_to_polygons` (`:115-171`) — `rasterio.features.shapes(..., connectivity=8)`,
   `shapely.geometry.shape`, `buffer(0)` repair, GeoDataFrame with `poly_id, feature, area_m2,
   area_km2, perim_m, provenance`.
6. Write GeoTIFF (`nodata=None`, tags include `PSR_PROVENANCE` + area) and both vector formats.
7. Provenance chosen at `psr.py:215`: `SYNTHETIC DEMO PSR Mask` or `Published / LOLA-derived PSR Mask (Reference)`.

> 📌 Note the honesty rule in action: even when using real LOLA elevation, the label says
> *"LOLA-derived … (Reference)"*, never "independently predicted".

### A5. Phase 3 — Terrain (`main.py:114-130` → `terrain.process_terrain_pipeline`, `terrain.py:293-425`)

- `calculate_slope_and_aspect` (`:21-87`):
  - valid mask from NoData; NoData cells filled with the **global valid median** before convolution (`:46-49`).
  - Horn kernels at `:55-64`, `scipy.ndimage.convolve(..., mode="nearest")`.
  - slope = `degrees(arctan(√(gx²+gy²)))`; aspect = `(90 − degrees(atan2(dz/dy, −dz/dx))) % 360`
    with flat (<0.01°) forced to 0.
  - NoData re-applied at `:84-85`.
- `calculate_roughness_std` (`:90-136`) — clever use of three `uniform_filter` passes to get
  `count`, `Σz`, `Σz²` per 3×3 window; variance = `E[z²] − (E[z])²` clipped at 0; needs ≥3 valid
  samples; NoData re-applied.
- `calculate_roughness_tri` (`:139-196`) — 8 manual shifts, `√(Σ diff² / count)`.
- Exports 4 GeoTIFFs with `METRIC`/`UNITS` tags, then `generate_terrain_histograms` (`:199-290`).
- Returns a metrics dict (`slope`, `aspect`, `roughness_std`, `roughness_tri`, `valid_mask`, stats).

### A6. Phase 4 — Hazard (`main.py:135-147` → `hazard.process_hazard_pipeline`, `hazard.py:185-263`)

The classifier contract, in evaluation order (`classify_hazard_surface`, `hazard.py:61-134`):

```
1. valid_mask   = slope!=-9999 & ~nan & rough!=-9999 & ~nan      (:80-86)
2. everything   = Class 0                                        (:89)
3. score H      = .50·clip(slope/15,0,1) + .30·clip(rough/5,0,1) + .20·D   (:41-54)
                 (D = shadow_fraction or 0 → 0 in this pipeline)
4. hard override= slope>=15  OR  rough>=5                        (:100-102)
5. is_unsafe    = valid & (H>=0.60 | hard)            → Class 3   (:105-106)
6. is_psr & ~unsafe                             → Class 4        (:109-113)
7. remaining non-PSR valid:
      is_safe   = H<0.25 & slope<5 & rough<1.5        → Class 1   (:119-125)
      else                                         → Class 2     (:127-129)
8. ~valid                                       → Class 0         (:132)
```

Then `generate_hazard_summary_table` (`:137-182`) counts pixels per class and multiplies by
`|px_x·px_y|`; CSV written at `:239-241`.

> 🔍 **Why the order matters:** Class 4 is assigned *after* Unsafe, so a steep PSR wall becomes
> Class 3, while a flat PSR floor becomes Class 4. Swapping steps 5 and 6 would break audit rule 8.

### A7. Phase 5 — Cartography (`main.py:152-167` → `mapping.generate_4panel_hazard_map`, `mapping.py:149-380`)

- Hillshade from slope+aspect (`compute_hillshade`, `:30-56`, sun az 315° / alt 45°).
- 2×2 figure at `figsize=(16,14)`, `dpi=300`:
  - A: DEM (viridis) over hillshade + scale bar + north arrow
  - B: slope (inferno, vmax 25°) + contours at 5/10/15°
  - C: PSR cyan overlay + GeoDataFrame outlines + area badge
  - D: hazard classes via `ListedColormap` + `BoundaryNorm([0.5,1.5,2.5,3.5,4.5])` + legend
- Bottom text: CRS + source provenance (`:350-359`).
- Saves PNG **and** PDF (`:364-365`).

### A8. Phase 6 — Validation (`main.py:172-186` → `validate.process_validation_pipeline`, `validate.py:283-357`)

1. `compute_psr_metrics(psr_mask, psr_mask, ...)` (`:301-308`) — ⚠️ **compares the mask with itself**,
   so precision/recall/IoU/F1 are 1.0 by construction. See Issue I-01.
2. `verify_rule_consistency` (`:311-318` → `:70-148`) — the 9 invariants, counted with numpy
   boolean reductions; returns `is_consistent`, `total_violations`, `audited_pixels`,
   `detailed_violations` (keys `rule1_…` … `rule9_…`).
3. `run_slope_sensitivity_analysis` (`:321-330` → `:151-280`) — 5 threshold scenarios, recomputes
   classification inline (without the shadow term, `:196`), asserts monotonic growth of safe area
   in the test (`tests/test_validate.py:129-132`), renders a stacked bar chart.

### A9. Phase 7 — Autonomy (`main.py:191-201` → `ml_recommender.run_mission_autonomy`, `:218-300`)

⚠️ This phase **re-opens files from disk** (`:238-253`) instead of using the in-memory arrays from
phases 1–4, and passes the **input** DEM path plus the **output** PSR/hazard/slope/roughness paths.
It therefore silently depends on phases 2–4 having been written to `outputs/` first.

1. `detect_boulder_micro_hazards(dem)` (`:18-81`): fill NoData with valid mean →
   `gaussian_filter(σ=2)` macro trend → `|dem − trend|` micro residual → z-score →
   `sigmoid(1.8·(z − 2.2))` probability; local maxima with `maximum_filter(5)` above the threshold
   become discrete boulder points, capped at 150.
2. `recommend_landing_sites(...)` (`:84-215`):
   - `safe_mask = (hazard == 1)`; `distance_transform_edt` → clearance in **pixels × pixel_size_m**
     (default 20 — see Issue I-12).
   - candidate pixels: `dist_m ≥ ellipse_radius_m` (100 m); graceful relaxation to 85 % of the
     maximum if none qualify (`:119-121`).
   - fitness = `0.35·clearance + 0.30·flatness + 0.20·smoothness + 0.15·science` (`:143-148`),
     science = Gaussian centred at 250 m from PSR (`:140`).
   - greedy arg-max with circular suppression of radius `2.5×ellipse` (`:154-155, 205-207`).
   - each site gets `easting_m/northing_m` via `rasterio.transform.xy(..., offset='center')`.
3. Writes `boulder_hazard.tif` and `landing_sites.json`.

### A10. Summary block (`main.py:206-234`)

Prints elapsed time, dataset provenance, `total_violations`, PSR km², and a 15-item artifact list.

---

## PART B — Web Mission Control (`python web_server.py`)

### B0. Process bootstrap (`web_server.py:1-56`)

1. `sys.path` insert (`:27-29`), resolve `PYTHON_BIN` to the venv if present (`:38-39`).
2. Declare four module-level state globals (`:42-56`).
3. `__main__` (`:858-864`) → `run_server(8050)`.

### B1. `run_server` (`web_server.py:834-855`)

1. `load_raster_cache()` (`:59-85`):
   - DEM = real if `data/lola_south_pole_dem.tif` exists else synthetic (`:62`) — **note: it does not
     check the PSR file for this choice**, unlike `/api/status` (`:220`).
   - Requires `outputs/slope_deg.tif` **and** `outputs/psr_binary.tif` to exist, else returns `False`
     (`:67-68`) — the console then cannot recalculate until a pipeline run happens.
   - Fills `RASTER_CACHE` with 4 numpy arrays + profile + transform.
2. `ThreadingHTTPServer(("", 8050), LunaSafeHandler)`; on `OSError` retry on 8080 (`:840-846`).

### B2. Request routing

`LunaSafeHandler.__init__` (`:91-93`) roots `SimpleHTTPRequestHandler` at the **repo root**.

`do_GET` (`:95-152`) order:
1. `/` or `/index.html` → `web/index.html`; `/styles.css`; `/app.js`
2. `/health`, `/api/health` → `handle_api_health` (`:210`)
3. `/api/status` → `handle_api_status` (`:263`)
4. `/api/data` → `handle_api_data` (`:309`) — builds the bundle on the fly if missing
5. `/api/logs` → `handle_api_logs` (`:320`) — last 150 lines under the lock
6. `/api/download-lola-status` → the `DOWNLOAD_STATUS` dict
7. `/api/psr-validation` → `handle_api_psr_validation` (`:681`)
8. `/api/download/<name>` → `handle_api_download` (`:789`)
9. `/vendor/*` → `web/vendor/*`
10. `/outputs/*` → repo `outputs/*`
11. **fallback → `super().do_GET()`** (`:152`) — serves *any* file under the repo root

`do_POST` (`:154-173`): `run-pipeline`, `recalculate`, `audit`, `download-lola`, `upload-raster`,
`validate-geotiff`, `load-offline-demo`; anything else → 404.

### B3. The hot path — `POST /api/recalculate` (`:411-547`)

This is the "60 FPS" feature. Step by step:

1. `read_json_body` (`:200-208`) — `Content-Length` bytes → `json.loads`; **errors become `{}`**.
2. Lazy `load_raster_cache()` if needed (`:415-419`).
3. Coerce every parameter with `float(body.get(key, config.KEY))` (`:422-435`).
4. **Write them into the `config` module globals** (`:438-446`) — permanent for the process lifetime.
5. `hazard.classify_hazard_surface(slope, roughness, psr)` (`:455-459`) — pure numpy on cached arrays.
6. Count pixels per class (`:462-468`); convert to km² using **`config.SYNTHETIC_PIXEL_SIZE_M`
   (20)** regardless of dataset (`:470`) → Issue I-02.
7. `ml_recommender.recommend_landing_sites(...)` (`:484-493`) — again with the default 20 m/px
   (`pixel_size_m` is not passed) → Issue I-12.
8. `validate.verify_rule_consistency(...)` (`:496-502`).
9. Build sensitivity bars at 5/10/15° and an "unsafe vs slope" curve (`:505-530`).
10. Reply with `summary`, `landing_sites`, **the full flattened `hazard_classes_flat`**, `rule_audit`,
    `sensitivity` (`:532-547`).

> 💡 Design note: shipping 40,000 integers back to the browser on every slider tick is fine at
> 200×200 but will not scale to real LOLA mosaics (62,500 today).

### B4. The slow path — `POST /api/run-pipeline` (`:329-409`)

1. Lock-guarded "already running?" check → 409 (`:331-335`); clear the log buffer.
2. Same config mutation as above (`:341-362`) — but these values are **lost** because:
3. `worker()` spawns `subprocess.Popen([PYTHON_BIN, "main.py", ("--force-synthetic",)])` (`:366-381`)
   — a *fresh interpreter* that re-reads `config.py` from disk. Only the synthetic flag propagates.
   → Issue I-04.
4. stdout lines are appended to `PIPELINE_LOGS` under the lock (`:383-387`).
5. On completion: `export_web_data.export_data_bundle()` + `load_raster_cache()` (`:395-397`).
6. `finally`: `PIPELINE_RUNNING = False` (`:402-404`).

### B5. Browser startup sequence (`web/app.js`)

```
DOMContentLoaded (≈line 80)
 ├─ initEventListeners()                       (≈88)
 ├─ checkStatusAndSummary()  GET /api/status   (≈128) → badges, KPIs from hazard_summary.csv
 ├─ loadDataset()            GET /api/data     (≈233)
 │    ├─ precomputeAllLayers()  → 8 offscreen canvases (hillshade, DEM, slope, roughness,
 │    │                           PSR, PSR-ref, hazard, minimap base)
 │    ├─ resetCanvasView() + drawMap()          layered composite, scale bar, minimap
 │    ├─ renderLandingSitesCards()
 │    └─ updateKpisFromData() → onParamChange()
 ├─ init3DScene()                              (≈1701) three.js scene + terrain mesh
 └─ startStatusHeartbeat()  /health @2500 ms, /api/status @5000 ms   (≈210)
```

Slider interaction:
`oninput=onParamChange()` → (a) instant **client-side** `previewReclassifyClient()` re-classification,
then (b) **debounced 250 ms** `recalculateFast()` → `POST /api/recalculate` → replaces
`currentHazardArray`, redraws canvas + 3D texture, updates the delta chips.

### B6. Rendering internals (2D)

- Layer state `mapLayers` + `offscreenCanvases` (≈39–60).
- Each `buildOffscreen*` writes an `ImageData` row by row.
- `drawMap()` (≈766–945) fits the raster to the canvas, applies per-layer `globalAlpha`, then draws
  PSR outlines, landing ellipses + 40 m dashed standoff (client-only!), reticle, AOI box,
  scale bar, minimap.
- Pixel inspector `inspectPixel(col,row,…)`: converts to easting/northing using
  `DATA.bounds` + pixel size, classifies or reads `currentHazardArray`, and renders
  `getPlainLanguageReason()` text.

### B7. Rendering internals (3D)

- `build3dTerrainMesh()` (≈1840): stride-decimate to ≤512×512, `PlaneGeometry` rotated to XZ,
  vertex Y from DEM min/max × exaggeration, `CanvasTexture` taken from the active 2D layer.
- `buildPsrOutlines3d()` (≈2060): densified GeoJSON rings draped at +1.8 world units.
- `update3dSun()` (≈2013): azimuth/elevation sliders move a `DirectionalLight` with shadows.
- Raycast click → `inspect3dPixel()`; transect tool samples 60–180 points bilinearly and plots a
  profile (≈2428–2650).

---

## PART C — Cross-cutting behaviours worth knowing

| Behaviour | Evidence | Why it matters |
| :--- | :--- | :--- |
| Two different "sources of truth" for class areas | CLI: `hazard_summary.csv`; web KPIs: same CSV via `/api/status` (`:273-290`); web recalc: recomputed with 20 m/px (`:470`) | Numbers can disagree between tabs on real data |
| Two different raster caches | Disk (`outputs/*.tif`) and RAM (`RASTER_CACHE`) | After a manual `python main.py` in another terminal, the web server keeps serving stale RAM until restart |
| Config is shared mutable state | `web_server.py:341-362,438-446` | A slider in one browser session changes results for every other session |
| The auditor is a second implementation | `validate.py:103-137` vs `hazard.py:99-133` | Any threshold change must be made in both, or rules silently drift (already happened in the web Rule 4 key) |
| `outputs/` is the only IPC | `main.py` writes, `web_server.py` reads | Concurrent runs are unsafe |

## PART D — Suggested reading exercise (30 min)

1. Put a breakpoint (or `print`) at `hazard.classify_hazard_surface` and run `python main.py --force-synthetic`.
2. Inspect `hazard_classes` — histogram it: `np.bincount(hazard_classes.ravel(), minlength=5)`.
3. Compare against `outputs/hazard_summary.csv`.
4. Then run `python -m pytest tests/test_hazard.py -v` and read each assertion to see which class
   rule it pins down.
5. Finally, open `web/app.js` and find the *client-side copy* of the same thresholds
   (`previewReclassifyClient`) — count how many places duplicate `config.py` numbers.

Step 5 is the single most valuable insight from this codebase: **the thresholds exist in many
places**, and keeping them in sync is the project's main maintenance risk.
