# FINDINGS_REPORT.md — LunaSafe / OrbisLuna

**Phase 0 audit findings, fix status, and final project state**
Evidence-based review performed across sessions (2026-10-18 → 2026-10-22) using:
static code inspection, server logs, live API probes, headless-Edge DOM/console smokes,
pytest + Node protocol tests, and Lighthouse audits (headless Edge, identical flags).

Severity scale: **P0** crash/security/data corruption · **P1** core workflow broken or
wrong data shown · **P2** usability/reliability · **P3** polish.
Full per-bug evidence rows: [BUG_TRACKER.md](BUG_TRACKER.md) (BUG-001…BUG-041).
Full chronological repairs: [PROJECT_REPAIR_LOG.md](PROJECT_REPAIR_LOG.md).

---

## 1. Executive summary

At Phase 0 the project was a partially-working prototype: the web dashboard could
load a dataset, but **grid mismatches silently corrupted every number** (areas off
by 144x, elevations from the wrong raster), **provenance badges claimed "REAL NASA
LRO LOLA" over synthetic outputs**, the Rover Studio and Artifact Hub tabs were
**literally invisible** (unclosed div), validation charts drew **hardcoded
fabricated data**, and real 240 m/px data classified as **98% Unsafe** because
20 m-calibrated roughness thresholds were applied unchanged.

After Phases 0-5:

| Area | State now |
|---|---|
| Data integrity | Grid-matched raster cache, shape validation, provenance from raster tags (BUG-001…006, 023, 031, 032) |
| Honesty | Honest badges/tags/disclaimers everywhere: PSR = derived proxy, illumination-time = analytic model, status = actual loaded dataset (BUG-003, 011, 025, 033, 034) |
| Correctness | Resolution-scaled roughness thresholds (20 m reference → 240 m scale factor 12) → Safe 2.91% / Caution 36.03% / Unsafe 55.96% / Shadow 5.11% with **0 rule violations** (BUG-030, 031) |
| UI/UX | All tabs render (BUG-019); live worker-backed reclassification; Rover Studio with avoid-PSR/battery/exports; Artifact Hub with manifest/search/preview/upload (BUG-019…029) |
| Crash bugs | NaN JSON kill (BUG-035) and AOI type crash (BUG-036) fixed + guarded by tests |
| Tests | 79 → **86 passed** (incl. known-grid exact hazard map + exact rover routes + parts= endpoints + scaled-sensitivity invariants); `npm run lint/build/test` green; pyflakes clean (34 files) |
| Performance | Lighthouse **0.36 → 0.80**, FCP 8.0 s → **2.0 s**, LCP 21.3 s → **2.5 s**, weight 5,472 → **2,373 KiB**, CLS 0.484 → 0.297 |

---

## 2. Findings by theme (Phase 0 → fixed)

### A. Data integrity / grid mismatches (P0/P1)
- **BUG-001…005** — `RASTER_CACHE` mixed a 250x250 @240 m LOLA DEM with
  200x200 @20 m synthetic outputs: `/api/rover-route` crashed (broadcast error),
  `/api/recalculate` areas inflated 144x, PSR targets returned wrong elevations,
  and `load_raster_cache()` accepted the mix silently. **Fixed:** grid-matched DEM
  selection + shape/pixel validation + 4 regression tests.
- **BUG-006** — `ACTIVE_SITE_ID` decoupled from loaded outputs. **Fixed:** single
  source of truth synced at startup/pipeline/site-switch.

### B. Provenance & honesty (P1)
- **BUG-003** — `/api/status` derived "REAL NASA LRO LOLA" from *input file
  existence*, not the outputs actually served. **Fixed:** provenance from loaded
  cache + raster tags.
- **BUG-011** — PSR mask is a DEM-threshold **proxy** (no official PSR product in
  the PDS polar archive) yet was labeled as a real product. **Fixed:** honest tags
  ("DERIVED PSR PROXY (NOT AN OFFICIAL PRODUCT)") + API disclosure + docs.
- **BUG-023/025** — mission-report PDF provenance by input existence + a
  fabricated fallback stats table. **Fixed:** hazard-tag provenance; honest
  empty-state rows.
- **BUG-032** — nine real `artemis_*` crops mislabeled "Procedural Site Model".
  **Fixed:** tag predicate covers `artemis_*`.
- **BUG-033/034** — data sources invisible/stale (dead USGS URL, wrong product
  names, missing checksums). **Fixed:** `/api/data-sources` dynamic panel +
  rewritten `DOWNLOAD_INSTRUCTIONS.md` with SHA-256 checksums.

### C. Crashes that killed core workflows (P0)
- **BUG-019** — unclosed duplicate `landingSitesTab` div nested Rover Studio +
  Artifact Hub inside a `display:none` parent: both tabs' content **never
  rendered**. **Fixed:** dead block removed; div depth balanced (0 unclosed).
- **BUG-030** — ~98% of real LOLA terrain classified Unsafe: roughness thresholds
  calibrated for 20 m applied at 240 m (720 m std footprint ≈ 40 m).
  **Fixed:** `config.scaled_roughness_thresholds(pixel_size_m)` threaded through
  classifier, audit, server, PDF, export defaults, and the frontend `TH` object.
