"""
LunaSafe Mapping & Cartography Module
Renders a publication-grade 4-panel cartographic figure:
1. Lunar Elevation Model (DEM) with 3D shaded relief
2. Topographic Slope with key thresholds (5°, 10°, 15°)
3. PSR Outlines with vector boundary overlay and area metrics
4. Hazard Map with Green (Safe), Yellow (Caution), Red (Unsafe), Violet (Shadowed-Unknown)
Complete with:
- Legend, scale bar, grid-north arrow, CRS note, source provenance, 300 DPI PNG & PDF.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Rectangle
import matplotlib.patheffects as pe

import config

try:
    import geopandas as gpd
except ImportError:
    gpd = None


def compute_hillshade(
    slope_deg: np.ndarray,
    aspect_deg: np.ndarray,
    azimuth_deg: float = 315.0,
    altitude_deg: float = 45.0,
    valid_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Computes shaded relief (hillshade) from slope and aspect.
    Returns array in range [0.0, 1.0].
    """
    az_rad = np.radians(azimuth_deg)
    alt_rad = np.radians(altitude_deg)
    slope_rad = np.radians(np.clip(slope_deg, 0.0, 90.0))
    aspect_rad = np.radians(aspect_deg % 360.0)

    # Standard hillshade equation
    shaded = (
        np.sin(alt_rad) * np.cos(slope_rad)
        + np.cos(alt_rad) * np.sin(slope_rad) * np.cos(az_rad - aspect_rad)
    )
    shaded = np.clip(shaded, 0.0, 1.0)
    
    if valid_mask is not None:
        shaded[~valid_mask] = 0.0
        
    return shaded


def add_scale_bar(
    ax: plt.Axes,
    extent: Tuple[float, float, float, float],
    length_km: float = 1.0,
    location: str = "lower right",
) -> None:
    """
    Draws a clean cartographic scale bar in meters/kilometers onto the axes.
    """
    xmin, xmax, ymin, ymax = extent
    total_w = xmax - xmin
    total_h = ymax - ymin
    length_m = length_km * 1000.0

    if location == "lower right":
        x_start = xmax - 0.35 * total_w
        y_pos = ymin + 0.07 * total_h
    else: # lower left
        x_start = xmin + 0.08 * total_w
        y_pos = ymin + 0.07 * total_h

    bar_h = 0.015 * total_h

    # Background box for readability
    bg_box = Rectangle(
        (x_start - 0.03 * total_w, y_pos - 0.02 * total_h),
        length_m + 0.06 * total_w,
        bar_h + 0.05 * total_h,
        facecolor="#111625",
        edgecolor="#37474f",
        alpha=0.85,
        zorder=10,
    )
    ax.add_patch(bg_box)

    # Draw two alternating segments
    seg_len = length_m / 2.0
    ax.add_patch(Rectangle((x_start, y_pos), seg_len, bar_h, facecolor="#ffffff", edgecolor="#000000", zorder=11))
    ax.add_patch(Rectangle((x_start + seg_len, y_pos), seg_len, bar_h, facecolor="#2c3e50", edgecolor="#000000", zorder=11))

    # Labels
    ax.text(x_start, y_pos + bar_h + 0.008 * total_h, "0", color="#ffffff", fontsize=8, ha="center", va="bottom", zorder=12, fontweight="bold")
    ax.text(x_start + seg_len, y_pos + bar_h + 0.008 * total_h, f"{length_km/2:.1f}", color="#ffffff", fontsize=8, ha="center", va="bottom", zorder=12, fontweight="bold")
    ax.text(x_start + length_m, y_pos + bar_h + 0.008 * total_h, f"{length_km:.0f} km", color="#ffffff", fontsize=8, ha="center", va="bottom", zorder=12, fontweight="bold")


