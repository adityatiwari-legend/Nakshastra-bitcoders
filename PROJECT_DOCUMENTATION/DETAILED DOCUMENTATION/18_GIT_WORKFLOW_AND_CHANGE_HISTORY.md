# 18 — Git Workflow and Change History

*Verified with `git log --stat` on 2026-10-17. Working tree state at that moment: **clean except
the untracked `PROJECT_DOCUMENTATION/` folder added by this documentation task** (no existing file
was modified).*

---

## 1. Repository identity

| Item | Value |
| :--- | :--- |
| Remote | `https://github.com/kushbansal2005/ORBISLUNA.git` |
| Active branch | `main` (only branch) |
| Commits | **2** |
| Author | Kush `<bansalkush2005@gmail.com>` (both commits) |
| Tracked files | **91** |
| Tags | none |
| `.gitignore` at root | **absent** (the only ignore file is `.venv/.gitignore` containing `*`) |
| Merge/PR history | none — direct commits to `main` |

---

## 2. Full change history

### `c3d26dd` — *"solution for PSR"* — 2026-10-12 11:08 +0530
**89 files changed, 17 846 insertions(+)** — the entire product landed in one commit.

| Group | Contents |
| :--- | :--- |
| Backend (10) | `config.py` 152 L · `main.py` 260 · `io_utils.py` 464 · `psr.py` 269 · `terrain.py` 425 · `hazard.py` 263 · `validate.py` 357 · `mapping.py` 380 · `ml_recommender.py` 303 · `mission_report.py` 229 |
| Web (5) | `web_server.py` 844 · `web/app.js` **4 473** · `web/index.html` 1 879 · `web/styles.css` 2 282 · vendored `three.min.js` + `OrbitControls.js` |
| Tooling (5) | `export_web_data.py` 112 · `prepare_lola_dataset.py` 107 · `build_interactive_ui.py` 1 131 · `dashboard.html` 1 100 · `view_ui.bat` |
| Tests (10) | `tests/` 9 modules + `__init__.py` (32 tests) |
| Data (6) | synthetic DEM/PSR, LOLA JP2 (10.5 MB), `lola_*.tif`, `DOWNLOAD_INSTRUCTIONS.md` |
| Outputs (24) | full artifact set incl. `mission_report.pdf`, `landing_sites.json`, **`web_data.json`** |
| Docs (4) | `README.md` 203 L · `README_WEB.md` · `PITCH_SCRIPT.md` · `.agents/rules/lunasafe.md` |
| Env (4) | `requirements.txt` 12 L · `requirement.txt` 11 L · `run.bat` · `run_website.bat/.ps1` |
| ⚠ Junk (23) | **12 `__pycache__/*.pyc`** + **10 `tests/__pycache__/*.pyc`** committed |

### `fa36e99` — *"assets update"* — 2026-10-17 16:51 +0530
**26 files changed, 1 207 insertions(+), 438 deletions(−)** — docs + UI polish + regenerated artifacts.

| Change | Files |
| :--- | :--- |
| **New** | `PROJECT_SPECIFICATION.md` (350 L) |
| **Rewritten** | `README.md` (203 → 371 lines, net +168) |
| **UI edits** | `web/app.js` +155/−?, `web/index.html` +163/−?, `web/styles.css` +283/−?, `web_server.py` +38/−? |
| **Regenerated outputs** | 15 files — most notably `hazard_summary.csv` (10 lines), `landing_sites.json` (265 lines), `psr_polygons.*` (all rewritten, `.prj` content changed), map PNG/PDF smaller, **new** `psr_polygons_bundle.zip` |
| ⚠ Junk | `__pycache__/mission_report.cpython-313.pyc` updated again |

### The staleness evidence for Issue I-06 (read this in `git log --stat`)

- `outputs/web_data.json` appears **only in `c3d26dd`** (2026-10-12).
- Every raster it should mirror (`slope_deg.tif`, `roughness_*`, `hazard_classes.tif`,
  `psr_binary.tif`, …) was rewritten in `fa36e99` (2026-10-17).
- ⇒ **The committed UI bundle is 5 days older than the rasters it encodes.** Exactly the
  inconsistency described in `19_CURRENT_STATUS_AND_KNOWN_ISSUES.md` (I-06).

---

## 3. Current tracked layout (top-level → count of files)

