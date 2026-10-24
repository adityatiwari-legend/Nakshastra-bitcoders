# 19 — Current Status and Known Issues

> **Status:** living register. Every entry has a stable ID, source-code evidence, and a suggested
> fix + regression test. All issues below were **OPEN** as of 2026-10-17; nothing in this
> documentation task modified application code.
> Severity: 🔴 high (wrong results / security) · 🟠 medium (broken feature) · 🟡 low (quality) · ⚪ informational.

**Baseline verification:** `python -m pytest -q` → `32 passed, 1 warning in 25.28s`; git tree clean
(except the new documentation folder).

---

## A. Correctness issues (wrong numbers / silently wrong results)

### I-01 🟠 PSR accuracy metrics compare the mask with itself
- **Where:** `validate.py:301-308` inside `process_validation_pipeline` — calls
  `compute_psr_metrics(psr_mask, psr_mask, …)`.
- **Effect:** precision = recall = IoU = F1 = **1.000 always**, regardless of data. The CSV/console
  "validation" numbers from the CLI path are meaningless.
- **Impact:** any slide/table quoting these four numbers is overclaiming (violates
  `.agents/rules/lunasafe.md:9-11` honesty rule in spirit).
- **Fix:** accept an independent reference (e.g. `data/independent_psr_reference.tif` if present, or
  compare `outputs/psr_binary.tif` against the *input* PSR only when they are genuinely different
  sources) and pass `is_independent=False` otherwise — as `/api/psr-validation` already does
  (`web_server.py:709-714`).
- **Regression test:** a test that feeds two *different* small masks and asserts the four metrics
  equal hand-computed values through `process_validation_pipeline` (the existing unit test
  `test_compute_psr_metrics_exactness` covers the function, not the call site).

### I-02 🟠 Web reclassification uses a fixed 20 m pixel for all area maths
- **Where:** `web_server.py:470` `px_size = config.SYNTHETIC_PIXEL_SIZE_M` (used for every
  `area_km2` in `summary`, `sensitivity.bars`, `sensitivity.curve`).
- **Effect:** on the real LOLA grid (240 m/px) areas are **144× wrong** (240²/20² = 144) in the
  `/api/recalculate` response, while `/api/status` (CSV-driven, `hazard.py:160`) stays correct →
  tabs disagree.
- **Fix:** derive pixel size from `RASTER_CACHE["transform"]` (`abs(transform.a)`,
  `abs(transform.e)`) and use it everywhere.
- **Regression test:** for the synthetic bundle assert `safe_px * (20*20)/1e6 == summary.safe.area_km2`.

### I-03 🟠 Rule 4 of the audit reads a key the validator never emits
- **Where:** `web_server.py:576` `detailed.get("rule4_safe_in_psr", 0)` vs
  `validate.py:117` emitting **`rule4_safe_pixel_in_psr`**.
- **Effect:** `POST /api/audit` Rule 4 always reports `violations: 0` / `passed: true` — the UI's
  "PSR exclusion" guarantee is unenforced on the web path. (Other 8 rules use matching keys.)
- **Impact:** silent false assurance on the project's central safety rule.
- **Fix:** change the key (and keep a test asserting every `rules_meta` key exists in
  `detailed_violations` — such a test would have caught this).
- **Regression test:** deliberately mark a PSR pixel as class 1, run `verify_rule_consistency`,
  assert both the emitted key **and** the `/api/audit` mapping report ≥ 1.

### I-04 🟠 UI slider thresholds are not applied to the full pipeline run
- **Where:** `web_server.py:341-362` mutates `config.*` in the **server** process, then `:369-381`
  spawns `Popen([python, "main.py", …])` — a child that re-imports `config.py` **from disk**.
- **Effect:** pressing RUN PIPELINE after tuning sliders silently re-runs with file defaults; only
  `force_synthetic` reaches the child.
- **Workaround today:** edit `config.py` itself before launching the server.
- **Fix:** add CLI flags to `main.py` (`--slope-safe …`) and pass every mutated value, or write a
  temporary JSON config file the child reads.
- **Regression test:** set `SLOPE_SAFE_MAX=9` via POST, run the pipeline handler with a stubbed
  subprocess capture, assert the argv contains the value.

### I-05 🟠 The 40 m clearance buffer is never enforced
- **Where:** `config.LANDING_CLEARANCE_BUFFER_M = 40.0` (`config.py:52`); the recommender gates only
  on `dist_m ≥ ellipse_radius_m` (`ml_recommender.py:115-116`). The buffer reaches the UI only as a
  **dashed ring drawn client-side**.
- **Effect:** sites labelled "ELIGIBLE … clearance 100 m" can sit 100 m from unsafe/PSR terrain —
  exactly what the 40 m standoff was meant to prevent; `landing_sites.json` has no buffer field.
