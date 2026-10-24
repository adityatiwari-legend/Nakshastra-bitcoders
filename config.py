"""
OrbisLuna Configuration Module
Centralized configuration: all thresholds, paths, class definitions, and constants.
No magic numbers elsewhere.
"""

from pathlib import Path
from typing import Dict

# Project Identity
PROJECT_NAME = "OrbisLuna"

# ==============================================================================
# Paths
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
TESTS_DIR = BASE_DIR / "tests"

# Ensure essential directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Synthetic Data Paths
SYNTHETIC_DEM_PATH = DATA_DIR / "synthetic_dem.tif"
SYNTHETIC_PSR_PATH = DATA_DIR / "synthetic_psr.tif"

# Real Data Target Paths (LOLA DEM and LOLA PSR mask)
REAL_DEM_PATH = DATA_DIR / "lola_south_pole_dem.tif"
REAL_PSR_PATH = DATA_DIR / "lola_psr_mask.tif"
REAL_ILLUMINATION_PATH = DATA_DIR / "lola_illumination_frac.tif"

# ==============================================================================
# External Public Dataset Cache (Phase 3 — real lunar datasets)
# Raw downloads live under data/external/. Never invent checksums — they are
# computed from the actual files after the first verified download.
# ==============================================================================
EXTERNAL_DATA_DIR = DATA_DIR / "external"
EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

# NASA PDS Geosciences Node — LRO LOLA Polar GDR, south polar DEM (240 m/px).
# PDS label: LDEM_75S_240M, V2.1, SCALING_FACTOR=0.5, OFFSET=1737400 (m),
# Polar Stereographic, R=1737.4 km, lon_0=0. Source file kept as JP2.
LOLA_DEM_JP2_PATH = DATA_DIR / "ldem_75s_240m.jp2"
LOLA_DEM_JP2_URL = (
    "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/"
    "lrolol_1xxx/data/lola_gdr/polar/jp2/ldem_75s_240m.jp2"
)
LOLA_DEM_JP2_SHA256 = "a0ebbad0a2650c742ed2d4ec1314aa095f869ba800f817b1b72eeb9194345c36"

# Mazarico et al. (2011, JGR) LOLA-derived published PSR map (240 m/px, 65S+).
# Hosted by MIT (D. E. Smith / LOLA GDR illumination products). DN=+20000 -> PSR,
# DN=-20000 -> illuminated. PDS label LPSR_65S_240M_201608 V1.05.
LPSR_JP2_PATH = EXTERNAL_DATA_DIR / "LPSR_65S_240M_201608.jp2"
LPSR_JP2_URL = "http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/LPSR_65S_240M_201608.JP2"
LPSR_JP2_SHA256 = "d0807d1b7d16c13e6e037ce9a9d82efb375cd2065da3f8beeed3f97157deaf94"

# Mazarico et al. (2011) average solar-disc visibility fraction (240 m/px, 65S+).
# DN * 0.00004 -> [0, ~0.93]; 0 = permanent shadow. Same grid as LPSR.
AVGVISIB_JP2_PATH = EXTERNAL_DATA_DIR / "AVGVISIB_65S_240M_201608.jp2"
AVGVISIB_JP2_URL = "http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/AVGVISIB_65S_240M_201608.JP2"
AVGVISIB_JP2_SHA256 = "4ccaf5ef7cdfc35bbff4d28e0d9b1051d9d56a66181cda633e71bfd42237dd49"

# PDS label metadata applied when converting raw JP2s (documented, not guessed)
LOLA_DEM_DN_SCALE = 0.5            # meters per DN (PDS LABEL: SCALING_FACTOR)
LPSR_DN_PSR = 20000                # PDS LABEL: +20000 => permanent shadow
LPSR_DN_LIT = -20000               # PDS LABEL: -20000 => illuminated
AVGVISIB_DN_SCALE = 0.00004        # PDS LABEL: SCALING_FACTOR -> visibility fraction