- **BUG-035** — `/api/data` emitted raw `NaN` (6 illumination cells) →
  `JSON.parse` throws → **entire dashboard dead** (skeleton stuck, KPIs `--`).
  **Fixed:** `_finite_round()` at export + strict-JSON sanitizer + null-tolerant
  frontend + tests.
- **BUG-036** — AOI-aware `computeSensitivityData` crashed on a legacy numeric
  `validPx` (`validPx.has is not a function`). **Fixed:** `instanceof Set`
  coercion at entry.

### D. Fabricated or decoupled UI data (P1/P3)
- **BUG-014/015** — validation charts drew hardcoded numbers and hardcoded axes
  while real server data was ignored (real data overflowed invisibly).
  **Fixed:** real-data-only rendering + dynamic `niceCeilAxis()`.
- **BUG-016** — "100.0% Mapped" chip hardcoded despite ~18% NoData.
  **Fixed:** computed "% Valid Terrain".

### E. Feature gaps closed (P1/P2/P3)
- **BUG-020/021** — rover profile chart blank on load / legend promised an
  undrawn slope curve. **Fixed.**
- **BUG-022** — `NO_PATH_FOUND` left stale KPIs + generic error. **Fixed:**
  dedicated failure UI state.
- **BUG-026/027** — Summit-Ridge goal always picked a PSR pixel; Artifact Hub
  lacked dataset context. **Fixed.**
- **BUG-028** — Rover Studio was display-only. **Fixed:** avoid-PSR constraint,
  hazard breakdown, GeoJSON/CSV export, reset/undo, loading states.
- **BUG-029** — Artifact Hub was a static grid. **Fixed:** manifest API, search/
  filter/sort, previews, upload with allow-list, Save-Route integration.
- **BUG-007…010, 012, 013, 017, 018, 024** — stubbed GeoTIFF validation,
  hardcoded paths/pixel sizes, test clobbering of live outputs, accessibility
  floor, favicon 404, stale PDF downloads: all fixed except **BUG-017**
  (accessibility, partially improved — documented) and **BUG-018** (legacy
  `dashboard.html` generator kept for reproducibility, unreferenced).

### F. Performance & quality (Phase 5)
- **5A baseline (Lighthouse):** perf 0.36, FCP 8.0 s, LCP 21.3 s, CLS 0.484,
  weight 5,472 KiB; 4,365 KiB compressible text served uncompressed; 6,250 ms
  render-blocking; three.min.js (603 KB) loaded eagerly for a tab most sessions
  never open.
- **5B server:** HTTP/1.1 keep-alive, gzip for text types (+`Vary`), ETag/304,
  cache policies, `/api/data?parts=core|extras` split (core = 408 KB wire vs
  2.56 MB full), strict-JSON retained.
- **5C frontend:** lazy `ensureThreeJs()` (removed blocking head scripts +
  `document.write` fallback), Web Worker preview pipeline (`worker.js` +
  shared `hazard_core.js`) with sync fallback and stale-response drop, param/
  AOI/compare memoization, deferred extras merge, tabular-nums CLS mitigation.
  Pre-release catches: **BUG-037** (top-level `new THREE.*`), **BUG-038**
  (worker params echo), **BUG-039** (missing server routes for new JS).
- **5D quality:** pyflakes clean across 34 Python files (11 findings fixed),
  dead code removed (`computeAndRenderClientSensitivity`, unused imports/locals),
  dependency-free `package.json` → `npm run lint` / `npm run build` / `npm test`.
- **5E tests:** known-grid **exact** 4x4 hazard class map (hand-computed),
  known-grid **exact** rover route (single channel) + forced single-gap crossing,
  3 `/api/data?parts=` endpoint tests, Node worker-protocol suite (5 tests).

---

## 3. Final verification state

| Check | Result |
|---|---|
| `npm run build` | **PASSED** (JS syntax, pyflakes 34 files, index asset integrity, script order, lazy-Three) |
| `npm run lint` | **PASSED** |
| `npm test` | **10/10 Node + 86/86 pytest** |
| HTTP probe (24 checks) | 24/24 (gzip, keep-alive, parts endpoints, routes, strict JSON) |
| Headless-Edge interaction smoke | boot via core bundle, extras merge, worker preview + memo, lazy 3D — 0 console errors |
| Lighthouse after | perf **0.80**, FCP 2.0 s, LCP 2.5 s, 2,373 KiB, CLS 0.297 (before/after table: README §12) |

## 4. Known limitations & next steps

Canonical list: **README §12** (honest limitations: PSR proxy, analytic
illumination model, resolution-scaling baseline, 250x250 browser grid,
fonts/CDN CLS headroom, a11y 0.78, stdlib single-process server, same-origin
worker requirement) and the six next steps (Playwright e2e, service worker +
font self-hosting, axe-core CI, tiled multi-region loading, documented-only
dataset ingestion, Lighthouse CI budget gate).
