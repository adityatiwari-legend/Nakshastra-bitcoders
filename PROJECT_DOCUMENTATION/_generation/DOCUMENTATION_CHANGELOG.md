# DOCUMENTATION_CHANGELOG — this generation run

Single-shot documentation pass. **Scope rule:** only files under `PROJECT_DOCUMENTATION/` were
created or edited; no project source/data/output file was modified (test-run side effects were
restored — see `../testing_documentation/TEST_EXECUTION_STATUS.md` §2).

---

## Run summary

| Item | Value |
| :--- | :--- |
| Date | 2026-10-17 |
| Base commit | `fa36e99` (branch `main`, tree clean apart from this folder) |
| Output | **70 files, ≈475 KB** — 26 core, 12 module, 9 feature, 4 architecture, 3 API, 3 testing, 6 change-history, 4 handover, 3 generation metadata |
| Verification | 32/32 tests green · pyflakes baseline (9) · 0 broken relative links (final check below) |

## Phase log

| # | Phase | Result |
| :-: | :--- | :--- |
| 1 | Repo/history/dependency discovery + full source reads | evidence base built (see `_generation/ANALYSIS_CHECKLIST.md` §2) |
| 2 | Core docs `00`–`24` + `README.md` | 26 files |
| 3 | Architecture diagrams (4 × Mermaid) | `architecture/` |
| 4 | Module docs (12) | `module_documentation/` |
| 5 | Feature docs F-01…F-09 (9) | `feature_documentation/` |
| 6 | API schemas (3) built from live JSON reads | `api_documentation/` |
| 7 | Testing docs (3), incl. located warning + pyflakes baseline | `testing_documentation/` |
| 8 | Change history (6) from `git` evidence | `change_history/` |
| 9 | Handover (4) | `handover/` |
| 10 | Metadata (3) + link validation | `_generation/` |

## Corrections applied during the run (docs were wrong → fixed)

| # | Wrong claim | Corrected to | Where |
| :-: | :--- | :--- | :--- |
| 1 | `config.MOON_CRS_WKT` referenced | `config.LUNAR_SOUTH_POLE_PROJ4` (`config.py:62`) | docs 08, 10, 11 |
| 2 | `write_geotiff` auto-injects tags | only caller-supplied tags; tables rebuilt from `rasterio` reads | doc 10 §2.1–3 |
| 3 | Landing-site schema: `designation "ALSS-SITE-01"`, `ellipse_center_*`, `ellipse_area_km2`, `status "ELIGIBLE"`, buffer field | real keys from `ml_recommender.py:180-202` (`"Alpha"`, `ellipse_semi_major/minor_m`, measured `clearance_radius_m`, constant `"APPROVED FOR DESCENT"`) | doc 10 §4.1, `ML_RECOMMENDER_MODULE.md` §4, `LANDING_SITES_SCHEMA.md` (new) |
| 4 | Bundle `bounds` keys `l/r/b/t`, `defaults` prose | `left/right/bottom/top`, exact 10 keys | doc 10 §4.2, `DATA_BUNDLE_SCHEMA.md` (new) |
| 5 | Fitness weights `0.35/0.35/0.30` | `0.35·clearance + 0.30·slope + 0.20·rough + 0.15·science` (`ml_recommender.py:143-148`) | `LANDING_SITES_SCHEMA.md` §2 |
| 6 | Single pytest warning = "third-party deprecation" | located: `NotGeoreferencedWarning` from `tests/test_preprocessing.py:55` itself (`-W error` run: 1 failed, 30 passed) | doc 14 §5, testing status §1 |
| 7 | "bundle export is a pipeline step" | `main.py` never calls `export_data_bundle()`; only `web_server.py:313,396` + `build_interactive_ui.py:14` (mtime evidence 10-11 vs 10-17) | doc 19 I-06 |
| 8 | — (new evidence) | `web_server.py:435 clearance_buf` parsed but unused → I-05 strengthened | doc 19 I-05, testing status §4 |
| 9 | `T-15` referenced but undefined (doc 10, doc 24, TOOLING) | task **T-15 "Bundle schema versioning" added** to doc 20 (P1) + M-C | doc 20 |
| 10 | Playwright smoke mapped to `T-16` (dep cleanup) | mapped to **T-20** per doc 20 | doc 14 §8, FEATURE_04, TEST_PLAN §8, testing status §5 |
| 11 | README index used a non-existent naming scheme (`21_TWO_MEMBER_TEAM_GUIDE`, `CONFIG_AND_IO`, `DATA_TOOLING`, feature files without `FEATURE_nn_`, missing `LANDING_SITES_SCHEMA`) | index rebuilt to actual filenames; `\_generation` backslash link fixed | `README.md` |
| 12 | Stale link `23_FAQ_AND_GLOSSARY.md` | `23_GLOSSARY_AND_ABBREVIATIONS.md` | `00_START_HERE.md` |
| 13 | doc 10 §4.1 write range `:247-270` | `:284-286` | doc 10 |
| 14 | Example numbers in `REST_API.md` were illustrative | replaced with values read from `outputs/hazard_summary.csv`, `inspect_raster` and the live bundle | `REST_API.md` |

## Final link validation

```
PROJECT_DOCUMENTATION/**/*.md  →  relative links checked: 169+
broken: 0   (script: markdown link regex → path exists; anchors/URLs excluded)
```
Last run: after corrections 11–13 (this file was the only false positive before it existed).

## Follow-ups for future doc edits

- Route/key changes → `09_API_REFERENCE.md` + `api_documentation/` in the same commit.
- Issue fixed → doc 19 (status + SHA) + this changelog's "corrections" table if a doc claim moved.
- Task completed → `handover/OPEN_TASKS.md` ⬜→✅ and doc 20.
- Re-run the link script + `ANALYSIS_CHECKLIST.md` §2 commands before handing the folder over.
