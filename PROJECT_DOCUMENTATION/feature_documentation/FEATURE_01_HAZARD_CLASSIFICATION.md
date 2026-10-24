# Feature — 5-Class Hazard Classification Surface

**IDs:** F-01 · **Status:** ✅ core implemented · **Owner module:** `hazard.py` (+ `validate.py`, `web/app.js`)
**Issues:** I-07 (shadow weight inert), M-08 (frontend copies of thresholds).

---

## 1. What the user gets

A class assigned to **every pixel** of the DEM:

| Id | Name | Meaning | Typical rule |
| :-: | :--- | :--- | :--- |
| 0 | Unknown / NoData | missing elevation or invalid metric | `~valid_mask` |
| 1 | Safe | candidate landing terrain | H < 0.25, slope < 5°, rough < 1.5 m, outside PSR |
| 2 | Caution | usable but not preferred | valid, non-PSR, not safe |
| 3 | Unsafe | hazardous | slope ≥ 15° **or** rough ≥ 5 m **or** H ≥ 0.60 |
| 4 | Shadowed-Unknown (PSR) | permanently dark → survey-required, never "safe" | psr==1 and not unsafe |

**The invariant:** class 4 exists to separate *unknown* from *safe*
(`.agents/rules/lunasafe.md`) — enforced by audit rule 8 and rule 4.

## 2. Where it appears

| Surface | How |
| :--- | :--- |
| File | `outputs/hazard_classes.tif` (uint8, nodata 0, tags verified doc 10 §3) |
| CSV | `outputs/hazard_summary.csv` (5 rows: count + km² + %) |
| Map panel D | discrete legend colours (`mapping.py:149+`) |
| Web Map Studio | hazard layer + legend totals (`web/app.js:656,723`) |
| Web sliders | live recompute via `POST /api/recalculate` (Feature F-07) |
| 3D texture | hazard texture mode (`app.js:1939`) |
| Landing sites | recommender reads `hazard == 1` as its search space (F-06) |
| PDF report | class table on page 2 (⚠️ partly hard-coded, I-14) |

## 3. Computation path

```
terrain outputs (slope_deg, roughness_std_m) ─┐
psr_binary.tif ───────────────────────────────┼─▶ hazard.classify_hazard_surface
config thresholds (safe/caution/hard, weights)┘        → hazard_classes (uint8)
                                                       → score_h (float32, 0…0.8 today)
```
Exact step order: `module_documentation/HAZARD_MODULE.md` §1 · line numbers `hazard.py:61-134`.

**CLI:** phase 4 of `main.py:135-147`. **Web:** `web_server.py:455-459` (in RAM).

## 4. Interactive controls

| Control | Range (UI) | Effect | Applied in |
| :--- | :--- | :--- | :--- |
| Slope safe / caution / hard | 0–20° | class 1 boundary, hard override | live via config mutation |
| Roughness safe / caution / hard | 0–10 m | idem | idem |
| Weights S/R/D | 0–1 | recompute H | D has **no effect today** (I-07) |
| Score limits | 0.25 / 0.60 | class 1/3 boundaries | `config.SCORE_*` |

Client-side instant preview: `previewReclassifyClient` (`web/app.js:2962`) — runs the same rule
order in JS before the server responds (literal thresholds, M-08).

## 5. Data quality guarantees

- Deterministic: same inputs + same config ⇒ byte-identical output (no RNG).
- Audited: 9 rules re-checked independently (F-08), violations counted per pixel.
- Areas in the CSV use true pixel size; the web recalc's areas currently don't (I-02).

## 6. Tests

`tests/test_hazard.py` (6): score formula, hard overrides, PSR-vs-unsafe ordering, safe/caution
boundaries, NoData safety, end-to-end exports. Mutation coverage for rules lives in
`tests/test_validate.py`.

## 7. Known gaps / roadmap

| Gap | Issue | Task |
| :--- | :-: | :-: |
| Shadow term always 0 → 2-factor reality | I-07 | T-12 |
| Threshold literals duplicated in JS/server text | M-08/I-11 | T-06 |
| 40 m standoff not part of the surface (it's site-level) | I-05 | T-12b |
| No class probabilities — hard classes only | — | future (roadmap P3) |

## 8. Change impact list

Touching this feature = update `hazard.py` + `validate.py` rule exprs + `web_server.py:573`
descriptions + `web/app.js` palette & preview + `mapping.py` legend + `mission_report.py` legend +
docs 03/07/10/23 + `test_hazard.py`. (Checklist: doc 06 §1, doc 12 §7.)
