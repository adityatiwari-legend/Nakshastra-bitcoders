# `mapping.py` — Publication Cartography (380 lines)

> Role: renders the **4-panel hazard map** (PNG + PDF at 300 DPI) and the hillshade used by it.
  Matplotlib-only; optionally overlays PSR outlines when geopandas is importable.

**Status:** ✅ · **Tested by:** `tests/test_mapping.py` (2) · **Issues:** none in-module
(representative of doc 19 §E: figure text repeats claims).

---

## 1. API

| Function | Line | Purpose |
| :--- | :-: | :--- |
| `compute_hillshade(slope_deg, aspect_deg, azimuth=315, altitude=45, z_factor=1)` | 30 | classic hillshade from slope+aspect arrays |
| `generate_4panel_hazard_map(dem, slope, psr_mask, hazard_classes, psr_gdf, dem_meta, output_png, output_pdf, …)` | 149 | the product figure; returns paths |
| helpers | 60-148 | colour norms, scale bar, north arrow, legend builders |

Called from `main.py:152-167` (phase 5). Outputs:
`outputs/lunasafe_hazard_map.png` (~1.7 MB) and `.pdf` (~636 KB).

## 2. The figure (`:149-380`)

- `figsize=(16,14)`, `dpi=config.PLOT_DPI` (300), `style=config.FIGURE_STYLE` (dark background).
- **Panel A — Context:** DEM (viridis) over hillshade with alpha; scale bar (km) + north arrow.
- **Panel B — Slope:** inferno, `vmax=config.SLOPE_NORM_MAX` (15°); contour lines at 5/10/15°.
- **Panel C — PSR:** DEM base + cyan PSR overlay + GeoDataFrame outlines (if geopandas present)
  + area badge text (km²).
- **Panel D — Hazard:** `ListedColormap` from `config.CLASS_COLORS` with
  `BoundaryNorm([0.5,1.5,2.5,3.5,4.5])` so class ids map to discrete colours; custom legend with
  the five class names + pixel counts.
- **Footer:** projection string (lunar polar stereographic) + dataset provenance line
  (`SYNTHETIC DEMO` vs `NASA LRO LOLA`).
- Saves PNG then PDF (`:364-365`); returns `(png_path, pdf_path)`.

## 3. Design notes

1. **Hillshade from slope+aspect, not from the DEM** — consistent with what the UI computes
   (`web/app.js` offscreen hillshade) because both consume the same two arrays. Changing the sun
   angle here (`azimuth=315, altitude=45`) does *not* change the UI's version unless you also
   change `app.js`.
2. **Optional geopandas:** outlines are wrapped in try/except → map still exports without vector
   styling if the geo stack is missing (graceful degradation; prints a warning).
3. **Colour config lives in `config.CLASS_COLORS`** — the same ids/names are duplicated in
   `web/app.js` (M-08) and in `mission_report.py` legend text. Update all three together.
4. **`vmax` clipping at 15°** means steeper terrain saturates to the top colour — intentional for
   readability; slope detail above 15° is already "Unsafe" anyway.

## 4. Test coverage

| Test | Guards |
| :--- | :--- |
| `test_hillshade_computation` | flat terrain → constant shade; monotonic behaviour |
| `test_generate_4panel_hazard_map_end_to_end` | both files exist and are non-empty |

**Gaps:** legend text contents; PDF page size; NoData rendering; what happens when `psr_gdf` is
None/empty (untested branch at `:250+`).

## 5. Output dependency notes

- The figure is a **pure function of its arguments** — two runs with identical inputs produce
  equivalent figures, but PDF/PNG byte-level diffs still occur (font embedding/timestamps), which
  is why every pipeline run dirties `outputs/lunasafe_hazard_map.pdf` (doc 14 §4).
- Nothing reads the PNG/PDF back; safe to regenerate freely.

## 6. Extending

- **5th panel / layout change:** adjust `plt.subplots(2, 2, …)` grid and `add_axes` fractions;
  keep `constrained_layout` or explicit spacing so the footer doesn't overlap.
- **New layer:** add a panel function following the existing pattern
  `(ax, cmap, norm, title, cbar_label)`; add colour config to `config.py`.
- **Scale bar accuracy:** verify with `rasterio.transform` pixel size — it assumes square pixels
  (`meta["transform"].a`); non-square grids would need separate x/y handling.
