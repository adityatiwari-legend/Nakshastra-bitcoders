# CHANGELOG

All notable changes to LunaSafe. Format inspired by [Keep a Changelog](https://keepachangelog.com/);
versions are **proposed** (the repo has no tags yet — see doc 18 §4).

## [Unreleased] — 2026-10-17

### Added
- `PROJECT_DOCUMENTATION/` — this documentation set (25 core docs, 4 architecture diagrams,
  12 module docs, 9 feature docs, 3 API schemas, 3 testing docs, 6 change-history docs,
  4 handover docs, 3 `_generation` metadata files). **Not yet committed** (untracked deliverable).

### Verification performed (2026-10-17)
- Full test suite executed: **32 passed, 1 warning in 25.28 s**; side effects on
  `outputs/lunasafe_hazard_map.pdf` and `outputs/psr_polygons.dbf` restored via
  `git checkout -- outputs/…` → tree clean again.
- Commit history, dependency inventory, REST routes, GeoTIFF tags, JSON schemas and frontend
  line anchors re-verified against source (evidence: every doc's VERIFIED/INFERRED labels).

### Fixed (documentation accuracy)
- Removed all references to a non-existent `config.MOON_CRS_WKT` → corrected to
  `config.LUNAR_SOUTH_POLE_PROJ4` (`config.py:62`) in docs 08, 10, 11.
- GeoTIFF tag/nodata tables in doc 10 rebuilt from actual `rasterio` tag reads.
- Landing-site field schema corrected to the real emitted keys
  (`ml_recommender.py:180-202`): `designation "Alpha"`, `ellipse_semi_major/minor_m`,
  measured `clearance_radius_m`, constant `status "APPROVED FOR DESCENT"`.

## [0.2.0] — 2026-10-17 — *"assets update"* (`fa36e99`)

### Added
- `PROJECT_SPECIFICATION.md` (350 lines).

### Changed
- `README.md` rewritten: 203 → 371 lines.
- Web UI polish: `web/app.js` (+155), `web/index.html` (+163), `web/styles.css` (+283),
  `web_server.py` (+38).

### Regenerated
- 15 files under `outputs/` (new grid/dataset), incl. `hazard_summary.csv`,
  `landing_sites.json`, full `psr_polygons.*` set (`.prj` content changed),
  map PNG/PDF; **new** `outputs/psr_polygons_bundle.zip`.

### Known problems introduced/left behind
- 🔴 **`outputs/web_data.json` was NOT regenerated** — it still encodes the older grid
  (see Issue **I-06**; staleness proven by `git log --stat`, doc 18 §2).
- ⚠ `__pycache__/mission_report.cpython-313.pyc` committed again (bytecode tracking, doc 18 §3).

## [0.1.0] — 2026-10-12 — *"solution for PSR"* (`c3d26dd`)

### Added — the entire product in one commit (89 files, 17 846 insertions)
- 7-phase CLI pipeline (`main.py`) + science core (`io_utils`, `psr`, `terrain`, `hazard`,
  `validate`, `mapping`, `ml_recommender`, `mission_report`) with `config.py` single source.
- Web "Mission Control" console: `web_server.py` (stdlib HTTP, 20 routes) + `web/` frontend
  (vanilla JS, vendored three.js) + legacy `dashboard.html`/`build_interactive_ui.py`.
- 32 tests in 9 files; NASA LOLA ingestion path (`prepare_lola_dataset.py`); launchers
  (`run.bat`, `run_website.*`, `view_ui.bat`).
- Data (synthetic DEM/PSR, LOLA JP2 + derived GeoTIFFs) and a full set of committed `outputs/`.
- Docs: `README.md`, `README_WEB.md`, `PITCH_SCRIPT.md`, `.agents/rules/lunasafe.md`.

### Security / hygiene debt recorded at birth
- 22 `__pycache__/*.pyc` files tracked; no root `.gitignore`; `requirement.txt` vs
  `requirements.txt` drift (Issue I-16); no CI, no tags.

---

*Conventions: issue IDs (`I-nn`), tasks (`T-nn`), security items (`SEC-nn`) are stable — see
[`../19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](../19_CURRENT_STATUS_AND_KNOWN_ISSUES.md) and
[`../20_ROADMAP_AND_NEXT_STEPS.md`](../20_ROADMAP_AND_NEXT_STEPS.md). Never renumber; only append.*
