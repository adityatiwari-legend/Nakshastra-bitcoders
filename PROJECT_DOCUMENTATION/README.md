# LunaSafe — Project Documentation Index

> **Documentation generation run:** 2026-10-17
> **Repository:** `https://github.com/kushbansal2005/ORBISLUNA.git` (local root: `E:\sistec\LunaSafe`)
> **Branch at generation time:** `main` (clean working tree, 2 commits)
>
> Every claim in this folder is labelled `VERIFIED`, `PARTIALLY VERIFIED`, `INFERRED`, `NOT FOUND` or `PLANNED`
> according to the evidence rules defined in [`_generation/ANALYSIS_CHECKLIST.md`](_generation/ANALYSIS_CHECKLIST.md).

---

## 1. What the project is

**LunaSafe** is a Python geospatial pipeline + web "Mission Control" console that screens the Lunar South
Pole for safe landing sites. It takes a Digital Elevation Model (DEM) and a Permanently Shadowed Region
(PSR) mask, derives terrain metrics, classifies every pixel into one of five hazard classes, recommends
the top-3 landing ellipses, and renders publication-grade maps and a PDF mission report.

- **Domain:** planetary GIS / lunar landing-site selection (Artemis-era South Pole, 80°S–90°S).
- **Problem statement:** "Hackathon Problem Statement 02 — Lunar Landing Site Characterization"
  (see [`.agents/rules/lunasafe.md`](../.agents/rules/lunasafe.md) and [`../PROJECT_SPECIFICATION.md`](../PROJECT_SPECIFICATION.md)).
- **Two run modes (both VERIFIED):**
  1. **Headless CLI pipeline** — `python main.py` → 15 artifacts in `outputs/`.
  2. **Web Mission Control** — `python web_server.py` → `http://localhost:8050/`.

## 2. Verified implementation status (snapshot)

| Area | Status | Evidence |
| :--- | :--- | :--- |
| CLI 7-phase pipeline | **Implemented and verified** | `main.py:38-234`; executed successfully during this documentation run (indirectly, via `pytest tests/test_main.py`) |
| Unit/integration tests (32) | **Implemented and verified — 32 passed in 25.28 s, 1 warning** | Executed with `.venv/Scripts/python.exe -m pytest -q` on 2026-10-17 (see [`testing_documentation/TEST_EXECUTION_STATUS.md`](testing_documentation/TEST_EXECUTION_STATUS.md)) |
| 5-class hazard classifier + 9-rule audit | **Implemented and verified** | `hazard.py:61-134`, `validate.py:70-148` |
| PSR delineation + vector export | **Implemented and verified** | `psr.py:174-269` |
| Terrain metrics (Horn slope/aspect, roughness, TRI) | **Implemented and verified** | `terrain.py:21-196` |
| 300 DPI 4-panel cartography | **Implemented and verified** | `mapping.py:149-380` |
| Landing-site recommender + boulder detector | **Implemented and verified (algorithmic)** | `ml_recommender.py:18-215` — no trained model; deterministic signal processing |
| Web REST API + 2D/3D console | **Implemented and partially verified** | `web_server.py`, `web/` — server code reviewed; browser UI **not** executed during this run |
| "AI"/"ML" claims in marketing text | **PARTIALLY VERIFIED / misleading label** | No training, no model file, no learned weights exist — see [`19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](19_CURRENT_STATUS_AND_KNOWN_ISSUES.md) Issue **I-09** |
| Deployment / CI / CD | **NOT FOUND** | No Dockerfile, no workflow files, no `pyproject.toml`, no CI config |
| Database | **NOT APPLICABLE** | File-based raster/CSV/JSON storage only — see [`10_DATABASE_AND_DATA_MODEL.md`](10_DATABASE_AND_DATA_MODEL.md) |
| Authentication / authorization | **NOT FOUND** | `web_server.py` has no auth of any kind — see [`16_SECURITY_AND_PRIVACY_REVIEW.md`](16_SECURITY_AND_PRIVACY_REVIEW.md) |

## 3. Technology stack (short form)

| Layer | Technology | Where |
| :--- | :--- | :--- |
| Language | Python 3.13.0 (verified in `.venv`) | whole backend |
| Scientific | numpy 2.5.3, scipy 1.18.1, pandas 3.0.6 | `terrain.py`, `hazard.py`, `psr.py`, `ml_recommender.py` |
| Geospatial | rasterio 1.5.2, geopandas 1.2.0, shapely 2.2.0, pyproj 3.8.0, scikit-image 0.26.0 | `io_utils.py`, `psr.py` |
| Visualisation | matplotlib 3.11.2 (Agg backend) | `mapping.py`, `terrain.py`, `validate.py`, `mission_report.py` |
| HTTP server | Python stdlib `http.server.ThreadingHTTPServer` (no Flask/Django) | `web_server.py` |
| Frontend | Vanilla HTML/CSS/JS, three.js **r128** (vendored), KaTeX 0.16.8 (CDN) | `web/index.html`, `web/app.js`, `web/styles.css` |
| Tests | pytest 9.1.1 | `tests/` |

Full detail: [`04_TECH_STACK_AND_DEPENDENCIES.md`](04_TECH_STACK_AND_DEPENDENCIES.md).

## 4. Reading order for the two team members

| Order | Document | Why |
| :---: | :--- | :--- |
| 1 | [`00_START_HERE.md`](00_START_HERE.md) | First-day onboarding plan and one traced feature |
| 2 | [`01_PROJECT_OVERVIEW.md`](01_PROJECT_OVERVIEW.md) | What exists, what does not |
| 3 | [`05_SYSTEM_ARCHITECTURE.md`](05_SYSTEM_ARCHITECTURE.md) + [`architecture/system_architecture.mmd`](architecture/system_architecture.mmd) | How the parts fit |
| 4 | [`11_SETUP_AND_INSTALLATION.md`](11_SETUP_AND_INSTALLATION.md) → [`13_HOW_TO_RUN_THE_PROJECT.md`](13_HOW_TO_RUN_THE_PROJECT.md) | Get it running yourself |
| 5 | [`07_CODEBASE_DEEP_DIVE.md`](07_CODEBASE_DEEP_DIVE.md) + module docs in [`module_documentation/`](module_documentation/) | Understand the code |
| 6 | [`09_API_REFERENCE.md`](09_API_REFERENCE.md) + [`08_DATA_FLOW_AND_WORKFLOWS.md`](08_DATA_FLOW_AND_WORKFLOWS.md) | Understand the web layer |
| 7 | [`14_TESTING_AND_QUALITY_ASSURANCE.md`](14_TESTING_AND_QUALITY_ASSURANCE.md) | How to prove your change is safe |
| 8 | [`19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](19_CURRENT_STATUS_AND_KNOWN_ISSUES.md) | What is broken today |
| 9 | [`handover/QUICK_START_CHECKLIST.md`](handover/QUICK_START_CHECKLIST.md) + [`handover/TEAM_HANDOVER.md`](handover/TEAM_HANDOVER.md) | How to split the work (two-person) |
| 10 | [`handover/OPEN_TASKS.md`](handover/OPEN_TASKS.md) | What to build first (M-A…M-D) |

