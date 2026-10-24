# 20 — Roadmap and Next Steps

> Prioritised, ID-stable task list (**T-01 … T-18**) for the two-person team. Every task names the
> issues it closes (doc 19), the files to touch, and its verification command. Nothing here has
> been implemented by this documentation pass.

**Sequencing rule:** correctness/honesty fixes (P0) → security (P0) → configuration coherence (P1)
→ quality infrastructure (P1) → features (P2) → product polish (P3).

---

## P0 — Correctness & honesty (1–2 days total)

### T-01 — Repair the web Rule 4 audit key · closes **I-03**
- `web_server.py:576` → `rule4_safe_pixel_in_psr`.
- Add the invariant test: every key in `rules_meta` must exist in `validate.…["detailed_violations"]`.
- **Done when:** `pytest tests/test_validate.py -v` green **and** a crafted array with a safe pixel
  inside PSR reports `violations ≥ 1` through `POST /api/audit`.

### T-02 — Real pixel size in `/api/recalculate` areas · closes **I-02**, **I-12b**
- Replace `config.SYNTHETIC_PIXEL_SIZE_M` at `web_server.py:470` with pixel size from
  `RASTER_CACHE["transform"]`; pass the same value as `pixel_size_m` into
  `ml_recommender.recommend_landing_sites` (`:484-493`).
- **Done when:** on LOLA data, `summary.safe.area_km2` equals
  `safe_px × 240²/1e6` and matches `hazard_summary.csv` within rounding.

### T-03 — Honest mission report · closes **I-14**
- `mission_report.py`: inject real `rule_audit` values (`:167-177`), real fallback stats (`:51-58`),
  and `datetime.now(timezone.utc)` for the "UTC" stamp (`:71`).
- **Done when:** PDF page 2 numbers equal `/api/status.summary_data` and audit output for the same
  `outputs/` snapshot.

### T-04 — Real PSR validation in the batch path · closes **I-01**
- `validate.py:301-308`: compare against an independent reference when present; otherwise report
  `null`s + provenance note (mirror `web_server.py:723-737`) instead of self-comparison.
- **Done when:** unit test with two different masks produces non-trivial metrics end-to-end.

### T-05 — Slim the recalculate payload · perf, supports **I-06**
- Return hazard deltas (or a checksum + only-on-change full array) instead of 40k–62k integers per
  slider tick; or send `hazard_classes_flat` only when `width×height ≤ 40 000`.
- **Done when:** slider round-trip on LOLA < 150 ms on the demo laptop.

---

## P0 — Security (before any non-local exposure)

### T-13 — Hardening pass · closes **SEC-01…06, 10**
- Implement doc 16 §5 items 1–6 + 10 (loopback default, `resolve()`+prefix checks, static root
  `web/` + no listings, delete `/api/upload-raster`, range/finite validation + 400 on bad JSON,
  POST token, subprocess timeout + log cap).
- **Done when:** the PoC curls from doc 16 SEC-01 return 404, `.git` is unreachable, and a new
  `tests/test_server_security.py` (T-08) passes.

---

## P1 — Configuration coherence & stale data (2–3 days)

### T-06 — Single source of truth for thresholds · closes **I-11**, **M-08**
- Snapshot `DEFAULTS` at import; make request handlers pass a *local* overrides dict into
  `classify_hazard_surface`/`verify_rule_consistency` instead of mutating `config`;
  add `GET /api/defaults`; have `app.js` read `defaults` from `web_data.json`/that endpoint instead
  of literal copies; optional `POST /api/reset-defaults`.
- **Done when:** two clients with different slider positions don't affect each other, and grep finds
  no threshold literals in `web/app.js`.

### T-07 — CI + lint · closes **M-04**, part of **I-16**
- `.github/workflows/ci.yml`: setup-python 3.13 → `pip install -r requirements.txt` →
  `python -m pyflakes` on all modules → `pytest -q --ignore=tests/test_main.py` → upload `outputs/`
  artifact.
- Declare `pyflakes` in `requirements.txt` (or drop it).
- **Done when:** a PR shows a green check.

### T-08 — Server test harness · closes **M-06**, protects **I-01/03/11b/12/14**
- `tests/test_server.py`: start `ThreadingHTTPServer` on port 0 in a thread, drive with `urllib`:
  health, status, data-shape, audit, recalculate (incl. rule-4 mutation), 409-busy, 404, 400-on-no-cache.
- **T-08b** — key-parity test (see T-01). **T-08c** — add `pytest-cov` with a 50 % backend floor.
- **Done when:** 10+ server tests green in < 10 s.

### T-09 — Non-destructive tests · closes **M-05**
- Monkeypatch `config.OUTPUT_DIR` (and artifact constants) to `tmp_path` in end-to-end tests, or
  mark heavy tests `@pytest.mark.pipeline` with a default deselect.
- **Done when:** `pytest -q` leaves `git status` clean.

### T-10 — Freshness guard for the data bundle · closes **I-06**
- Test comparing `web_data.json` `width/height` vs `outputs/hazard_classes.tif` + an
  `export_web_data.export_data_bundle()` call at the end of `main.py`'s phase summary (so a manual
  CLI run refreshes it too).
- **Done when:** the doc-15 one-liner comparison is asserted in CI.

---

## P1 — Hygiene (half a day)

