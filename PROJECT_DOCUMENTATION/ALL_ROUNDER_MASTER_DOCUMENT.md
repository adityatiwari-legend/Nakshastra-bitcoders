# LunaSafe: The Complete All-Rounder Project Master Guide
*From Scratch to Advanced Lunar Science, Architecture, Features, and 2-Developer Engineering Roadmap*

---

## Table of Contents
1. [Executive Summary & Project Mission](#1-executive-summary--project-mission)
2. [From Scratch: Core Lunar & GIS Concepts Explained](#2-from-scratch-core-lunar--gis-concepts-explained)
3. [System Architecture & Execution Paths](#3-system-architecture--execution-paths)
4. [Complete Feature Catalog & Scientific Significance](#4-complete-feature-catalog--scientific-significance)
5. [Codebase & Module Deep Dive](#5-codebase--module-deep-dive)
6. [Data Model, File Formats & Geodetic Standards](#6-data-model-file-formats--geodetic-standards)
7. [REST API Reference & Web Architecture](#7-rest-api-reference--web-architecture)
8. [Setup, Execution & Testing Handbook](#8-setup-execution--testing-handbook)
9. [Transparent Technical Audit: Known Issues & Fixes](#9-transparent-technical-audit-known-issues--fixes)
10. [2-Developer Comprehensive Engineering Roadmap](#10-2-developer-comprehensive-engineering-roadmap)

---

# 1. Executive Summary & Project Mission

### 1.1 What is LunaSafe?
**LunaSafe** is an autonomous lunar landing site characterization and hazard evaluation engine designed specifically for the extreme conditions of the **Lunar South Pole (80°S – 90°S)**. 

When landing a spacecraft near the lunar south pole, mission planners face a lethal paradox:
1. **The Scientific Prize:** Permanently Shadowed Regions (PSRs) inside deep impact craters have remained in pitch-black darkness for billions of years, acting as cold traps that store vast deposits of water ice and volatile compounds essential for future human exploration and rocket propellant.
2. **The Operational Trap:** Spacecraft need sunlight for solar power, optical navigation, and thermal survival. Landing inside darkness, on steep crater walls, or on boulder-strewn ground leads to mission loss.

LunaSafe processes Digital Elevation Models (DEMs) and shadow masks to evaluate every single pixel of the lunar terrain across three physical dimensions:
- **Slope:** How steep is the incline?
- **Roughness:** How bumpy or boulder-strewn is the local topography?
- **Illumination:** Is the terrain in permanent shadow?

From these inputs, LunaSafe synthesizes an objective, deterministic 5-class safety verdict surface, pinpoints the top 3 optimal landing ellipses with safe clearance buffers, and generates publication-grade cartography, interactive 3D WebGL visualizations, and mission briefings.

### 1.2 Two Non-Negotiable Core Philosophies
Every line of code in LunaSafe is governed by two fundamental principles:

1. **Geodetic Honesty (Lunar Truth):**
   The Moon is not Earth. Terrestrial GIS software frequently defaults to Earth datums (WGS84, EPSG:4326), which distort lunar surface distances by thousands of kilometers. LunaSafe strictly enforces a lunar coordinate reference system based on a spherical Moon of radius **$R = 1,737,400\text{ meters}$**. Any ingested dataset containing Earth coordinate reference system strings is actively rejected.

2. **Never Call Darkness Safe (The Class 4 Innovation):**
   Classical terrain classifiers treat flat ground as "safe" regardless of illumination. But at the lunar south pole, unilluminated terrain cannot be visually verified by lander cameras and offers no solar power. LunaSafe introduces **Class 4: Shadowed-Unknown**. If a patch of ground inside a PSR is flat, LunaSafe refuses to label it safe; it classifies it as unknown, preventing catastrophic false confidence.

---

# 2. From Scratch: Core Lunar & GIS Concepts Explained

For any developer or newcomer joining the project, here are the essential building blocks explained in plain English:

### 2.1 Raster vs. Vector Data
- **Raster:** Think of a raster as a digital image, but instead of red/green/blue pixels, each pixel stores a scientific physical measurement (such as surface elevation in meters, slope in degrees, or hazard class). Rasters are stored as **GeoTIFF (`.tif`)** files.
- **Vector:** Instead of a grid of pixels, vectors represent geographic boundaries using mathematical coordinates (points, lines, polygons). LunaSafe extracts the vector outlines of PSRs and exports them as **GeoJSON (`.geojson`)** and **ESRI Shapefiles (`.shp`)**.

### 2.2 Digital Elevation Model (DEM)
A DEM is a 2D raster grid where every pixel value $z$ represents the exact height of the lunar surface in meters relative to the lunar reference radius (1,737.4 km). For example, a pixel value of `-2500.0` means the ground sits 2.5 kilometers below the mean lunar radius.

### 2.3 Permanently Shadowed Regions (PSRs)
Because the Moon’s rotational axis has a tiny tilt of only 1.54° relative to the ecliptic plane, the Sun always skims low across the horizon at the lunar poles. Deep crater floors never see direct sunlight. These regions are called PSRs.

### 2.4 Coordinate Reference System (CRS) & Polar Stereographic Projection
To convert 2D grid pixels into accurate physical meters on the ground without distorting distances at the poles, LunaSafe utilizes the **Moon South Pole Polar Stereographic projection** (`+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs`). This maps the 3D spherical Moon onto a flat plane centered at the South Pole ($90^\circ\text{S}$).

### 2.5 NoData Sentinel (`-9999.0`)
Satellite instruments frequently miss pixels due to orbital gaps or sensor occlusion. LunaSafe marks these missing pixels with a sentinel value of `-9999.0`. A critical rule of the system is: **NoData must never be treated as valid flat terrain.** It is quarantined into **Class 0**.

### 2.6 The 5 Decision Surface Classes
LunaSafe maps every square meter of analyzed ground into one of five definitive classes:

| Class ID | Class Name | Color Code | Scientific & Operational Meaning |
| :---: | :--- | :---: | :--- |
| **0** | **NoData** | Dark Grey (`#4a4a4a`) | Sensor gaps or missing data. **Never** considered safe. |
| **1** | **Safe** | Bright Emerald Green (`#2ecc71`) | Flat (slope $< 5^\circ$), smooth (roughness $< 1.5\text{ m}$), low hazard score ($H < 0.25$), and fully illuminated. |
| **2** | **Caution** | Amber Gold (`#f39c12`) | Borderline terrain (slope $5^\circ - 15^\circ$ or moderate roughness). Landable with advanced hazard avoidance. |
| **3** | **Unsafe** | Vivid Crimson Red (`#e74c3c`) | Lethal terrain. Steep slopes ($\ge 15^\circ$), extreme roughness ($\ge 5\text{ m}$), or high hazard score ($H \ge 0.60$). Hard veto. |
| **4** | **Shadowed-Unknown** | Deep Cyan/Electric Blue (`#3498db`) | Flat/smooth terrain inside a PSR. Cannot be confirmed safe due to lack of sunlight. |

---

# 3. System Architecture & Execution Paths

LunaSafe is structured as a **two-process, file-mediated, layered monolith**. It offers two complementary interfaces into the identical scientific algorithms:

```
                  ┌───────────────────────────────────────────────┐
                  │                 USER / CLIENT                 │
                  └───────┬───────────────────────────────┬───────┘
                          │                               │
            Headless CLI  │                               │ Browser HTTP
            `python main.py`                              │ `python web_server.py`
                          ▼                               ▼
     ┌────────────────────────────────────┐    ┌───────────────────────────────────┐
     │      HEADLESS BATCH PIPELINE       │    │      MISSION CONTROL CONSOLE      │
     │      (Single-Process Runner)       │    │     (ThreadingHTTPServer :8050)   │
     └─────────────────┬──────────────────┘    └─────────────────┬─────────────────┘
                       │                                         │
                       │ Calls In-Process                        │ Serves UI & API
                       │                                         ▼
                       │                       ┌───────────────────────────────────┐
                       │                       │      BROWSER SINGLE-PAGE APP      │
                       │                       │ (Canvas 2D, Three.js 3D, Sliders) │
                       │                       └─────────────────┬─────────────────┘
                       │                                         │
                       │                                         │ POST /api/recalculate
                       │                                         ▼
                       │                       ┌───────────────────────────────────┐
                       │                       │       IN-MEMORY FAST PATH         │
                       │                       │   (Cached numpy arrays in RAM)    │
                       │                       └─────────────────┬─────────────────┘
                       │                                         │
                       ▼                                         ▼
     ┌─────────────────────────────────────────────────────────────────────────────┐
     │                            CORE DOMAIN MODULES                              │
     │                                                                             │
     │   io_utils.py       psr.py        terrain.py      hazard.py                 │
     │   [Data & CRS]   [Shadow Mask]   [Slope & TRI]   [Classification]           │
     │                                                                             │
     │   mapping.py       validate.py     ml_recommender.py   mission_report.py    │
     │   [Cartography]   [Rule Auditor]    [ALSS & Boulders]    [PDF Synthesis]    │
     └──────────────────────────────────────┬──────────────────────────────────────┘
                                            │ Writes & Reads
                                            ▼
     ┌─────────────────────────────────────────────────────────────────────────────┐
     │                            PERSISTENT ARTIFACTS                             │
     │                                                                             │
     │   data/                            outputs/                                 │
     │   ├── synthetic_dem.tif            ├── hazard_classes.tif                   │
     │   ├── synthetic_psr.tif            ├── psr_binary.tif & psr_polygons.*     │
     │   ├── lola_south_pole_dem.tif      ├── slope_deg.tif & roughness_std_m.tif │
     │   └── ldem_75s_240m.jp2            ├── landing_sites.json & boulder_*.tif   │
     │                                    ├── lunasafe_hazard_map.png/.pdf         │
     │                                    └── web_data.json & mission_report.pdf   │
     └─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 The Two Execution Paths
1. **Headless Batch Pipeline (`main.py`):**
   - Executed via `python main.py`.
   - Runs a sequential 7-phase execution: Ingestion $\to$ PSR Delineation $\to$ Terrain Characterization $\to$ Hazard Classification $\to$ Cartography $\to$ Validation Audit $\to$ Autonomy.
   - Outputs 15 verified physical artifacts into `outputs/` and logs full metrics to standard output.
   - Ideal for automated batch processing, headless environments, and continuous testing.

2. **Interactive Mission Control Server (`web_server.py`):**
   - Executed via `python web_server.py` (hosts at `http://localhost:8050`).
   - Loads the primary rasters into an in-memory RAM cache (`RASTER_CACHE`).
   - Exposes REST endpoints allowing mission operators to move sliders (e.g. adjust maximum safe slope from $5^\circ$ to $8^\circ$) and trigger instantaneous in-memory reclassification (<20 ms latency) without re-reading disks.
   - Serves an interactive Single-Page Application (SPA) with a 2D multi-layer inspection studio and a 3D WebGL terrain viewer.

---

# 4. Complete Feature Catalog & Scientific Significance

Every feature in LunaSafe was engineered for a specific operational or scientific purpose. Below is the full feature catalog:

### 4.1 Synthetic Lunar Crater Benchmark Generator (`io_utils.py`)
- **What it does:** Procedurally builds a photorealistic, mathematically exact synthetic lunar impact crater with an elevated rim, realistic depth profiles, power-law ejecta blankets, seeded pseudo-random noise, and a designated PSR disc on the crater floor.
- **Significance:** Real planetary datasets often have gaps or calibration ambiguities. The synthetic generator provides a 100% deterministic, reproducible ground-truth benchmark ($200 \times 200$ pixels at $20\text{ m/pixel}$) that allows unit tests and validation suites to run anywhere without requiring internet access or multi-gigabyte downloads.

### 4.2 Strict Lunar Coordinate & CRS Sentinel (`io_utils.py`)
- **What it does:** Inspects ingested raster metadata and actively intercepts Earth Coordinate Reference Systems. If it detects signatures like `EPSG:4326`, `EPSG:3857`, `WGS 84`, or `WGS_1984`, it halts execution with an explicit `ValueError`.
- **Significance:** Protects mission planners from fatal navigational errors caused by amateur GIS pipelines that mistakenly apply Earth's ellipsoidal geometry to the Moon.

### 4.3 Automated Dual-Raster Grid Alignment (`io_utils.py`)
- **What it does:** Compares the affine transformation matrix, bounding box, shape, and CRS of incoming DEM and PSR rasters. If a mismatch is detected, it automatically re-samples and re-projects the PSR mask onto the DEM grid using nearest-neighbor interpolation.
- **Significance:** Different lunar orbiter instruments (e.g. LOLA laser altimetry vs. LROC optical imaging) capture data at different resolutions and spatial extents. Automated alignment ensures pixel-for-pixel mathematical registration.

### 4.4 Morphological PSR Despeckling & Vectorization (`psr.py`)
- **What it does:** Binarizes the shadow mask, removes noise artifacts smaller than 9 connected pixels (`scipy.ndimage.label`), computes accurate surface area in $\text{km}^2$, and vectorizes continuous shadow regions into GIS-compatible GeoJSON and ESRI Shapefiles.
- **Significance:** Optical shadows often exhibit single-pixel noise spikes. Morphological filtering cleans the boundary edges, and vector polygons enable seamless integration into industry-standard GIS packages (QGIS, ArcGIS).

### 4.5 Horn’s 3×3 Slope & Aspect Calculation (`terrain.py`)
- **What it does:** Implements Horn’s classic finite-difference 3×3 convolution kernel to derive accurate topographic slope (steepness in degrees) and aspect (compass heading of slope face from 0° to 360°).
- **Significance:** Horn’s algorithm applies higher weights to orthogonal neighbors, providing optimal noise suppression on noisy lunar elevation datasets. Slope is the #1 physical constraint on lander stability; slopes $> 15^\circ$ cause spacecraft to tip over upon landing.

### 4.6 Dual Roughness Metrics: Elevation Std-Dev & Riley TRI (`terrain.py`)
- **What it does:** Computes surface roughness through two independent mathematical formulations:
  1. *Local Standard Deviation:* Moving $3 \times 3$ window elevation standard deviation $\sigma_z$, measuring micro-relief variation in meters.
  2. *Terrain Ruggedness Index (TRI):* Riley et al. formulation measuring cumulative absolute elevation differences between the center pixel and all 8 surrounding neighbors.
- **Significance:** Slopes measure macro-inclination, but a flat slope can still be covered in small boulders, furrows, or micro-craters. Roughness quantifies surface texture at the lander footpad scale.

### 4.7 Continuous Hazard Scoring ($H$) & Hard Overrides (`hazard.py`)
- **What it does:** Normalizes slope, roughness, and shadow into $[0, 1]$ indices and computes a composite weighted hazard score:
  $$H = 0.50 \cdot S_{\text{norm}} + 0.30 \cdot R_{\text{norm}} + 0.20 \cdot D_{\text{shadow}}$$
  It then applies non-negotiable hard overrides: any pixel with slope $\ge 15^\circ$ or roughness $\ge 5\text{ m}$ is immediately forced to **Class 3 (Unsafe)** regardless of other attributes.
- **Significance:** Weighted scoring provides a continuous spectrum of risk, while hard overrides ensure that single fatal hazards cannot be masked by favorable scores in other dimensions.

### 4.8 9-Rule Independent Safety Verification Auditor (`validate.py`)
- **What it does:** Re-derives the classification criteria independently and executes a 9-rule formal audit on every single pixel in the output raster:
  1. No valid pixel is left unclassified.
  2. Every Safe pixel has slope $< 5^\circ$.
  3. Every Safe pixel has roughness $< 1.5\text{ m}$.
  4. **No Safe pixel is inside a PSR.**
  5. Every pixel with slope $\ge 15^\circ$ is Unsafe.
  6. Every pixel with roughness $\ge 5\text{ m}$ is Unsafe.
  7. Every pixel with $H \ge 0.60$ is Unsafe.
  8. **No PSR pixel is labeled Safe (enforcing Class 4).**
  9. Every NoData pixel is Class 0.
- **Significance:** Acts as the mission's mathematical safety contract. If any software bug or memory corruption causes a rule violation, the pipeline sounds an alarm.

### 4.9 Autonomous Landing Site Selection (ALSS) (`ml_recommender.py`)
- **What it does:** Uses Euclidean Distance Transforms (EDT) on the safe terrain mask to locate candidate landing ellipses with guaranteed radius clearance ($r = 100\text{ m}$). It ranks candidates using a multi-criteria fitness function:
  $$\text{Fitness} = 0.35 \cdot \text{Clearance} + 0.30 \cdot \text{Flatness} + 0.20 \cdot \text{Smoothness} + 0.15 \cdot \text{ScienceProximity}$$
  where science proximity rewards sites located within a 250-meter walking/traversing distance from a PSR edge.
- **Significance:** Identifies landing sites that maximize lander safety while keeping rover science targets (water ice) within operational traverse distance.

### 4.10 Signal-Processing Micro-Hazard & Boulder Detection (`ml_recommender.py`)
- **What it does:** Applies a 2D Gaussian bandpass filter ($\sigma = 2$) to isolate local high-frequency micro-elevations from the regional macro-topography. Passing the residual z-score through a calibrated sigmoid curve yields a spatial boulder hazard probability raster and identifies discrete boulder coordinates.
- **Significance:** Identifies localized physical obstructions that are smaller than the regional slope trends but large enough to destroy a landing engine or leg.

### 4.11 Multi-Panel Cartography & Hillshade Rendering (`mapping.py`)
- **What it does:** Renders a synchronized 4-panel publication-grade figure (PNG at 300 DPI + vector PDF):
  - Panel A: Shaded relief hillshade with elevation colormap, scale bar, and lunar north arrow.
  - Panel B: Quantitative slope map with $5^\circ, 10^\circ, 15^\circ$ contour overlays.
  - Panel C: PSR shadow mask with vector outlines and calculated area badges.
  - Panel D: 5-class hazard map with explicit color key and coordinate grid.
- **Significance:** Mission directors and scientists require standardized, publication-ready visual artifacts for flight reviews and mission planning meetings.

### 4.12 Interactive Mission Control Console (`web/` & `web_server.py`)
- **What it does:** A browser-based operational dashboard featuring:
  - 2D Canvas Studio with multi-layer overlays (Elevation, Slope, Roughness, PSR, Hazard, Boulders).
  - Split-screen Swipe tool for comparing terrain features.
  - Dynamic Inspector for clicking any coordinate to see pixel-level physical readouts.
  - 3D WebGL Interactive Viewer powered by Three.js with realistic lunar surface meshes, interactive sun-angle simulation, and cross-sectional elevation transects.
- **Significance:** Provides mission teams with an intuitive, dynamic exploration tool for real-time decision-making.

---

# 5. Codebase & Module Deep Dive

The repository is organized cleanly as a flat collection of specialized Python domain modules:

```
LunaSafe/
├── config.py                 # Central configuration: thresholds, paths, colors, CRS strings
├── main.py                   # Master CLI pipeline orchestrator (Phases 1 - 7)
├── io_utils.py               # Raster I/O, CRS validation, synthetic generator, alignment
├── psr.py                    # Shadow binarization, morphological cleaning, vector export
├── terrain.py                # Horn slope, aspect, elevation std-dev roughness, Riley TRI
├── hazard.py                 # Multi-criteria scoring, hard overrides, 5-class generator
├── mapping.py                # 4-panel cartography rendering (hillshade, contours, PDF/PNG)
├── validate.py               # 9-rule formal audit engine, slope sensitivity analysis
├── ml_recommender.py         # Autonomous landing site selection, boulder probability
├── mission_report.py         # Automated multi-page PDF mission brief generator
├── web_server.py             # Threading HTTP server, REST endpoints, in-memory cache
├── export_web_data.py        # Bundles all raster outputs into outputs/web_data.json
├── prepare_lola_dataset.py   # Converts NASA PDS LOLA JP2 files to analysis-ready GeoTIFFs
├── build_interactive_ui.py   # Legacy standalone HTML dashboard builder
├── tests/                    # 32 pytest unit and end-to-end regression tests
│   ├── test_smoke.py
│   ├── test_preprocessing.py
│   ├── test_psr.py
│   ├── test_terrain.py
│   ├── test_hazard.py
│   ├── test_validate.py
│   ├── test_ml_recommender.py
│   ├── test_mapping.py
│   └── test_main.py
├── data/                     # Input datasets (synthetic benchmarks & real LOLA rasters)
├── outputs/                  # Generated products (rasters, vectors, JSON, PDF reports)
└── web/                      # Static web assets (HTML, CSS, JavaScript SPA, Three.js)
```

### 5.1 Pipeline Execution Flow (`main.py`)
When `python main.py` runs, it executes seven strictly ordered phases:

```
[Phase 1: Ingestion & Geodesy]
      │  Checks CRS, validates non-Earth datums, aligns PSR to DEM grid.
      ▼
[Phase 2: PSR Delineation]
      │  Binarizes shadow, filters <9 px noise, extracts polygons, computes km².
      ▼
[Phase 3: Terrain Characterization]
      │  Convolves Horn 3x3 kernels for slope/aspect, computes roughness & TRI.
      ▼
[Phase 4: Hazard Classification]
      │  Evaluates H score, applies 15°/5m overrides, generates 5-class surface.
      ▼
[Phase 5: Cartography Synthesis]
      │  Computes hillshade, renders 4-panel publication map (PNG & PDF).
      ▼
[Phase 6: Invariant Validation Audit]
      │  Executes 9-rule consistency check, runs 5-scenario slope sensitivity.
      ▼
[Phase 7: Autonomous Landing Site Selection]
      │  Calculates distance transforms, ranks top 3 ellipses, detects boulders.
      ▼
[Artifact Summary Generation]
         Logs elapsed runtime and verifies the 15 output deliverables.
```

---

# 6. Data Model, File Formats & Geodetic Standards

LunaSafe avoids the operational overhead of a relational database. All persistent state is stored as self-describing, industry-standard scientific GIS formats.

### 6.1 Input Datasets (`data/`)
- **Synthetic Benchmark (`synthetic_dem.tif` & `synthetic_psr.tif`):**
  - Dimensions: $200 \times 200$ pixels.
  - Spatial Resolution: $20.0\text{ meters/pixel}$ (spans $4.0\text{ km} \times 4.0\text{ km}$).
  - Projection: Moon South Pole Polar Stereographic ($R = 1,737,400\text{ m}$).
  - NoData Sentinel: `-9999.0`.
- **Real NASA LOLA South Pole Dataset (`lola_south_pole_dem.tif` & `lola_psr_mask.tif`):**
  - Dimensions: $250 \times 250$ pixels.
  - Spatial Resolution: $240.0\text{ meters/pixel}$ (spans $60.0\text{ km} \times 60.0\text{ km}$).
  - Elevation: Calibrated in real surface meters derived from LRO laser altimetry.

### 6.2 Output Deliverables (`outputs/`)
A complete pipeline run produces 15 primary artifacts:

| Filename | Data Format | Contents & Description |
| :--- | :---: | :--- |
| `hazard_classes.tif` | GeoTIFF (uint8) | Classified decision surface (Classes 0–4) with embedded metadata tags. |
| `hazard_summary.csv` | CSV | Tabular breakdown of pixel counts, area in $\text{km}^2$, and percentages. |
| `psr_binary.tif` | GeoTIFF (uint8) | Cleaned, despeckled binary shadow mask ($0 = \text{illuminated}, 1 = \text{shadow}$). |
| `psr_polygons.geojson` | GeoJSON | Vector boundary polygons of all delineated PSRs. |
| `psr_polygons.shp` | ESRI Shapefile | Complete shapefile bundle (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`). |
| `psr_polygons_bundle.zip`| ZIP Archive | Packaged vector distribution bundle for external GIS software. |
| `slope_deg.tif` | GeoTIFF (float32) | Topographic slope in degrees ($0^\circ - 90^\circ$). |
| `aspect_deg.tif` | GeoTIFF (float32) | Terrain aspect compass heading in degrees ($0^\circ - 360^\circ$). |
| `roughness_std_m.tif` | GeoTIFF (float32) | Elevation standard deviation in meters within $3 \times 3$ window. |
| `roughness_tri_m.tif` | GeoTIFF (float32) | Riley Terrain Ruggedness Index in meters. |
| `terrain_histograms.png` | PNG (300 DPI) | 4-panel statistical distribution histograms for terrain metrics. |
| `lunasafe_hazard_map.png`| PNG (300 DPI) | 4-panel publication cartographic map. |
| `lunasafe_hazard_map.pdf`| Vector PDF | High-resolution printable cartographic document. |
| `slope_sensitivity.png` | PNG (300 DPI) | Sensitivity analysis chart showing safe area vs. slope thresholds. |
| `landing_sites.json` | JSON | Coordinates, clearance, score, and rankings for top 3 landing sites. |
| `boulder_hazard.tif` | GeoTIFF (float32) | Micro-hazard boulder probability surface $[0.0, 1.0]$. |
| `mission_report.pdf` | PDF Document | Comprehensive multi-page mission briefing and safety audit report. |
| `web_data.json` | JSON Bundle | Optimized raster grid bundle powering the interactive web console. |

---

# 7. REST API Reference & Web Architecture

The interactive console is powered by `web_server.py`, a multi-threaded HTTP server (`ThreadingHTTPServer`) operating at `http://localhost:8050`.

### 7.1 Key Endpoints Summary

| Method | Endpoint | Description | Typical Response |
| :---: | :--- | :--- | :--- |
| **GET** | `/health` | Server heartbeat and pipeline status | `{"status": "connected", "pipeline_running": false}` |
| **GET** | `/api/status` | Current dataset metadata & summary CSV | JSON containing active dataset, CRS, and class areas |
| **GET** | `/api/data` | Serves `web_data.json` raster bundle | Full 2D array payload for map rendering |
| **GET** | `/api/logs` | Real-time log buffer (last 150 lines) | Array of log strings streamed from pipeline |
| **POST** | `/api/recalculate` | **Fast-path in-memory reclassification** | Recalculated class areas, landing sites, audit metrics |
| **POST** | `/api/audit` | Triggers the 9-rule formal audit | Total violations, pass/fail status per rule |
| **POST** | `/api/run-pipeline` | Spawns full headless CLI run in child thread | Initiates subprocess execution of `main.py` |
| **POST** | `/api/download-lola`| Downloads real NASA LOLA JP2 in background | Status updates on PDS download and conversion |
| **GET** | `/api/download/<file>`| Downloads generated artifact files | Binary attachment stream (GeoTIFF, Shapefile, PDF) |

### 7.2 The Hot Path: In-Memory Recalculation (`POST /api/recalculate`)
When a user moves a threshold slider on the web UI:
1. The browser sends the new thresholds (`slope_safe_max`, `roughness_safe_max`, etc.) in a JSON POST.
2. `web_server.py` pulls the pre-loaded numpy arrays for slope, roughness, and PSR directly from RAM (`RASTER_CACHE`).
3. It re-runs `hazard.classify_hazard_surface()` and `ml_recommender.recommend_landing_sites()`.
4. In under 20 milliseconds, it returns the updated landing sites and summary statistics back to the browser without touching the hard drive.

---

# 8. Setup, Execution & Testing Handbook

### 8.1 Prerequisites
- **Operating System:** Windows, Linux, or macOS.
- **Python Version:** Python 3.10, 3.11, 3.12, or 3.13.
- **Git:** Installed and configured.

### 8.2 Installation Steps

Open your terminal or PowerShell and run:

```powershell
# 1. Clone the repository (if not already local)
git clone https://github.com/kushbansal2005/ORBISLUNA.git
cd LunaSafe

# 2. Create a dedicated virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# 4. Install required scientific dependencies
pip install -r requirements.txt
```

### 8.3 Running the System

#### Mode A: Headless Pipeline Execution (CLI)
```powershell
python main.py
```
*Optional CLI Flags:*
- `--force-synthetic`: Forces the use of synthetic benchmark crater even if real LOLA data is present.
- `--fail-on-mismatch`: Throws a loud exception if DEM and PSR grids do not match, instead of auto-resampling.
- `--quiet`: Suppresses banner logs.

#### Mode B: Interactive Mission Control (Web Console)
```powershell
python web_server.py
```
Open your browser and navigate to: **`http://localhost:8050`** (or `8080` if 8050 is occupied).

### 8.4 Running the Test Suite
The codebase includes 32 automated tests covering geodesy, terrain math, hazard logic, and cartography:
```powershell
python -m pytest -q
```
*Expected Result:* **`32 passed, 1 warning in ~25s`**.

---

# 9. Transparent Technical Audit: Known Issues & Fixes

In keeping with LunaSafe's core philosophy of scientific honesty, the documentation records an open register of known issues identified during architectural audits. These are prioritized in the roadmap:

### 9.1 High-Priority Correctness Items
1. **Issue I-01 (PSR Metrics Self-Comparison):**
   - *Problem:* In `validate.py:301-308`, the batch pipeline evaluates PSR accuracy by comparing the mask against itself (`compute_psr_metrics(psr_mask, psr_mask)`), yielding IoU/F1 of 1.000 artificially.
   - *Fix:* Accept an external independent ground-truth raster if present; otherwise honestly report `UNLOADED / Not Independently Benchmarked`.
2. **Issue I-02 (Web Recalculation Pixel Scale):**
   - *Problem:* `web_server.py:470` hardcodes pixel size to 20 m (`config.SYNTHETIC_PIXEL_SIZE_M`). When processing real LOLA data (240 m/px), calculated areas in the web console are scaled down by $144\times$.
   - *Fix:* Dynamically read pixel size from `RASTER_CACHE["transform"]`.
3. **Issue I-03 (Audit Rule 4 Dictionary Key Mismatch):**
   - *Problem:* `web_server.py:576` queries `rule4_safe_in_psr`, but `validate.py:117` emits `rule4_safe_pixel_in_psr`. As a result, Rule 4 violations in the web console always report 0.
   - *Fix:* Synchronize the dictionary key string across both files.
4. **Issue I-04 (CLI Subprocess Config Decoupling):**
   - *Problem:* When the web UI triggers `POST /api/run-pipeline`, slider changes only mutated the server's in-memory `config`. The spawned child process (`python main.py`) re-imported defaults from disk.
   - *Fix:* Pass dynamic CLI threshold flags to `main.py` or write an active `run_config.json`.
5. **Issue I-05 (40m Landing Clearance Enforcement):**
   - *Problem:* While `config.LANDING_CLEARANCE_BUFFER_M = 40.0` exists, the recommender only checks `dist_m >= ellipse_radius_m`. The 40 m standoff is drawn visually in the UI, but not enforced mathematically in the candidate ranking.
   - *Fix:* Enforce `dist_m >= ellipse_radius_m + LANDING_CLEARANCE_BUFFER_M`.

---

# 10. 2-Developer Comprehensive Engineering Roadmap

To advance LunaSafe from a hackathon prototype to a flight-ready mission planning system, here is a structured **18-day engineering plan specifically divided between 2 developers**.

### 10.1 Team Structure & Role Division

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               DEVELOPER 1                                       │
│          Core Science, Geodesy, Backend Algorithms & Safety Lead                │
│                                                                                 │
│  • Domain Modules: io_utils.py, psr.py, terrain.py, hazard.py, validate.py      │
│  • Algorithm accuracy, mathematical formulation, numerical optimization         │
│  • Geodetic integrity, coordinate reference systems, map projections            │
│  • Formal audit invariants, scientific unit testing, test fixtures             │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                         Collaborative Integration Gate
                                         │
┌────────────────────────────────────────┴────────────────────────────────────────┘
│                               DEVELOPER 2                                       │
│          Web Mission Control, APIs, Visual Cartography & Tooling Lead           │
│                                                                                 │
│  • Modules & Frontends: web_server.py, web/* (app.js, styles.css), mapping.py   │
│  • REST API endpoints, threading concurrency, server security hardening        │
│  • 2D Canvas studio, Three.js 3D WebGL renderer, client-side UX                 │
│  • Export pipelines (PDF reports, web_data.json bundling, packaging)           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### 10.2 Milestone Breakdown & Sprint Schedule

```
  DAYS 1 - 2       DAYS 3 - 5       DAYS 6 - 9       DAYS 10 - 14      DAYS 15 - 18
 ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌─────────────┐   ┌────────────┐
 │Milestone 0 │   │Milestone 1 │   │Milestone 2 │   │ Milestone 3 │   │Milestone 4 │
 │ Repository │──▶│     P0     │──▶│     P1     │──▶│     P2      │──▶│ P3 Polish  │
 │  Hygiene   │   │Correctness │   │ Coherence  │   │  Advanced   │   │& Production│
 │   & CI     │   │ & Security │   │ & Harness  │   │   Science   │   │  Delivery  │
 └────────────┘   └────────────┘   └────────────┘   └─────────────┘   └────────────┘
```

#### Milestone 0: Repository Hygiene, Tooling & CI (Days 1 – 2)
*Goal: Establish clean git habits, prevent diff churn, and ensure automated verification.*
- **Dev 1:**
  - Create standard `.gitignore` (untrack `__pycache__`, `.pytest_cache`, temporary files).
  - Clean up dependencies: consolidate `requirements.txt` and delete redundant duplicate `requirement.txt`.
  - Set up GitHub Actions CI workflow (`.github/workflows/ci.yml`) to run `pytest` and `pyflakes` on every commit.
- **Dev 2:**
  - Audit committed binaries in `outputs/`. Implement non-destructive testing (direct tests to write to `tmp_path` so running tests does not dirty the git tree).
  - Implement a clean output-refresh build script (`scripts/build_artifacts.ps1`).

---

#### Milestone 1: P0 Correctness, Safety Invariants & Security Hardening (Days 3 – 5)
*Goal: Fix all mathematical and audit bugs, close network security gaps.*
- **Dev 1 (Science & Core Fixes):**
  - **Task T-01:** Fix web Rule 4 audit key mismatch (`web_server.py:576` $\to$ `rule4_safe_pixel_in_psr`). Add an automated test asserting that every key in `rules_meta` matches `validate.py`.
  - **Task T-02:** Fix pixel scaling in `web_server.py:470`. Compute pixel size dynamically from affine transform `abs(transform.a)`. Fix 144× area discrepancy on LOLA data.
  - **Task T-04:** Fix PSR benchmark self-comparison (`validate.py:301-308`). If no independent ground truth exists, return explicit `null`s with a provenance disclosure.
  - **Task T-05:** Enforce the 40-meter clearance buffer in `ml_recommender.py:115` (`dist_m >= ellipse_radius_m + buffer_m`).
- **Dev 2 (Web & Security Hardening):**
  - **Task T-13 (Security Pass):**
    - Bind `web_server.py` to loopback (`127.0.0.1`) by default instead of open `0.0.0.0`.
    - Restrict static file serving to the `web/` directory (prevent arbitrary repository file downloads via path traversal).
    - Remove dead/unsafe raw file upload endpoint (`/api/upload-raster`).
    - Add JSON payload validation and return proper HTTP 400 Bad Request on malformed inputs.
  - **Task T-03:** Fix PDF mission report (`mission_report.py`). Replace hard-coded audit statistics with dynamic values from the active audit engine. Use true UTC timestamps.

---

#### Milestone 2: P1 Configuration Coherence, Test Harness & Freshness (Days 6 – 9)
*Goal: Decouple server state, sync CLI with UI sliders, and build server tests.*
- **Dev 1 (State & CLI Coordination):**
  - **Task T-06:** Eliminate global `config.py` mutation. Refactor classifier functions to accept explicit parameters or a `ThresholdConfig` dataclass instead of modifying module attributes.
  - Upgrade `main.py` CLI parser to accept explicit threshold overrides (`--slope-safe`, `--roughness-safe`, etc.) so CLI and web executions can be parameterized identically.
  - **Task T-09:** Update `test_main.py` and pipeline tests to redirect output generation to `tmp_path`, maintaining a clean git tree.
- **Dev 2 (API Testing & Data Synchronization):**
  - **Task T-08:** Create an automated integration test suite for the server (`tests/test_server.py`) testing `/health`, `/api/status`, `/api/data`, `/api/recalculate`, `/api/audit`, and error codes.
  - **Task T-10:** Resolve stale `outputs/web_data.json` bug (Issue I-06). Integrate `export_web_data.py` into the end of `main.py` so every pipeline run immediately updates the web bundle. Add a version/shape validator.
  - **Task T-17:** Fix sensitivity charts in `web/app.js` (`renderSensitivityCharts`). Replace hardcoded demo arrays with live data returned from `/api/recalculate`.

---

#### Milestone 3: P2 Science Realism & Advanced Planetary Features (Days 10 – 14)
*Goal: Upgrade physics realism, illumination modeling, and visual interaction.*
- **Dev 1 (Planetary Physics & Detection):**
  - **Task T-12 (Illumination Modeling):** Activate the shadow term $D$ in `hazard.compute_hazard_score()`. Compute a lunar solar grazing illumination angle from DEM elevation and aspect to pass real illumination values into $H$.
  - Refine boulder detection algorithm: calibrate Gaussian residual thresholds against known lunar boulder fields (e.g., Apollo/Artemis candidate sites).
  - Implement crater-rim detectability heuristics to prevent lander touchdown on unstable ridgelines.
- **Dev 2 (Interactive Visualizations & UX):**
  - Upgrade 3D WebGL viewer (`web/app.js`): Add dynamic shadows that move across the terrain mesh in real-time as the user drags a "Sun Elevation Angle" slider.
  - Optimize recalculate payload (Task T-05): Send run-length encoded or binary typed arrays for the hazard surface to achieve smooth 60 FPS slider interactions on large grids.
  - Enhance 2D Canvas Studio with interactive landing ellipse measurement tools and coordinate bookmarking.

---

#### Milestone 4: P3 Polish, Packaging, Production Readiness & Presentation (Days 15 – 18)
*Goal: Finalize documentation, package distribution, and deliver judge/executive presentation.*
- **Dev 1 (Packaging & Documentation):**
  - Package LunaSafe as an installable Python package (`pyproject.toml` with `pip install -e .`).
  - Write complete developer API documentation and CLI reference.
  - Verify full end-to-end reproducibility on both Windows and Linux environments.
- **Dev 2 (Release Assets & Demo Walkthrough):**
  - Polish the 60-Second Automated Judge Tour in `web/app.js` for pitch presentations.
  - Add `/api/version` endpoint exposing git commit SHA and build timestamp.
  - Build a one-click launcher for Windows and Linux (`run_lunasafe.sh` / `run_lunasafe.bat`).
  - Assemble high-resolution presentation slides and video demonstrations.

---

### 10.3 Developer Daily Accountability & Task Assignment Matrix

| Day | Dev 1 Focus (Science / Backend / Safety) | Dev 2 Focus (Web / API / Visualization) | Joint Milestone Gate |
| :---: | :--- | :--- | :--- |
| **Day 1** | Git untrack, `.gitignore`, dependency cleanup | Non-destructive test harness setup | Clean repository tree, zero untracked caches |
| **Day 2** | Setup GitHub Actions CI workflow | Implement `build_artifacts` script | Automated CI passing green on push |
| **Day 3** | Fix Rule 4 key (T-01) & dynamic pixel scale (T-02) | Loopback binding & static route lockdown (T-13) | Correct areas on LOLA data, safe localhost server |
| **Day 4** | Fix PSR validation self-comparison (T-04) | Path traversal protection & 400 error handling | Zero false PSR claims, robust HTTP input checking |
| **Day 5** | Enforce 40m standoff buffer in ALSS (T-05) | Dynamic PDF mission report generation (T-03) | All P0 safety issues resolved and verified |
| **Day 6** | Refactor `config` into explicit dataclass (T-06) | Create `test_server.py` integration harness (T-08) | Zero global config mutation in web server |
| **Day 7** | Parameterize `main.py` CLI with slider flags | Bind live sensitivity charts in UI (T-17) | Web sliders & CLI run with identical options |
| **Day 8** | Isolate outputs in tests to `tmp_path` (T-09) | Hook `export_web_data` into `main.py` (T-10) | Fresh `web_data.json` on every run, clean git |
| **Day 9** | End-to-end validation of P1 milestones | Integration testing of web console & API | **Milestone 1 & 2 Complete & Tagged** |
| **Day 10** | Implement solar grazing illumination model (T-12) | Optimize recalculation binary payload (T-05) | $H$ score shadow term active with real physics |
| **Day 11** | Calibrate boulder micro-hazard thresholds | 3D WebGL real-time sun angle shadow mesh | Visual sun movement matches physical DEM shadows |
| **Day 12** | Crater-rim stability heuristic | 2D Canvas studio polygon measurement tools | Enhanced interactive exploration features |
| **Day 13** | Benchmark real LOLA 60km polar datasets | Implement client-side coordinate bookmarking | Scalable performance verified on real terrain |
| **Day 14** | Code freeze on scientific algorithms | Complete UI regression testing | **Milestone 3 Complete & Tagged** |
| **Day 15** | Standardize package with `pyproject.toml` | Refine 60-second automated judge tour | System installable via `pip install -e .` |
| **Day 16** | Cross-platform validation (Linux/macOS/Windows) | Version endpoint `/api/version` & release scripts | Unified one-click launchers ready |
| **Day 17** | Finalize technical documentation & user manuals | Polish cartography & export deliverables | All documentation synchronized with code |
| **Day 18** | Rehearse technical demo & pitch | Final release packaging (`v1.0.0`) | **Final Production Release Delivered** |

---

### 10.4 Definition of Done (DoD) for Every Feature
A task is considered complete only when:
1. **Code Integrity:** All new or modified functions contain type annotations and docstrings.
2. **Test Coverage:** Corresponding unit or regression tests are added in `tests/` and pass with `pytest`.
3. **Scientific Invariance:** `validate.py` 9-rule audit returns 0 violations on the resulting output rasters.
4. **Clean Tree:** Running tests or building data does not leave untracked artifacts in git.
5. **Peer Review:** Code is committed via a pull request reviewed and signed off by the partner developer.

---
*LunaSafe Project Master Guide — Built for Mission Success at the Lunar South Pole.*
