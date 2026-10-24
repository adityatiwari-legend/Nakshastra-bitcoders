# Feature — 3D Terrain Explorer (three.js)

**IDs:** F-05 · **Status:** ✅ implemented · **Owner:** `web/app.js` §3D (`init3DScene:1701` … `:2761`) + vendored `web/vendor/three.min.js` (r128)
**Issues:** frozen r128 (SEC-07/T-21), no automated tests.

---

## 1. Capabilities

- Textured terrain mesh of the active dataset with **vertical exaggeration** slider, wireframe
  toggle, orbit/zoom/tilt camera (`OrbitControls`).
- **Texture mode switch**: DEM / slope / roughness / hazard / hillshade — reuses the same offscreen
  canvases built for Map Studio.
- **Dynamic sun**: azimuth + elevation sliders move a `DirectionalLight` with shadow mapping;
  reset button; optional lighting panel.
- **PSR outlines** draped above the surface (`toggle3dPsrOutlines:2005`, builder `:2060`).
- **Click-to-inspect** via raycasting → 3D inspector card (same data model as 2D).
- **Cross-section / transect tool**: click two points → profile chart (elevation vs distance),
  with hover readout (`init3dMouseEvents:2210`, `handleCrossSectionClick:2384`,
  `computeAndDrawTransect:2428`, `drawTransectProfileChart:2525`).
- **Snapshot** of the WebGL canvas (`capture3dSnapshot:2735`).
- Context-loss handling + retry (`retry3dContext:2049`).

## 2. Rendering architecture

```
loadDataset() → init3DScene():1701
  ├─ renderer (antialias, shadowMap), scene, PerspectiveCamera, OrbitControls
  ├─ build3dTerrainMesh():1840
  │    decimate DEM to ≤512×512 → PlaneGeometry (XZ plane)
  │    vertex Y = normalized elevation × exaggeration
  │    MeshStandardMaterial + CanvasTexture ← get3dSourceCanvas():1928 (active 2D layer)
  ├─ update3dTexture(mode):1939   swaps texture source
  ├─ update3dExaggeration():1953  rewrites vertex Y
  ├─ update3dSun():2013           DirectionalLight azimuth/elevation + shadows
  ├─ buildPsrOutlines3d():2060    densified GeoJSON rings at +1.8 world units
  └─ animate():1827               render loop (rAF)
```

World mapping: mesh extent mirrors the raster bounds; raycast hits → pixel indices → the same
sample helpers as 2D (`sampleDemElevation:2155`, `sampleSlope:2176`, `sampleRoughness:2183`,
`sampleHazardClass:2190`).

## 3. Controls & code map

| Control / tool | Function(s) (app.js) |
| :--- | :--- |
| tab activation | `switchTab:4480` → lazy `init3DScene` |
| camera reset | `reset3dCamera:2041` |
| exaggeration / wireframe / PSR | `update3dExaggeration:1953`, `toggle3dWireframe:1996`, `toggle3dPsrOutlines:2005` |
| sun & lighting | `update3dSun:2013`, `toggle3dLightingPanel:4552` |
| hover / click | `init3dMouseEvents:2210`, `get3dRaycastHit:2234`, `inspect3dPixel:2287` |
| transect tool | `toggle3dCrossSectionTool:2362` → `handleCrossSectionClick:2384` → `computeAndDrawTransect:2428` |
| snapshot | `capture3dSnapshot:2735` |
| landing focus from card | `focusOnSite3D:3673` |

## 4. Dependencies

- `web/vendor/three.min.js` (r128) loaded first; CDN fallback only if `window.THREE` is undefined
  (`web/index.html:20-28`) — offline-safe by default.
- Requires WebGL; shows retry UI on context loss. No SSR/CI coverage — a broken WebGL browser
  affects only this tab (2D remains usable).

## 5. Known limitations / risks

| Item | Detail |
| :--- | :--- |
| Mesh decimation ≤512×512 | finer detail than 512² is averaged away — acceptable for 250² data, lossy for future high-res |
| r128 freeze | 2021 release; no security patches; upgrade is a coordinated refactor (T-21) |
| Shadows | `DirectionalLight` shadow map cost on low-end GPUs; lighting panel hides it |
| Transect sampling | bilinear over in-memory arrays; falls back gracefully on NoData gaps |
| Tests | none; manual check items in doc 14 §6 ("mesh visible, sun responds, transect plots") |

## 6. Extension guidance

- New texture mode: add a canvas in Map Studio precompute → case in `update3dTexture` → UI select
  option. Reuse, don't duplicate, the 2D builders.
- Changing world↔pixel mapping must be done in **both** `build3dTerrainMesh` and the raycast
  helpers, or clicks will drift from the mesh (2D inspector uses different maths).
- Do not upgrade three.js casually: r128-era globals (`THREE.PlaneGeometry` behaviour, material
  params, OrbitControls import style) appear throughout `:1701-2761`.
