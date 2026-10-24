# Changelog

All notable changes to the OrbisLuna platform are documented in this file.

## [Unreleased] - 2026-10-23

### Task 1: Cross-Platform Test Runner
- **Added `scripts/run-pytest.js`**: Cross-platform Python interpreter resolver inspecting `.venv/Scripts/python.exe` (Windows), `.venv/bin/python` (POSIX), `python3`, and `python` in order. Runs `pytest tests -q`, forwards CLI arguments, and exits with child status.
- **Updated `package.json`**: Changed `"test"` script from hardcoded `.\.venv\Scripts\python.exe` to `"node --test \"tests/js/*.test.js\" && node scripts/run-pytest.js"`.
- **Updated `scripts/build.js`**: Refactored to share the cross-platform Python interpreter discovery.
- **Added `tests/js/run_pytest.test.js`**: Unit test suite verifying candidate priority, venv resolution, POSIX fallback, and CLI argument forwarding.

### Task 2: Architecture Hygiene & Legacy UI Relocation
- **Moved `dashboard.html` -> `legacy/dashboard.html`**: Cleaned up the 1.3 MB single-file export from repo root.
- **Added `legacy/README.md`**: Clarified that `legacy/dashboard.html` is a legacy self-contained snapshot, while `web/index.html` served by `web_server.py` is the live web platform.
- **Updated Scripts & Configs**: Updated `build_interactive_ui.py`, `view_ui.bat`, and `README.md` to point to `legacy/dashboard.html`.
- **Added Regression Test**: `test_legacy_dashboard_location` in `tests/test_smoke.py`.

### Task 3: Multi-Scale Tile Pyramid Engine
- **Added `tile_pyramid.py`**: Zero-dependency multiscale raster pyramid module generating $z = 0..\text{maxZ}$ levels with $256\times 256$ tiles.
  - Continuous layers (DEM, slope, roughness, score): $2\times 2$ block `nanmean` downsampling preserving valid edges.
  - Categorical layers (Hazard, PSR): Safety-preserving downsampling where Unsafe (3) overrides Shadowed (4) overrides Caution (2) overrides Safe (1), preventing hazard erasure at coarse zoom.
  - Edge padding: Padded with NoData (NaN or 0) without stretching.
  - Thread-safe LRU caching (`TilePyramidCache`).
- **Added API Endpoints in `web_server.py`**:
  - `GET /api/tiles/<layer>/<z>/<x>/<y>`: Serves raw binary Float32 / Uint8 tile chunks with proper caching and 404/400 validation.
  - `GET /api/tiles/<layer>/meta`: Returns `{ tileSize: 256, maxZ, width, height, dtype, tiles_x, tiles_y }`.
  - Cache invalidation hooked into `load_raster_cache()`, `handle_api_recalculate()`, and `handle_api_select_site()`.
- **Added Tile Pyramid Export**: `export_tile_pyramid()` in `export_web_data.py`.
- **Added Frontend Integration**: Client pyramid fetcher in `web/app.js` activating for rasters $> 1000\text{ px}$.
- **Added Tests**: `tests/test_tile_pyramid.py` (7 tests) and endpoint tests in `tests/test_phase4_apis.py`.

### Task 4: Accessibility & Keyboard Ergonomics (WCAG 2.1 AA)
- **Aria-Live Region**: Added `#a11yLiveAnnouncer` (`aria-live="polite"`) with debounced `announceA11y(msg, delay)` streaming pixel inspector coordinates and real-time recalculation deltas (e.g. `"Recalculation: Safe area 12.4 km², down 0.80 km² from baseline."`).
- **2D Canvas Ergonomics**: `#mapCanvas` upgraded with `tabindex="0"`, `role="application"`, `aria-label`, `aria-describedby="mapCanvasSummary"`, and full keyboard navigation:
  - Arrow keys: Pan viewport.
  - `+` / `-`: Zoom in / out.
  - `Shift` + Arrows: Step pixel inspector 1 cell with live speech readout.
  - `Enter`: Pin inspector reticle.
  - `Escape`: Clear inspector reticle.
  - `[` / `]`: Cycle visible map layers with speech readout.
- **3D Topography Ergonomics**: `#threeCanvas` upgraded with `tabindex="0"`, `role="application"`, `aria-label`, `aria-describedby="threeCanvasSummary"`, and controls:
  - Arrow keys: Orbit camera azimuth and polar angle.
  - `+` / `-`: Camera distance zoom.
  - `Q` / `E`: Rotate solar grazing azimuth ($15^\circ$ steps) with live announcement.
  - Dynamic text alternative `#threeCanvasSummary` & `#threeA11yStatus`.
