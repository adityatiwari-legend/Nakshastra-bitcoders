# `io_utils.py` — Geospatial I/O & Dataset Utilities (464 lines)

> Role: the **only** module that touches raster files on disk (read, write, inspect, align,
  generate). Everything downstream receives numpy arrays + a metadata dict.

**Status:** ✅ · **Tested by:** `test_smoke.py` (roundtrip), `test_preprocessing.py` (4) ·
**Issues:** I-15 sibling (path assumptions), synthetic fallbacks hide bad inputs.

---

## 1. Lazy import guard

```python
try:
    import rasterio ...
except ImportError:
    rasterio = None        # then every entry raises ImportError with a clear message
```
(`io_utils.py:14-24`) — keeps `config`-only imports working in partial environments and lets the
venv auto-switch in `main.py:18-26` trigger on the *first* rasterio use.

## 2. API surface

| Function | Line | In → Out | Notes |
| :--- | :-: | :--- | :--- |
| `write_geotiff(path, data, transform, crs, nodata, tags)` | 116 | ndarray → `.tif` | `driver=GTiff`, `compress="lzw"`, single band, caller-supplied tags only |
| `read_geotiff(path)` | 154 | `.tif` → dict | keys: `data, crs, transform, nodata, bounds, pixel_size_x/y, shape, dtype, profile, tags` |
| `inspect_raster(path, verbose)` | 191 | `.tif` → stats dict | **Earth-EPSG sentinel** at `:199-206` → `ValueError`; prints banner; computes valid/nodata counts, min/max |
| `check_grid_alignment(shape, crs, transform, ref…, tol=1e-4)` | 257 | metadata → (ok, list-of-diffs) | shape + CRS + all 6 affine coefficients |
| `align_psr_to_dem(psr_path, dem_meta, fail_on_mismatch, verbose)` | 288 | file → aligned array | overlap check (`:324-333`) → raise (`:309-318`) or nearest reprojection (`:339-348`) |
| `load_and_align_datasets(dem_path, psr_path, force_synthetic, fail_on_mismatch, verbose)` | 380 | paths → `(dem, psr, dem_meta, psr_meta)` | synthetic fallback ladder (`:392-404`) |
| `generate_synthetic_lunar_crater(...)` | 416 | params → `(dem, psr, transform, lunar_crs)` | seeded RNG; writes nothing; used by tests + `get_started` paths |

## 3. The metadata dict (`dem_meta`)

Every consumer relies on this shape (produced by `read_geotiff`):

```python
{"data": np.ndarray, "crs": rasterio CRS, "transform": Affine,
 "nodata": float|None, "bounds": BoundingBox, "pixel_size_x": float, "pixel_size_y": float,
 "shape": (ny, nx), "dtype": str, "profile": dict, "tags": dict}
```
Passing a bare array instead of this dict is the most common way to break a new call site.

## 4. Design decisions

1. **Earth-EPSG rejection is string-based** (`:199-206`): five signatures
   (`EPSG:4326`, `WGS 84`, `WGS_1984`, `ETRS89`, `NAD83`) are checked against `str(crs)`.
   A lunar CRS containing those substrings would be refused (none do).
   *Limitation:* a non-listed Earth CRS (e.g. `EPSG:3413`) would pass — the rule is
   allow-list-in-spirit, block-list-in-fact.
2. **Fallback is silent-ish:** missing files log `[INFO]` and switch to synthetic
   (`:394-404`) rather than raising — great for demos, risky for scripted research (a bad `--dem`
   path *succeeds* with different data). Consider adding a `strict` flag alongside
   `--fail-on-mismatch` in a future refactor.
3. **Reprojection is nearest-neighbour only** — correct for masks, slightly lossy for continuous
   elevation; acceptable because alignment mismatches are exceptional.
4. **Synthetic generator is deterministic** (seeded `np.random.default_rng`) → tests can assert
   exact geometry (`test_smoke.py::test_synthetic_crater_topography`).
5. **Writes never preserve input tags** — callers pass `tags` explicitly; there is no automatic
   provenance injection (see doc 10 §3 for the verified tag inventory).

## 5. Read/write invariants to preserve

- Lunar CRS must round-trip: `read(write(x)).crs == x.crs` (covered by `test_synthetic_geotiff_roundtrip`).
- NoData must survive: readers use `data != nodata` masks everywhere downstream.
- Grid alignment tolerance is `1e-4` in world units — do not loosen without revisiting
  `align_psr_to_dem`.
- Never write to `data/` from this module except via tooling (`prepare_lola_dataset`).

## 6. Gotchas

| Gotcha | Detail |
| :--- | :--- |
| `nodata=None` vs `-9999` | PSR masks are written with `nodata=None` (`psr.py:231`); float metrics with `-9999`. Code that assumes a non-None nodata will mis-mask PSR |
| `bounds` are in the raster's CRS (metres on the Moon) | UI converts to easting/northing using them (`web_data.json.bounds`) |
| Importing this module is side-effect free (unlike `config`) | safe to import in isolation |
| `prepare_lola_dataset` has its **own** hardcoded root (I-15) | it does not use `io_utils.BASE_DIR` for sys.path |

## 7. When editing

- New output file → always go through `write_geotiff` (gets LZW + consistent profile).
- Changing the Earth-CRS check → add a test in `test_preprocessing.py` and update doc 16's
  "not a problem" table if you weaken it.
- Adding a dataset type → document it in doc 10 §2 and add an `inspect_raster` smoke test.
