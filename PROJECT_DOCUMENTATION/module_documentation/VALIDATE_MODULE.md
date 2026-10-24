# `validate.py` — Rule Auditor, PSR Metrics & Sensitivity (357 lines)

> Role: **independent verification layer.** Re-derives whether the classified raster obeys the
  project's 9 safety rules, computes PSR agreement metrics, and runs the slope-threshold sensitivity
  study. It deliberately *re-implements* classification logic rather than importing it, so the
  auditor can disagree with the classifier (that's the point).

**Status:** 🟠 correct internally, two integration bugs upstream (I-01, I-03) ·
**Tested by:** `tests/test_validate.py` (4, incl. mutation test) ·
**Issues:** **I-01** (self-comparison at batch call site), **I-03** (web reads wrong key), M-06.

---

## 1. The 9 rules (`verify_rule_consistency`, `:70-148`)

Inputs: `hazard_classes, slope, roughness, psr_mask, score_h` — all arrays, no I/O.

| # | Description (as served by `/api/audit`) | Violation expression | Emitted key |
| :-: | :--- | :--- | :--- |
| 1 | Safe slope strictly < safe threshold | `hazard==1 & slope >= SLOPE_SAFE_MAX` | `rule1_safe_slope_exceeded` |
| 2 | Safe roughness < 1.5 m | `hazard==1 & rough >= ROUGHNESS_SAFE_MAX` | `rule2_safe_roughness_exceeded` |
| 3 | Safe H < 0.25 | `hazard==1 & score_h >= SCORE_SAFE_MAX` | `rule3_safe_score_exceeded` |
| 4 | Safe pixels strictly outside PSR | `hazard==1 & psr==1` | **`rule4_safe_pixel_in_psr`** (`:117`) |
| 5 | slope ≥ 15 ⇒ Unsafe | `slope>=HARD & hazard!=3` | `rule5_hard_slope_not_unsafe` |
| 6 | rough ≥ 5 ⇒ Unsafe | `rough>=HARD & hazard!=3` | `rule6_hard_roughness_not_unsafe` |
| 7 | H ≥ 0.60 ⇒ Unsafe | `score>=UNSAFE & hazard!=3` | `rule7_high_score_not_unsafe` |
| 8 | PSR ⇒ {3,4} never {1,2} | `psr==1 & hazard in (1,2)` | `rule8_psr_pixel_marked_safe_or_caution` |
| 9 | NoData ⇒ class 0 | `~valid & hazard != 0` | `rule9_nodata_misclassified_as_surface` |

Return value:
```python
{"is_consistent": bool, "total_violations": int, "audited_pixels": int,
 "valid_surface_pixels": int, "detailed_violations": {<key>: int, ...}}
```
Counts are numpy `np.count_nonzero` reductions — cheap enough to run per slider tick.

> 🔴 **Bug I-03:** `web_server.py:576` looks up `rule4_safe_in_psr`, which is **never emitted** →
> Rule 4 always reports 0 on the web path. The other 8 keys match. Fix: T-01 + a key-parity test.

## 2. PSR metrics (`compute_psr_metrics`, `:166+`)

```
precision = TP/(TP+FP) · recall = TP/(TP+FN) · IoU = TP/(TP+FP+FN) · F1 = 2PR/(P+R)
```
Signature `(candidate, reference, reference_name, is_independent)`; also returns provenance text.
Handles all-zero denominators safely (returns 0/None-style values rather than dividing by zero).

- ✅ Unit-tested with hand-computed values (`test_compute_psr_metrics_exactness`).
- 🔴 **Batch call site bug I-01:** `process_validation_pipeline:301-308` calls it as
  `compute_psr_metrics(psr_mask, psr_mask, …)` → always 1.000. The *function* is fine; the *call*
  never passes an independent reference. Fix: T-04.
- The web endpoint `/api/psr-validation` (`web_server.py:709-714`) calls it correctly with two
  files, and honestly returns `null`s when no reference exists (`:723-737`).

## 3. Sensitivity analysis (`run_slope_sensitivity_analysis`, `:151-280`)

- 5 scenarios (threshold sets around 5/10/15° families, defined `:156-166`).
- For each: re-classify **inline** (`:180-210`) — a *third* copy of the rule logic, without the
  shadow term — then compute class areas (% of valid terrain).
- Verifies area growth is monotonic with threshold in tests (`test_slope_sensitivity_analysis_execution`).
- Renders `outputs/slope_sensitivity.png` (stacked bars, dark theme, 300 DPI).
- **Web twin:** `web_server.py:504-530` produces `sensitivity.bars` (5/10/15°) + `curve`
  (10 points 3→25°) for the UI — currently ignored by `renderSensitivityCharts()` (I-10).

## 4. Batch wrapper (`process_validation_pipeline`, `:283-357`)

Runs metrics (buggy, I-01) → audit → sensitivity → prints a console verdict → returns dict
`{"psr_metrics", "rule_audit", "sensitivity", ...}`. Called only by `main.py:172-186`.

## 5. Test coverage

| Test | Value |
| :--- | :--- |
| `test_compute_psr_metrics_exactness` | arithmetic correctness of the function |
| `test_verify_rule_consistency_passes_on_pipeline_output` | zero violations on good output |
| `test_verify_rule_consistency_catches_deliberate_errors` | **mutations trip specific counters** — the anti-tautology guard |
| `test_slope_sensitivity_analysis_execution` | runs + monotonicity |

**Gap that let I-03 through:** no test asserts that every key read by a *consumer* exists in the
emitted dict. T-01 adds exactly that (both directions: `validate` → `web_server.rules_meta`).

## 6. Rules when editing

1. Changing a threshold in `config.py` → re-check rule expressions here **and**
   `hazard.classify_hazard_surface` **and** `web_server.py:573-581` description strings.
2. Adding a rule → append an entry in all: `validate.py`, `/api/audit` `rules_meta`, UI table
   (auto-generates from the API), docs 07 §A8, 19, and a mutation test.
3. Never "fix" the auditor by importing the classifier — independence is the feature
   (`.agents/rules/lunasafe.md`).