- **Navigation Rail Roving Tabindex**: Keyboard arrow navigation on `#mainTabList` tabs with `role="tablist"`, `role="tab"`, `aria-selected`, and `tabindex="0"` / `"-1"`.
- **Shortcuts Modal**: Accessible dialog `#shortcutsDialog` triggered by `?` or footer button, dismissible with `Escape`.
- **Non-Color Hazard Legend**: Augmented hazard classes with symbols (`✓`, `▲`, `✕`, `☾`, `⊘`) and explicit textual status badges.
- **Prefers-Reduced-Motion**: Motion preference query honored in CSS and Three.js orbit controls.
- **Added Tests**: `tests/js/a11y.test.js` (5 unit tests).

### Task 5: Zero-CLS Font Metric Optimization
- **Non-Blocking Font Swapping**: Added `&display=swap` to Google Fonts URL in `web/index.html` with preconnect to `fonts.googleapis.com` and `fonts.gstatic.com` (crossorigin) and stylesheet preloading.
- **Derived Fallback `@font-face` Rules**: Configured metric overrides in `web/styles.css` matching target OpenType table ratios:
  - `Inter Fallback`: Arial with `size-adjust: 107%`, `ascent-override: 90%`, `descent-override: 22.5%`, `line-gap-override: 0%`.
  - `Outfit Fallback`: Arial with `size-adjust: 102%`, `ascent-override: 98%`, `descent-override: 25%`, `line-gap-override: 0%`.
  - `JetBrains Mono Fallback`: Courier New / monospace with `size-adjust: 98%`, `ascent-override: 96%`, `descent-override: 26%`, `line-gap-override: 0%`.
- **Dimension Reservations**: Added strict `min-height` and `box-sizing: border-box` to header (`48px`), navigation rail (`64px`), tab container (`42px`), tab buttons (`38px`), KPI boxes (`58px`), KPI chips (`18px`), and large value labels (`24px`). Preserved `font-variant-numeric: tabular-nums`.
- **Empirical CLS Verification**: Added `scripts/measure-cls.js` and `tests/js/cls_font.test.js`, demonstrating Cumulative Layout Shift reduction from $0.0061$ (with up to $15.5\text{px}$ drift) down to $0.0001$ ($< 0.01$ zero-reflow grade).

### Task 6: 3D Model Blue Lines Alignment & Synthetic Demo Removal
- **3D Raised PSR Outlines Alignment Across All Models**:
  - Identified root cause of floating/detached cyan crater rings on non-LOLA models: on site switch, `web_server.py` did not vectorize the selected site's PSR mask, leaving stale `lola_crop` coordinates in `outputs/psr_polygons.geojson`.
  - Added on-the-fly PSR vectorization in `handle_api_select_site()` (`web_server.py`) so `config.OUTPUT_PSR_POLYGONS_GEOJSON` matches the active site's geographic coordinates, CRS, and transform.
  - Added spatial bounds validation in `buildPsrOutlines3d()` and `drawPsrPolygonsOverlay()` (`web/app.js`): discards any ring whose vertices fall outside the active terrain bounds `[-2, w + 2]` and `[-2, h + 2]`.
  - NASA LOLA (`lola_crop`) remains 100% undisturbed and continues rendering its verified PSR rings directly on its crater floors.
- **Rover 3D Route Terrain Conformance**:
  - Replaced hardcoded formula `(wp.elevation_m / 35.0) + 2.5` with terrain-accurate scaling `(elev - terrainMinElev) * terrainVertScale * exag + 2.2` and horizontal bounds `u * terrainWorldW`, `v * terrainWorldH`.
  - The traverse line now hovers stably +2.2 units above the 3D terrain surface across all models (Mons Mouton, Peak near Cabeus B, Slater Plain, Nobile Rim 2, etc.), eliminating ground clipping and void floating.
  - Connected `updateRover3DPath()` to `update3dExaggeration()` so traverse route scales with vertical exaggeration slider adjustments.
- **Synthetic Demo Model Removal**:
  - Removed `<option value="synthetic">Synthetic Benchmark Crater</option>` from `#lunarSiteSelector` in `web/index.html`.
  - Removed `#cardSynthetic` ("Synthetic Calibration Benchmark Crater") from the dataset ingestion interface.
  - Changed default header badge from `SYNTHETIC DEMO` to `REAL NASA LOLA` (`badge-connected`).
  - Set `ACTIVE_SITE_ID = "lola_crop"` as default in `web_server.py` and `let activeDataset = 'lola';` in `web/app.js`.
  - Excluded `synthetic` from `lunar_catalog.get_catalog_summary()` while preserving all real NASA LOLA and Artemis candidate regions (`lola_crop`, `artemis_haworth`, `artemis_malapert_massif`, `artemis_mons_mouton`, `artemis_nobile_rim_2`, `artemis_slater_plain`, `artemis_peak_cabeus_b`, `shackleton`, `malapert`, `faustini`, `nobile`).
