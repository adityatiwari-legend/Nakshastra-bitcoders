# 22 — Contributing and Code Conventions

*Derived by observing the existing code (not invented): 14 backend modules, 9 test files, one
4.5k-line frontend. Follow these and your diffs will look native to this repo.*

---

## 1. Ground rules (project-specific)

1. **Config first.** Every threshold/path/colour lives in `config.py`. Never introduce a magic
   number into a module if it can be a `config` constant (see doc 12 §7 for the duplication map —
   and *search* for existing literals before adding one).
2. **Honesty rules are binding** — `.agents/rules/lunasafe.md`: no invented accuracy numbers, no
   mislabelled provenance, no Earth EPSG codes, Class 4 ≠ safe. If a feature can't honour them,
   update the docs instead of faking it.
3. **Arrays in, arrays out** for domain modules — pass numpy arrays + `dem_meta`-style dicts; do
   **not** open files inside `hazard/validate/ml_recommender` core functions.
4. **Never modify `web/vendor/*`** (vendored three.js r128).
5. **Never hand-edit `outputs/`** — regenerate.
6. **Tests accompany behaviour changes** (doc 20 DoD).

---

## 2. Module & file conventions

| Rule | Evidence / pattern |
| :--- | :--- |
| Flat top-level modules, no packages | every file `import config` at top |
| First lines of a script | `sys.path.insert(0, str(Path(__file__).resolve().parent))` (`main.py:14-16`, `web_server.py:27-29`, `prepare_lola_dataset.py:15-16`) |
| Optional heavy imports guarded | `if rasterio is None: raise ImportError(...)` (`io_utils.py:14-24`), same for geopandas/shapely in `psr.py` |
| One module = one domain responsibility | doc 05 §2 table |
| Public functions | `snake_case`, module-level, with a **docstring** (Google-ish plain prose + Args/Returns sections as in `hazard.py`, `ml_recommender.py`) |
| Entry points | `if __name__ == "__main__":` blocks at file bottom (`main.py:237`, `web_server.py:858`, …) |
| No `logging` module | `print()` banners with `[INFO]`/`[WARN]` prefixes and `====` separators |
| Comments | sparse, in English, explaining *why* (e.g. `hazard.py:111-113` on Class 4) — do not narrate obvious code |
| Type hints | light: `Path`, `Optional[float]`, `Dict[str, Any]` on I/O functions; none on hot numpy paths |
| CLI | `argparse` with `--flags` only (`main.py:237-256`) |

---

## 3. Backend style patterns (copy these)

**Reading config**
```python
import config
...
threshold = config.SLOPE_SAFE_MAX
```

**Writing a raster** (always via the helper, never raw rasterio):
```python
io_utils.write_geotiff(output_path=cfg_path, data=arr, transform=meta["transform"],
                       crs=meta["crs"], nodata=config.DEFAULT_NODATA_VALUE,
                       tags={"PROJECT": "LunaSafe", "METRIC": "SLOPE", "UNITS": "DEGREES"})
```
(`terrain.py:342-349`, `psr.py:226-233`, `hazard.py:223-230`)

**Guard rails at function entry** — raise early with a specific message:
```python
if arr.shape != ref.shape:
    raise ValueError(f"GRID MISMATCH: expected {ref.shape}, got {arr.shape}")
```
(`io_utils.py:309-318` style; project rule: *fail loudly, never silently approximate*.)

**Classify functions take keyword arrays and return `(result, score)`** —
`hazard.classify_hazard_surface(slope=…, roughness=…, psr_mask=…)`.

**Verbose flag** is threaded through pipeline functions (`verbose: bool = True`) so `--quiet` works.

---

## 4. Frontend conventions (`web/`)

| Rule | Detail |
| :--- | :--- |
| No build step | plain ES2017-ish JS, no bundler/npm — **do not introduce one** without a team decision |
| One file for logic | `app.js` is sectioned by comments (`/* ===== SECTION ===== */`); new features append a section, keep the pattern |
| Select by id | `document.getElementById(...)`; ids live in `index.html` |
| API calls | `fetch('/api/…')` + `async/await`; every POST sends `Content-Type: application/json` |
| Threshold access | read from `DATA.defaults` (bundle) — **not** literals (T-06); until then mirror `config.py` exactly |
| Rendering | 2D = `ImageData` offscreen canvases composited by `drawMap()`; 3D = three.js r128, no newer API |
| Styling | CSS custom properties (`--color-cyan`, `--text-muted`); dark theme is the only theme |
| Unsafe sinks | prefer `textContent`; if you must `innerHTML`, interpolate only escaped/`config`-derived values (doc 16 SEC-08) |