| Path | Kind | Tracked? |
| :--- | :--- | :-: |
| `*.py` (14 modules) | source | ✅ |
| `tests/` (10) | tests | ✅ |
| `web/` (4 + `vendor/` 2) | frontend | ✅ |
| `data/` (6, incl. 10.5 MB JP2) | inputs | ✅ |
| `outputs/` (24 binaries + csv/json) | generated | ✅ ⚠ |
| `__pycache__/` + `tests/__pycache__/` (22) | bytecode | ✅ ⚠ |
| `.agents/rules/lunasafe.md` | rules | ✅ |
| `README*.md`, `PITCH_SCRIPT.md`, `PROJECT_SPECIFICATION.md` | docs | ✅ |
| `requirement.txt` | near-duplicate | ✅ ⚠ (I-16) |
| `dashboard.html`, `view_ui.bat` | legacy UI | ✅ |
| `PROJECT_DOCUMENTATION/` | this task | ❌ untracked (deliverable) |

---

## 4. Workflow conventions: what exists vs what is needed

| Aspect | Current | Recommended for a 2-person team |
| :--- | :--- | :--- |
| Branching | everything on `main` | short-lived branches: `feat/*`, `fix/*`, `docs/*` → PR → review |
| Commit style | free text, 1–2 words | `<type>: <summary>` with a body listing issue IDs (`fix: rule4 audit key (I-03)`) |
| Pre-commit checks | none | script `check.bat`: `pyflakes` + `pytest -q --ignore=tests/test_main.py` |
| `.gitignore` | none at root | see §5 |
| Issue tracking | none in repo | GitHub issues; reference IDs in commits + `19_…` doc |
| Releases | no tags | tag `v0.1.0` at demo date (doc 17 §4) |
| Binary churn | `outputs/` diffed every run | decide once: track (regeneration script) **or** ignore (doc 06 §3) |
| Reviewing docs | n/a | `PROJECT_DOCUMENTATION/` should be committed as its own commit |

---

## 5. Proposed root `.gitignore` (task T-11 — *not yet present in the repo*)

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/

# keep demo artifacts? choose ONE of the two blocks below:

# Option A — stop tracking generated products (recommended for clean diffs)
# outputs/*.tif
# outputs/*.png
# outputs/*.pdf
# outputs/web_data.json
# outputs/*.zip

# Never track the legacy dashboard
dashboard.html
```

Removing already-tracked bytecode:
```powershell
git rm -r --cached __pycache__ tests/__pycache__
git commit -m "chore: stop tracking bytecode"
```

---

## 6. Recovering artifacts after test/demo runs (practical)

```powershell
git status --short                      # see what moved
git diff --stat outputs/                # text-level view (csv/json visible)
git checkout -- outputs/                # restore ALL committed artifacts
git checkout -- outputs/hazard_summary.csv   # restore one file
git stash -u                            # park everything incl. untracked (careful: includes PROJECT_DOCUMENTATION/)
```

**Caveat:** `git checkout -- outputs/` will also delete *your intentional* new artifacts that are
untracked (e.g. a freshly downloaded JP2 is in `data/`, so it's safe; but any new file in
`outputs/` disappears). Prefer restoring specific paths.

---

## 7. Two-person collaboration playbook (agreed-once, then follow)

1. **Before starting work:** `git pull --rebase origin main` and run the fast test subset.
2. **Work in small commits** — one concern per commit (docs vs code vs artifacts never mixed).
3. **Never commit `outputs/` casually:** run it through the §6 restore, or commit it deliberately
   with a message saying the artifacts are part of the change.
4. **Code review checklist** (5 min): new `float(...)` from request bodies range-checked? any new
   `innerHTML`? thresholds changed in `config.py` *and* every duplicate site (doc 12 §7)? tests added?
5. **Docs follow code:** if you change a route, endpoint table (doc 09 + `api_documentation/`);
   if you fix an issue, close it in doc 19.
6. **The README is marketing** — verified claims live in `PROJECT_DOCUMENTATION/` and doc 19 flags
   the specific overstated statements.

---

## 8. Linking history to documentation

| Deliverable | Contents |
| :--- | :--- |
| `change_history/RELEASE_NOTES.md` | human-readable v0.1 notes derived from the two commits above |
| `change_history/COMMITS.md` | per-commit file-level digest + how to reproduce |
| `change_history/MIGRATION_NOTES.md` | what a future refactor must preserve (contracts, artifacts, tests) |
| `19_CURRENT_STATUS_AND_KNOWN_ISSUES.md` | live issue register (I-01…I-16) — update on every fix |
| `20_ROADMAP_AND_NEXT_STEPS.md` | prioritised tasks (T-01…) |