- **Added Tests**:
  - `tests/test_model_selection_and_psr.py` (5 tests): Verifies default site is `lola_crop`, synthetic is excluded from catalog summary and HTML, all real models are preserved, and LOLA and Artemis site PSR polygons fall strictly within their own raster footprints.
### Task 7: Premium Vector Icon Integration & Complete Emoji Elimination
- **Integrated Offline Lucide Icon System**:
  - Installed vendor bundle `web/vendor/lucide.min.js` (zero runtime npm backend dependency, served locally via `web_server.py` `/vendor/`).
  - Added dedicated styling rules in `web/styles.css` for `.lucide` and `[data-lucide]`, tuning vector sizing, aspect ratios, stroke widths (1.75 - 2px), and aerospace cyan accents for navigation, buttons, cards, headers, and inspector toolbars.
  - Implemented `initLucideSystem()` with automatic DOM `MutationObserver` in `web/app.js` to automatically rehydrate vector icons as tabs, dialogs, tour steps, and dynamic artifact cards are mounted.
- **Eradicated All Emojis Across Entire Web Application**:
  - Replaced all emojis in `web/index.html` across navigation rail, header action buttons, quick presets, 2D studio toolbars, 3D topography controls, candidate screening, telemetry cards, and shortcuts dialog with semantic Lucide vector icons (`moon`, `satellite`, `map`, `orbit`, `bar-chart-3`, `target`, `navigation`, `database`, `archive`, `sliders`, `award`, `activity`, `zap`, `check-circle-2`, `play`, `download`, `eye`, `plus`, `minus`, `rotate-ccw`, `crosshair`, `shield-check`, etc.).
  - Replaced all emojis in `web/app.js` (tour banner steps, log prefixes, toast notifications, artifact type icons, artifact cards).
  - Cleaned all non-color hazard legend symbols and fallback cards in `web/styles.css`.
  - Replaced unicode character close buttons with sleek `<i data-lucide="x"></i>` and info indicators with `<i data-lucide="info"></i>`.
- **Added Automated Verification**:
  - Added `tests/js/lucide_icons.test.js` verifying:
    1. Lucide vendor bundle exists and is loaded in `web/index.html`.
    2. Lucide initialization and DOM mutation observer exist in `web/app.js`.
    3. Proper CSS tokens and stroke-width rules exist in `web/styles.css`.
    4. Exact regular-expression scan asserts **0 emojis remain** across `web/index.html`, `web/styles.css`, and `web/app.js`.

### Task 8: Interactive 3D Moon Site Navigator & Pop-Up 3D Reconnaissance View
- **Global 3D Moon Site Interactivity**:
  - Transformed the 3D Moon globe from a passive background visual into an active **Planetary Site Navigator**.
  - Enriched `renderArtemisMarkers()` in `web/lunar_moon.js` with complete catalog coverage (`nobile`, `lola_crop`, all Artemis candidate down-select regions, landmarks, and candidate landing sites Alpha/Beta/Gamma).
  - Hovering over any site dot shows coordinate telemetry and prompt: `Click to inspect 3D site topography model`.
  - Clicking any site dot smoothly focuses the Moon sphere on the location and immediately opens the dedicated 3D Site Reconnaissance pop-up view.
- **Embedded 3D Topography Mesh Pop-Up View**:
  - Built `#siteInspectionModal` in `web/index.html` with an aerospace HUD layout:
    - **Interactive Three.js 3D Topographic Mesh Viewport**: Renders the exact 3D elevation surface and crater relief of the clicked site. Features OrbitControls (drag to orbit, scroll to zoom, shift-drag to pan), auto-orbit spin toggle, wireframe topology toggle, vertical exaggeration control (1.0x to 5.0x), and solar grazing illumination angle control.
    - **Reconnaissance Dossier & Scientific Metrics Grid**: Displays site diameter, total relief elevation, mean slope, cryogenic PSR cold-trap percentage, solar illumination visibility, and landing safety suitability score.
    - **One-Click Mission Command Activation**: "Set as Active Mission Terrain Model" immediately switches the active site model platform-wide (`onLunarSiteChange`), updating 2D Studio, 3D Mesh Studio, and Rover Traverse.
    - Quick transition buttons: "Open in 3D Studio" and "Open in 2D Studio".
- **Backend High-Speed 3D Preview API**:
  - Added `GET /api/site-preview?site_id=...` in `web_server.py`:
    - Generates downsampled, lightweight 3D DEM grids with exact geodetic relief, mean slope, and cold-trap distribution.
    - Thread-safe memory caching provides `< 1ms` subsequent response times.
- **Added Automated Verification**:
  - Added `tests/test_site_preview.py` (3 unit tests) verifying API response schema, DEM array validity, relief calculation, and caching.
  - Added `tests/js/site_inspection.test.js` (4 unit tests) verifying modal DOM structure, CSS tokens, JS 3D mesh engine methods, and marker telemetry enrichment.

