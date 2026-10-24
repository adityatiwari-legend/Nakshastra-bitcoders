# `main.py` — CLI Pipeline Orchestrator (260 lines)

> Role: **the batch entry point.** Selects inputs, runs the 7 phases in order, prints a summary,
> exits 0/≠0. Contains no scientific logic of its own.

**Status:** ✅ · **Tested by:** `tests/test_main.py::test_main_pipeline_execution` (destructive, M-05) ·
**Issues:** M-02 (phase labels), I-04 (web spawns it without config), I-07 (shadow term omitted).

---

## 1. Public surface

| Symbol | Line | Purpose |
| :--- | :-: | :--- |
| `sys.path` bootstrap | 14-16 | makes flat modules importable |
| venv auto-switch | 18-26 | if `rasterio` missing → re-exec under `.venv\Scripts\python.exe` |
| imports | 28-35 | `config, io_utils, psr, terrain, hazard, mapping, validate, ml_recommender` |
| `run_pipeline(dem_path, psr_path, force_synthetic, fail_on_mismatch, verbose=True)` | 38 | the whole workflow; returns exit-code-relevant results |
| input selection ladder | 60-80 | see §2 |
| `main()` + argparse | 237-256 | flags `--dem --psr --force-synthetic --fail-on-mismatch --quiet` |
| `if __name__ == "__main__"` | 258 | `raise SystemExit(main())` |

**Import side effects:** importing `config` creates `data/` and `outputs/`.

## 2. Input selection (verified behaviour)

```
--force-synthetic  → data/synthetic_{dem,psr}.tif
--dem/--psr given & exist → those files
else data/lola_* exists → real dataset
else → synthetic fallback (io_utils.load_and_align_datasets also falls back internally)
```
`is_synthetic = "synthetic" in str(dem_target).lower()` (`:80`) — a **substring test**, so any path
containing "synthetic" is labelled synthetic. Silent fallbacks print `[INFO] … Utilizing synthetic
dataset` (`io_utils.py:394-404`) — a wrong `--dem` path therefore *succeeds* with different data.

## 3. Phase map (the 7 phases)

| Phase | Lines | Calls | Writes |
| :-: | :-- | :--- | :--- |
| 1 Ingest | 85-93 | `io_utils.load_and_align_datasets` | — (console only) |
| 2 PSR | 98-109 | `psr.process_and_export_psr` | `psr_binary.tif`, `psr_polygons.*` |
| 3 Terrain | 114-130 | `terrain.process_terrain_pipeline` | 4 metric GeoTIFFs + `terrain_histograms.png` |
| 4 Hazard | 135-147 | `hazard.process_hazard_pipeline(slope, rough, psr, …)` | `hazard_classes.tif`, `hazard_summary.csv` |
| 5 Cartography | 152-167 | `mapping.generate_4panel_hazard_map` | `lunasafe_hazard_map.png/.pdf` |
| 6 Validation | 172-186 | `validate.process_validation_pipeline` | `slope_sensitivity.png` + audit dict |
| 7 Autonomy | 191-201 | `ml_recommender.run_mission_autonomy` ⚠ **re-opens files from disk** | `boulder_hazard.tif`, `landing_sites.json` |
| Summary | 206-234 | prints elapsed time, provenance, `total_violations`, PSR km², 15-artifact list | — |

Notes:
- **Phase 7 does not reuse in-memory arrays** (`ml_recommender.py:238-253` reads paths) → it
  silently depends on phases 2/3/4 having written their files.
- **`shadow_fraction` is not passed** at `:137` → `D = 0` (I-07).
- Phase banners say `x/6` while `ml_recommender` prints `7/7` (M-02).
- `--fail-on-mismatch` only influences `io_utils.align_psr_to_dem`; other failures always raise.

## 4. Exit & error contract

- Any uncaught exception → traceback, non-zero exit (propagated by `run.bat` and by the web
  subprocess worker, which logs `[Server] Pipeline finished with exit code N`).
- Validation non-zero violations do **not** fail the run (only `--fail-on-mismatch`-class errors do).

## 5. Usage

```powershell
python main.py
python main.py --force-synthetic --quiet
python main.py --dem data\lola_south_pole_dem.tif --psr data\lola_psr_mask.tif --fail-on-mismatch
```
Expected: ~8-10 s, exit 0, 15 artifacts refreshed.

## 6. Known weaknesses (with tasks)

| Weakness | ID | Task |
| :--- | :-: | :-: |
| No CLI flags for thresholds → web config can't reach it | I-04 | T-06 |
| Shadow term never supplied | I-07 | T-12 |
| Phase label mismatch `x/6` vs `7/7` | M-02 | T-18 |
| Full run rewrites `outputs/` (also via pytest) | M-05 | T-09 |
| Bundle not refreshed for manual CLI runs (only the web worker does it) | I-06 | T-10 |
| `is_synthetic` substring heuristic | — | consider `dem_target == config.SYNTHETIC_DEM_PATH` |

## 7. Extension points

- **Add a phase:** insert between existing blocks, print a banner, add its artifacts to the summary
  list (`:216-230`) *and* to `tests/test_main.py:36` (or the test's artifact list) and doc 06 §2.
- **Add a flag:** argparse (`:237-256`) → `run_pipeline` parameter → the phase that needs it.
  For web-driven config, also thread the value through `web_server.py`'s `cmd` list (`:369`).