# Active ROI crop for the south-pole hazard workspace (pixels at 240 m/px)
POLE_CROP_SIZE_PX = 250            # 250 * 240 m = 60 km x 60 km around the pole

# ==============================================================================
# Official Artemis III candidate landing regions (NASA, October 2024 down-select
# from 13 to 9 regions — NTRS 20250011660 / NASA news release 2024-10-28).
# Centers are the mean of the published representative candidate landing sites
# (Wueller et al., 2026, JGR Planets, Table A1 — peer-reviewed coordinates).
# Connecting Ridge and Peak near Shackleton were REMOVED in the 2024
# down-select; do not reintroduce them as official Artemis III regions.
# No priority order among the nine.
# ==============================================================================
ARTEMIS_III_REGIONS = {
    "artemis_peak_cabeus_b": {
        "name": "Peak near Cabeus B",
        "center_lat": -83.5732,
        "center_lon": -69.0850,
    },
    "artemis_haworth": {
        "name": "Haworth",
        "center_lat": -86.7920,
        "center_lon": -22.9474,
    },
    "artemis_malapert_massif": {
        "name": "Malapert Massif",
        "center_lat": -86.0434,
        "center_lon": 0.1514,
    },
    "artemis_mons_mouton": {
        "name": "Mons Mouton",
        "center_lat": -85.3955,
        "center_lon": 31.1899,
    },
    "artemis_mons_mouton_plateau": {
        "name": "Mons Mouton Plateau",
        "center_lat": -84.5061,
        "center_lon": 30.5135,
    },
    "artemis_nobile_rim_1": {
        "name": "Nobile Rim 1",
        "center_lat": -85.1876,
        "center_lon": 37.2379,
    },
    "artemis_nobile_rim_2": {
        "name": "Nobile Rim 2",
        "center_lat": -83.8864,
        "center_lon": 58.4089,
    },
    "artemis_de_gerlache_rim_2": {
        "name": "de Gerlache Rim 2",
        "center_lat": -88.3691,
        "center_lon": -67.4597,
    },
    "artemis_slater_plain": {
        "name": "Slater Plain",
        "center_lat": -87.2013,
        "center_lon": 126.5711,
    },
}

