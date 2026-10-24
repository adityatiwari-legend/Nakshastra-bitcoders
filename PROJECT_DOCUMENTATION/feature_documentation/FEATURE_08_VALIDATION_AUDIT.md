# Feature — Validation Console & Rule Audit

**IDs:** F-08 · **Status:** 🟠 core works; one rule silently disabled on web · **Owner:** `validate.py` (+ `web_server.py:549-599`, UI `web/app.js:3948-4040`)
**Issues:** **I-03** (rule-4 key), **I-01** (batch metrics), **I-11b** (validate-geotiff), M-06.

---

## 1. What the user gets

1. **9-rule consistency audit** with per-rule PASS/FAIL and violation counts
   (modal + Validation tab table, `openAuditModal:3948`, table render `:3968`).
2. **Live "RULE CONSISTENCY" chip** in the console header updated after every recalculation
   (`app.js:3053/3056`, `:3480/3483`).
3. **PSR validation card**: precision/recall/IoU/F1 **or** an honest `UNLOADED` explanation
   (`checkPsrValidation:3985`, benchmark toggle).
4. **GeoTIFF preflight panel**: dimensions, pixel size, NoData, min/max (`validateRastersPreflight:4220`
   → `POST /api/validate-geotiff`).
5. CLI equivalent: phase 6 prints the audit verdict + writes `slope_sensitivity.png`.

## 2. The 9 rules (what "consistent" means)

| # | Statement | Key emitted by `validate.py` |
| :-: | :--- | :--- |
| 1 | Safe pixels have slope < safe threshold | `rule1_safe_slope_exceeded` |
| 2 | Safe pixels have roughness < 1.5 m | `rule2_safe_roughness_exceeded` |
| 3 | Safe pixels have H < 0.25 | `rule3_safe_score_exceeded` |
| 4 | Safe pixels are outside PSR | **`rule4_safe_pixel_in_psr`** |
| 5 | slope ≥ 15° ⇒ Unsafe | `rule5_hard_slope_not_unsafe` |
| 6 | rough ≥ 5 m ⇒ Unsafe | `rule6_hard_roughness_not_unsafe` |
| 7 | H ≥ 0.60 ⇒ Unsafe | `rule7_high_score_not_unsafe` |
| 8 | PSR pixels ∈ {3,4} (never 1/2) | `rule8_psr_pixel_marked_safe_or_caution` |
| 9 | NoData ⇒ class 0 | `rule9_nodata_misclassified_as_surface` |

Response shape (`POST /api/audit`): `{status: PASSED|FAILED, total_violations,
rule_results:[{rule_id, description, violations, passed}×9], total_pixels, valid_pixels}`.

## 3. 🔴 Defect I-03 — rule 4 never fires on the web

`web_server.py:576` reads `detailed.get("rule4_safe_in_psr", 0)` — a key **never produced**
(`validate.py:117` emits `rule4_safe_pixel_in_psr`). The default `0` is returned, so rule 4 shows
PASSED always. The other 8 keys match.

- Visible effect: Validation tab + audit modal give false assurance on the project's core rule.
- Batch CLI path is unaffected (it prints counts straight from the emitted dict).
- **Fix T-01:** correct the key + add a parity test asserting
  `set(rules_meta keys) ⊆ validate emitted keys`.

## 4. Defect I-01 — batch accuracy metrics are self-comparisons

`process_validation_pipeline:301-308` calls `compute_psr_metrics(psr_mask, psr_mask, …)` →
precision/recall/IoU/F1 = 1.000 always. The web card is *not* affected (it compares files or
returns nulls honestly). **Until T-04, do not quote CLI PSR accuracy.**

## 5. GeoTIFF preflight (I-11b)

`POST /api/validate-geotiff` returns real dimensions/pixel size/NoData/min/max but hard-codes
`crs_valid: true` and `all_passed: true` (`web_server.py:760-771`). An Earth-EPSG file would be
certified valid — contradicting `io_utils.inspect_raster`'s guard. Fix: call `inspect_raster` +
surface its errors (fold into T-08 scope).

## 6. Console-level honesty features worth keeping

- `/api/psr-validation` refuses to invent numbers: `precision: null …` + `provenance_note`
  explaining that ground truth needs VIPER/rover prospecting (`web_server.py:727-731`).
- Audit chip turns red only on `total_violations > 0` — no fake green elsewhere (except rule 4).
- Rules table descriptions embed the *live* thresholds, so judges see exactly what was tested.

## 7. Tests

| Existing | Guards |
| :--- | :--- |
| `test_verify_rule_consistency_passes_on_pipeline_output` | happy path |
| `test_verify_rule_consistency_catches_deliberate_errors` | mutations trip counters |
| `test_compute_psr_metrics_exactness` | metric maths (function only) |
| `test_slope_sensitivity_analysis_execution` | sensitivity runs |

**Planned (T-01/T-08):** key-parity test (validate ↔ web_server), audit endpoint HTTP test,
validate-geotiff truthfulness test.

## 8. Change guidance

- Adding a rule → `validate.py` + `rules_meta` (`web_server.py:572-582`) + UI table (auto from
  API) + docs 07/19/23 + a mutation test in `test_validate.py`.
- Fixing thresholds → keep rule expressions in sync with `hazard.py` (they're independent copies).