def add_grid_north_arrow(
    ax: plt.Axes,
    extent: Tuple[float, float, float, float],
    location: str = "upper right",
) -> None:
    """
    Draws a stylized Grid-North arrow on the axes.
    """
    xmin, xmax, ymin, ymax = extent
    total_w = xmax - xmin
    total_h = ymax - ymin

    if location == "upper right":
        x_c = xmax - 0.08 * total_w
        y_c = ymax - 0.10 * total_h
    else:
        x_c = xmin + 0.08 * total_w
        y_c = ymax - 0.10 * total_h

    arrow_len = 0.06 * total_h

    # North arrow
    ax.annotate(
        "N",
        xy=(x_c, y_c + arrow_len),
        xytext=(x_c, y_c),
        arrowprops=dict(
            facecolor="#ffffff",
            edgecolor="#111625",
            width=2.5,
            headwidth=8,
            headlength=8,
            shrink=0.05,
        ),
        ha="center",
        va="bottom",
        color="#ffffff",
        fontsize=10,
        fontweight="bold",
        zorder=12,
        path_effects=[pe.withStroke(linewidth=2, foreground="#111625")],
    )


def generate_4panel_hazard_map(
    dem: np.ndarray,
    slope: np.ndarray,
    aspect: np.ndarray,
    psr_mask: np.ndarray,
    hazard_classes: np.ndarray,
    dem_meta: Dict[str, Any],
    psr_gdf: Optional[Any] = None,
    output_png: Path = config.OUTPUT_MAP_4PANEL_PNG,
    output_pdf: Path = config.OUTPUT_MAP_4PANEL_PDF,
    is_synthetic: bool = True,
    verbose: bool = True,
) -> Tuple[Path, Path]:
    """
    Renders publication-grade 4-panel cartographic figure at 300 DPI in PNG and PDF:
    - Panel 1: Elevation (DEM) + Hillshade
    - Panel 2: Slope (degrees) + threshold contours
    - Panel 3: Permanently Shadowed Regions (PSR) + Boundary Outlines
    - Panel 4: Multi-Criteria Hazard Map (Green / Yellow / Red / Violet)
    """
    output_png = Path(output_png)
    output_pdf = Path(output_pdf)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    b = dem_meta["bounds"]
    extent = (b.left, b.right, b.bottom, b.top)
    nodata_val = dem_meta["nodata"]

    valid_mask = (dem != nodata_val) & ~np.isnan(dem)

    # 1. Compute hillshade for 3D realism
    hillshade = compute_hillshade(slope, aspect, valid_mask=valid_mask)

    plt.style.use(config.FIGURE_STYLE)
    fig, axes = plt.subplots(2, 2, figsize=(16, 14), dpi=config.PLOT_DPI)
    fig.patch.set_facecolor("#0b0e14")

    source_tag = config.SYNTHETIC_LABEL if is_synthetic else "NASA LRO LOLA Topography"
    fig.suptitle(
        f"LunaSafe: Lunar PSR Identification & Surface Hazard Classification\n"
        f"Region: Lunar South Pole ({source_tag}) | Spatial Resolution: {dem_meta['pixel_size_x']:.1f} m/pixel",
        fontsize=16,
        fontweight="bold",
        color="#e6edf3",
        y=0.98,
    )

    # Mask arrays for visualization
    dem_vis = np.ma.masked_where(~valid_mask, dem)
    slope_vis = np.ma.masked_where(~valid_mask, slope)
    psr_vis = np.ma.masked_where(~valid_mask, psr_mask)
    hazard_vis = np.ma.masked_where(hazard_classes == config.CLASS_NODATA, hazard_classes)

    # --------------------------------------------------------------------------
    # Panel 1: Elevation (DEM) + Hillshade
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor("#151b23")
    ax1.set_title("A. Lunar Digital Elevation Model (DEM)", fontsize=13, fontweight="bold", color="#ffffff", pad=10)
    # Background hillshade
    ax1.imshow(hillshade, cmap="gray", extent=extent, origin="upper", alpha=0.6)
    im1 = ax1.imshow(dem_vis, cmap="viridis", extent=extent, origin="upper", alpha=0.7)
    cbar1 = fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.03)
    cbar1.set_label("Elevation (meters relative to datum)", fontsize=10, color="#8b949e")
    cbar1.ax.tick_params(labelsize=8, colors="#8b949e")
    add_scale_bar(ax1, extent, length_km=1.0, location="lower right")
    add_grid_north_arrow(ax1, extent, location="upper right")
    ax1.set_xlabel("Easting (m)", fontsize=9, color="#8b949e")
    ax1.set_ylabel("Northing (m)", fontsize=9, color="#8b949e")
    ax1.tick_params(labelsize=8, colors="#8b949e")

    # --------------------------------------------------------------------------
    # Panel 2: Topographic Slope (degrees)
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor("#151b23")
    ax2.set_title("B. Topographic Slope & Critical Limits", fontsize=13, fontweight="bold", color="#ffffff", pad=10)
    ax2.imshow(hillshade, cmap="gray", extent=extent, origin="upper", alpha=0.35)
    im2 = ax2.imshow(slope_vis, cmap="inferno", extent=extent, origin="upper", alpha=0.85, vmin=0.0, vmax=25.0)
    cbar2 = fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.03)
    cbar2.set_label("Slope (degrees)", fontsize=10, color="#8b949e")
    cbar2.ax.tick_params(labelsize=8, colors="#8b949e")

    # Contours for critical thresholds: Safe (<5), Caution (<10), Hard Unsafe (>=15)
    cs = ax2.contour(
        slope_vis,
        levels=[config.SLOPE_SAFE_MAX, config.SLOPE_CAUTION_MAX, config.SLOPE_HARD_UNSAFE_MIN],
        colors=["#2ecc71", "#f39c12", "#e74c3c"],
        linewidths=[1.2, 1.4, 1.8],
        linestyles=["-", "--", "-"],
        extent=extent,
        origin="upper",
    )
    ax2.clabel(cs, inline=True, fontsize=8, fmt="%d°")
    add_grid_north_arrow(ax2, extent, location="upper right")
    ax2.set_xlabel("Easting (m)", fontsize=9, color="#8b949e")
    ax2.set_ylabel("Northing (m)", fontsize=9, color="#8b949e")
    ax2.tick_params(labelsize=8, colors="#8b949e")

    # --------------------------------------------------------------------------
    # Panel 3: PSR Identification & Vector Outlines
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor("#151b23")
    psr_px = int(np.sum(psr_mask == 1))
    psr_area_km2 = (psr_px * dem_meta["pixel_size_x"] * dem_meta["pixel_size_y"]) / 1.0e6
    ax3.set_title(f"C. Permanently Shadowed Regions (Area: {psr_area_km2:.3f} km²)", fontsize=13, fontweight="bold", color="#ffffff", pad=10)
    
    # Base terrain relief
    ax3.imshow(hillshade, cmap="bone", extent=extent, origin="upper", alpha=0.7)
    # PSR shaded overlay
    psr_overlay = np.zeros((*dem.shape, 4), dtype=np.float32)
    # Bright cyan / ice-blue for PSR fill
    psr_overlay[psr_vis == 1] = [0.0, 0.85, 1.0, 0.55]
    ax3.imshow(psr_overlay, extent=extent, origin="upper", zorder=3)

    # Plot vector polygon outlines if available
    if psr_gdf is not None and not psr_gdf.empty:
        for geom in psr_gdf.geometry:
            if geom.geom_type == "Polygon":
                bx, by = geom.exterior.xy
                ax3.plot(bx, by, color="#00ffff", linewidth=1.8, zorder=5)
                for interior in geom.interiors:
                    ix, iy = interior.xy
                    ax3.plot(ix, iy, color="#00ffff", linewidth=1.2, linestyle="--", zorder=5)
            elif geom.geom_type == "MultiPolygon":
                for poly in geom.geoms:
                    bx, by = poly.exterior.xy
                    ax3.plot(bx, by, color="#00ffff", linewidth=1.8, zorder=5)

    add_scale_bar(ax3, extent, length_km=1.0, location="lower right")
    add_grid_north_arrow(ax3, extent, location="upper right")
    ax3.set_xlabel("Easting (m)", fontsize=9, color="#8b949e")
    ax3.set_ylabel("Northing (m)", fontsize=9, color="#8b949e")
    ax3.tick_params(labelsize=8, colors="#8b949e")

    # Annotation badge
    ax3.text(
        0.04, 0.94,
        f"PSR Pixels: {psr_px:,}\nTotal Area: {psr_area_km2:.3f} km²",
        transform=ax3.transAxes,
        fontsize=9,
        color="#ffffff",
        fontweight="bold",
        va="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#111625", edgecolor="#00e5ff", alpha=0.9),
        zorder=10,
    )

    # --------------------------------------------------------------------------
    # Panel 4: Hazard Map (Green / Yellow / Red / Violet)
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor("#151b23")
    ax4.set_title("D. Surface Landing Hazard Classification", fontsize=13, fontweight="bold", color="#ffffff", pad=10)

    # Hillshade backdrop
    ax4.imshow(hillshade, cmap="gray", extent=extent, origin="upper", alpha=0.35)

    # Custom discrete palette matching prompt rules strictly:
    # 1: Safe (#2ecc71 Green)
    # 2: Caution (#f39c12 Yellow/Amber)
    # 3: Unsafe (#e74c3c Red)
    # 4: Shadowed-Unknown (#8e44ad Violet)
    class_colors = [
        config.CLASS_COLORS[config.CLASS_SAFE],              # Green
        config.CLASS_COLORS[config.CLASS_CAUTION],           # Yellow
        config.CLASS_COLORS[config.CLASS_UNSAFE],            # Red
        config.CLASS_COLORS[config.CLASS_SHADOWED_UNKNOWN],   # Violet
    ]
    cmap_hazard = ListedColormap(class_colors)
    norm_hazard = BoundaryNorm([0.5, 1.5, 2.5, 3.5, 4.5], cmap_hazard.N)

    ax4.imshow(hazard_vis, cmap=cmap_hazard, norm=norm_hazard, extent=extent, origin="upper", alpha=0.9, zorder=2)
    add_scale_bar(ax4, extent, length_km=1.0, location="lower right")
    add_grid_north_arrow(ax4, extent, location="upper right")
    ax4.set_xlabel("Easting (m)", fontsize=9, color="#8b949e")
    ax4.set_ylabel("Northing (m)", fontsize=9, color="#8b949e")
    ax4.tick_params(labelsize=8, colors="#8b949e")

    # Legend for Hazard Classes
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=config.CLASS_COLORS[config.CLASS_SAFE], edgecolor="#000000", label="Class 1: Safe (Slope<5°, R<1.5m, H<0.25)"),
        Patch(facecolor=config.CLASS_COLORS[config.CLASS_CAUTION], edgecolor="#000000", label="Class 2: Caution (0.25≤H<0.60)"),
        Patch(facecolor=config.CLASS_COLORS[config.CLASS_UNSAFE], edgecolor="#000000", label="Class 3: Unsafe (H≥0.60 | Slope≥15° | R≥5m)"),
        Patch(facecolor=config.CLASS_COLORS[config.CLASS_SHADOWED_UNKNOWN], edgecolor="#000000", label="Class 4: Shadowed-Unknown (PSR unconfirmed)"),
        Patch(facecolor=config.CLASS_COLORS[config.CLASS_NODATA], edgecolor="#555555", label="Class 0: NoData (Unmapped/Border)"),
    ]
    ax4.legend(
        handles=legend_elements,
        loc="upper left",
        fontsize=8.5,
        framealpha=0.9,
        facecolor="#111625",
        edgecolor="#37474f",
        labelcolor="#e6edf3",
    )

    # Bottom Metadata Note: CRS and Source Info
    crs_str = "Lunar South Pole Polar Stereographic (Moon IAU 2015 Sphere R=1,737,400 m, Central Meridian 0°)"
    source_str = f"Source: {source_tag} | Processing: LunaSafe Automated Hazard Pipeline"
    fig.text(
        0.5, 0.015,
        f"Projection: {crs_str} | {source_str}",
        ha="center",
        fontsize=9,
        color="#8b949e",
        fontstyle="italic",
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])

    # Save PNG and PDF at 300 DPI
    fig.savefig(output_png, dpi=config.PLOT_DPI, facecolor=fig.get_facecolor(), edgecolor="none")
    fig.savefig(output_pdf, dpi=config.PLOT_DPI, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    if verbose:
        print("=" * 70)
        print("PUBLICATION-GRADE 4-PANEL MAP GENERATION COMPLETED")
        print("=" * 70)
        print(f"Target DPI:          {config.PLOT_DPI}")
        print(f"PNG File:            {output_png} ({output_png.stat().st_size / 1024:.1f} KB)")
        print(f"PDF File:            {output_pdf} ({output_pdf.stat().st_size / 1024:.1f} KB)")
        print("Scale Bar:           1.0 km calibrated")
        print("Grid-North:          Standard Cartographic Vector (+Y Axis)")
        print("Palette:             Green / Yellow / Red / Violet / Dark Gray")
        print("=" * 70 + "\n")

    return output_png, output_pdf