# ==============================================================================
# Public dataset registry — sources, versions, licenses, access notes.
# Used by the Data Sources panel, README, and the preprocessing pipeline.
# 'status' must reflect reality: downloaded | available | registration_required.
# ==============================================================================
PUBLIC_DATASETS = [
    {
        "id": "lola_dem_75s",
        "name": "LRO LOLA South Polar DEM (LDEM_75S_240M)",
        "mission": "LRO (NASA)",
        "instrument": "LOLA",
        "version": "V2.1 (product 2017-06-15)",
        "resolution": "240 m/pixel",
        "coverage": "75°S–90°S, polar stereographic (R=1737.4 km, lon_0=0)",
        "publisher": "NASA PDS Geosciences Node (Washington University in St. Louis)",
        "url": LOLA_DEM_JP2_URL,
        "license": "NASA PDS — unrestricted; credit LRO/LOLA team",
        "citation": "Smith, D. E., et al. (2017). LRO-LOLA GDR, LDEM_75S_240M. NASA PDS Geosciences Node.",
        "local_path": str(LOLA_DEM_JP2_PATH.relative_to(BASE_DIR)) if LOLA_DEM_JP2_PATH.exists() else "data/ldem_75s_240m.jp2",
        "status": "downloaded" if LOLA_DEM_JP2_PATH.exists() else "available",
        "role": "Primary elevation model (slope, roughness, 3D terrain)",
    },
    {
        "id": "lpsr_psr",
        "name": "LOLA-derived Permanent Shadow Map (LPSR_65S_240M)",
        "mission": "LRO (NASA)",
        "instrument": "LOLA (illumination model)",
        "version": "V1.05 (product 2016-09-15)",
        "resolution": "240 m/pixel",
        "coverage": "65°S–90°S, polar stereographic",
        "publisher": "MIT / NASA GSFC (Mazarico, Smith et al.)",
        "url": LPSR_JP2_URL,
        "license": "NASA PDS / MIT — credit Mazarico et al. (2011)",
        "citation": "Mazarico, E., et al. (2011). Illumination conditions of the lunar polar regions. JGR Planets, 116, E00H17.",
        "local_path": str(LPSR_JP2_PATH.relative_to(BASE_DIR)) if LPSR_JP2_PATH.exists() else "data/external/LPSR_65S_240M_201608.jp2",
        "status": "downloaded" if LPSR_JP2_PATH.exists() else "available",
        "role": "Published PSR mask (replaces DEM-threshold proxy)",
    },
    {
        "id": "avgvisib_illum",
        "name": "Average Solar-Disc Visibility (AVGVISIB_65S_240M)",
        "mission": "LRO (NASA)",
        "instrument": "LOLA (illumination model)",
        "version": "V1.05 (product 2016-09-15)",
        "resolution": "240 m/pixel",
        "coverage": "65°S–90°S, polar stereographic",
        "publisher": "MIT / NASA GSFC (Mazarico, Smith et al.)",
        "url": AVGVISIB_JP2_URL,
        "license": "NASA PDS / MIT — credit Mazarico et al. (2011)",
        "citation": "Mazarico, E., et al. (2011). Illumination conditions of the lunar polar regions. JGR Planets, 116, E00H17.",
        "local_path": str(AVGVISIB_JP2_PATH.relative_to(BASE_DIR)) if AVGVISIB_JP2_PATH.exists() else "data/external/AVGVISIB_65S_240M_201608.jp2",
        "status": "downloaded" if AVGVISIB_JP2_PATH.exists() else "available",
        "role": "Continuous illumination fraction (0=PSR .. 1=fully lit)",
    },
    {
        "id": "diviner_polar_temp",
        "name": "Diviner Lunar Radiometer polar temperatures",
        "mission": "LRO (NASA)",
        "instrument": "Diviner",
        "version": "L2 calibrated RDR / derived polar products",
        "resolution": "native swath; polar mosaics commonly 240 m–1 km",
        "coverage": "South polar regions",
        "publisher": "NASA PDS Planetary Plasma Interactions Node (UCLA)",
        "url": "https://pds-ppi.igpp.ucla.edu/diviner/",
        "license": "NASA PDS — credit Diviner team (Williams et al.)",
        "citation": "Williams, J.-P., et al. (2019). Lunar South Pole temperatures and illumination. (See PDS PPI Diviner archives.)",
        "local_path": None,
        "status": "available",
        "role": "Surface temperature context (not required for hazard classes)",
        "access_notes": (
            "Temperatures are NOT bundled in this repo. Download from PDS PPI: "
            "https://pds-ppi.igpp.ucla.edu/diviner/ → browse 'Calibrated Data' or "
            "derived polar products. Exact file selection depends on epoch/resolution; "
            "no single canonical 'polar temperature' file exists. Do not treat "
            "un-downloaded Diviner values as present."
        ),
    },
    {
        "id": "chandrayaan2_ohrc",
        "name": "Chandrayaan-2 OHRC / TMC-2 (ISRO PRADAN)",
        "mission": "Chandrayaan-2 (ISRO)",
        "instrument": "OHRC (0.32 m), TMC-2 (5 m stereo)",
        "version": "PRADAN archive",
        "resolution": "0.32 m (OHRC) / 5 m (TMC-2)",
        "coverage": "Selected lunar sites incl. south polar strips",
        "publisher": "ISRO PRADAN (https://wwwpradan.gov.in / https://www.isro.gov.in)",
        "url": "https://wwwpradan.gov.in/",
        "license": "ISRO — registration + data-request approval required",
        "citation": "ISRO Chandrayaan-2 mission documentation (PRADAN catalogue)",
        "local_path": None,
        "status": "registration_required",
        "role": "High-resolution stereo context (documented only — cannot be fetched anonymously)",
        "access_notes": (
            "PRADAN requires institutional registration and per-dataset approval; "
            "no anonymous download exists. Steps: (1) create account at "
            "https://wwwpradan.gov.in, (2) select Chandrayaan-2 > OHRC/TMC-2, "
            "(3) submit request, (4) place downloaded GeoTIFF/IMG under data/external/ "
            "and register it in PUBLIC_DATASETS. LunaSafe never claims these files are present."
        ),
    },
    {
        "id": "moon_trek_tiles",
        "name": "Moon Trek (NASA GSFC) basemap tiles",
        "mission": "Multi-mission portal",
        "instrument": "various mosaics",
        "version": "trek.nasa.gov",
        "resolution": "depends on layer (LOLA WAC mosaics etc.)",
        "coverage": "Global Moon",
        "publisher": "NASA GSFC / PDS",
        "url": "https://trek.nasa.gov/moon/",
        "license": "NASA — see per-layer credits on Moon Trek",
        "citation": "Moon Trek, NASA GSFC (https://trek.nasa.gov/moon/)",
        "local_path": None,
        "status": "available",
        "role": "Optional visual basemap reference only (not used in hazard math)",
        "access_notes": (
            "Moon Trek is a visualization portal, not a bulk-download API. Use it "
            "for manual context checks. Hazard/PSR math in LunaSafe uses the PDS "
            "JP2 products above, never scraped tiles."
        ),
    },
    {
        "id": "lroc_psr_nac",
        "name": "LROC NAC South Polar PSR polygons (digitized)",
        "mission": "LRO (NASA)",
        "instrument": "LROC NAC",
        "version": "LRO-L-LROC-5-RDR-V1.0 EXTRAS",
        "resolution": "vector polygons (PSRs > 5 km²)",
        "coverage": "South polar region",
        "publisher": "LROC / ASU + PDS",
        "url": "https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/EXTRAS/BROWSE/NAC_POLE/NAC_POLE_PSR_SOUTH/NAC_POLE_PSR_SOUTH.ZIP",
        "license": "NASA PDS — credit LROC team",
        "citation": "Mazarico, E., et al. (2011) / LROC PSR atlas (https://lroc.im-ldi.com/atlases/psr)",
        "local_path": None,
        "status": "available",
        "role": "Independent vector check of raster PSR mask",
        "access_notes": (
            "ZIP (~1 MB) requires accepting LROC data policy; direct hotlinking "
            "may return 403 to scripts. Manual download from the LROC PSR atlas "
            "page works. LunaSafe uses the MIT LPSR raster as the primary PSR source."
        ),
    },
]

