# DOCUMENTATION_COVERAGE — what this set covers (and what it does not)

**Snapshot:** 2026-10-17 · **Folder size:** 70 files ≈ 475 KB (26 core + 12 module + 9 feature +
4 architecture + 3 API + 3 testing + 6 change-history + 4 handover + 3 generation metadata).

---

## 1. Source-file → documentation coverage

### Backend (14 modules)
| Source | Primary doc(s) | Secondary |
| :--- | :--- | :--- |
| `config.py` | `12_ENVIRONMENT_CONFIGURATION.md`, `module_documentation/CONFIG_MODULE.md` | 04, 06, smoke test |
| `main.py` | `module_documentation/MAIN_PIPELINE.md`, `07_CODEBASE_DEEP_DIVE.md` (A1–A10) | 08, 13, 15 |
| `io_utils.py` | `module_documentation/IO_UTILS_MODULE.md` | 07 §A3, 10 §2–3, F-03 |
| `psr.py` | `module_documentation/PSR_MODULE.md`, `feature_documentation/FEATURE_02_PSR_MAPPING.md` | 07 §A4, 10 §3.2 |
| `terrain.py` | `module_documentation/TERRAIN_MODULE.md`, `FEATURE_03_TERRAIN_ANALYTICS.md` | 07 §A5 |
| `hazard.py` | `module_documentation/HAZARD_MODULE.md`, `FEATURE_01_HAZARD_CLASSIFICATION.md` | 10 §3.1, 23 |
| `validate.py` | `module_documentation/VALIDATE_MODULE.md`, `FEATURE_08_VALIDATION_AUDIT.md` | 07 §A8, 19 (I-01/03) |
| `mapping.py` | `module_documentation/MAPPING_MODULE.md` | 08 §2, FEATURE_09 (exports) |
| `mission_report.py` | `module_documentation/MISSION_REPORT_MODULE.md` | FEATURE_09, 19 (I-14) |
| `ml_recommender.py` | `module_documentation/ML_RECOMMENDER_MODULE.md`, `FEATURE_06_LANDING_SITES.md` | 10 §4.1, `LANDING_SITES_SCHEMA.md` |
| `web_server.py` | `module_documentation/WEB_SERVER_MODULE.md`, `09_API_REFERENCE.md`, `REST_API.md` | 16 (SEC), 05 (A1/A2/A5) |
| `export_web_data.py` | `module_documentation/TOOLING_MODULES.md` §1, `DATA_BUNDLE_SCHEMA.md` | 10 §4.2, 19 (I-06) |
| `prepare_lola_dataset.py` | `TOOLING_MODULES.md` §2 | FEATURE_09 §3, 19 (I-15) |
| `build_interactive_ui.py` | `TOOLING_MODULES.md` §3 | 03, 06 (legacy) |

### Frontend (3 first-party + 2 vendored)
| Source | Primary |
| :--- | :--- |
| `web/app.js` (≈4 561 L) | `FEATURE_04/05/06/07/08` (line anchors), `WEB_SERVER_MODULE.md` §frontend pointers |
| `web/index.html` (≈1 888 L) | same feature docs (tabs), 06 (tree) |
| `web/styles.css` (≈2 282 L) | feature docs (visual notes), 06 |
| `web/vendor/three.min.js`, `OrbitControls.js` | 04 (vendored, r128), 16 (SEC-07) |

### Tests (9 files / 32 cases)
`14_TESTING_AND_QUALITY_ASSURANCE.md` (full inventory) · `testing_documentation/TEST_CASES.md`
(TC-AUTO-01…32) · `TEST_EXECUTION_STATUS.md` (results + pyflakes baseline) · `TEST_PLAN.md`.

### Tooling & repo files
| File(s) | Covered in |
| :--- | :--- |
| `run*.bat/.ps1`, `view_ui.bat` | 13, 11 |
| `requirements.txt` / `requirement.txt` | 04, 19 (I-16) |
| `tests/`, `.agents/rules/lunasafe.md` | 14, README §7 |
| `dashboard.html` | 03, 06, TOOLING §3 |
| `data/*` | 10 §2, FEATURE_09 §3, `DOWNLOAD_INSTRUCTIONS` pointer |
| `outputs/*` (24 files) | 10 §3–4, both API schemas, 15 (debug) |

## 2. User need → coverage (objectives O1…O15 of doc 02)

| Need | Docs |
| :--- | :--- |
| Set up & run (CLI + web) | 11 → 13 + `handover/QUICK_START_CHECKLIST.md` |
| Understand architecture | 05 + `architecture/*.mmd` + 07 |
| Call/change the API | 09 + `api_documentation/*` |
| Change science behaviour | 07, module docs, F-01/02/03, 12 (threshold duplicates) |
| Change UI behaviour | F-04…F-08, `WEB_SERVER_MODULE.md` |
| Test safely | 14 + `testing_documentation/*` |
| Know what's broken | 19 + 24 (matrix) |
| Plan work (2 people) | 20 + `handover/OPEN_TASKS.md` + `TEAM_HANDOVER.md` |
| Release/deploy | 17 + `change_history/RELEASE_NOTES.md` |
| Onboard someone new | 00 + `handover/*` + 21 |
| Demo/pitch | 01, 03, pre-existing `PITCH_SCRIPT.md` |

## 3. Coverage gaps (known, accepted for this run)

| Gap | Why | Where it would live |
| :--- | :--- | :--- |
| Generated diagrams not rendered to PNG/SVG | Mermaid sources only (`.mmd`) — render is a viewer step | `architecture/` |
| No screenshots of the UI | binary assets out of scope (no project files touched) | future `feature_documentation/assets/` |
| `app.js` line anchors are approximate | 4.5k-line file; anchors are search-stable, not commit-pinned | all feature docs |
| Pre-existing docs (README, PROJECT_SPECIFICATION, PITCH) not rewritten | out of scope — overstated claims catalogued instead | 19 §E |
| Per-function API of pure helpers (small private fns) | covered by module-doc tables, not 1:1 signatures | module docs |

## 4. Integrity checks performed

- ✅ all 70 files exist with the names indexed in `../README.md` §5 (link check, see
  `DOCUMENTATION_CHANGELOG.md`)
- ✅ issue IDs `I-01…I-16`, `M-01…M-08`, `SEC-01…SEC-10` consistent across docs
- ✅ task IDs `T-01…T-24` all defined in doc 20 (T-15 was missing → added during this pass)
- ✅ cross-folder references (`api_documentation/*`, `testing_documentation/*`, `handover/*`,
  `change_history/*`, `_generation/*`) resolve
