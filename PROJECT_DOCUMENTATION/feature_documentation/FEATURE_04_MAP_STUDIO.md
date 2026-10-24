# Feature — Map Studio (2D Interactive Console)

**IDs:** F-04 · **Status:** ✅ implemented · **Owner:** `web/index.html` + `web/app.js` (sections §1-§4)
**Issues:** M-08 (duplicated thresholds), SEC-08 (innerHTML sinks), perf ceiling doc 05 §10.

---

## 1. Capabilities

- 7 toggleable raster layers with individual **opacity sliders**: DEM, hillshade, slope,
  roughness, PSR (derived), PSR-reference, hazard classes + minimap.
- **Pan / zoom / reset**, swipe-compare tool, AOI box selection with live stats, target reticle.
- **Pixel inspector popup**: pixel/row-col, world coordinates (lunar metres), elevation, slope,
  roughness, class name, and a plain-language safety reason.
- **Landing-site ellipses** + 40 m dashed standoff ring (client-drawn), PSR white outlines.
- **Legend with per-class totals** (km²/%), scale bar, minimap with viewport rectangle.
- **PNG export of the current view** (canvas → dataURL → download).

## 2. Rendering architecture

```
GET /api/data ──▶ DATA{width,height,bounds,arrays…}
   └─▶ precomputeAllLayers():422
         buildOffscreenHillshade:452 · Dem:514 · Slope:548 · Roughness:577
         Psr:606 · PsrRef:631 · rebuildOffscreenHazard:656 · MinimapBase:710
         (each writes an ImageData pixel loop → OffscreenCanvas)
   └─▶ drawMap():766   composites layers at current opacity/zoom,
                       then drawPsrWhiteOutlines:947 · drawLandingSitesOverlay:995
                       · drawTargetReticle:1040 · drawAoiBoxOverlay:1067
                       · updateScaleBar:1085 · updateMinimap:1109
```
- Layer state lives in `mapLayers`; view state (center/zoom/transform) drives world↔pixel maths
  from `DATA.bounds` + pixel size.
- Hazard layer is rebuilt by `rebuildOffscreenHazard()` when classes change (server response or
  client preview), then `redrawCanvas():1549`.

## 3. Interaction model

| Input | Handler | Behaviour |
| :--- | :--- | :--- |
| wheel / buttons | `zoomMap:1519`, `resetCanvasView:1534` | zoom about cursor |
| drag | init handlers `initStudioMapEventListeners:268` | pan |
| click | `inspectPixel:1161` | opens inspector with values from all arrays |
| hover | `updateHoverTelemetry:1285` | HUD readout |
| AOI drag | `computeAoiStats:1346` / `clearAoiSelection:1414` | %safe/psr/slope means inside box |
| tool switch | `setStudioTool:1430` | pan / swipe / reticle / AOI |
| layer checkboxes/opacity | `onLayerToggle:1489`, `onOpacityChange:1500` | immediate redraw |
| preset views | `applyPreset:2761`, `resetDefaults:2816` | jump to configured camera+layer states |
| export | `exportCurrentViewAsPng:1558` | downloads composite PNG |

## 4. Data dependencies

- Requires `GET /api/data` (Feature bundle). Grid staleness (I-06) directly corrupts coordinates
  and minimap alignment.
- Class names/colours duplicated from `config.CLASS_*` (M-08).
- The **40 m standoff ring is UI-only** — the ranking algorithm doesn't enforce it (I-05); the ring
  can suggest safety the data doesn't guarantee. If T-12b lands, the ring becomes truthful.

## 5. Performance profile

- Initial build: ~7 ImageData loops over `width×height` — fine at 40 k pixels, ~100-200 ms at 62 k,
  multi-second beyond ~1 MP.
- Redraws are full-canvas composites (cheap: 2D `drawImage`).
- **No tiling/pyramids** — zoom only rescales; ceiling documented in doc 05 §10; payload slimming
  is task T-05.

## 6. Testing today

**None automated** (no browser tests). Manual checklist: doc 13 §4.4 / doc 14 §6.
Suggested smoke (T-20): boot server → assert `#mapCanvas` exists, `DATA.width>0`, layer toggle
changes a sampled pixel, inspector shows a class name for a known safe pixel.

## 7. Extension guidance

1. New layer → add builder `buildOffscreen<Name>()`, register in `precomputeAllLayers`, add a
   checkbox in `index.html`, hook in `onLayerToggle`, ensure `/api/data` includes the array (schema
   doc update!), add legend handling.
2. New inspector field → `inspectPixel` + `getPlainLanguageReason` (keep the language plain —
   project rule about clear safety explanations).
3. Keep world-coordinate maths in one place (`DATA.bounds`/pixel size) — mismatches here cause
   "coordinates drift" bugs after dataset switches.