# Output Product Paths
OUTPUT_PSR_BINARY_TIF = OUTPUT_DIR / "psr_binary.tif"
OUTPUT_PSR_POLYGONS_GEOJSON = OUTPUT_DIR / "psr_polygons.geojson"
OUTPUT_PSR_POLYGONS_SHP = OUTPUT_DIR / "psr_polygons.shp"

OUTPUT_SLOPE_TIF = OUTPUT_DIR / "slope_deg.tif"
OUTPUT_ASPECT_TIF = OUTPUT_DIR / "aspect_deg.tif"
OUTPUT_ROUGHNESS_STD_TIF = OUTPUT_DIR / "roughness_std_m.tif"
OUTPUT_ROUGHNESS_TRI_TIF = OUTPUT_DIR / "roughness_tri_m.tif"
OUTPUT_TERRAIN_HIST_PNG = OUTPUT_DIR / "terrain_histograms.png"

OUTPUT_HAZARD_CLASSES_TIF = OUTPUT_DIR / "hazard_classes.tif"
OUTPUT_HAZARD_SUMMARY_CSV = OUTPUT_DIR / "hazard_summary.csv"

OUTPUT_MAP_4PANEL_PNG = OUTPUT_DIR / "lunasafe_hazard_map.png"
OUTPUT_MAP_4PANEL_PDF = OUTPUT_DIR / "lunasafe_hazard_map.pdf"
OUTPUT_SENSITIVITY_PNG = OUTPUT_DIR / "slope_sensitivity.png"

