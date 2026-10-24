# Feature — Terrain Analytics (Slope, Aspect, Roughness, Histograms)

**IDs:** F-03 · **Status:** ✅ implemented · **Owner module:** `terrain.py` (+ `mapping.py`, `web/app.js`)
**Issues:** none functional; documented NoData-halo quirk (doc 15 §4).

---

## 1. What the user gets

| Product | File / surface | Units |
| :--- | :--- | :--- |
| Slope | `outputs/slope_deg.tif`, Map Studio layer, map panel B | degrees (0–90) |
| Aspect | `outputs/aspect_deg.tif` | degrees clockwise from N, flat=0 |
| Micro-relief roughness | `outputs/roughness_std_m.tif` | metres (3×3 std) |
| Ruggedness (TRI) | `outputs/roughness_tri_m.tif` | metres (Riley) |
| Statistics + histograms | console summary + `outputs/terrain_histograms.png` | — |
| Hillshade (derived) | map panel A background, Map Studio layer, 3D lighting reference | — |
| Live telemetry | hover readouts in Map Studio / 3D inspector | — |

## 2. Algorithms (summary)

- **Horn 3×3** slope/aspect (`terrain.py:21-87`), NoData filled with the valid median first.
- **Rolling std** via three `uniform_filter` passes (`:90-136`), ≥3 valid samples required.
- **Riley TRI** over 8 neighbours (`:139-196`).
- **Hillshade** from slope+aspect, sun az 315° / alt 45° (`mapping.py:30-56`).

Exactness is pinned by `tests/test_terrain.py::test_planar_ramp_slope_exactness` — a flat-surface
and NoData test round it out.

## 3. Pipeline & web behaviour

- **CLI:** phase 3 (`main.py:114-130`) writes 4 GeoTIFFs + histogram PNG.
- **Web:** does **not** recompute terrain — `RASTER_CACHE` loads `slope` and `roughness` from disk
  (`web_server.py:59-85`). Consequence: *you cannot change terrain metrics from the UI*; sliders only
  affect classification (by design, doc 05 A4).
- Histograms are a CLI-only artifact (not embedded in the UI).

## 4. UI surfaces

| Surface | Functions (app.js) |
| :--- | :--- |
| Offscreen layers | `buildOffscreenSlope:548`, `buildOffscreenRoughness:577`, `buildOffscreenHillshade:452`, `buildOffscreenDem:514` |
| Composite draw | `drawMap:766` with per-layer opacity (`onOpacityChange:1500`) |
| Hover telemetry | `updateHoverTelemetry:1285` (slope/roughness/elevation at cursor) |
| Pixel inspector | `inspectPixel:1161` + plain-language reason `getPlainLanguageReason:1249` |
| 3D sampling | `sampleSlope:2176`, `sampleRoughness:2183`, elevation `sampleDemElevation:2155` |
| Transect profile | `computeAndDrawTransect:2428` (elevation vs distance, 60–180 samples) |

## 5. Interpretation rules (used by classifier + copy)

| Metric | Safe | Caution | Unsafe |
| :--- | :--- | :--- | :--- |
| Slope | < 5° | 5–10° | ≥ 15° (hard) |
| Roughness (std) | < 1.5 m | 1.5–3 m | ≥ 5 m (hard) |

Intermediate values influence the continuous score H (weights .50/.30).

## 6. Known quirks (by design, documented)

1. **1-px NoData halo** — median fill before convolution bleeds valid-looking values next to gaps;
   ignore slope/roughness within 1 px of class-0 areas.
2. **Aspect on flat = 0°** rather than NaN — avoids random azimuths, means "no direction".
3. **`vmax=15°` saturation** on the map — steeper terrain all renders at the top colour.
4. Hillshade in UI vs PDF may differ if either sun angle changes independently.

## 7. Tests & gaps

Covered: flat exactness, planar-ramp exactness, NoData preservation, end-to-end exports.
Gaps: aspect wrap-around, non-square pixels, all-NoData input, hillshade golden image.

## 8. Change impact

Changing kernels or units affects: classifier inputs → audit thresholds → map colours → UI legend →
`landing_sites` fitness → docs 07/10/23 and the slope-sensitivity expectations in
`tests/test_validate.py`. Regenerate `outputs/` (and bundle) after any change — see doc 13 §7.
