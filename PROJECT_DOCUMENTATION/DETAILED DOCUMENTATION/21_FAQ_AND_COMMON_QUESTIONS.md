# 21 — FAQ and Common Questions

> Answers are grounded in the code as of 2026-10-17; each cites evidence. For judge-style questions
> about honesty/claims, see [`19_CURRENT_STATUS_AND_KNOWN_ISSUES.md`](19_CURRENT_STATUS_AND_KNOWN_ISSUES.md) §E.

---

## Project basics

**Q1 — What is LunaSafe, in one sentence?**
A lunar South-Pole mapping console that renders a DEM with permanent-shadow regions, classifies every
pixel into a 5-class safety surface, ranks three landing ellipses, and exports a publication-ready
map + mission report — as a CLI pipeline plus a browser "Mission Control" UI.

**Q2 — Why is it called "hazard classification" and not just a map?**
Because the output is a *decision surface*: `hazard_classes.tif` with the invariant
"PSR pixels are never Safe" enforced by an independent 9-rule auditor (`validate.py:70-148`).

**Q3 — Where does the data come from?**
- Synthetic demo: procedurally generated crater + PSR (`io_utils.py:416-500`) → 200×200 @ 20 m.
- Real: NASA LRO LOLA polar DEM (`data/ldem_75s_240m.jp2` → `prepare_lola_dataset.py`) →
  250×250 @ 240 m, cropped to 80°S–90°S.
Which one is live is decided by **file existence** (`main.py:66-73`, `web_server.py:266`).

**Q4 — Is the PSR mask scientifically published?**
No. With real data it is our own heuristic: `depth < −900 m` (`prepare_lola_dataset.py:51-56`).
The UI's PSR-validation card therefore honestly answers `UNLOADED` with an explanation when no
independent reference exists (`web_server.py:723-737`). See I-08.

---

## Running it

**Q5 — `python main.py` vs `run.bat`?**
Same thing; `run.bat` picks `.venv\Scripts\python.exe` for you (`run.bat:3-7`). `main.py:18-26`
also self-upgrades to the venv if `rasterio` is missing.

**Q6 — How long does a full run take?**
≈8–10 s synthetic on the reference laptop; the whole pytest suite (which includes one full run)
takes 25 s.

**Q7 — Which port, and what if it's taken?**
8050, automatic fallback to 8080 (`web_server.py:840-846`). Read the startup banner.

**Q8 — The sliders say "Raster cache not ready".**
`outputs/slope_deg.tif` or `outputs/psr_binary.tif` missing at first recalc
(`web_server.py:415-419`). Run the pipeline once or press OFFLINE DEMO.

**Q9 — Why does my browser show stale data after editing Python?**
Neither `RASTER_CACHE` nor `web_data.json` is file-watched. Restart the server and hard-refresh
(Ctrl+F5).

**Q10 — Tests changed files in `outputs/`. Is that bad?**
Expected: `tests/test_main.py:19` runs the real pipeline. Restore with
`git checkout -- outputs/` (task T-09 makes this unnecessary).

---

## Understanding the science

**Q11 — How is the hazard score computed?**
`H = 0.50·clip(slope/15) + 0.30·clip(roughness/5) + 0.20·shadow_fraction`
(`hazard.py:41-54`), then hard overrides: slope ≥ 15° or roughness ≥ 5 m → Unsafe regardless
(`hazard.py:100-102`). ⚠️ `shadow_fraction` is never supplied by the pipeline, so D = 0 today
(I-07).

**Q12 — What do classes 0–4 mean?**
0 = NoData/unknown · 1 = Safe · 2 = Caution · 3 = Unsafe · 4 = PSR (Shadowed-Unknown).
Class 4 exists to separate "unknown" from "safe" — `.agents/rules/lunasafe.md`.