- **Fix:** require `dist_m ≥ ellipse_radius_m + LANDING_CLEARANCE_BUFFER_M` (and surface the value
  in the JSON). Decide whether docs/README claims then change.
- **Regression test:** synthetic safe-island raster where the nearest unsafe pixel is at 120 m with
  radius 100 → must be rejected once buffer applied.
- **Re-verified 2026-10-17 (pyflakes):** `web_server.py:435` assigns `clearance_buf = float(body
  .get("clearance_buffer_m", …))` and **never uses it** — the slider value is parsed, then dropped
  (and `config.LANDING_CLEARANCE_BUFFER_M` itself is not in the config-mutation block `:438-446`).

### I-06 🟠 `outputs/web_data.json` is stale relative to the rasters
- **Evidence:** `git log --stat` — `web_data.json` last written in `c3d26dd` (2026-10-12); all
  rasters rewritten in `fa36e99` (2026-10-17). On disk the bundle is a **250×250** set while the
  other artifacts are **200×200** (verify with the one-liner in doc 15 §11).
- **Effect:** first paint of the console can show geometry/coordinates from a different dataset than
  the KPIs, map exports, and 3D mesh — the classic "two truths" bug.
- **Fix:** regenerate (`python export_web_data.py`) + rebuild the bundle inside the test suite or as
  a pipeline step. **Verified 2026-10-17:** `main.py` never calls `export_data_bundle()` (only
  `web_server.py:313,396` and `build_interactive_ui.py:14` do), and `outputs/web_data.json`'s
  mtime is **2026-10-11 14:36** while the rasters are **2026-10-17 17:07** — a CLI run (even the
  test-suite run that rewrote everything else) leaves the bundle untouched.
- **Housekeeping:** done for this snapshot? Re-run the check after any `main.py`.

### I-07 🟡 The shadow term D is always zero in the batch pipeline
- **Where:** `main.py:137` calls `compute_hazard_score(slope, roughness)` **without**
  `shadow_fraction`; default `shadow_fraction=0` ⇒ `H = 0.50·S + 0.30·R`, max ≈ 0.8 even at
  extreme terrain, and `WEIGHT_SHADOW` (0.20) is dead weight.
- **Effect:** the advertised three-factor index behaves as two-factor; `SCORE_UNSAFE_MIN=0.60`
  becomes easier to hit purely from slope+roughness, and the UI's weight slider for D is cosmetic.
- **Fix options:** (a) compute an illumination/grazing mask from DEM+aspect and pass it (feature);
  (b) set `WEIGHT_SHADOW=0`, renormalise, and update copy (honest simplification).

### I-08 🟡 The "real PSR mask" is a depth heuristic, not a published PSR product
- **Where:** `prepare_lola_dataset.py:51-56` builds `lola_psr_mask.tif` as `depth < −900 m`.
- **Effect:** with real elevation data, the app still labels provenance `LOLA-derived … (Reference)`
  (`config.py:138`, `psr.py:215`) — accurate-ish wording, but the underlying mask is our own
  threshold, not an external truth. `/api/psr-validation`'s honest `UNLOADED` note
  (`web_server.py:727-731`) is therefore the *correct* display.
- **Fix:** state "topographic depression proxy" explicitly in `PSR_PROVENANCE_PUBLISHED` or acquire
  an actual PSR atlas (e.g. from a published PSR dataset) as `independent_psr_reference.tif`.

### I-09 ⚪ "AI/ML" labelling vs implementation reality
- **Where:** `ml_recommender.py` — deterministic Gaussian bandpass residual + sigmoid
  (`:18-81`) and EDT+fitness ranking (`:84-215`). No model file, no training, no `sklearn`/torch.
  The GeoTIFF tag says `MODEL=Lunar High-Pass Residual AI`; README/pitch use ML language.
- **Effect:** judge question "where's the training data?" has a factual answer: **there is no
  learned model** — it is signal processing + multi-criteria decision analysis.
- **Recommendation:** keep the capability, adjust wording to "deterministic detection + scoring
  (ML-style pipeline)" in README/pitch, or genuinely train a small detector (roadmap T-12).

---

## B. Feature/UI defects

### I-10 🟡 Sensitivity charts in the Prediction tab plot hard-coded arrays
- **Where:** `web/app.js` `renderSensitivityCharts()` (≈ line 4041) uses literal arrays instead of
  `POST /api/recalculate` → `sensitivity.bars/curve` (`web_server.py:504-530`) which are already
  computed for real.
- **Effect:** charts do not respond to slider changes → "show me the sensitivity" looks fixed.
- **Fix:** bind the real response fields (they exist — see doc 09 `/api/recalculate`).