## 5. Documentation map

### Core guides
- [`00_START_HERE.md`](00_START_HERE.md) — onboarding, reading order, first-day checklist
- [`01_PROJECT_OVERVIEW.md`](01_PROJECT_OVERVIEW.md) — verified product overview
- [`02_PROBLEM_STATEMENT_AND_OBJECTIVES.md`](02_PROBLEM_STATEMENT_AND_OBJECTIVES.md) — problem, objectives, boundaries
- [`03_FEATURES_AND_IMPLEMENTATION_STATUS.md`](03_FEATURES_AND_IMPLEMENTATION_STATUS.md) — feature × status matrix
- [`04_TECH_STACK_AND_DEPENDENCIES.md`](04_TECH_STACK_AND_DEPENDENCIES.md) — every dependency and why it is used
- [`05_SYSTEM_ARCHITECTURE.md`](05_SYSTEM_ARCHITECTURE.md) — architecture, decisions, failure paths
- [`06_REPOSITORY_STRUCTURE.md`](06_REPOSITORY_STRUCTURE.md) — annotated directory tree
- [`07_CODEBASE_DEEP_DIVE.md`](07_CODEBASE_DEEP_DIVE.md) — startup → request → response, file by file
- [`08_DATA_FLOW_AND_WORKFLOWS.md`](08_DATA_FLOW_AND_WORKFLOWS.md) — numbered workflows + Mermaid diagrams
- [`09_API_REFERENCE.md`](09_API_REFERENCE.md) — all 20 verified HTTP routes
- [`10_DATABASE_AND_DATA_MODEL.md`](10_DATABASE_AND_DATA_MODEL.md) — no DB; file/JSON/GeoTIFF data model
- [`11_SETUP_AND_INSTALLATION.md`](11_SETUP_AND_INSTALLATION.md) — clean-machine setup
- [`12_ENVIRONMENT_CONFIGURATION.md`](12_ENVIRONMENT_CONFIGURATION.md) — configuration surface (no env vars exist)
- [`13_HOW_TO_RUN_THE_PROJECT.md`](13_HOW_TO_RUN_THE_PROJECT.md) — run / stop / verify
- [`14_TESTING_AND_QUALITY_ASSURANCE.md`](14_TESTING_AND_QUALITY_ASSURANCE.md) — test strategy and gaps
- [`15_DEBUGGING_AND_TROUBLESHOOTING.md`](15_DEBUGGING_AND_TROUBLESHOOTING.md) — symptom → cause → fix
- [`16_SECURITY_AND_PRIVACY_REVIEW.md`](16_SECURITY_AND_PRIVACY_REVIEW.md) — findings with severity
- [`17_DEPLOYMENT_AND_RELEASE_GUIDE.md`](17_DEPLOYMENT_AND_RELEASE_GUIDE.md) — nothing deployed; proposal labelled as such
- [`18_GIT_WORKFLOW_AND_CHANGE_HISTORY.md`](18_GIT_WORKFLOW_AND_CHANGE_HISTORY.md) — 2-commit history, evidence based
- [`19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](19_CURRENT_STATUS_AND_KNOWN_ISSUES.md) — issue register (I-01…I-16, M-01…M-08, SEC-01…10)
- [`20_ROADMAP_AND_NEXT_STEPS.md`](20_ROADMAP_AND_NEXT_STEPS.md) — prioritised task list with acceptance criteria
- [`21_FAQ_AND_COMMON_QUESTIONS.md`](21_FAQ_AND_COMMON_QUESTIONS.md) — common errors and answers
- [`22_CONTRIBUTING_AND_CODE_CONVENTIONS.md`](22_CONTRIBUTING_AND_CODE_CONVENTIONS.md) — safe change workflow + checklists
- [`23_GLOSSARY_AND_ABBREVIATIONS.md`](23_GLOSSARY_AND_ABBREVIATIONS.md) — terms and acronyms
- [`24_CROSS_REFERENCE_MATRIX.md`](24_CROSS_REFERENCE_MATRIX.md) — feature × code × tests × issues matrix

### Diagrams
- [`architecture/system_architecture.mmd`](architecture/system_architecture.mmd)
- [`architecture/component_diagram.mmd`](architecture/component_diagram.mmd)
- [`architecture/data_flow_diagram.mmd`](architecture/data_flow_diagram.mmd)
- [`architecture/database_er_diagram.mmd`](architecture/database_er_diagram.mmd) — data *files*, no tables

### Module documentation (one file per backend module/topic)
- [`module_documentation/CONFIG_MODULE.md`](module_documentation/CONFIG_MODULE.md) — `config.py`
- [`module_documentation/IO_UTILS_MODULE.md`](module_documentation/IO_UTILS_MODULE.md) — `io_utils.py`
- [`module_documentation/MAIN_PIPELINE.md`](module_documentation/MAIN_PIPELINE.md) — `main.py`
- [`module_documentation/PSR_MODULE.md`](module_documentation/PSR_MODULE.md) — `psr.py`
- [`module_documentation/TERRAIN_MODULE.md`](module_documentation/TERRAIN_MODULE.md) — `terrain.py`
- [`module_documentation/HAZARD_MODULE.md`](module_documentation/HAZARD_MODULE.md) — `hazard.py`
- [`module_documentation/VALIDATE_MODULE.md`](module_documentation/VALIDATE_MODULE.md) — `validate.py`
- [`module_documentation/MAPPING_MODULE.md`](module_documentation/MAPPING_MODULE.md) — `mapping.py`
- [`module_documentation/MISSION_REPORT_MODULE.md`](module_documentation/MISSION_REPORT_MODULE.md) — `mission_report.py`
- [`module_documentation/ML_RECOMMENDER_MODULE.md`](module_documentation/ML_RECOMMENDER_MODULE.md) — `ml_recommender.py`
- [`module_documentation/WEB_SERVER_MODULE.md`](module_documentation/WEB_SERVER_MODULE.md) — `web_server.py`
- [`module_documentation/TOOLING_MODULES.md`](module_documentation/TOOLING_MODULES.md) — `export_web_data.py`, `prepare_lola_dataset.py`, `build_interactive_ui.py`

### Feature documentation (F-01…F-09)
- [`feature_documentation/FEATURE_01_HAZARD_CLASSIFICATION.md`](feature_documentation/FEATURE_01_HAZARD_CLASSIFICATION.md)
- [`feature_documentation/FEATURE_02_PSR_MAPPING.md`](feature_documentation/FEATURE_02_PSR_MAPPING.md)
- [`feature_documentation/FEATURE_03_TERRAIN_ANALYTICS.md`](feature_documentation/FEATURE_03_TERRAIN_ANALYTICS.md)
- [`feature_documentation/FEATURE_04_MAP_STUDIO.md`](feature_documentation/FEATURE_04_MAP_STUDIO.md)
- [`feature_documentation/FEATURE_05_3D_TERRAIN.md`](feature_documentation/FEATURE_05_3D_TERRAIN.md)
- [`feature_documentation/FEATURE_06_LANDING_SITES.md`](feature_documentation/FEATURE_06_LANDING_SITES.md)
- [`feature_documentation/FEATURE_07_LIVE_RECLASSIFICATION.md`](feature_documentation/FEATURE_07_LIVE_RECLASSIFICATION.md)
- [`feature_documentation/FEATURE_08_VALIDATION_AUDIT.md`](feature_documentation/FEATURE_08_VALIDATION_AUDIT.md)
- [`feature_documentation/FEATURE_09_EXPORTS_REPORT_INGESTION.md`](feature_documentation/FEATURE_09_EXPORTS_REPORT_INGESTION.md)

### API documentation
- [`api_documentation/REST_API.md`](api_documentation/REST_API.md) — per-endpoint contracts
- [`api_documentation/DATA_BUNDLE_SCHEMA.md`](api_documentation/DATA_BUNDLE_SCHEMA.md) — `outputs/web_data.json`
- [`api_documentation/LANDING_SITES_SCHEMA.md`](api_documentation/LANDING_SITES_SCHEMA.md) — `outputs/landing_sites.json`

### Testing
- [`testing_documentation/TEST_PLAN.md`](testing_documentation/TEST_PLAN.md)
- [`testing_documentation/TEST_CASES.md`](testing_documentation/TEST_CASES.md)
- [`testing_documentation/TEST_EXECUTION_STATUS.md`](testing_documentation/TEST_EXECUTION_STATUS.md)

### Change history
- [`change_history/CHANGELOG.md`](change_history/CHANGELOG.md)
- [`change_history/RELEASE_NOTES.md`](change_history/RELEASE_NOTES.md)
- [`change_history/COMMITS.md`](change_history/COMMITS.md)
- [`change_history/IMPLEMENTATION_TIMELINE.md`](change_history/IMPLEMENTATION_TIMELINE.md)
- [`change_history/ARCHITECTURAL_DECISIONS.md`](change_history/ARCHITECTURAL_DECISIONS.md)
- [`change_history/MIGRATION_NOTES.md`](change_history/MIGRATION_NOTES.md)

### Handover
- [`handover/QUICK_START_CHECKLIST.md`](handover/QUICK_START_CHECKLIST.md)
- [`handover/TEAM_HANDOVER.md`](handover/TEAM_HANDOVER.md)
- [`handover/OPEN_TASKS.md`](handover/OPEN_TASKS.md)
- [`handover/KNOWLEDGE_GAPS.md`](handover/KNOWLEDGE_GAPS.md)

### Generation metadata
- [`_generation/ANALYSIS_CHECKLIST.md`](_generation/ANALYSIS_CHECKLIST.md)
- [`_generation/DOCUMENTATION_COVERAGE.md`](_generation/DOCUMENTATION_COVERAGE.md)
- [`_generation/DOCUMENTATION_CHANGELOG.md`](_generation/DOCUMENTATION_CHANGELOG.md)

## 6. Pre-existing project documents (not created by this run)

| File | Role |
| :--- | :--- |
| [`../README.md`](../README.md) | Project marketing/readme (some claims overstated — cross-check with [`03_FEATURES_AND_IMPLEMENTATION_STATUS.md`](03_FEATURES_AND_IMPLEMENTATION_STATUS.md)) |
| [`../README_WEB.md`](../README_WEB.md) | Web-platform readme + Mermaid diagram |
| [`../PROJECT_SPECIFICATION.md`](../PROJECT_SPECIFICATION.md) | Long-form specification / feature dossier |
| [`../PITCH_SCRIPT.md`](../PITCH_SCRIPT.md) | 5-minute pitch script + 8 judge Q&A |
| [`../data/DOWNLOAD_INSTRUCTIONS.md`](../data/DOWNLOAD_INSTRUCTIONS.md) | NASA/USGS data ingestion guide |
| [`../.agents/rules/lunasafe.md`](../.agents/rules/lunasafe.md) | Machine-readable project rules the code must obey |

## 7. Non-negotiable project rules (extracted from `.agents/rules/lunasafe.md`)

1. Never assign an Earth EPSG code to lunar data; keep the native lunar CRS.
2. All thresholds/paths live in `config.py` — no magic numbers elsewhere.
3. Never treat NoData as Safe. Never label a published PSR mask as "independently predicted".
4. Every module must run on synthetic data when real data is missing and must label outputs `SYNTHETIC DEMO`.
5. After writing code, run it **and** the tests; do not report success until the commands pass.
6. Ask before downloading files larger than 500 MB.
