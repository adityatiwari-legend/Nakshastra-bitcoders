# 02 — Problem Statement & Objectives

> Evidence labels used below: **VERIFIED** = confirmed in code/config; **AUTHOR STATED** = claimed in
> project documents (`PROJECT_SPECIFICATION.md`, `README.md`, `PITCH_SCRIPT.md`) but not independently
> reproducible from the repository; **PLANNED** = proposed, not implemented.

---

## 1. Problem statement (as the project defines it)

**Source:** `PROJECT_SPECIFICATION.md:8-70`, `README.md:27-48`, `.agents/rules/lunasafe.md`.

At the Lunar South Pole, exploration targets and landing hazards overlap:

1. **The target resource** — water ice is trapped inside Permanently Shadowed Regions (PSRs) inside
   craters. *(AUTHOR STATED — consistent with public lunar science; not verifiable from this repo.)*
2. **The operational trap** — PSRs sit inside craters with steep escarpments, boulder fields, and
   total darkness. A lander touching down on an unseen boulder or a >15° slope tips over. *(AUTHOR STATED.)*
3. **Workflow failures of ad-hoc GIS:**
   - Earth datums (WGS84 / EPSG:4326 / Web Mercator) applied to lunar data → kilometre-scale
     distortion. LunaSafe's counter-measure is **VERIFIED**: `io_utils.py:199-206`.
   - The "flat crater floor fallacy": flat ground in shadow labelled *Safe*. Counter-measure is
     **VERIFIED**: Class 4 in `hazard.py:111-113` + rule 8 in `validate.py:131-133`.
   - Fragmented tools and magic numbers. Counter-measure **VERIFIED**: every threshold lives in
     `config.py`, enforced by the rule "All thresholds and paths live in config.py. No magic numbers
     elsewhere." (`.agents/rules/lunasafe.md:9`).

## 2. Stated objectives

`.agents/rules/lunasafe.md` is the authoritative rule set (10 lines) and implies these objectives.
Each is mapped to its implementation.

| # | Objective (from project rules/spec) | Implementation (VERIFIED) | Status |
| :---: | :--- | :--- | :--- |
| O1 | Keep the source lunar CRS from input rasters; never assign an Earth EPSG | `config.py:62`; guard in `io_utils.py:199-206`; tag writing in `io_utils.py:436-437` | Implemented |
| O2 | Centralise all thresholds/paths in `config.py` | `config.py` (152 lines, 60+ constants) | Implemented (with exceptions — see §4) |
| O3 | Never treat NoData as Safe | `terrain.py:82-85,133`; `hazard.py:89,132`; rule 9 `validate.py:135-137` | Implemented |
| O4 | Never label a published PSR mask as "independently predicted" | provenance strings `config.py:138-139`, `psr.py:215`; provenance note `validate.py:49-53`; truthful `UNLOADED` response `web_server.py:722-737` | Implemented |
| O5 | Every module must run on synthetic data and label outputs `SYNTHETIC DEMO` | `config.py:76`, fallback logic `main.py:60-80`, `io_utils.py:392-404` | Implemented |
| O6 | Deliver GeoTIFF/GeoJSON/Shapefile/PNG/PDF/CSV in `outputs/` | `config.py:30-49`, `main.py:216-230` | Implemented (19 files present) |
| O7 | Hazard matrix `H = 0.50S + 0.30R + 0.20D` + hard overrides | `hazard.py:41-54,100-106` | Implemented (see §5 for the D caveat) |
| O8 | Class 4 Shadowed-Unknown | `hazard.py:111-113`, `config.py:113` | Implemented |
| O9 | 9-point rule consistency audit | `validate.py:70-148` | Implemented and tested (`tests/test_validate.py:51-101`) |
| O10 | Slope sensitivity study | `validate.py:151-280` | Implemented and tested (`tests/test_validate.py:104-132`) |
| O11 | Publication-grade 300 DPI cartography | `mapping.py`, `config.PLOT_DPI = 300` (`config.py:144`) | Implemented and tested (`tests/test_mapping.py`) |
| O12 | Autonomous landing-site recommender (Top-3) | `ml_recommender.py:84-215` | Implemented (algorithmic; see §6) |
| O13 | Boulder / micro-hazard detector | `ml_recommender.py:18-81` | Implemented (deterministic filtering, not ML) |
| O14 | Web Mission Control with live recalculation | `web_server.py:411`, `web/app.js` | Implemented (not browser-verified in this run) |
| O15 | Run tests yourself before claiming success | `.agents/rules/lunasafe.md:13` | Followed in this run: 32 passed |

## 3. Original objectives vs. what is implemented

