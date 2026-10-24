# TEST_PLAN — LunaSafe

**Scope:** backend pipeline + web console. **Owner:** both members. **Baseline:** core doc
[`../14_TESTING_AND_QUALITY_ASSURANCE.md`](../14_TESTING_AND_QUALITY_ASSURANCE.md).
**Status of this plan:** living document — update `TEST_EXECUTION_STATUS.md` after every run.

---

## 1. Objectives

1. Protect the 7-phase pipeline's numerical contracts (CRS, thresholds, rule audit, exact areas).
2. Catch regressions in the 20-route web API (currently **zero** automated coverage).
3. Keep the verification loop honest: tests must fail when the *system* is wrong, not only when a
   *function* is wrong (see false-confidence risks, doc 14 §9).

## 2. Test levels

| Level | Tooling | Existing today | Planned |
| :--- | :--- | :-: | :--- |
| L0 lint (static) | `pyflakes` (installed, undeclared — I-16) | ❌ | T-07 pseudo-CI |
| L1 unit | `pytest==9.1.1` | ✅ 32 tests / 9 files | add web_server + report modules |
| L2 integration (pipeline e2e) | `tests/test_main.py` | ✅ 1 destructive test | make non-destructive (T-09) |
| L3 API contract | — | ❌ | T-08 harness on a random port |
| L4 UI smoke | — | ❌ | T-16 (playwright, optional) |
| L5 manual QA | checklist | ✅ doc 14 §6 | keep as release gate |
| L6 coverage | — | ❌ | `pytest-cov` floor 50 % backend (T-08c) |

## 3. Environment

- Windows + `.venv` (`Python 3.13.0`), repo root as CWD, no network required (all tests use
  `tmp_path` fixtures / committed data).
- ⚠ **Destructive by default:** `test_main.py` and the end-to-end module tests rewrite `outputs/`.
  Restore afterwards: `git checkout -- outputs/` (observed: `lunasafe_hazard_map.pdf`,
  `psr_polygons.dbf`).

## 4. Test data policy

| Data | Use in tests |
| :--- | :--- |
| Synthetic fixtures built in-test (`tmp_path`) | preferred — hermetic |
| `data/synthetic_dem.tif` + `data/synthetic_psr.tif` | allowed — committed, stable |
| Real LOLA GeoTIFFs | **never** in CI — optional local-only marker (not yet defined) |
| `outputs/` | treated as read-only input *except* during pipeline e2e (then restored) |

## 5. Entry / exit criteria

- **Entry:** venv built (`11_SETUP_AND_INSTALLATION.md`), `pytest` collects 32 tests.
- **Exit (per run):** all selected tests pass; `git status` clean (or outputs restored);
  results logged in [`TEST_EXECUTION_STATUS.md`](TEST_EXECUTION_STATUS.md);
  new/changed behaviour has a test case in [`TEST_CASES.md`](TEST_CASES.md).

## 6. Risk-based priority (what to test next)

| Rank | Risk | Evidence | Planned case |
| :-: | :--- | :--- | :--- |
| 1 | audit key drift (I-03) | `validate.py:117` vs `web_server.py:576` | TC-API-04 |
| 2 | unit pixel size used for areas (I-02) | `web_server.py:470` | TC-API-05 |
| 3 | params not forwarded to child (I-04) | `web_server.py:369-381` | TC-API-06 |
| 4 | stale bundle (I-06) | 250×250 vs 200×200 | TC-API-07 |
| 5 | report prints hard-coded pass (I-14) | `mission_report.py:167-177` | TC-REP-01 |
| 6 | report/route traversal (SEC-01) | `web_server.py:129-140` | TC-SEC-01 |
| 7 | destructive tests (T-09) | doc 14 §4 | harness change |
| 8 | converter path (I-15) | `prepare_lola_dataset.py:15` | TC-ING-01 |

## 7. Cadence

- **Before any push:** fast subset — `pytest -q --ignore=tests\test_main.py` (≈20 s, non-pipeline).
- **Before any release/demo:** full suite + manual QA checklist (doc 14 §6) + integrity check from
  [`../api_documentation/DATA_BUNDLE_SCHEMA.md`](../api_documentation/DATA_BUNDLE_SCHEMA.md) §6.
- **After touching `validate.py` or `web_server.py`:** mandatory TC-API-04 (key-name contract).

## 8. Traceability

Every automated test → module doc §5; every defect found → issue ID in
[`../19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](../19_CURRENT_STATUS_AND_KNOWN_ISSUES.md);
every planned test → task in [`../20_ROADMAP_AND_NEXT_STEPS.md`](../20_ROADMAP_AND_NEXT_STEPS.md)
(T-08, T-08b, T-08c, T-09, T-10, T-07, T-20).
