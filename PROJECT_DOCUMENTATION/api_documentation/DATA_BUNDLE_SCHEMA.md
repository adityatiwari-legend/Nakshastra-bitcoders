# Data Bundle Schema — `outputs/web_data.json`

**Producer:** `export_web_data.export_data_bundle()` (`export_web_data.py:11-112`, called from
`main.py` phase 7 and from `web_server.py` after pipeline runs / offline-demo load).
**Consumer:** `GET /api/data` → `loadDataset()` (`web/app.js:233`) → every visual layer.
**Companion docs:** [`REST_API.md`](REST_API.md), [`../10_DATABASE_AND_DATA_MODEL.md`](../10_DATABASE_AND_DATA_MODEL.md) §4.2.

> ⚠️ The **committed** bundle is stale (Issue **I-06**): 250×250 @240 m, 62 500-element arrays,
> while the committed rasters are 200×200 @20 m. Values below were verified by loading the file
> directly on 2026-10-17.

---

## 1. Top-level contract (16 keys, order as written)

| # | Key | Type | Semantics (code) |
| :-: | :--- | :--- | :--- |
| 1 | `width` | int | `nx` of the embedded DEM (`:69`) |
| 2 | `height` | int | `ny` of the embedded DEM (`:70`) |
| 3 | `pixel_size_x` / 4 `pixel_size_y` | float | from DEM profile (`:71-72`) |
| 5 | `bounds` | object | **`left, right, bottom, top`** floats (`:73-78`) |
| 6 | `nodata` | float | `config.DEFAULT_NODATA_VALUE` = −9999.0 (`:79`) |
| 7 | `dem` | float[] | DEM flattened row-major, rounded 2 dp (`:80`) |
| 8 | `slope` | float[] | from `outputs/slope_degrees.tif`, 2 dp (`:18,:81`) |
| 9 | `roughness` | float[] | from `outputs/roughness_std.tif`, 2 dp (`:19,:82`) |
| 10 | `psr` | int[] | from `outputs/psr_binary.tif` (`:20,:83`) |
| 11 | `psr_reference` | int[] | real `data/lola_psr_mask.tif` if embedded DEM is real, else `data/synthetic_psr.tif` (`:50-54`) |
| 12 | `psr_polygons` | object\|null | `outputs/psr_polygons.geojson` verbatim (`:57-60`) |
| 13 | `hazard_classes` | int[] | from `outputs/hazard_classes.tif` (`:44-47`) |
| 14 | `boulder_hazard` | float[] | from `outputs/boulder_hazard.tif`, rounded 2 dp (`:63-66`) |
| 15 | `landing_sites` | object[] | `landing_sites.json → top_sites` (`:88`) — schema in [`LANDING_SITES_SCHEMA.md`](LANDING_SITES_SCHEMA.md) |
| 16 | `boulder_points` | object[] | `landing_sites.json → boulder_points_sample` ≤30 (`:89`) |
| 17 | `defaults` | object | **exactly 10** slider defaults echoed from `config` (`:90-101`) — see §3 |

## 2. DEM selection rule (`:25-50`)

```
if data/lola_south_pole_dem.tif exists AND shape == shape(slope from outputs):
        embed REAL DEM + lola_psr_mask as psr_reference   (is_real=True)
else:   embed synthetic DEM + synthetic_psr as psr_reference
```
⚠️ No shape validation for `slope/roughness/psr/hazard_classes` themselves — `width/height` are
re-derived from the DEM at `:34`, so a DEM/outputs mismatch would ship inconsistent array lengths
(derived from code, not yet observed).

## 3. `defaults` — the 10 keys

`slope_safe_max, slope_caution_max, slope_hard_unsafe, rough_safe_max, rough_caution_max,
rough_hard_unsafe, weight_slope, weight_roughness, weight_shadow, landing_ellipse_radius_m`
(values = `config` at export time; **`clearance_buffer_m` is absent**, mirroring I-05).

## 4. Verified snapshot of the committed file

```jsonc
{
  "width": 250, "height": 250, "pixel_size_x": 240.0, "pixel_size_y": 240.0,
  "nodata": -9999.0,
  "psr_polygons": {"type":"FeatureCollection","name":"…","features":[ /* 7 */ ]},
  "landing_sites": [ /* 3 sites, old-schema values (e.g. clearance_radius_m 20.0) */ ],
  "boulder_points": [ /* 11 */ ]
}
```
Because the bundle embeds `landing_sites.json` **as it was at export time**, stale bundles can carry
site objects whose values no longer match a fresh run (`suitability_pct` 79.3 vs 94.3 on the fresh
file). Regenerate with `python main.py` or `POST /api/load-offline-demo` + a pipeline run.

## 5. Consumer map (what breaks if a key is missing/mistyped)

| Consumer | Key(s) | app.js |
| :--- | :--- | :--- |
| grid setup + layer builders | `width/height/pixel_size/bounds/nodata` | `:233`, `:422-710` |
| hillshade / slope / rough layers | `dem/slope/roughness` | offscreen builders `:452-710` |
| PSR overlay + reference toggle | `psr/psr_reference/psr_polygons` | `:995-1067` |
| hazard reclassify + audit chips | `hazard_classes` | `:2962`, `:3053` |
| boulder layer | `boulder_hazard/boulder_points` | `:1040` |
| ALSS cards | `landing_sites` | `:3588` |
| slider initial values | `defaults` | `:2845` |
| 3D texture | all arrays | `:1939` |

## 6. Integrity checklist (manual, before release)

```powershell
& ".venv\Scripts\python.exe" -c "import json; d=json.load(open('outputs/web_data.json')); n=d['width']*d['height']; \
bad=[k for k in ('dem','slope','roughness','psr','psr_reference','hazard_classes','boulder_hazard') if len(d.get(k,[]))!=n]; \
print('expected',n,'mismatched:',bad,'sites:',len(d['landing_sites']),'boulders:',len(d['boulder_points']))"
```
Expected on a fresh synthetic run: `expected 40000 mismatched: []` (today: `expected 62500` with a
200×200 raster set → caught immediately).

## 7. Known issues touching this file

| Issue | Effect here |
| :--- | :--- |
| I-06 | file only rebuilt on pipeline run/offline-demo; stale grid & embedded sites |
| I-12b | `landing_sites` computed with 20 m pixel assumption (`ml_recommender.py:278`) |
| I-05 | no buffer field/constraint; UI ring decorative |
| derived §2 | no array-shape validation between DEM and `outputs/` layers |