**Q13 — What are the 9 audited rules?**
Safe slope < 5°; safe roughness < 1.5 m; safe H < 0.25; safe ∉ PSR; slope ≥ 15° → Unsafe;
roughness ≥ 5 m → Unsafe; H ≥ 0.60 → Unsafe; PSR ∈ {3,4} only; NoData = class 0 only
(`validate.py:70-148`).

**Q14 — How are landing sites chosen?**
Safe pixels → Euclidean distance transform → candidates ≥ ellipse radius (100 m) from any unsafe/PSR
pixel → fitness `0.35·clearance + 0.30·flatness + 0.20·smoothness + 0.15·science` → greedy top-3 with
250 m mutual suppression (`ml_recommender.py:84-215`). The 40 m standoff is **not** applied (I-05).

**Q15 — How are boulders detected?**
Gaussian low-pass trend (σ=2) subtracted from the DEM, z-score of the residual, sigmoid
`1.8·(z − 2.2)` → probability raster; local maxima become up to 150 boulder points
(`ml_recommender.py:18-81`).

**Q16 — Slope uses which algorithm?**
Horn (1981) 3×3 kernels (`terrain.py:55-64`); roughness = rolling 3×3 std (`:90`) and Riley TRI
(`:139`).

---

## Architecture & API

**Q17 — Is there a database?**
No. Files + two JSON documents + one CSV. See doc 10.

**Q18 — Why is the UI so fast when sliders move?**
`POST /api/recalculate` re-classifies **in RAM** from `RASTER_CACHE` (~20 ms) and returns the new
class array; terrain metrics are never recomputed (`web_server.py:411-547`).

**Q19 — Why do threshold changes not affect RUN PIPELINE?**
The run spawns a fresh `main.py` that re-reads `config.py` from disk (`web_server.py:369-381`) — I-04.

**Q20 — Can I add an endpoint?**
Add a branch in `do_POST` (`web_server.py:154-173`), write a handler, document it in doc 09 +
`api_documentation/REST_API.md`, add a test in `tests/test_server.py` (T-08).

---

## Honest-answer questions (judges / reviewers)

**Q21 — "Where's the training data?"**
There is no trained model: the detector is deterministic signal processing (I-09). Say so plainly.

**Q22 — "Is this validated against real ground truth?"**
Not yet: precision/recall/IoU on the CLI path were self-comparisons (I-01, being fixed by T-04) and
no independent PSR reference ships with the repo. The web endpoint already refuses to invent numbers.

**Q23 — "What happens with a real 4k×4k mission dataset?"**
Today: too large — the bundle and cache hold full arrays in RAM/JSON (doc 05 §10 ceiling ≈1 MP).
Mitigations on the roadmap: T-05 (payload), T-24 (tiling).

**Q24 — "Is it secure to put on a network?"**
Not as-is: no auth, open CORS, traversal in three routes (doc 16). Localhost demo is fine;
apply T-13 before LAN use.

**Q25 — "How do you know the classifier obeys its own rules?"**
An independent auditor re-derives violations with numpy reductions and counts them (9 rules);
`POST /api/audit` exposes the result. Caveat: Rule 4's counter was mis-keyed on the web path (I-03).

---

## Two-person team questions

**Q26 — What should I read first as a new member?**
`00_START_HERE.md` → `01_PROJECT_OVERVIEW.md` → `03_FEATURES…` → your module's file in
`module_documentation/` → `19_CURRENT_STATUS…`.

**Q27 — Which file do I edit for X?**
Doc 06 §1 "Where to edit for a given change".

**Q28 — What must I never hand-edit?**
Anything in `outputs/` (regenerated), `dashboard.html` (generated), `web/vendor/*`.

**Q29 — Where is the definition of done?**
Doc 20 (Definition of Done) — test before/after, clean git, issue register updated, no new
threshold literals.

**Q30 — What is deliberately out of scope?**
Multi-user/multi-instance serving, authentication UX, cloud deployment, tiling (>1 MP), and a
trained ML model (unless T-12c is chosen).
