# Feature — Permanent Shadow Region (PSR) Mapping

**IDs:** F-02 · **Status:** ✅ implemented (input provenance caveats) · **Owner module:** `psr.py` (+ `io_utils.py`, `prepare_lola_dataset.py`)
**Issues:** I-08 (real mask is a heuristic), I-01 (accuracy metrics), honesty strings per doc 19 §E.

---

## 1. What the user gets

1. A **binary PSR mask** aligned to the DEM grid (`outputs/psr_binary.tif`, cleaned of speckle).
2. **Vector polygons** of each shadow region with areas/perimeters
   (`psr_polygons.geojson` + shapefile bundle + zip) — drawn on map panel C and in the UI.
3. **Total PSR area in km²** — console summary, map badge, KPI tiles, PDF.
4. A **PSR overlay layer** in Map Studio (toggle) and PSR outlines draped in 3D.
5. Truthful **PSR validation card** (metrics or an explicit "no reference" explanation).

## 2. Data sources

| Mode | Mask file | How produced | Label written |
| :--- | :--- | :--- | :--- |
| Synthetic | `data/synthetic_psr.tif` | procedural generator (`io_utils.py:465-500`) | `SYNTHETIC DEMO PSR Mask` |
| Real | `data/lola_psr_mask.tif` | **depth < −900 m** heuristic on the LOLA DEM (`prepare_lola_dataset.py:51-56`) | `Published / LOLA-derived PSR Mask (Reference)` |
| External reference (optional) | `data/independent_psr_reference.tif` | *not shipped* — would enable true metrics | used only by `/api/psr-validation` |

⚠️ **I-08:** neither mode is an independently published PSR atlas; the *web* endpoint's honest
`UNLOADED` note (`web_server.py:727-731`) is the accurate description of the current state.

## 3. Processing steps

```
raw mask + DEM NoData mask
 → binarise (0.5 / >0 / bool)          psr.py:30
 → despeckle: remove components < 9 px  psr.py:61   (8-connectivity, scipy.ndimage.label)
 → area = count × |px_x·px_y|           psr.py:94
 → vectorise (rasterio.shapes, conn=8, buffer(0) repair)  psr.py:115
 → write tif (nodata=None, provenance tags) + geojson + shp + zip
```
Grid safety: if the input PSR grid mismatches the DEM, `io_utils.align_psr_to_dem`
reprojects (nearest) or raises with `--fail-on-mismatch`.

## 4. Where it is consumed

| Consumer | Use |
| :--- | :--- |
| `hazard.py` | class 4 assignment + audit rules 4/8 |
| `mapping.py` panel C | cyan overlay + outlines + area badge |
| `ml_recommender.py` | science term (250 m preference) + `dist_to_psr_m` |
| `validate.py` | rules 4/8; `compute_psr_metrics` |
| `web/app.js` | PSR layer (`:606`), outlines (`:947`, 3D `:2060`), validation tab (`:3985`) |
| `export_web_data.py` | `psr[]`, `psr_reference[]`, embedded GeoJSON |
| `mission_report.py` | PSR area figure |

## 5. Accuracy & metrics (I-01)

- The **function** `validate.compute_psr_metrics` is unit-tested and correct (precision, recall,
  IoU, F1).
- The **batch pipeline** calls it as `metrics(psr, psr)` (`validate.py:301-308`) → always 1.000.
- The **web endpoint** compares candidate vs reference file when one exists, and otherwise returns
  `{"status":"UNLOADED", … precision: null …}` with a provenance note — the behaviour to keep.
- **Never quote the four metrics until T-04 lands.**

## 6. UI controls & behaviours

- Layer toggles: PSR (derived) and PSR-reference (input) in Map Studio; white outlines on top.
- Validation tab: `checkPsrValidation(benchmarkMode)` (`app.js:3985`) — `?benchmark=true` compares
  against the input mask and is *labelled* a benchmark.
- 3D: PSR outlines toggle (`:2005`) rendered at a fixed hover height above terrain.

## 7. Tests

`tests/test_psr.py` (5): binarise semantics, 9-px despeckle boundary, exact area arithmetic,
vector schema/validity, end-to-end exports. **Not covered:** NaN inputs, reprojection path,
empty-region (0 polygons) export behaviour.

## 8. Gaps & tasks

| Gap | ID | Task |
| :--- | :-: | :-: |
| No independent reference shipped → no truthful accuracy numbers | I-01/I-08 | T-04, T-23 |
| Provenance wording "Published / …" stronger than the heuristic underneath | I-08 | T-12a/T-23 |
| Depth threshold −900 m is a constant inside `prepare_lola_dataset.py`, not `config.py` | — | move to config when touching |