### I-11 🟠 Thresholds become process-global state with no server-side reset
- **Where:** `web_server.py:438-446` (+ `:341-362`) assign `config.*` attributes.
- **Effect:** (a) one client's slider move changes results for every other session;
  (b) values persist until the server restarts — the UI's `resetDefaults()` only re-posts literal
  defaults; (c) server state silently diverges from `config.py` on disk (feeds I-04).
- **Fix:** keep a `DEFAULTS` snapshot dict; apply request values as a **local dict passed into the
  classifiers** instead of mutating `config`; add `POST /api/reset-defaults`.
- **Regression test:** POST a modified threshold, then POST `{}` and assert the response matches the
  defaults snapshot.

### I-11b 🟡 `/api/validate-geotiff` always reports success
- **Where:** `web_server.py:760-772` — `crs_valid: true`, `crs_name: "Moon South Pole …"`,
  `all_passed: true` are **literals**; only readability/min/max are real.
- **Effect:** an Earth-EPSG GeoTIFF would be certified "crs_valid: true" — directly contradicting
  `io_utils.py:199-206`'s guard elsewhere.
- **Fix:** call `io_utils.inspect_raster` and run the same Earth-EPSG + grid checks.

### I-12 🟠 Dead + unsafe upload endpoint; recommender ignores real pixel size
- **Where (a):** `POST /api/upload-raster` (`web_server.py:669-679`) is referenced **nowhere** in
  `web/app.js`, writes raw body bytes to fixed `data/custom_upload.tif` with no validation.
- **Where (b):** `ml_recommender.recommend_landing_sites` is called without `pixel_size_m`
  (`web_server.py:484-493`; `ml_recommender.py:~231` default 20.0) → clearance distances and
  easting/northing scaling are wrong on 240 m data.
- **Fix:** delete the route (or validate + deduplicate names); pass
  `abs(RASTER_CACHE["transform"].a)` as `pixel_size_m`.
- **Regression test:** LOLA-shaped cache → assert `clearance_radius_m` equals the configured radius
  and that `dist_to_psr_m` scales ×12 vs the synthetic cache.

### I-13 🔴 No auth, repo-root static serving, traversal, open CORS, LAN bind
- **Where:** doc 16 — `web_server.py:93` (root dir), `:134-149` (custom routes without `..` checks),
  `:152` (fallback = directory listings incl. `.git`), `:196` (`*` CORS), `:840` (bind `""`).
- **Effect:** unauthenticated arbitrary file read + full-repo exposure to anything on the LAN or any
  page open in the browser (SEC-01…SEC-03).
- **Fix:** the 11-item checklist in doc 16 §5 (task T-13).

### I-14 🟠 Mission report contains hard-coded numbers and labels
- **Where:** `mission_report.py:167-177` (rule-audit table always `0 / PASSED`),
  `:51-58` (fallback statistics block), `:71` ("UTC" printed from local time).
- **Effect:** the PDF can certify "0 violations" while the pipeline recorded violations — the
  single most dangerous artifact for a judge-facing claim.
- **Fix:** inject `process_validation_pipeline()["rule_audit"]` + real stats; format with
  `datetime.now(timezone.utc)`.

---

## C. Portability / repository hygiene

### I-15 🟡 Hard-coded absolute path + silent error swallowing
- **Where:** `prepare_lola_dataset.py:15` `ROOT_DIR = Path(r"e:\sistec\LunaSafe")` — breaks the
  ingestion path on any other machine; `web_server.py:207` and `:289` swallow exceptions silently.
- **Fix:** `ROOT_DIR = Path(__file__).resolve().parent`; return 400 with the parse error.

### I-16 🟡 Dependency file drift and unused pins
- **Where:** `requirement.txt` (singular) ≠ `requirements.txt`; `scikit-image` pinned but never
  imported (only pulled transitively by nothing — it is a direct pin with no consumer);
  `pandas` pinned but imported only by geopandas; `pyflakes==4.0.3` installed yet declared nowhere.
- **Effect:** editing the wrong file silently loses a pin; unused pins widen supply chain.
- **Fix:** delete `requirement.txt`, drop `scikit-image` (verify `ImageIO/tifffile` need), declare
  `pyflakes` if kept as the lint tool.

### M-01 ⚪ No `.gitignore` — 22 `.pyc` files tracked
Evidence: `git ls-files | findstr pycache` → 22 files; one is updated in *every* commit.
Fix: doc 18 §5 (task T-11).

### M-02 ⚪ Phase label mismatch in logs
`main.py` prints `[PHASE x/6]`-style banners for 6 phases while `ml_recommender` prints
`[PHASE 7/7]` — cosmetic confusion in the UI log pane. Normalise to `n/7`.

