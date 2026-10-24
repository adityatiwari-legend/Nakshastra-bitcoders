# OPEN_TASKS

**Status legend:** ⬜ not started · 🟦 in progress · ✅ done (record SHA in doc 19) · ⏸ blocked.
**All tasks are ⬜ as of 2026-10-17** — the documentation pass changed no project code.
Authoritative details (files, line numbers, "Done when"): [`../20_ROADMAP_AND_NEXT_STEPS.md`](../20_ROADMAP_AND_NEXT_STEPS.md).

---

## P0 — correctness & honesty (M-A "Honest demo", ≈2 days)

| ID | Task | Closes | Owner | Size |
| :-- | :--- | :--- | :-: | :-: |
| ⬜ T-01 | Fix web Rule-4 audit key (`web_server.py:576` → `rule4_safe_pixel_in_psr`) + key-parity test | I-03 | A | S |
| ⬜ T-02 | Real pixel size in `/api/recalculate` areas + recommender call | I-02, I-12b | A | S |
| ⬜ T-03 | Honest mission report (real audit values, real fallback stats, real UTC) | I-14 | A | M |
| ⬜ T-04 | Real PSR validation in batch path (independent ref or `null`+provenance) | I-01 | A | M |
| ⬜ T-10 | Bundle freshness test + export at end of `main.py` | I-06 | A | S |

## P0 — security (before any non-local exposure; M-B, ≈1 day inside M-B)

| ID | Task | Closes | Owner | Size |
| :-- | :--- | :--- | :-: | :-: |
| ⬜ T-13 | Hardening pass: loopback bind, path `resolve()` checks, static root, delete `/api/upload-raster`, range/finite validation, 400 on bad JSON, POST token, subprocess timeout + log cap | SEC-01…06, 10 | B | M |

## P1 — configuration, tests, hygiene (M-B + M-C, ≈3 days)

| ID | Task | Closes | Owner | Size |
| :-- | :--- | :--- | :-: | :-: |
| ⬜ T-06 | Threshold single-source: request-local overrides, `GET /api/defaults`, no literals in `app.js` | I-11, M-08 | A+B | M |
| ⬜ T-07 | CI workflow + declare pyflakes + burn down the 9-finding baseline | M-04, I-16 part | B | S |
| ⬜ T-08 / 08b / 08c | Server test harness (port 0 + `urllib`, 10+ tests) / key-parity test / `pytest-cov` 50 % floor | M-06 + protects I-01/03/11/12/14 | B | M |
| ⬜ T-09 | Non-destructive tests (`OUTPUT_DIR` → `tmp_path` or `pipeline` marker) | M-05 | A | S |
| ⬜ T-11 | Root `.gitignore` + untrack 22 `.pyc` | M-01 | B | XS |
| ⬜ T-14 | Decide fate of `outputs/` in git (A: drop binaries / B: keep + refresh script) | doc 18 §5 | A+B | XS |
| ⬜ T-15 | Bundle `schema_version` + UI mismatch guard | I-06 part | B | S |
| ⬜ T-16 | Dependency cleanup: delete `requirement.txt`, drop unused pins, optional hash lock | I-16, SEC-09 | B | XS |

## P2 — features & release (M-C/M-D)

| ID | Task | Closes | Owner | Size |
| :-- | :--- | :--- | :-: | :-: |
| ⬜ T-05 | Slim the recalculate payload (deltas / checksum instead of 40k ints) | perf + I-06 | A | M |
| ⬜ T-12 | Science honesty **or** ambition: 12a reword claims · 12b real shadow + 40 m buffer · 12c trained detector | I-07, I-05, I-09 | A | M–L |
| ⬜ T-17 | Bind real sensitivity charts to `sensitivity.bars/curve` | I-10 | B | S |
| ⬜ T-18 | Release hygiene: `/api/version`, CHANGELOG (done: `change_history/CHANGELOG.md`), first tag, phase labels, downloader URL, portable converter | M-02, M-03, I-15 | B | S |

## P3 — optional (stretch)

| ID | Idea | Notes |
| :-- | :--- | :--- |
| ⬜ T-19 | `mypy --strict` on `hazard/validate/psr` first | low churn, high signal |
| ⬜ T-20 | Playwright smoke of the 8 tabs (needs T-08) | doc 14 §8 |
| ⬜ T-21 | three.js off r128 + SRI on CDN (SEC-07) | risk: r128-era API in `app.js` |
| ⬜ T-22 | Docker image (`python:3.13-slim`, EXPOSE 8050) | doc 17 §1 E |
| ⬜ T-23 | Real PSR atlas → `independent_psr_reference.tif` (truthful P/R UI) | highest scientific value |
| ⬜ T-24 | Pyramids/tiling for >1 MP datasets | removes doc 05 §10 ceiling |

## Milestone view

| Milestone | Tasks | Exit criterion |
| :--- | :--- | :--- |
| **M-A Honest demo** | T-01, T-02, T-03, T-04, T-10, T-17 | every number on screen/PDF reproducible from `outputs/` |
| **M-B Safe to share on LAN** | T-13, T-08(+08b), T-11, T-14 | doc 16 checklist green; tests don't dirty git |
| **M-C Team-ready** | T-06, T-07, T-09, T-15, T-16, T-18 | CI green; no config drift; tagged release |
| **M-D Feature complete** | T-12b, T-23 (+T-05) | README claims literally true |

## Rules of engagement

1. Pick from the top; M-A before M-B before anything greenfield.
2. Definition of Done (doc 20): test that fails before/passes after · full suite green ·
   `git status` clean after restore · doc 19 updated with SHA · no new threshold literals
   outside `config.py`.
3. Status changes happen **in this table and in doc 19 in the same commit**.
