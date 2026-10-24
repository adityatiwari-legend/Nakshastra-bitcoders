# TEAM_HANDOVER

**Handover date:** 2026-10-17 · **Repo state:** `main` @ `fa36e99`, working tree clean except the
untracked `PROJECT_DOCUMENTATION/` deliverable · **Members:** 2 (this doc assumes the
A/B split of doc 20 §"Suggested first week").

---

## 1. What you are inheriting (verified state)

| Pillar | State |
| :--- | :--- |
| Product | 7-phase CLI pipeline + "Mission Control" web console (8 tabs) for lunar South Pole PSR/hazard mapping — demo-ready on synthetic data, works offline |
| Tests | **32/32 green** (2026-10-17, 25.28 s); `pyflakes` baseline 9 findings; **no** server/frontend tests |
| History | 2 squashed commits (`c3d26dd`, `fa36e99`); no tags/CI/issues; 22 `.pyc` files tracked |
| Documentation | this folder (25 core docs + 7 subfolders) + pre-existing README/PROJECT_SPECIFICATION |
| Defects | 16 issues (`I-01…I-16`), 8 minor (`M-01…M-08`), 10 security items (`SEC-01…10`) — **none fixed yet**; register = doc 19 |
| Work queue | tasks `T-01…T-24`, milestones `M-A…M-D` — doc 20 + [`OPEN_TASKS.md`](OPEN_TASKS.md) |

## 2. Ownership split (agreed model — adjust once, then hold)

| | **Owner A — backend/science** | **Owner B — frontend/infra** |
| :--- | :--- | :--- |
| Owns | `hazard/psr/terrain/validate/ml_recommender/main/config`, science honesty, doc 19 | `web_server`, `web/*`, launchers, CI/tests harness, packaging, doc 17 |
| First tasks | T-01, T-02, T-04, T-03, T-10 | T-11+T-14, T-07, T-08, T-13 (routes/bind) |
| Shared | doc 19/20 updates in the same commit as any fix; Definition of Done (doc 20) | same |
| Escalation | 🔴 decisions (`ARCHITECTURAL_DECISIONS.md` §3 classes) need **both** sign-off | same |

## 3. Non-negotiable invariants (do not silently break)

1. **No Earth CRS** anywhere (IAU 2015 sphere, `LUNAR_SOUTH_POLE_PROJ4`; guard in
   `io_utils.py:199-206`).
2. **Never invent accuracy numbers** — PSR metrics show `UNLOADED` + provenance note without an
   independent reference; keep the client's `provenance_note` path intact.
3. **Class 4 ≠ Safe** — audit rule 8 enforces it; UI/PDF must keep the distinction.
4. **IDs are append-only** (`I-/M-/T-/SEC-/A-/TC-`), docs updated in the same change as code.
5. **`outputs/` is a minefield** — tests rewrite it; restore with `git checkout -- outputs/…`
   (see [`../testing_documentation/TEST_EXECUTION_STATUS.md`](../testing_documentation/TEST_EXECUTION_STATUS.md) §2).

## 4. Pending team decisions (parked — see also `../change_history/ARCHITECTURAL_DECISIONS.md` §4)

| # | Decision | Blocks | Options on the table |
| :-: | :--- | :--- | :--- |
| 1 | Track or ignore `outputs/` in git (T-14) | T-11 | A: drop binaries, keep text artifacts · B: keep + refresh script |
| 2 | Shadow term: honest copy vs real modelling (I-07 → T-12) | M-A wording | 12a reword · 12b implement illumination |
| 3 | Server framework / auth exposure (A11-A13) | T-13, T-19 | stay stdlib+loopback vs FastAPI+token |
| 4 | Report strategy (I-14 → T-03) | M-A | fix injection vs regenerate-only |
| 5 | First tag: `v0.1.0` or `v0.2.0` (T-18) | release | doc 17 §4 |

## 5. Day-to-day protocol (2-person)

1. `git pull --rebase origin main` + fast test subset before starting (doc 18 §7).
2. One concern per commit; artifacts never mixed with code.
3. Before push: `pytest -q --ignore=tests\test_main.py` + pyflakes; clean `git status`.
4. After touching routes/keys: update doc 09 + `api_documentation/`; after a fix: mark the
   issue **FIXED** in doc 19 with the commit SHA.
5. Demo day: run the full gate — `TEST_CASES.md` §3 (TC-MAN-01…12) + regenerate bundle.

## 6. Contacts & external state

| Item | Value |
| :--- | :--- |
| GitHub remote | `https://github.com/kushbansal2005/ORBISLUNA.git` (push access required for both) |
| Commit author on file | Kush `<bansalkush2005@gmail.com>` |
| Secrets/tokens | **none in repo** (good) — keep it that way (never commit `.venv`, keys) |
| Data licensing | NASA/LOLA-derived files; keep `data/DOWNLOAD_INSTRUCTIONS.md` provenance intact |
| Deployment | local-only today (bind `""` = all interfaces — SEC-02; no hosting configured, doc 17) |

## 7. Handback checklist (when you change something big)

- [ ] `pytest -q` green + documented restore step; pyflakes not worse than baseline (9)
- [ ] doc 19 register updated (close/open issues with SHA)
- [ ] doc 20 task marked done per Definition of Done
- [ ] Contracts: doc 09/10 + `api_documentation/` if routes/keys moved
- [ ] `CHANGELOG.md` `[Unreleased]` entry added
- [ ] This folder committed as its own `docs:` commit