### M-03 ⚪ Downloader URL inconsistency
`web_server.py:633` vs `data/DOWNLOAD_INSTRUCTIONS.md:23` cite different NASA URLs. One of them is
stale; verify both and keep a single source (recommend: instructions doc + constant read by the
server).

### M-04 🟡 No CI, no linter run, no coverage, no issue tracker usage
No `.github/workflows`, no `pytest-cov`, no `mypy` config; `pyflakes` available but unused.
Fix: task T-07 (a 20-line workflow suffices).

### M-05 🟡 Tests are destructive to `outputs/`
`tests/test_main.py:19` + end-to-end tests rewrite artifacts (observed diff:
`lunasafe_hazard_map.pdf`, `psr_polygons.dbf`). Fix: task T-09 (redirect `OUTPUT_DIR` to `tmp_path`).

### M-06 🟡 Untested surface: all 4 non-CLI support modules + the whole web layer
`web_server.py` (864 L, 21 routes), `mission_report.py`, `export_web_data.py`,
`prepare_lola_dataset.py` have **zero** tests — precisely where I-03, I-11b, I-12, I-14 live.
Fix: task T-08.

### M-07 ⚪ Unbounded pipeline log buffer; no request logging
`PIPELINE_LOGS` grows for the process lifetime after a run (`web_server.py:44`); HTTP requests are
only logged by the stdlib to stderr. Fix: cap at N lines + rotate; add a one-line request log.

### M-08 ⚪ Client-side duplicated thresholds (drift risk)
`web/app.js` hard-codes defaults for previews/40 m ring (doc 12 §7). Fix: serve `defaults` (already
in `web_data.json`) and read them into the sliders on boot — plus a `config` echo endpoint (T-06).

---

## D. Security findings summary

Full detail with PoC strings: [`16_SECURITY_AND_PRIVACY_REVIEW.md`](16_SECURITY_AND_PRIVACY_REVIEW.md).

| ID | Severity | One-liner |
| :--- | :-: | :--- |
| SEC-01 | 🔴 | Path traversal in `/vendor/*`, `/outputs/*`, `/api/download/<name>` |
| SEC-02 | 🔴 | Static server rooted at repo + directory listings (incl. `.git`) |
| SEC-03 | 🔴 | No auth + `Access-Control-Allow-Origin: *` + binds all interfaces |
| SEC-04 | 🟠 | Unauthenticated subprocess spawn (DoS; argv is fixed → not command injection) |
| SEC-05 | 🟠 | Unbounded, unvalidated upload to a fixed path |
| SEC-06 | 🟠 | No range/finite checks on POST numbers; bad JSON → `{}` |
| SEC-07 | 🟡 | No SRI on CDN tags; vendored three.js frozen at r128 |
| SEC-08 | 🟡 | 19 `innerHTML` sinks fed by server strings |
| SEC-09 | 🟡 | Pins without hashes; undeclared `pyflakes`; no dependency scanning |
| SEC-10 | ⚪ | No subprocess timeout → possible permanent `BUSY` state |

**Clean:** no secrets, no PII, no cookies, no shell=True, no pickle/eval (doc 16 §3).

---

## E. Documentation claims that overstate the code (for the README owners)

| Claim (README / PITCH / SPEC) | Reality | Issue |
| :--- | :--- | :-: |
| "AI/ML-powered landing site recommender" | deterministic EDT + fitness + bandpass | I-09 |
| "validated PSR accuracy / F1" (batch path) | self-comparison → always 1.0 | I-01 |
| "40 m clearance guaranteed" | not in the algorithm | I-05 |
| "three-factor hazard score" | shadow factor always 0 in pipeline | I-07 |
| "rule 4 never safe in PSR (verified)" | web audit key bug → check never runs | I-03 |
| "Real NASA PSR mask" | depth < −900 m heuristic | I-08 |
| "interactive sensitivity analysis" (Prediction tab) | hard-coded chart data | I-10 |
| "reports 0 violations" in PDF | hard-coded text | I-14 |

---

## F. Priority order for fixing (see also doc 20)

1. **I-03, I-14** — false "all clear" signals (honesty-critical)
2. **I-02, I-12b, I-01** — wrong numbers on real data
3. **I-05, I-07** — features claimed but not implemented (either implement or stop claiming)
4. **I-06** — regenerate + guard against stale bundle
5. **SEC-01…03** — before any non-local exposure
6. **I-04, I-11** — configuration coherence
7. **I-13 remaining, I-11b, I-12a, I-10** — dead/unsafe/lying endpoints & UI
8. **I-15, I-16, M-01…M-08** — hygiene

---

## G. Change log of this register

| Date | Change |
| :--- | :--- |
| 2026-10-17 | Initial register created during documentation pass: I-01…I-16, M-01…M-08, SEC-01…10, evidence table §E. All OPEN. |