### T-11 — `.gitignore` + untrack bytecode · closes **M-01**
- Add root `.gitignore` (doc 18 §5), `git rm -r --cached __pycache__ tests/__pycache__`.
- Decide **T-14** below in the same commit.

### T-14 — Decide the fate of `outputs/` in git
- Option A (recommended): stop tracking binaries, keep `hazard_summary.csv` + `landing_sites.json`
  as reviewable text, ship artifacts as a release asset.
- Option B: keep tracking + add `scripts/refresh_outputs.bat` so regeneration is one command.
- **Done when:** documented in `README.md` + `17_DEPLOYMENT_AND_RELEASE_GUIDE.md` §3.

### T-16 — Dependency cleanup · closes **I-16**
- Delete `requirement.txt`; drop unused `scikit-image`/`pandas` direct pins (verify imports);
  optionally `--require-hashes` lock (SEC-09).

### T-15 — Bundle schema versioning · closes part of **I-06**
- Add `"schema_version"` (and optionally `grid_signature`) to `outputs/web_data.json`
  (`export_web_data.py:68-102`); have `loadDataset()` refuse/refresh on mismatch (UI hint only).
- **Done when:** an old-format bundle is detected by the UI instead of silently rendering
  (referenced by `10_DATABASE_AND_DATA_MODEL.md`, `24_CROSS_REFERENCE_MATRIX.md`,
  `module_documentation/TOOLING_MODULES.md`).

---

## P2 — Features (choose based on demo feedback)

### T-12 — Make the science match the claims (pick one path)
- **12a (honesty):** reword README/pitch/`PROJECT_SPECIFICATION.md`: "deterministic multi-criteria
  classifier + signal-processing detector", set `WEIGHT_SHADOW` handling per I-07 option (b).
- **12b (ambition):** implement real shadow modelling (grazing illumination from DEM+aspect →
  `shadow_fraction` into `compute_hazard_score`, `main.py:137`), enforce the 40 m buffer (I-05),
  then the "three-factor + clearance" claims become true.
- **12c (ML):** small trained boulder/PSR detector (scikit-learn/torch) with a data provenance note
  — only if time allows (I-09).

### T-17 — Bind the real sensitivity charts · closes **I-10**
- Point `renderSensitivityCharts()` at `sensitivity.bars`/`curve` from the recalculate response.
- **Done when:** moving a slider visibly moves the bars.

### T-18 — Version identity & release hygiene
- `GET /api/version` (git SHA + build date), `CHANGELOG.md`, first annotated tag `v0.1.0`,
  unify phase labels `x/7` (**M-02**), single downloader URL constant (**M-03**),
  `prepare_lola_dataset` relative root (**I-15**).
- **Done when:** doc 17 §5 gate passes end-to-end.

---

## Optional / later (P3)

| ID | Idea | Notes |
| :--- | :--- | :--- |
| T-19 | `mypy --strict` on `hazard/validate/psr` first | low churn, high signal |
| T-20 | Playwright smoke test of the 8 tabs (needs T-08 harness) | doc 14 §8 |
| T-21 | three.js upgrade off r128 + SRI on CDN tags (SEC-07) | risk: `app.js` 3D code uses r128-era API |
| T-22 | Docker image (`python:3.13-slim`, EXPOSE 8050) | doc 17 §1 option E |
| T-23 | Real PSR atlas import as `independent_psr_reference.tif` → unlocks truthful precision/recall UI (I-01/I-08) | highest scientific value |
| T-24 | Pyramids/tiling for >1 MP datasets | removes doc 05 §10 ceiling |

---

## Milestones

| Milestone | Contents | Est. effort | Exit criterion |
| :--- | :--- | :-: | :--- |
| **M-A "Honest demo"** | T-01, T-02, T-03, T-04, T-10, T-17 | 2 days | every number on screen/PDF reproducible from `outputs/` |
| **M-B "Safe to share on LAN"** | T-13, T-08 (+08b), T-11, T-14 | 2 days | doc 16 checklist green; tests don't dirty git |
| **M-C "Team-ready codebase"** | T-06, T-07, T-09, T-15, T-16, T-18 | 2–3 days | CI green; no config drift; tagged v0.2.0 |
| **M-D "Feature complete"** | T-12b, T-23 (+ T-05) | 4–7 days | claims in README are literally true |

---

## Suggested first week for the two-person team

| Day | Owner A (backend/science) | Owner B (frontend/infra) |
| :-- | :--- | :--- |
| 1 | T-01, T-02 (2 hours each incl. tests) | T-11 + T-14 decision, T-07 skeleton CI |
| 2 | T-04, T-03 | T-08 server harness (pairs with A's fixes) |
| 3 | T-06 (config snapshot + API) | T-17 + consume `defaults` in `app.js` |
| 4 | T-10 freshness test; I-07 decision (12a vs 12b) | T-13 items 1–4 (routes/bind) |
| 5 | T-12 (start), doc 19 updates | T-16, T-18, walk doc 17 §5 gate |

## Definition of Done (per task)

1. Code change + at least one test that fails before / passes after.
2. `python -m pytest -q` green; `git status` clean after the documented restore step.
3. Doc 19 issue marked **FIXED** with commit SHA; doc 09/10/12 updated if a contract moved.
4. No new threshold literals outside `config.py` (grep check, doc 12 §7).
