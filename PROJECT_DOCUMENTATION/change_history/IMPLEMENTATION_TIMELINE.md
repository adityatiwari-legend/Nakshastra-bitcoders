# Implementation Timeline

Evidence policy: entries marked **VERIFIED** come from `git` metadata or commands executed during
this documentation run; **INFERRED** entries are reasoned orderings (no WIP commits exist to prove
them). Dates are author-local (+0530).

---

## Verified timeline

| When | What | Evidence |
| :--- | :--- | :--- |
| **2026-10-12 11:08:53 +0530** | **`c3d26dd` "solution for PSR"** — entire product (89 files, 17 846 insertions): pipeline, science core, web console, 32 tests, data, outputs, docs | `git log` |
| **2026-10-17 16:51:21 +0530** | **`fa36e99` "assets update"** — `PROJECT_SPECIFICATION.md`, README rewrite, UI edits, regenerated 15 outputs (**not** `web_data.json`) | `git log --stat` |
| **2026-10-17 (documentation run)** | Full test suite executed: `32 passed, 1 warning in 25.28 s`; destructive side effects (`lunasafe_hazard_map.pdf`, `psr_polygons.dbf`) restored; tree clean | `testing_documentation/TEST_EXECUTION_STATUS.md` |
| **2026-10-17 (same run)** | `PROJECT_DOCUMENTATION/` created (untracked); sources re-read line-by-line, tags/schemas/routes verified | folder contents |

Nothing else is dated in the repo (no tags, no issues, no CI logs, no CHANGELOG before this folder).

## Inferred construction order (INFERRED — no commit evidence)

1. **Rules & problem framing** — `.agents/rules/lunasafe.md`, `PITCH_SCRIPT.md` exist as the
   earliest intent documents (both landed in the first commit, but they read as inputs).
2. **Science core** — `config.py` → `io_utils` → `psr`/`terrain`/`hazard` → `validate`;
   tests written alongside (suite covers these first).
3. **Orchestration** — `main.py` 7 phases + `mapping`/`mission_report`/`ml_recommender`.
4. **Data prep** — synthetic generators, LOLA conversion, committed `data/` + first `outputs/`.
5. **Web layer** — `web_server.py` + `web/*` (largest files: `app.js` 4 473 L at first commit);
   legacy `dashboard.html`/`build_interactive_ui.py` appear to pre-date the SPA (kept, unused).
6. **Hardening pass** — second commit: spec document, README rewrite, UI polish, artifact
   regeneration for the demo.
7. **Documentation pass** — this folder (2026-10-17), including defect register I-01…I-16/SEC
   discovered by source re-reading.

## What the two-commit history implies

- **No incremental history:** bisect/blame cannot attribute individual features → treat both
  commits as snapshots; rely on this folder + doc 19 for state.
- **Demo-driven cadence:** a 5-day gap between "everything" and "assets update", both landing
  on demo-prep days (spec document + regenerated screenshots/artifacts).
- **Known debt was shipped, not introduced:** issues I-01…I-16 exist in `c3d26dd`; I-06 became
  *observable* in `fa36e99` when rasters moved ahead of the bundle.

## Forward timeline (planned only — see doc 20)

| Milestone | Window (suggested) | Contents |
| :--- | :--- | :--- |
| **M-A "trustworthy demo"** | immediately | T-01…T-06: fix I-01…I-04 evidence bugs, regenerate bundle (closes I-06) |
| **M-B "safety & tests"** | next sprint | T-07…T-10: lint gate, route tests, non-destructive runs, SEC-01 fix |
| **M-C "science fidelity"** | following | T-11…T-15: real shadow term, buffer semantics, real pixel size, tracked-outputs decision |
| **M-D "engineering floor"** | optional/stretch | T-16…T-24: CI, frontend tests, framework/DB migrations per `MIGRATION_NOTES.md` |
