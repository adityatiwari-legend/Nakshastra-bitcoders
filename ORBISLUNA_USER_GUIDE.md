# OrbisLuna: Team User Guide & Operational Manual
## Autonomous Lunar South Pole PSR Mapping, Surface Hazard Classification & Rover Traverse System

---

## 📋 Executive Overview

**OrbisLuna** (formerly *LunaSafe*) is an autonomous, geodetically rigorous terrain intelligence and mission control system designed for Artemis-era lunar South Pole ($80^\circ\text{S} - 90^\circ\text{S}$) missions. 

The platform solves the critical landing and surface mobility challenges facing lunar surface missions:
1. **Permanently Shadowed Regions (PSRs)**: Delineating cryogenic cold-traps where volatile water ice ($\text{H}_2\text{O}$) is preserved, while safeguarding landers from touchdown in uncharacterized darkness.
2. **Deterministic Hazard Classification**: Enforcing a strict 4-class taxonomy:
   - **Class 1 (Safe)**: Slopes $< 5^\circ$, roughness $< 0.8\text{ m}$, hazard score $< 0.25$.
   - **Class 2 (Caution)**: Moderate slopes $5^\circ - 10^\circ$ or intermediate roughness.
   - **Class 3 (Unsafe)**: Slopes $\ge 10^\circ$, roughness $\ge 2.0\text{ m}$, score $\ge 0.45$, or PSR interior for landers.
   - **Class 4 (Shadowed-Unknown)**: Cold-trap shadows requiring rover surface prospecting.
   - **Class 0 (NoData)**: Void / space pixels, strictly barred from safety claims.
3. **Autonomous Landing Site Selection (ALSS)**: Automated identification and ranking of top Artemis landing zones (**Site Alpha**, **Site Beta**, **Site Gamma**) with a mandatory $\ge 40\text{ m}$ standoff clearance buffer.
4. **Autonomous Rover Optimal Traverse Planning**: Multi-objective 8-connected kinematic routing incorporating Bekker terramechanics, slope resistance, battery State-of-Charge (SoC) management, and volatile ice sampling sortie targeting.
5. **Multi-Site Lunar Catalog**: Standardized support for primary Artemis candidate zones (Shackleton Crater, Malapert Mountain, Faustini Basin, Nobile Rim VIPER site, and synthetic validation models).

---

## 🚀 Quickstart Guide for the Team

