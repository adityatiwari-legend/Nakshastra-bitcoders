# Tooling Modules — `export_web_data.py`, `prepare_lola_dataset.py`, `build_interactive_ui.py`

> The three offline utilities. None are on the critical CLI path; one (`export_web_data`) **is**
  called by the web server after every pipeline run.

---

## 1. `export_web_data.py` (112 lines) — the UI data contract writer

**Status:** 🟠 essential but untested · **Issues:** I-06 (staleness), M-06 (no tests), T-15 (no schema version).

### `export_data_bundle()` (`:11-108`)

1. Read current rasters from `outputs/` (hazard/slope/roughness/psr/boulder) → arrays.
2. Choose DEM/PSR reference arrays (`:25-50`): **if `data/lola_south_pole_dem.tif` exists and its
   shape matches the rasters** → real arrays as `dem`/`psr_reference`; else synthetic.
3. Read `psr_polygons.geojson` (may be absent → empty FeatureCollection), `landing_sites.json`,
   boulder points (max 30).
4. Write `outputs/web_data.json` (`:104`): header (`width, height, pixel_size_x/y, bounds, nodata,
   defaults`) + flat arrays + embedded vectors/sites.

CLI: `python export_web_data.py` (`:111`). Called by `web_server.py:313` (on-demand for
`GET /api/data`) and `:396` (after each UI pipeline run).

### Key risks
- **Silent staleness (I-06):** manual `python main.py` runs do *not* call this → bundle can be days
  older than the rasters (proven in git history, doc 18 §2).
- **Shape guard is one-directional:** mismatched shapes fall back to synthetic silently rather than
  erroring — which can produce a bundle whose `psr_reference` belongs to a different dataset.
- No `schema_version` field → the UI can't detect an old-format bundle (T-15).
- Output is a single ~2-3 MB pretty-printed JSON, no compression (doc 10 §7).

### Schema ownership
Documented in `api_documentation/DATA_BUNDLE_SCHEMA.md`. Any field change = edit producer + schema
doc + `web/app.js` loader together.

---

## 2. `prepare_lola_dataset.py` (107 lines) — NASA JP2 → lunar GeoTIFFs

**Status:** 🟡 works only on the original machine · **Issues:** **I-15** (hard-coded root),
**I-08** (PSR is a depth heuristic), M-03 (URL drift), M-06 (no tests).

### `convert_real_lola_to_geotiff()` (`:19-104`)

```
1. locate  data/ldem_75s_240m.jp2         (:20)
2. open with rasterio, centre-crop 250×250 (:29-60)
3. scale DN × 0.5 → metres                 (tag UNITS=metres, :90-93)
4. assign lunar polar stereographic CRS     (config.LUNAR_SOUTH_POLE_PROJ4)
5. DEM → data/lola_south_pole_dem.tif
6. PSR heuristic: depth < -900 m → uint8    (:51-56)  ← I-08
   → data/lola_psr_mask.tif
7. tags: PROJECT/BODY/DATA_TYPE/DESCRIPTION/MISSION=LRO/INSTRUMENT=LOLA (verified on disk)
```

### Landmines
| Line | Problem | Task |
| :--: | :--- | :-: |
| 15 | `ROOT_DIR = Path(r"e:\sistec\LunaSafe")` — breaks elsewhere | T-18 |
| 51-56 | PSR = depression threshold, **not** a published PSR product | I-08 / T-23 |
| — | no test coverage; PSR/DEM grid must match `check_grid_alignment` assumptions | T-08 scope |

Both outputs are **committed to git** — re-running overwrites them (repo diff on any machine with
different rasterio versions possible).

Invoked by: manual CLI, and `web_server.py:626/654` inside the download worker.

---

## 3. `build_interactive_ui.py` (1131 lines) — legacy single-file dashboard

**Status:** ⚪ legacy / unused by the main app · **Issues:** dead weight (see doc 06).

- Reads `outputs/web_data.json` (`:11`) and emits a **self-contained `dashboard.html`** (~1.3 MB)
  with inline CSS/JS — a pre-web-server generation of the console.
- Opened only by `view_ui.bat` (double-click). Not linked from `web/index.html`; the server serves
  it accidentally via the repo-root static fallback (`http://localhost:8050/dashboard.html`).
- Writes to `config.BASE_DIR / "dashboard.html"` (`:1123`).
- **No consumers in code, no tests.** Keep for offline viewing or delete (team decision, T-14
  adjacent); if kept, note it must be regenerated whenever the bundle schema changes.

---

## 4. Cross-cutting notes for all three

| Concern | Detail |
| :--- | :--- |
| Import style | all three do `sys.path.insert(ROOT_DIR)` + `import config` (I-15 is the outlier with a literal path) |
| Failure mode | `export_web_data` fails loudly; `prepare_lola_dataset` raises; `build_interactive_ui` swallows some read errors |
| Tests | **zero** for all three (M-06) |
| Documentation | covered here + doc 08 §4-5, doc 10 §4.2, doc 13 §3.3-3.6 |
| Suggested minimal tests (T-08) | bundle: `width*height == len(dem)` and grid == raster grid (this is T-10's freshness guard); converter: crop shape + scale + PSR dtype using a tiny synthetic JP2 fixture; dashboard: "generates a file containing `<html`" |

## 5. Recommended ownership boundaries

- `export_web_data` → **web/frontend owner** (contract changes need UI review)
- `prepare_lola_dataset` → **science/data owner** (provenance claims live here)
- `build_interactive_ui` → whoever volunteers to delete or freeze it
