# DATA & MODEL PROVENANCE — OrbisLuna

This file documents every dataset and "model" used by the application, its true origin, and known limitations. Per project rules, derived/proxy data must never be presented as an official product, and no invented metrics may be displayed.

---

## D1 — LRO LOLA South Pole DEM (REAL, verified)

- **File**: `data/lola_south_pole_dem.tif` (250×250, 240 m/px, float32, nodata −9999)
- **Original product**: `ldem_75s_240m.jp2` — LRO LOLA Lunar Orbiter Laser Altimeter Gridded Data Record, Polar (75°S–90°S), 240 m/px
- **Publisher**: NASA PDS Geosciences Node, Washington University in St. Louis
- **Source URL (verified live 2026-10-18)**: https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/ldem_75s_240m.jp2
- **Local archive**: `data/ldem_75s_240m.jp2` — byte size 10,766,928 matches PDS listing exactly.
- **License/usage**: NASA PDS public archive data; redistribution permitted with attribution.
- **Processing (reproducible)**: `prepare_lola_dataset.convert_real_lola_to_geotiff()` — center 250×250 window (60 km × 60 km at pole), scaling elevation = DN × 0.5 (per LOLA GDR polar product definition), 2-px nodata collar, native `Moon2000_spole` CRS retained.
- **Validation performed (2026-10-18)**: shape 250×250 @ 240 m; CRS = Moon 2000 IAU sphere R=1,737,400 m; elevation range −3235.5 m … +1955.0 m; 1,984 nodata px (LOLA polar voids + collar). Values plausible for south polar terrain.
- **Consumers**: main pipeline (`main.py`), web 3D/2D views, rover router, landing recommender.

## D2 — LOLA "PSR mask" (DERIVED PROXY — not an official product)

- **File**: `data/lola_psr_mask.tif` (250×250, uint8 {0,1})
- **True origin**: computed by `prepare_lola_dataset.py` as `elev < (mean_elev − 900 m)` over the LOLA DEM crop. This is a topographic-depression proxy for permanently shadowed terrain.
- **IMPORTANT**: The NASA PDS LOLA GDR polar archive (checked 2026-10-18) contains **no PSR mask product**. This mask is a project-derived approximation, **not** the LOLA/LROC PSR atlas product.
- **Required labeling everywhere in the app**: "LOLA-derived shadow proxy (elevation threshold)" — never "NASA PSR product".
- **Known limitations**: simple threshold cannot capture true illumination geometry; actual PSRs depend on grazing solar angles; some deep polar craters may be missed/false-positive.
- **Consumers**: PSR classification (Class 4), rover science targets, KPI shadowed-area stats.

## D3 — Synthetic benchmark crater (explicitly synthetic)

- **Files**: `data/synthetic_dem.tif`, `data/synthetic_psr.tif` (200×200, 20 m/px)
- **Origin**: `io_utils.generate_synthetic_crater_topography()` — procedural 1.2-km-radius crater, deterministic.
- **Usage**: test benchmark + offline demo when real data missing. Must always carry "SYNTHETIC DEMO" label (config.SYNTHETIC_LABEL).

## D4 — Multi-site catalog models (synthetic site models)

- **Files**: `data/sites/<site_id>/<site_id>_dem.tif`, `<site_id>_psr.tif`
- **Origin**: `lunar_catalog.generate_site_terrain()` — procedurally generated from published morphometric summaries (crater diameters/depths from published mission-target descriptions). Exception: `lola_crop` site = real LOLA DEM (D1) + derived PSR proxy (D2).
- **Status**: synthetic terrain models inspired by real catalog values; must be labeled as site models, not as real altimetry (except lola_crop DEM).

## M1 — "Boulder & Micro-Hazard AI" (algorithmic detector, not a trained ML model)

- **Module**: `ml_recommender.detect_boulder_micro_hazards()` — multi-scale Gaussian bandpass residual detection on the DEM; sigmoid probability mapping; estimated boulder diameters.
- **Status**: deterministic signal-processing algorithm, **not** a trained model. Outputs are "detected residual anomalies with estimated sizes", not validated boulder detections. No ground-truth evaluation exists.
- **Rule**: UI must not present its outputs as trained-model predictions with validated confidence. (Pending UI audit.)

## M2 — Autonomous Landing Site Selection (ALSS)

- **Module**: `ml_recommender.recommend_landing_sites()` — deterministic multi-criteria optimization (clearance distance transform + slope/roughness/science-proximity fitness). Not ML training; no learned weights. Weights are mission-engineering constants. Reproducible for a given raster + thresholds.
- **Correctness fix (2026-10-18)**: `run_mission_autonomy` previously hardcoded 20 m/px spacing for all datasets — clearance/distance outputs were 12× wrong on LOLA 240 m data. Pixel size is now derived from the DEM transform, and a grid-consistency guard rejects mixed-dataset inputs.

## M3 — Rover traverse planner

- **Module**: `rover_router.find_optimal_rover_path()` — A* on 8-connected grid with terramechanics + battery SoC simulation. Deterministic. Rover power constants (2 kWh battery, 120 W drive, 80 W heater, 250 W solar) are engineering assumptions documented in `config.py`; SoC results are simulations, not measured values.
- **Honest failure mode**: terrain models whose walls exceed the 18° rover limit (e.g., Shackleton's 25-32° escarpments) return `NO_PATH_FOUND` with an explicit error message — no fabricated routes.

## Evaluation & validation status

- **9-point rule consistency audit**: real, runs cell-by-cell over generated rasters (`validate.verify_rule_consistency`); covered by tests. Result varies per dataset run and is reported from actual computation.
- **PSR accuracy metrics (precision/recall/IoU/F1)**: `/api/psr-validation` honestly reports `UNLOADED` unless an independent reference is available. Benchmark mode compares pipeline output against the input mask family — NOT an independent evaluation and must be labeled as such. No independent ground-truth PSR catalog is currently ingested → metrics are and must remain null in default mode.