# Autonomous Landing Site Recommender & Micro-Hazard AI
OUTPUT_LANDING_SITES_JSON = OUTPUT_DIR / "landing_sites.json"
OUTPUT_BOULDER_HAZARD_TIF = OUTPUT_DIR / "boulder_hazard.tif"

# Autonomous Surface Mobility & Rover Traverse Planning
OUTPUT_ROVER_ROUTE_JSON = OUTPUT_DIR / "rover_traverse.json"
ROVER_MAX_SLOPE_DEG = 18.0
ROVER_SPEED_MPS = 0.1                 # Standard Artemis rover speed (0.1 m/s = 360 m/h)
ROVER_BATTERY_CAPACITY_WH = 2000.0    # 2.0 kWh battery
ROVER_DRIVE_POWER_W = 120.0           # Nominal driving power
ROVER_HEATER_SHADOW_W = 80.0          # Survival heating power in shadow
ROVER_SOLAR_RECHARGE_W = 250.0        # Solar array power in sunlight

LANDING_ELLIPSE_RADIUS_M = 100.0        # Baseline 100 m landing safety radius
LANDING_CLEARANCE_BUFFER_M = 40.0       # Minimum standoff from hazardous slope / PSR
TOP_LANDING_SITES_COUNT = 3             # Sites Alpha, Beta, Gamma
BOULDER_RESIDUAL_THRESHOLD_STD = 2.2    # Standard deviations for high-pass boulder detection



# ==============================================================================
# Lunar Coordinate Reference System (CRS)
# Lunar South Pole Stereographic (Moon 2000 / 2015 IAU sphere R=1737400m)
# Never assign an Earth EPSG code to lunar data!
# ==============================================================================
LUNAR_SOUTH_POLE_PROJ4 = "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs"

# ==============================================================================
# Raster / DEM Processing Constants
# ==============================================================================
DEFAULT_NODATA_VALUE = -9999.0
SYNTHETIC_DEM_SHAPE = (200, 200)       # 200 x 200 grid
SYNTHETIC_PIXEL_SIZE_M = 20.0          # 20 meters per pixel
SYNTHETIC_CRATER_RADIUS_M = 1200.0     # 1.2 km radius
SYNTHETIC_CRATER_DEPTH_M = 350.0       # 350 m depth
SYNTHETIC_CRATER_RIM_HEIGHT_M = 80.0   # 80 m rim elevation above regional surface
SYNTHETIC_REGIONAL_ELEVATION_M = -2500.0  # Representative South Pole depression elevation

# Label for synthetic outputs
SYNTHETIC_LABEL = "SYNTHETIC DEMO"

# ==============================================================================
# Hazard Classification Thresholds
# ==============================================================================
# Slope (degrees)
SLOPE_SAFE_MAX = 5.0
SLOPE_CAUTION_MAX = 10.0
SLOPE_UNSAFE_MIN = 10.0
SLOPE_HARD_UNSAFE_MIN = 15.0
SLOPE_NORM_MAX = 15.0
# Published HLS Artemis landing-slope suitability bound (Wueller et al. 2026):
# regions are screened for slopes <8 deg. Our Safe band (<5 deg) is intentionally
# STRICTER than this literature bound. Reference constant only — not used in the
# 5/10/15 classification rules above.
HLS_LANDING_SLOPE_MAX_DEG = 8.0

