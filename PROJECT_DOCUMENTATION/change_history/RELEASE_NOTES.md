# Release Notes — v0.1.0 (and v0.2.0 asset update)

Derived from the two commits in `git log` (verified 2026-10-17). There are **no git tags** yet —
tagging `v0.1.0` at demo time is task T-14 (doc 18 §4, doc 17 §4).

---

## v0.1.0 — *"solution for PSR"* — 2026-10-12 (`c3d26dd`)

**One commit, 89 files, 17 846 insertions — the full product.**

### What you get
- **CLI 7-phase pipeline** (`python main.py`): ingest → PSR delineation → terrain metrics →
  5-class hazard surface → 4-panel cartography → 9-rule consistency audit → autonomous
  landing-site recommender. Produces 13+ artifacts under `outputs/`.
- **Web Mission Control console** (`run_website.bat` → `http://localhost:8050`): live threshold
  sliders with ~ms reclassification, Map Studio (7 layers + pixel inspector), 3D terrain with
  sun/shadow and transect tool, ALSS landing-site cards, mission-report view, validation/audit
  panels, offline demo mode, NASA LOLA download.
- **Tests:** 32 pytest cases across 9 files (science core + end-to-end).
- **Data:** synthetic DEM/PSR fixtures + committed LOLA South Pole JP2 (10.5 MB) and derived
  GeoTIFFs; artifacts committed so a demo runs without a re-run.
- **Launchers:** `run.bat` (pipeline), `run_website.bat`/`.ps1` (server, port 8050→8080),
  `view_ui.bat` (static).

### Supported configuration (verified)
Windows + Python 3.13 venv; pinned `requirements.txt` (numpy, scipy, rasterio, geopandas,
shapely, matplotlib, pyproj, scikit-image, pandas, pytest). No database, no network required
after data is present (CDN fonts/KaTeX degrade gracefully offline; three.js is vendored).

### Known issues at release (full register: doc 19)
| ID | One-liner |
| :-- | :--- |
| I-01 | PSR validation compares `mask` with `mask` → metrics always 1.0 |
| I-02 | Web areas assume 20 m/px → wrong on 240 m real data (144×) |
| I-03 | Rule-4 audit key mismatch → always reported as 0 violations |
| I-04 | Slider values don't reach the pipeline subprocess |
| I-05 | 40 m clearance buffer never applied |
| I-06 | `web_data.json` older than the rasters it encodes (see v0.2.0) |
| I-07…I-16 | shadow term always 0 · heuristic PSR · no trained model · hard-coded UI charts · fake `crs_valid` · dead routes · path traversal/CORS-over-`*` · hard-coded report stats · hard-coded converter path · requirements drift |
| SEC-01…10 | security register (doc 16) |

**Honesty note:** PSR accuracy is reported as `UNLOADED` when no independent reference exists —
by design (project rule: never invent accuracy numbers).

---

## v0.2.0 — *"assets update"* — 2026-10-17 (`fa36e99`)

**26 files, +1 207 / −438.**

- **New:** `PROJECT_SPECIFICATION.md` (350 L). **README** rewritten (203 → 371 L).
- **UI polish:** `app.js`/`index.html`/`styles.css`/`web_server.py` edited.
- **Artifacts regenerated** (15 files): new `hazard_summary.csv` (5-class totals now sum to the
  40 000-pixel grid), rewritten `landing_sites.json`, complete `psr_polygons.*` set (`.prj`
  updated), new `psr_polygons_bundle.zip`, re-rendered map PNG/PDF and analysis charts.
- 🔴 **`web_data.json` not regenerated** → the committed UI bundle still encodes the previous
  grid (Issue I-06; demonstrable via `git log --stat outputs/`).

---

## Upgrade / compatibility notes (v0.1 → v0.2)

No breaking contract changes: routes, JSON keys, artifact names and class IDs are unchanged.
Consumers only need to re-pull `outputs/` (and rebuild the bundle: `python export_web_data.py`).

## Verification status of each release

| | v0.1.0 | v0.2.0 | current `main` |
| :-- | :-: | :-: | :-: |
| `pytest -q` | ✅ (32) | ✅ (32, re-run 2026-10-17) | ✅ |
| `outputs/` consistent with `web_data.json` | ✅ at commit | 🔴 no (I-06) | 🔴 no |
| Security issues closed | — | none | none (SEC register open) |