### 1. System Requirements & Environment
- **Operating System**: Windows 10/11, Linux, or macOS.
- **Python**: Version 3.10, 3.11, 3.12, or 3.13.
- **Dependencies**: Listed in [requirements.txt](file:///d:/OribsLuna/ORBISLUNA-kush/requirements.txt) (`rasterio`, `numpy`, `scipy`, `geopandas`, `matplotlib`, `pytest`).

If using an active virtual environment:
```powershell
# Windows PowerShell
.venv\Scripts\activate
```

---

### 2. Launching Mission Control (Web Platform)

The web dashboard runs a lightweight multithreaded Python HTTP/REST backend and an accelerated client-side frontend (2D Canvas compositing + 3D WebGL mesh viewer).

#### Option A: One-Click Launch (Windows)
Double-click [run_website.bat](file:///d:/OribsLuna/ORBISLUNA-kush/run_website.bat) in File Explorer or run:
```cmd
run_website.bat
```
*This launches the server and automatically opens [http://localhost:8050](http://localhost:8050) in your default web browser.*

#### Option B: Terminal Command
```bash
python web_server.py
```
*(If port `8050` is already in use, the server automatically fails over to port `8080`).*

---

### 3. Headless Pipeline Execution (CLI Batch Processing)

To run the complete 8-phase geospatial and routing pipeline without opening the browser:
```bash
python main.py
```

#### What `main.py` executes:
- **Phase 1**: Ingests and geodetically aligns Lunar DEM and PSR rasters.
- **Phase 2**: Delineates PSR boundaries and exports GeoTIFF, GeoJSON, and Shapefiles.
- **Phase 3**: Calculates Topographic Slope, Compass Aspect, Roughness (Std Dev), and Riley TRI.
- **Phase 4**: Classifies surface landing hazards into Classes 0–4 and exports `outputs/hazard_summary.csv`.
- **Phase 5**: Generates publication-grade 300 DPI 4-panel cartographic maps (`outputs/lunasafe_hazard_map.png` & `.pdf`).
- **Phase 6**: Runs the 9-point rule consistency audit and slope-threshold sensitivity simulation.
- **Phase 7**: Runs Autonomous Landing Site Selection (ALSS) and Boulder Micro-Hazard AI.
- **Phase 8**: Computes the optimal rover traverse sortie from Site Alpha into the adjacent PSR cold trap and saves `outputs/rover_traverse.json`.
- **Sync**: Automatically bundles all outputs into `outputs/web_data.json` for immediate web dashboard consumption.

#### Command-Line Flags:
```bash
# Force synthetic benchmark mode
python main.py --synthetic

# Strict grid validation (fails if DEM and PSR raster geometries differ)
python main.py --fail-on-mismatch

# Quiet mode (suppresses verbose engineering logs)
python main.py --quiet
```

---

## 🚜 New Feature: Rover Traverse Studio (`rover_router.py`)

The Rover Traverse Engine models physical rover dynamics on lunar regolith:

### 1. Physical & Terramechanic Principles
- **8-Connected Grid Search**: Evaluates cardinal ($d = \Delta x$) and diagonal ($d = \sqrt{2}\Delta x$) transitions.
- **Slope Resistance Multiplier (Bekker Terramechanics)**:
  $$\text{Multiplier} = 1.0 + w_{\text{slope}} \cdot \left(\frac{\theta_{\text{slope}}}{\theta_{\text{max}}}\right)^{1.8}$$
  Uphill traverses penalize motor torque non-linearly. Downhill traverses apply braking control stabilization.
- **Hard Slope Barrier**: Any micro-slope $\ge 18.0^\circ$ is strictly impassable to prevent static roll-over or wheel entrapment.
- **Cliff Clearance Buffer**: Cells within $40\text{ m}$ of impassable cliffs or NoData voids receive an exponential hazard avoidance penalty.
- **Cryogenic Shadow Excursion**: Tracks traversal in darkness where solar power is zero and survival heaters consume extra power.
- **Battery SoC Modeling**:
  - Solar array charging in illumination: $+250\text{ W}$
  - Motor driving load: $-120\text{ W}$
  - Survival heating load in shadow: $-80\text{ W}$
  - Total battery capacity: $2000\text{ Wh}$ ($2.0\text{ kWh}$)

### 2. Using the Rover Studio in Web Mission Control
1. Click the **🚜 Rover Traverse Studio** tab on the navigation bar.
2. In the left panel, inspect the precomputed traverse from **Site Alpha** to the primary volatile cold-trap target.
3. **Interactive Waypoint Selection**:
   - Click **📍 Pick Start Point on Map**, then click anywhere on the 2D map to set the rover deployment point.
   - Click **🎯 Pick Destination on Map**, then click your target exploration point.
   - Adjust parameters: **Max Climb Slope** (e.g. $18^\circ$), **Slope Weight**, **Roughness Weight**, and **Rover Speed**.
   - Click **⚡ Recompute Optimal Rover Route**.
4. **Visualizations**:
   - **2D Map**: Glowing green/cyan traverse path with start and goal radar markers.
   - **3D WebGL**: Draped 3D mobility vector across crater rims and slopes.
   - **Elevation Profile Chart**: Interactive canvas cross-section displaying elevation ($m$), slope gradients ($^\circ$), and shadow intervals.
   - **Waypoints Table**: Detailed step-by-step telemetry (easting, northing, elevation, slope, battery SoC %, cumulative distance).

---

## 🌙 New Feature: Multi-Site Lunar Catalog (`lunar_catalog.py`)

OrbisLuna now provides georeferenced polar models for key exploration sites:

| Site ID | Site Name | Latitude / Coordinates | Description & Exploration Value |
| :--- | :--- | :--- | :--- |
| `shackleton` | Shackleton Crater Rim | $89.9^\circ\text{S}, 0.0^\circ\text{E}$ | Artemis III primary landing candidate; permanent ridge sunlight adjacent to deep volatile cold-traps. |
| `malapert` | Malapert Mountain (Peak) | $84.9^\circ\text{S}, 12.9^\circ\text{E}$ | High elevation peak offering uninterrupted Direct-To-Earth (DTE) communication lines. |
| `faustini` | Faustini Crater Basin | $87.3^\circ\text{S}, 77.0^\circ\text{E}$ | Enclosed impact basin with extensive low-temperature volatile deposits. |
| `nobile` | Nobile Crater Rim | $85.2^\circ\text{S}, 53.5^\circ\text{E}$ | NASA VIPER rover traverse target; accessible slope corridors into shadow. |
| `synthetic` | Synthetic Benchmark Crater | $89.5^\circ\text{S}, 0.0^\circ\text{E}$ | Deterministic mathematical crater model for unit testing and sub-pixel calibration. |
| `lola_crop` | NASA LRO LOLA South Pole | $80.0^\circ\text{S} - 90^\circ\text{S}$ | Full-scale $60\text{ km} \times 60\text{ km}$ NASA LOLA altimetry tile ($240\text{ m/px}$). |

### How to Switch Sites:
- **In Web Mission Control**: Use the **Lunar Model Selector** dropdown in the top header. The server instantly reloads the terrain, updates the 2D/3D map, recalculates landing zones, and refreshes telemetry.
- **Via REST API**:
  ```bash
  curl -X POST http://localhost:8050/api/select-site \
       -H "Content-Type: application/json" \
       -d "{\"site_id\": \"shackleton\"}"
  ```

---

## 🛠️ Core Scientific & Mathematical Fixes Implemented

The following issues were audited and resolved:

1. **Audit Key Consistency (Issue I-03)**:
   - Unified validation key naming: `web_server.py` and `validate.py` now check `rule4_safe_pixel_in_psr` (with fallback to `rule4_safe_in_psr`), ensuring zero rule violations across both CLI and Web.
2. **Dynamic Pixel Scale Resolution (Issue I-02)**:
   - `/api/recalculate` and `/api/transect` now derive true ground sampling distance from the GeoTIFF Affine transform matrix ($240.0\text{ m}$ for real LOLA, $20.0\text{ m}$ for synthetic) rather than hardcoding $20.0\text{ m}$.
3. **True Standoff Landing Clearance (Issue I-05)**:
   - In `ml_recommender.py`, minimum standoff distance is now calculated as:
     $$\text{Clearance Radius} = R_{\text{ellipse}} + R_{\text{buffer}} = 100\text{ m} + 40\text{ m} = 140\text{ m}$$
     Guaranteeing the entire landing dispersion footprint remains safe from hazard borders.
4. **Data Bundle Auto-Sync**:
   - `main.py` automatically invokes `export_web_data.export_data_bundle()` upon pipeline completion, keeping `outputs/web_data.json` synchronized without manual exports.

---

## 🌐 Web Mission Control Layout

```
+---------------------------------------------------------------------------------------------------+
|  [OrbisLuna Mission Control]   [Site: Shackleton Crater v]   [NASA LOLA / SYNTHETIC]   [60s Tour] |
+---------------------------------------------------------------------------------------------------+
|  Navigation Tabs:                                                                                 |
|  [2D Geospatial Studio]  [3D WebGL Mesh]  [🚜 Rover Traverse Studio]  [Recalculate]  [Validation] |
+---------------------------------------------------------------------------------------------------+
|                                 |                                                                 |
|  MAP VIEWPORT / 3D CANVAS       |  TELEMETRY & INSPECTOR DOCK                                     |
|                                 |                                                                 |
|  - 2D Canvas compositing        |  - Coordinates: (Easting, Northing, Lat/Lon)                    |
|  - 3D WebGL elevation drape     |  - Slope, Aspect, Roughness (TRI / Std)                         |
|  - Dynamic Sun angle slider     |  - Hazard Classification & Plain-Language Override Reason       |
|  - Elevation transect tool      |  - Top 3 Landing Ellipses (Alpha, Beta, Gamma)                  |
|  - Rover route draping          |  - Rover Traverse Stats (km, hrs, Battery SoC %)                |
|                                 |                                                                 |
+---------------------------------------------------------------------------------------------------+
```

---

## 📡 REST API Reference

The embedded HTTP server exposes REST endpoints for automated integration:

| Method | Endpoint | Request Body | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/dataset` | None | Returns the complete serialized mission data bundle (`web_data.json`). |
| `GET` | `/api/sites` | None | Returns list of available lunar site models and currently active site. |
| `POST` | `/api/select-site` | `{"site_id": "shackleton"}` | Switches active terrain model, recomputes metrics, and updates cache. |
| `POST` | `/api/rover-route` | `{"start": [c, r], "goal": [c, r], ...}` | Computes optimal rover path, battery SoC, and step waypoints. |
| `GET` | `/api/psr-targets` | None | Returns ranked water ice sampling candidate locations inside PSRs. |
| `POST` | `/api/recalculate` | `{"slope_safe": 5.0, ...}` | Live client-side hazard reclassification with updated thresholds. |
| `POST` | `/api/transect` | `{"x1": 10, "y1": 10, "x2": 50, "y2": 50}` | Returns elevation profile transect between two points. |
| `GET` | `/api/audit-summary` | None | Returns results of the 9-point rule consistency audit. |
| `GET` | `/download?file=...` | Query param: `file=<name>` | Downloads output GeoTIFFs, Shapefiles, JSONs, or full ZIP bundle. |

---

## 🧪 Automated Verification & Test Suite

OrbisLuna maintains a comprehensive **37-test automated verification suite** with 100% pass rate:

```bash
# Run the entire test suite
python -m pytest -v

# Run only rover router tests
python -m pytest tests/test_rover_router.py -v

# Run only hazard classification tests
python -m pytest tests/test_hazard.py -v
```

### Test Coverage Summary:
- **`test_rover_router.py` (5 tests)**: Verifies A* obstacle avoidance around cliffs, impassability of $\ge 18^\circ$ slopes, battery SoC discharge curves, and PSR volatile target detection.
- **`test_hazard.py` (6 tests)**: Verifies deterministic hard overrides, Class 4 separation, NoData exclusion, and continuous score normalization.
- **`test_terrain.py` (4 tests)**: Verifies Horn's slope algorithm exactness on mathematical ramps, aspect calculation, and roughness std/TRI.
- **`test_ml_recommender.py` (3 tests)**: Verifies landing site ellipse selection, $40\text{ m}$ clearance buffer enforcement, and boulder bandpass filtering.
- **`test_preprocessing.py` (4 tests)**: Verifies IAU 2015 Lunar CRS protection, anti-Earth datum checks, and grid mismatch detection.
- **`test_psr.py` (5 tests)**: Verifies PSR binarization, speckle filtering, polygon vectorization, and geodesic area calculations.
- **`test_validate.py` (4 tests)**: Verifies the 9-point consistency auditor and slope sensitivity analyses.
- **`test_main.py` & `test_smoke.py` (6 tests)**: Verifies end-to-end headless pipeline execution and configuration integrity.

---

## 📂 Deliverables & Output Artifacts

All pipeline outputs are automatically generated in the [outputs/](file:///d:/OribsLuna/ORBISLUNA-kush/outputs) directory:

| Artifact | Format | Description |
| :--- | :--- | :--- |
| `outputs/psr_binary.tif` | GeoTIFF | Binarized Permanently Shadowed Region mask. |
| `outputs/psr_polygons.geojson` | GeoJSON | Vector polygons of delineated PSR cold traps. |
| `outputs/psr_polygons.shp` | Shapefile | ESRI Shapefile package of PSR boundary vectors. |
| `outputs/slope_deg.tif` | GeoTIFF | High-resolution topographic slope in degrees ($0^\circ - 90^\circ$). |
| `outputs/aspect_deg.tif` | GeoTIFF | Compass aspect raster in degrees ($0^\circ - 360^\circ$ from North). |
| `outputs/roughness_std_m.tif` | GeoTIFF | Elevation standard deviation roughness in meters. |
| `outputs/roughness_tri_m.tif` | GeoTIFF | Riley Terrain Ruggedness Index (TRI) in meters. |
| `outputs/terrain_histograms.png` | 300 DPI PNG | 4-panel distribution histograms for slope, aspect, and roughness. |
| `outputs/hazard_classes.tif` | GeoTIFF | Classified surface hazard map (Classes 0, 1, 2, 3, 4). |
| `outputs/hazard_summary.csv` | CSV | Tabular summary of pixel counts, area ($\text{km}^2$), and valid %. |
| `outputs/lunasafe_hazard_map.png` | 300 DPI PNG | Publication-grade 4-panel cartographic figure with scale bars. |
| `outputs/lunasafe_hazard_map.pdf` | Vector PDF | Archival publication-grade cartographic figure. |
| `outputs/slope_sensitivity.png` | 300 DPI PNG | Sensitivity analysis curves for slope thresholds ($3^\circ, 5^\circ, 7^\circ, 10^\circ, 15^\circ$). |
| `outputs/landing_sites.json` | JSON | Telemetry for top recommended Artemis landing sites (Alpha, Beta, Gamma). |
| `outputs/boulder_hazard.tif` | GeoTIFF | High-frequency sub-meter boulder anomaly probability surface. |
| `outputs/rover_traverse.json` | JSON | Optimal rover route waypoints, slope profile, and battery SoC timeline. |
| `outputs/web_data.json` | JSON | Serialized multi-layer data bundle powering the Mission Control dashboard. |

---

## 🔒 Team Rules & Contribution Guidelines
- **Git Commit Rule**: Never execute `git commit` without explicit permission from the mission lead.
- **Geodetic Standard**: All rasters must remain in Moon Polar Stereographic (`IAU 2015 Sphere R=1,737,400m`). Terrestrial datums are strictly forbidden.
- **Truth in Cartography**: Published masks are baselines, not predictions. Never display synthetic accuracy numbers without clear provenance labeling.