| Original intent (AUTHOR STATED) | Reality check |
| :--- | :--- |
| "Geodetically rigorous end-to-end system" | **Mostly true** for CRS handling; but web area math hardcodes 20 m/px (`web_server.py:470`) so displayed areas are not rigorous on real data |
| "Autonomous, AI-driven landing site selection" | **Partially true** — a deterministic distance-transform optimiser (`ml_recommender.py:100-149`); no learning, no model file |
| "Sub-meter boulder detection" | **Not achievable with the data** — the detector operates on a DEM whose native cell size is 20 m (synthetic) or 240 m (real). `mission_report.py:215` itself admits: *"DEM cell resolution … does not resolve boulders < 1 meter."* |
| "Verified 0 rule violations across 40,000 pixels" | **True for the current synthetic dataset** (200×200 = 40,000) — but the audit's own report is what certifies this, and the web endpoint under-reports Rule 4 (Issue I-03) |
| "IoU / F1 validation metrics" | **Misleading in the CLI pipeline** — self-comparison yields 1.0 by construction (`validate.py:303-308`). The web `/api/psr-validation` endpoint behaves better (Issue I-01) |
| "60 FPS / <20 ms recalculation" | **NOT VERIFIED** — no benchmark exists in the repo; the claim appears only in prose (`README.md:141`, `web_server.py:6`) |

## 4. Constraints imposed by the project rules

From `.agents/rules/lunasafe.md` (all VERIFIED as rules; compliance noted):

| Constraint | Compliance evidence | Violations found |
| :--- | :--- | :--- |
| Python 3.10+, venv, pinned `requirements.txt` | `requirements.txt` pins 12 packages; `.venv` is Python 3.13.0 | `requirement.txt` is a near-duplicate alias file (drift risk) |
| Libraries: numpy, scipy, rasterio, scikit-image, geopandas, shapely, matplotlib | All pinned; **scikit-image is pinned but never imported** in any source file (search → NOT FOUND) | Unused dependency |
| No magic numbers outside `config.py` | Mostly true in backend | Exceptions: `web_server.py:470` (20 m), `ml_recommender.py:138-140` (250 m science optimum), `prepare_lola_dataset.py:56` (−900 m), `mission_report.py:53-58` (hard-coded table) |
| Ask before downloading > 500 MB | The downloader fetches a ~10 MB JP2 (`web_server.py:633`) | Compliant |
| No Earth EPSG on lunar data | Guard + tests | Compliant |

## 5. Business rules (the classifier contract)

Written down in `.agents/rules/lunasafe.md:17-25`, implemented in `hazard.py`, re-implemented for
auditing in `validate.py`. **Any change to one must be mirrored in the other.**

| Rule | Definition | Code |
| :--- | :--- | :--- |
| Slope bands | Safe < 5°, Caution 5–<10°, Unsafe ≥ 10°, hard Unsafe ≥ 15° | `config.py:82-85` |
| Roughness bands | Safe < 1.5 m, Caution 1.5–<3 m, Unsafe ≥ 3 m, hard Unsafe ≥ 5 m | `config.py:89-92` |
| Score | `H = 0.50·min(slope/15,1) + 0.30·min(rough/5,1) + 0.20·D` | `hazard.py:41-54` |
| Class 1 Safe | non-PSR ∧ H < 0.25 ∧ slope < 5° ∧ roughness < 1.5 m | `hazard.py:119-125` |
| Class 2 Caution | non-PSR ∧ valid ∧ ¬Safe ∧ ¬Unsafe | `hazard.py:127-129` |
| Class 3 Unsafe | H ≥ 0.60 ∨ slope ≥ 15° ∨ roughness ≥ 5 m | `hazard.py:100-106` |
| Class 4 | PSR ∧ valid ∧ ¬Unsafe | `hazard.py:111-113` |
| Class 0 | ¬valid | `hazard.py:89,132` |

**Important caveat (VERIFIED):** because the pipeline passes no `shadow_fraction`
(`main.py:137-146`), `D = 0` (`hazard.py:46-48`), so in practice `H = 0.50·S + 0.30·R` and can never
exceed 0.80. The `0.20` shadow weight only matters if a fractional shadow raster is supplied — which
no caller in this repository does.

## 6. Success criteria for the project (how to judge it)

Suggested, grounded in what the system can actually demonstrate:

| Criterion | Measurable check | Status |
| :--- | :--- | :--- |
| Reproducible end-to-end run | `python main.py --force-synthetic` exits 0 and writes 15 artifacts | VERIFIED (via `tests/test_main.py`) |
| Self-consistency of the classifier | `validate.verify_rule_consistency()` → `total_violations == 0` | VERIFIED (`tests/test_validate.py:51-70`) |
| Auditor catches real errors | Injected violations detected ≥ 2 | VERIFIED (`tests/test_validate.py:73-101`) |
| No Earth datum contamination | `io_utils.inspect_raster()` raises on EPSG:4326 | VERIFIED (`tests/test_preprocessing.py:48-63`) |
| Test suite green | `pytest -q` | VERIFIED: 32 passed in 25.28 s |
| Interactive demo | Web console loads at `:8050` | NOT VERIFIED in this run (server code reviewed only) |
| Honest metrics | No fabricated accuracy numbers shown to users | **Partially failing** — see Issues I-01, I-10 |

## 7. Explicit non-goals

Stated by the project itself in `mission_report.py:211-218` (assumptions/limitations block):

- Regolith bearing capacity / soil firmness is **not modelled**.
- Long-term (diurnal) illumination modelling is **not performed** — single-frame lighting only.
- Boulder-scale obstacles below DEM resolution are **not resolved**.

Additionally NOT FOUND anywhere: multi-region mosaicking, tiling for very large rasters, GPU use,
user management, multi-user collaboration, or an API for third-party consumers.