# Roughness (local elevation standard deviation in meters)
# Calibrated at REFERENCE_ROUGHNESS_PIXEL_M = 20 m (the synthetic benchmark grid).
# For coarser DEMs, thresholds scale linearly with pixel size via
# scaled_roughness_thresholds() — local std grows with the 3x3 window baseline.
# At 240 m/px (real LOLA): safe <18 m, caution <36 m, hard unsafe >=60 m.
ROUGHNESS_SAFE_MAX = 1.5
ROUGHNESS_CAUTION_MAX = 3.0
ROUGHNESS_UNSAFE_MIN = 3.0
ROUGHNESS_HARD_UNSAFE_MIN = 5.0
ROUGHNESS_NORM_MAX = 5.0
REFERENCE_ROUGHNESS_PIXEL_M = 20.0


def scaled_roughness_thresholds(pixel_size_m: float) -> Dict[str, float]:
    """Resolution-aware roughness thresholds (linear baseline scaling).

    Local elevation std over a fixed 3x3 window grows roughly linearly with
    pixel size for self-affine lunar regolith (documented first-order model).
    Slope thresholds are angular and NOT scaled.
    """
    scale = max(float(pixel_size_m), 1.0) / REFERENCE_ROUGHNESS_PIXEL_M
    return {
        "safe_max": ROUGHNESS_SAFE_MAX * scale,
        "caution_max": ROUGHNESS_CAUTION_MAX * scale,
        "unsafe_min": ROUGHNESS_UNSAFE_MIN * scale,
        "hard_unsafe_min": ROUGHNESS_HARD_UNSAFE_MIN * scale,
        "norm_max": ROUGHNESS_NORM_MAX * scale,
        "scale_factor": scale,
    }

# Neighbourhood window size for roughness / terrain metrics (in pixels, odd integer)
TERRAIN_WINDOW_SIZE = 3

# Hazard Score (H) Weights
WEIGHT_SLOPE = 0.50
WEIGHT_ROUGHNESS = 0.30
WEIGHT_SHADOW = 0.20

# Hazard Score Thresholds
SCORE_SAFE_MAX = 0.25
SCORE_CAUTION_MAX = 0.60
SCORE_UNSAFE_MIN = 0.60

# Hazard Classes
CLASS_NODATA = 0
CLASS_SAFE = 1
CLASS_CAUTION = 2
CLASS_UNSAFE = 3
CLASS_SHADOWED_UNKNOWN = 4

CLASS_NAMES = {
    CLASS_NODATA: "NoData",
    CLASS_SAFE: "Safe",
    CLASS_CAUTION: "Caution",
    CLASS_UNSAFE: "Unsafe",
    CLASS_SHADOWED_UNKNOWN: "Shadowed-Unknown",
}

CLASS_COLORS = {
    CLASS_NODATA: "#222222",            # Very dark gray / black
    CLASS_SAFE: "#2ecc71",              # Vibrant Emerald Green
    CLASS_CAUTION: "#f39c12",           # Rich Amber / Yellow
    CLASS_UNSAFE: "#e74c3c",            # Coral Red
    CLASS_SHADOWED_UNKNOWN: "#8e44ad",  # Deep Violet / Purple
}

# ==============================================================================
# PSR Processing Thresholds
# ==============================================================================
PSR_BINARIZE_THRESHOLD = 0.5
# Minimum connected component size in pixels to retain (filter noise/speckle)
PSR_MIN_SIZE_PIXELS = 9

PSR_PROVENANCE_PUBLISHED = "Published / LOLA-derived PSR Mask (Reference)"
PSR_PROVENANCE_SYNTHETIC = "SYNTHETIC DEMO PSR Mask"

# ==============================================================================
# Map & Visualization Settings
# ==============================================================================
PLOT_DPI = 300
FIGURE_STYLE = "dark_background"

# Ensure headless plotting across all environments
try:
    import matplotlib
    matplotlib.use("Agg")
except ImportError:
    pass