---

## 5. Test conventions

```python
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
```
(copy the header from `tests/test_smoke.py:1-8`)

- Function names: `test_<behaviour>[_and_<behaviour>]` — descriptive of the *invariant*
  (`test_nodata_is_never_treated_as_safe`).
- Use `tmp_path` for artifacts; **never** write into `outputs/` (until T-09 lands, avoid adding new
  end-to-end tests that do).
- Prefer **exactness assertions** over tolerances where the maths is exact
  (`test_planar_ramp_slope_exactness`, `test_calculate_psr_area_exactness`).
- Every bug fix adds a test that **fails before** the fix (see T-01/T-02 examples in doc 20).
- File placement: `tests/test_<module>.py`; web server tests go in `tests/test_server.py` (T-08).

---

## 6. Documentation conventions (this folder)

| Rule | Detail |
| :--- | :--- |
| File naming | `NN_TOPIC.md` for core docs, descriptive names in subfolders |
| Evidence labels | VERIFIED / PARTIALLY VERIFIED / INFERRED / NOT FOUND / PLANNED |
| Citations | `file.py:line` (and `web/app.js` ≈line for the un-line-numbered frontend) |
| Status icons | ✅ complete · 🟡 partial · 🟠 stub/risky · 🔴 broken/absent · ⚪ info |
| Issue/task IDs | `I-nn` issues (doc 19), `T-nn` tasks (doc 20), `SEC-nn` security (doc 16) — never renumber, only append |
| Diagrams | Mermaid sources in `architecture/*.mmd`, referenced from the markdown that explains them |
| After a code change | update the touched doc + mark doc 19 entry FIXED with SHA |

---

## 7. Git conventions

- Branch names: `feat/<summary>`, `fix/<summary>`, `docs/<summary>`.
- Commit subject: `<type>: <imperative summary>` where type ∈
  `feat|fix|docs|test|chore|refactor` (e.g. `fix: use emitted rule4 key in audit (I-03)`).
- Body: bullet the issue ID, the visible effect, and the verification command.
- Never `git add -A` — 22 `.pyc` files are tracked today (M-01); stage explicit paths.
- Commit artifacts only deliberately (T-14 decides the policy).
- One concern per commit; docs and code that *must* move together may share a commit.

---

## 8. Python/dependency policy

- Python 3.10+ (3.13 in `.venv`); stdlib first — the server deliberately uses `http.server`
  (doc 05 A1). **Adding a web framework is a team decision, not a drive-by change.**
- New dependency ⇒ pin in `requirements.txt` **and** update doc 04 + `11_SETUP…` §3.
- No unpinned installs (`pip install foo` without `==` is discouraged; it already bit us with
  `pyflakes`, I-16).
- Keep optional-import guards for geopandas-class libraries so a partial install still runs the CLI.

---

## 9. Review checklist (≈5 minutes)

- [ ] No new literal thresholds outside `config.py` (grep the number repo-wide)
- [ ] New/changed route documented in doc 09 + `api_documentation/REST_API.md`
- [ ] New `float()`-from-request is finite and range-checked
- [ ] `innerHTML` avoided or escaped
- [ ] Test added/updated; `pytest -q` green; `git status` clean after restore
- [ ] Issue register (doc 19) and roadmap (doc 20) updated if applicable
- [ ] No claims added to README that the code doesn't literally do (doc 19 §E)

---

## 10. "First PR" exercise (safe onboarding task)

1. Pick **M-02** (phase label `x/7`) — touches one print in `main.py` and one in `ml_recommender.py`.
2. Branch `fix/phase-labels`, commit with body, run `pytest -q --ignore=tests/test_main.py`.
3. Update the one line in `07_CODEBASE_DEEP_DIVE.md` that mentions the mismatch.
4. Open the PR with the checklist above ticked.

You will have touched code, tests, and docs exactly the way this project expects.
