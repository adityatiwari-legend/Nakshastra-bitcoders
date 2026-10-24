# Feature — Live Reclassification & Sensitivity Sliders

**IDs:** F-07 · **Status:** 🟠 fast path works, three defects · **Owner:** `web_server.py:411-547` + `web/app.js:2912-3441`
**Issues:** **I-02** (20 m areas), **I-11** (global config), **I-10** (fake charts), **I-04** (pipeline ignores sliders), M-08.

---

## 1. What the user gets

Dragging **slope/roughness threshold** and **weight** sliders updates, within ~250 ms:

- hazard class map (canvas + 3D texture),
- KPI chips: Safe / Caution / Unsafe / PSR km² + deltas vs baseline,
- rule-audit chip (violations count),
- top-3 landing sites re-ranked,
- sensitivity bars & unsafe-vs-slope curve,
- the KaTeX formula rendering of H (`renderKatexFormula:2897`).

## 2. The two-stage update pipeline (client)

```
slider input ─▶ onParamChange():2912
   ├─(instant)─▶ previewReclassifyClient():2962       local JS copy of the rule order
   │              → rebuildOffscreenHazardFast():3096 → drawPreviewHazardCanvas():3118
   │              → computeAndRenderClientSensitivity():3173  (client-side bars/curve)
   │              → renderKatexFormula (live formula)
   └─(debounce 250 ms)─▶ recalculateFast():3441
                    POST /api/recalculate  {slope_safe_max, slope_caution_max, slope_hard_unsafe,
                                            rough_*, weight_*, landing_ellipse_radius_m, …}
                       └─ server: mutate config.* → classify → summary → sites → audit → sensitivity
                          → response {summary, landing_sites, hazard_classes_flat,
                                      rule_audit, sensitivity}
                    └─ replace currentHazardArray → redrawMap + 3D texture
                       → updateKpisFromSummary:3546 · renderLandingSitesCards:3588
                       → updateBaselineDeltas:3126 (or populateKpisFromRealSummary:3505)
```

**Baseline** for deltas comes from `/api/status` CSV data (`populateKpisFromRealSummary:3505`) —
*i.e.* from `hazard_summary.csv`, computed with the real pixel size, while the *live* chips come from
the recalc, computed with 20 m (I-02). On synthetic data they agree; on LOLA they don't (144×).

## 3. Server-side hot path (verified, `web_server.py:411-547`)

1. lazy `load_raster_cache` → else 400 `"Raster cache not ready"`.
2. `float(body.get(key, config.KEY))` for 11 keys — **no range checks** (SEC-06).
3. **write into `config.*`** (`:438-446`) — process-global, cross-session (I-11).
4. `hazard.classify_hazard_surface(slope, rough, psr)` on cached arrays (ms).
5. class histogram → areas with `config.SYNTHETIC_PIXEL_SIZE_M` (**I-02**).
6. `ml_recommender.recommend_landing_sites(...)` with default 20 m (**I-12b**).
7. `validate.verify_rule_consistency(...)` → `rule_audit` (⚠ Rule 4 mis-keyed, I-03).
8. sensitivity: bars at 5/10/15° (inline recompute `:505-521`) + curve at 10 slope points (`:523-530`).
9. response with **full flattened** `hazard_classes_flat` (T-05 candidate).

## 4. Sensitivity charts caveat (I-10)

The server ships real `sensitivity.bars/curve`, but `renderSensitivityCharts():4041` renders
**hard-coded arrays** in the Prediction tab. The client-side live version
(`computeAndRenderClientSensitivity:3173` → `renderSensitivityBars:3240` → `renderSensitivityCurve:3328`)
*is* real and is what users see while dragging. Fix (T-17): feed the API payload to the same
renderers.

## 5. Related controls in the same panel

| Control | Handler | Notes |
| :--- | :--- | :--- |
| weight sliders | `onWeightChange:2845` | D slider updates the formula but not results (I-07) |
| presets | `applyPreset:2761` | named threshold sets |
| reset | `resetDefaults:2816` | re-posts literals to `/api/recalculate` (server keeps its own mutated state — no server reset endpoint, I-11) |
| run pipeline | `triggerRunPipeline:3690` | separate slow path; **ignores current sliders** (I-04) |

## 6. Guarantees & non-guarantees

✔ Fast (<1 s even on 62 k px) because terrain is never recomputed.
✔ Deterministic: same request → same classification (server is stateless *per request*, though
global config leaks between requests).
✘ Areas not trustworthy on real data (I-02) until T-02.
✘ Thresholds not honoured by RUN PIPELINE (I-04).
✘ Thresholds leak across browser sessions (I-11).

## 7. Tests

None for this feature (M-06). Planned in T-08: recalculate-shape test, config-reset test (post
T-06), area-vs-CSV equivalence test (T-02), and an audit-key parity test (T-01).
