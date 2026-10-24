# Feature — ALSS Landing-Site Recommender & Boulder Micro-Hazards

**IDs:** F-06 · **Status:** 🟠 implemented with two correctness gaps · **Owner:** `ml_recommender.py` (+ UI cards in `web/app.js`)
**Issues:** **I-05** (40 m standoff not enforced), **I-12b** (pixel size default), I-09 (AI wording).

---

## 1. What the user gets

1. **Top-3 landing sites** ranked by fitness, each with a designated ellipse (100 m radius default),
   world coordinates, elevation, slope/roughness stats, distance to PSR, clearance, mission role
   (Primary / Relay / Survey).
2. `outputs/landing_sites.json` (schema: `module_documentation/ML_RECOMMENDER_MODULE.md` §4,
   `api_documentation/LANDING_SITES_SCHEMA.md`).
3. **Boulder/crater micro-hazard probability raster** `outputs/boulder_hazard.tif` (0…1) + up to
   150 discrete boulder points (30 sampled into the UI).
4. UI: landing-site cards with rank/suitability/clearance, "focus" buttons that fly the 2D canvas
   and the 3D camera to the ellipse; boulder layer toggle; ellipse + standoff ring overlays.

## 2. Algorithm (deterministic — no trained model)

**Search space:** `hazard_classes == 1` (Safe only).
**Clearance:** `EDT(safe) × pixel_size` → metres. Candidates need
`dist ≥ ellipse_radius_m` (100). ⚠️ **No +40 m buffer** despite `config.LANDING_CLEARANCE_BUFFER_M`
(I-05); the UI still draws a 40 m ring.
**Fitness:** `.35·clearance + .30·flatness + .20·smoothness + .15·science`
(`science` = Gaussian preference ≈250 m from PSR).
**Selection:** greedy arg-max with circular suppression of radius `2.5×ellipse`, repeat 3×.
**Statuses:** `ELIGIBLE`; `SUCCESS_NO_SITE` when no candidates (relaxation to 85 % of max clearance
is attempted first, with a console warning).

**Boulders:** DEM → mean-fill NoData → σ=2 Gaussian trend → |residual| → z-score →
`sigmoid(1.8·(z−2.2))` probability → 5×5 local maxima as points (cap 150).
Thresholds: `config.BOULDER_RESIDUAL_THRESHOLD_STD=2.2`.

Exact line map: `module_documentation/ML_RECOMMENDER_MODULE.md`.

## 3. Execution paths

| Path | Trigger | Notes |
| :--- | :--- | :--- |
| Batch | `main.py` phase 7 (`:191-201`) | **re-reads files from disk** — needs phases 2-4 outputs present |
| Standalone | `python ml_recommender.py` | own argparse `--dem/--psr/--out` |
| Web (fast) | `POST /api/recalculate` → `recommend_landing_sites(...)` (`web_server.py:484-493`) | ⚠️ `pixel_size_m` not passed → 20 m assumed (I-12b); uses cached arrays |
| Web (full) | pipeline worker → phase 7 | correct pixel size (from DEM transform) but subject to I-04 config |

## 4. UI surfaces

| Element | app.js function |
| :--- | :--- |
| cards (rank, suitability %, stats) | `renderLandingSitesCards:3588` |
| focus 2D / 3D | `focusOnSite:3657`, `focusOnSite3D:3673` |
| ellipse + ring overlays | `drawLandingSitesOverlay:995` (ring is client-side 40 m — I-05) |
| boulder layer | offscreen hazard-family layer + `DATA.boulder_points` |
| data source | `DATA.landing_sites` from `GET /api/data` **or** `landing_sites` array in the recalculate response |

## 5. Honest description for demos (I-09)

Say: *"deterministic multi-criteria decision + signal-processing detector; no training data."*
Avoid: "the model learned…". Roadmap options: T-12a (reword), T-12c (actually train something).

## 6. Tests

`tests/test_ml_recommender.py` (3): boulder peaks detected on synthetic bumps; recommender returns
well-formed sites on a synthetic safe island; artifacts written end-to-end.
**Missing (would have caught current bugs):**
- pixel-size scaling test (I-12b) — same site, 20 m vs 240 m grids ⇒ different `dist_to_psr_m`;
- standoff test (I-05) — unsafe pixel at 120 m with radius 100 + buffer 40 ⇒ reject;
- `SUCCESS_NO_SITE` path; suppression radius between two islands.

## 7. Fix snippets (tasks T-02 / T-12b)

```python
# web_server.py:484  — pass real pixel size (T-02)
px = abs(RASTER_CACHE["transform"].a)
ml_recommender.recommend_landing_sites(..., pixel_size_m=px)

# ml_recommender.py:115 — enforce standoff (T-12b)
min_clear = ellipse_radius + config.LANDING_CLEARANCE_BUFFER_M
candidates = dist_m >= min_clear
```
Both need the regression tests above + JSON schema field `clearance_required_m`.
