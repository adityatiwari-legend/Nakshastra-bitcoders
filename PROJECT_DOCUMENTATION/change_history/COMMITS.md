# COMMITS — per-commit digest & reproduction

Repo: `https://github.com/kushbansal2005/ORBISLUNA.git` · branch `main` · 2 commits · author Kush ·
no tags, no merges (verified 2026-10-17).

---

## 1. `c3d26dd` — *"solution for PSR"*

| Field | Value |
| :--- | :--- |
| Full hash | `c3d26dd70d8922cc6af32fe4720351383f460bf2` |
| Date | 2026-10-12 11:08:53 +0530 |
| Size | 89 files changed, **17 846 insertions(+)** (root commit) |

### File-level digest (grouped)
| Group | Files (insertions) |
| :--- | :--- |
| Backend | `config.py` 152 · `main.py` 260 · `io_utils.py` 464 · `psr.py` 269 · `terrain.py` 425 · `hazard.py` 263 · `validate.py` 357 · `mapping.py` 380 · `ml_recommender.py` 303 · `mission_report.py` 229 |
| Web | `web_server.py` 844 · `web/app.js` 4 473 · `web/index.html` 1 879 · `web/styles.css` 2 282 · `web/vendor/three.min.js`, `web/vendor/OrbitControls.js` 1 045 |
| Tooling | `export_web_data.py` 112 · `prepare_lola_dataset.py` 107 · `build_interactive_ui.py` 1 131 · `dashboard.html` 1 100 · `view_ui.bat` 3 |
| Tests | `tests/` 9 modules + `__init__.py` (32 cases) |
| Data | `data/ldem_75s_240m.jp2` (10.5 MB) · `lola_south_pole_dem.tif` · `lola_psr_mask.tif` · `synthetic_dem.tif` · `synthetic_psr.tif` · `DOWNLOAD_INSTRUCTIONS.md` |
| Outputs | full artifact set incl. `mission_report.pdf`, `landing_sites.json`, **`web_data.json`** (only ever appears here) |
| Docs | `README.md` 203 · `README_WEB.md` 138 · `PITCH_SCRIPT.md` 136 · `.agents/rules/lunasafe.md` 25 |
| Env | `requirements.txt` 12 · `requirement.txt` 11 · `run.bat` · `run_website.bat`/`.ps1` |
| ⚠ Junk | 12 root + 10 `tests/` `__pycache__/*.pyc` (23 binaries) |

### View it
```powershell
git show --stat c3d26dd
git show c3d26dd:web_server.py | Select-Object -First 40    # file as committed
git diff c3d26dd^..c3d26dd -- config.py                     # (root commit: use c3d26dd -- config.py)
```

---

## 2. `fa36e99` — *"assets update"*

| Field | Value |
| :--- | :--- |
| Full hash | `fa36e9964058603a7c2589e318a7a4c710135785` |
| Date | 2026-10-17 16:51:21 +0530 |
| Size | 26 files changed, **1 207 insertions(+), 438 deletions(−)** |

### File-level digest
| Category | Files |
| :--- | :--- |
| New | `PROJECT_SPECIFICATION.md` +350 |
| Docs | `README.md` 203 → 371 (net +168) |
| UI | `web/app.js` +155 · `web/index.html` +163 · `web/styles.css` +283 · `web_server.py` +38 |
| Outputs regenerated (15) | `hazard_summary.csv` (10 lines), `landing_sites.json` (+265/−…), `psr_polygons.{shp,shx,dbf,prj,geojson}` rewritten, **new** `psr_polygons_bundle.zip`, `hazard_classes.tif`, `psr_binary.tif`, `slope_deg.tif`, `aspect_deg.tif`, `roughness_{std,tri}_m.tif`, `boulder_hazard.tif`, map PNG/PDF, `slope_sensitivity.png`, `terrain_histograms.png` |
| ⚠ Junk | `__pycache__/mission_report.cpython-313.pyc` re-committed |
| **Missing** | **`outputs/web_data.json` — not touched** ⇒ Issue I-06 |

### View it / prove the staleness
```powershell
git show --stat fa36e99
git log --oneline -- outputs/web_data.json      # only c3d26dd
git log --oneline -- outputs/slope_deg.tif      # both commits (rewritten in fa36e99)
```

---

## 3. How to reproduce each release state

```powershell
git clone https://github.com/kushbansal2005/ORBISLUNA.git lunasafe
cd lunasafe
git checkout c3d26dd          # v0.1.0 state
git checkout fa36e99          # v0.2.0 / current main state

# sanity after any checkout (venv from 11_SETUP_AND_INSTALLATION.md)
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests\test_main.py
.\.venv\Scripts\python.exe -m pytest -q           # full, destructive → restore outputs/ after
git status --porcelain outputs/                   # expect clean (see testing doc §2)
```

## 4. Things that cannot be reproduced from git alone

- **The exact environment of the original author** — only the two requirement files exist; they
  disagree (`requirements.txt` vs `requirement.txt`, Issue I-16); the verified venv used
  `requirements.txt` on 2026-10-17.
- **Intermediate work** — there are no WIP commits; both commits are squashed end states.
- **`outputs/` byte-identity** — regenerating on another machine/mplib version changes binary
  encodings (observed: the test run re-encoded `lunasafe_hazard_map.pdf` and `psr_polygons.dbf`).

## 5. Commit-message history (verbatim)

```
c3d26dd solution for PSR
fa36e99 assets update
```
Recommended next style (doc 18 §4): `<type>: <summary>` + body with issue IDs, e.g.
`fix: rule-4 audit key mismatch (I-03)`.
