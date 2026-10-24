"""
LunaSafe Terrain Module
Calculates topographic slope, aspect, and roughness metrics (local elevation
standard deviation and Terrain Ruggedness Index - TRI) tied to DEM pixel resolution.
Exports GeoTIFFs preserving Lunar CRS and creates distribution histograms.
Strictly preserves NoData: NoData pixels are never treated as Safe.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import scipy.ndimage as ndi
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
import io_utils


def calculate_slope_and_aspect(
    dem: np.ndarray,
    pixel_size_x: float,
    pixel_size_y: float,
    nodata_val: Optional[float] = config.DEFAULT_NODATA_VALUE,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes terrain slope (degrees) and aspect (degrees clockwise from North, 0-360)
    using Horn's 3x3 finite-difference algorithm.
    Preserves NoData pixels.
    
    Returns:
        slope: 2D float32 array in degrees (0 to 90), NoData where DEM is NoData
        aspect: 2D float32 array in degrees (0 to 360), NoData where DEM is NoData
        valid_mask: 2D boolean array (True where valid, False where NoData)
    """
    if nodata_val is not None and not np.isnan(nodata_val):
        valid_mask = (dem != nodata_val)
    elif nodata_val is not None and np.isnan(nodata_val):
        valid_mask = ~np.isnan(dem)
    else:
        valid_mask = np.ones(dem.shape, dtype=bool)

    # Replace NoData temporarily with nearest neighbor or edge value for kernel calculation
    filled_dem = dem.copy()
    if np.any(~valid_mask):
        # Fill NoData with median of valid to prevent gradient explosion at boundaries
        valid_median = float(np.median(dem[valid_mask])) if np.any(valid_mask) else 0.0
        filled_dem[~valid_mask] = valid_median

    # Horn kernels for dz/dx and dz/dy
    # [ -1  0  1 ]
    # [ -2  0  2 ] / (8 * dx)
    # [ -1  0  1 ]
    kernel_x = np.array([[-1.0, 0.0, 1.0],
                         [-2.0, 0.0, 2.0],
                         [-1.0, 0.0, 1.0]], dtype=np.float32) / (8.0 * float(pixel_size_x))

    # [  1  2  1 ]
    # [  0  0  0 ] / (8 * dy)
    # [ -1 -2 -1 ] (North positive in cartesian y, top is positive row index decreasing)
    kernel_y = np.array([[ 1.0,  2.0,  1.0],
                         [ 0.0,  0.0,  0.0],
                         [-1.0, -2.0, -1.0]], dtype=np.float32) / (8.0 * float(pixel_size_y))

    dz_dx = ndi.convolve(filled_dem, kernel_x, mode="nearest")
    dz_dy = ndi.convolve(filled_dem, kernel_y, mode="nearest")

    # Slope calculation
    rise_run = np.sqrt(dz_dx**2 + dz_dy**2)
    slope_rad = np.arctan(rise_run)
    slope_deg = np.degrees(slope_rad).astype(np.float32)

    # Aspect calculation (clockwise from North: 0 = North, 90 = East, 180 = South, 270 = West)
    # Mathematical angle in radians from X-axis: atan2(dz_dy, -dz_dx)
    aspect_math = np.degrees(np.arctan2(dz_dy, -dz_dx))
    aspect_deg = (90.0 - aspect_math) % 360.0
    # Flat areas (slope < 0.01 deg) have undefined / neutral aspect (set to 0.0)
    aspect_deg[slope_deg < 0.01] = 0.0
    aspect_deg = aspect_deg.astype(np.float32)

    # Re-apply NoData mask: NoData pixels must NEVER be treated as valid or safe
    fill_nodata = config.DEFAULT_NODATA_VALUE
    slope_deg[~valid_mask] = fill_nodata
    aspect_deg[~valid_mask] = fill_nodata

    return slope_deg, aspect_deg, valid_mask


def calculate_roughness_std(
    dem: np.ndarray,
    window_size: int = config.TERRAIN_WINDOW_SIZE,
    nodata_val: Optional[float] = config.DEFAULT_NODATA_VALUE,
) -> np.ndarray:
    """
    Computes local surface roughness as the elevation standard deviation (meters)
    within a moving square window of size window_size x window_size.
    Preserves NoData pixels.
    """
    if nodata_val is not None and not np.isnan(nodata_val):
        valid_mask = (dem != nodata_val)
    elif nodata_val is not None and np.isnan(nodata_val):
        valid_mask = ~np.isnan(dem)
    else:
        valid_mask = np.ones(dem.shape, dtype=bool)

    z = np.where(valid_mask, dem, 0.0)
    w_sq = float(window_size * window_size)

    # Count of valid pixels in each window
    valid_float = valid_mask.astype(np.float32)
    count = ndi.uniform_filter(valid_float, size=window_size, mode="reflect") * w_sq

    # Sum of z and sum of z^2
    sum_z = ndi.uniform_filter(z.astype(np.float32), size=window_size, mode="reflect") * w_sq
    sum_z2 = ndi.uniform_filter((z**2).astype(np.float32), size=window_size, mode="reflect") * w_sq

    # Mean and variance
    # Require at least 3 valid pixels in window for variance
    enough_samples = count >= 3
    mean_z = np.zeros_like(dem, dtype=np.float32)
    mean_z[enough_samples] = sum_z[enough_samples] / count[enough_samples]

    variance = np.zeros_like(dem, dtype=np.float32)
    variance[enough_samples] = np.maximum(
        0.0,
        (sum_z2[enough_samples] / count[enough_samples]) - (mean_z[enough_samples] ** 2)
    )

    roughness = np.sqrt(variance).astype(np.float32)

    # Reapply NoData mask
    roughness[~valid_mask] = config.DEFAULT_NODATA_VALUE
    roughness[~enough_samples] = config.DEFAULT_NODATA_VALUE

    return roughness


def calculate_roughness_tri(
    dem: np.ndarray,
    nodata_val: Optional[float] = config.DEFAULT_NODATA_VALUE,
) -> np.ndarray:
    """
    Computes Terrain Ruggedness Index (TRI) following Riley et al. (1999):
    TRI = sqrt( mean( (z_neighbor - z_center)^2 ) ) across the 8-neighborhood.
    Preserves NoData pixels.
    """
    if nodata_val is not None and not np.isnan(nodata_val):
        valid_mask = (dem != nodata_val)
    elif nodata_val is not None and np.isnan(nodata_val):
        valid_mask = ~np.isnan(dem)
    else:
        valid_mask = np.ones(dem.shape, dtype=bool)

    ny, nx = dem.shape
    sum_sq_diff = np.zeros(dem.shape, dtype=np.float32)
    count_valid_neighbors = np.zeros(dem.shape, dtype=np.float32)

    # 8 neighbor offsets
    offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),          ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1),
    ]

    for dy, dx in offsets:
        # Construct shifted neighbor array with padding
        neighbor = np.full_like(dem, fill_value=np.nan)
        y_src_start = max(0, dy)
        y_src_end = min(ny, ny + dy)
        x_src_start = max(0, dx)
        x_src_end = min(nx, nx + dx)

        y_dst_start = max(0, -dy)
        y_dst_end = min(ny, ny - dy)
        x_dst_start = max(0, -dx)
        x_dst_end = min(nx, nx - dx)

        neighbor[y_dst_start:y_dst_end, x_dst_start:x_dst_end] = dem[y_src_start:y_src_end, x_src_start:x_src_end]

        if nodata_val is not None:
            n_valid = (neighbor != nodata_val) & ~np.isnan(neighbor) & valid_mask
        else:
            n_valid = ~np.isnan(neighbor) & valid_mask

        diff = np.where(n_valid, neighbor - dem, 0.0)
        sum_sq_diff += (diff ** 2).astype(np.float32)
        count_valid_neighbors += n_valid.astype(np.float32)

    has_neighbors = count_valid_neighbors > 0
    tri = np.full_like(dem, fill_value=config.DEFAULT_NODATA_VALUE, dtype=np.float32)
    tri[has_neighbors & valid_mask] = np.sqrt(
        sum_sq_diff[has_neighbors & valid_mask] / count_valid_neighbors[has_neighbors & valid_mask]
    )

    return tri


def generate_terrain_histograms(
    slope: np.ndarray,
    aspect: np.ndarray,
    rough_std: np.ndarray,
    rough_tri: np.ndarray,
    output_png: Path = config.OUTPUT_TERRAIN_HIST_PNG,
    nodata_val: float = config.DEFAULT_NODATA_VALUE,
    is_synthetic: bool = True,
) -> Path:
    """
    Renders publication-grade 4-panel distribution histograms for terrain metrics
    with statistical markers and hazard threshold reference lines.
    """
    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    # Filter out NoData
    v_slope = slope[slope != nodata_val]
    v_aspect = aspect[aspect != nodata_val]
    v_rstd = rough_std[rough_std != nodata_val]
    v_rtri = rough_tri[rough_tri != nodata_val]

    plt.style.use(config.FIGURE_STYLE)
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), dpi=config.PLOT_DPI)
    fig.patch.set_facecolor("#111625")

    title_suffix = f" ({config.SYNTHETIC_LABEL})" if is_synthetic else " (LRO LOLA Data)"
    fig.suptitle(
        f"LunaSafe Terrain Topographic Metrics Distribution{title_suffix}",
        fontsize=16,
        fontweight="bold",
        color="#e0e6ed",
        y=0.98,
    )

    # 1. Slope Histogram
    ax_s = axes[0, 0]
    ax_s.set_facecolor("#1a2234")
    ax_s.hist(v_slope, bins=40, color="#3498db", edgecolor="#111625", alpha=0.85, density=True)
    ax_s.axvline(config.SLOPE_SAFE_MAX, color="#2ecc71", linestyle="--", linewidth=1.8, label=f"Safe Threshold (<{config.SLOPE_SAFE_MAX}°)")
    ax_s.axvline(config.SLOPE_CAUTION_MAX, color="#f39c12", linestyle="--", linewidth=1.8, label=f"Caution Threshold (<{config.SLOPE_CAUTION_MAX}°)")
    ax_s.axvline(config.SLOPE_HARD_UNSAFE_MIN, color="#e74c3c", linestyle="--", linewidth=2.0, label=f"Hard Unsafe (≥{config.SLOPE_HARD_UNSAFE_MIN}°)")
    med_s = float(np.median(v_slope)) if len(v_slope) else 0.0
    p95_s = float(np.percentile(v_slope, 95)) if len(v_slope) else 0.0
    ax_s.set_title(f"Slope Distribution (Median: {med_s:.1f}°, 95th: {p95_s:.1f}°)", fontsize=12, color="#ffffff")
    ax_s.set_xlabel("Slope (degrees)", fontsize=10, color="#b0bec5")
    ax_s.set_ylabel("Probability Density", fontsize=10, color="#b0bec5")
    ax_s.legend(fontsize=8, loc="upper right")
    ax_s.grid(True, linestyle=":", alpha=0.3, color="#546e7a")

    # 2. Aspect Histogram
    ax_a = axes[0, 1]
    ax_a.set_facecolor("#1a2234")
    ax_a.hist(v_aspect, bins=36, range=(0, 360), color="#9b59b6", edgecolor="#111625", alpha=0.85, density=True)
    ax_a.set_title("Aspect Distribution (0° - 360° Compass Bearing)", fontsize=12, color="#ffffff")
    ax_a.set_xlabel("Aspect (degrees from North)", fontsize=10, color="#b0bec5")
    ax_a.set_ylabel("Probability Density", fontsize=10, color="#b0bec5")
    ax_a.set_xticks([0, 90, 180, 270, 360])
    ax_a.set_xticklabels(["0° (N)", "90° (E)", "180° (S)", "270° (W)", "360° (N)"])
    ax_a.grid(True, linestyle=":", alpha=0.3, color="#546e7a")

    # 3. Roughness (Std Dev) Histogram
    ax_rs = axes[1, 0]
    ax_rs.set_facecolor("#1a2234")
    ax_rs.hist(v_rstd, bins=40, color="#1abc9c", edgecolor="#111625", alpha=0.85, density=True)
    ax_rs.axvline(config.ROUGHNESS_SAFE_MAX, color="#2ecc71", linestyle="--", linewidth=1.8, label=f"Safe Threshold (<{config.ROUGHNESS_SAFE_MAX}m)")
    ax_rs.axvline(config.ROUGHNESS_CAUTION_MAX, color="#f39c12", linestyle="--", linewidth=1.8, label=f"Caution Threshold (<{config.ROUGHNESS_CAUTION_MAX}m)")
    ax_rs.axvline(config.ROUGHNESS_HARD_UNSAFE_MIN, color="#e74c3c", linestyle="--", linewidth=2.0, label=f"Hard Unsafe (≥{config.ROUGHNESS_HARD_UNSAFE_MIN}m)")
    med_r = float(np.median(v_rstd)) if len(v_rstd) else 0.0
    p95_r = float(np.percentile(v_rstd, 95)) if len(v_rstd) else 0.0
    ax_rs.set_title(f"Roughness - Elevation Std Dev (Median: {med_r:.2f}m, 95th: {p95_r:.2f}m)", fontsize=12, color="#ffffff")
    ax_rs.set_xlabel("Local Elevation Std Dev (meters)", fontsize=10, color="#b0bec5")
    ax_rs.set_ylabel("Probability Density", fontsize=10, color="#b0bec5")
    ax_rs.legend(fontsize=8, loc="upper right")
    ax_rs.grid(True, linestyle=":", alpha=0.3, color="#546e7a")

    # 4. Roughness (TRI) Histogram
    ax_tri = axes[1, 1]
    ax_tri.set_facecolor("#1a2234")
    ax_tri.hist(v_rtri, bins=40, color="#e67e22", edgecolor="#111625", alpha=0.85, density=True)
    med_tri = float(np.median(v_rtri)) if len(v_rtri) else 0.0
    p95_tri = float(np.percentile(v_rtri, 95)) if len(v_rtri) else 0.0
    ax_tri.set_title(f"Terrain Ruggedness Index - TRI (Median: {med_tri:.2f}m, 95th: {p95_tri:.2f}m)", fontsize=12, color="#ffffff")
    ax_tri.set_xlabel("Riley TRI Metric (meters)", fontsize=10, color="#b0bec5")
    ax_tri.set_ylabel("Probability Density", fontsize=10, color="#b0bec5")
    ax_tri.grid(True, linestyle=":", alpha=0.3, color="#546e7a")

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(output_png, dpi=config.PLOT_DPI, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    return output_png


def process_terrain_pipeline(
    dem: np.ndarray,
    dem_meta: Dict[str, Any],
    output_slope: Path = config.OUTPUT_SLOPE_TIF,
    output_aspect: Path = config.OUTPUT_ASPECT_TIF,
    output_rough_std: Path = config.OUTPUT_ROUGHNESS_STD_TIF,
    output_rough_tri: Path = config.OUTPUT_ROUGHNESS_TRI_TIF,
    output_hist: Path = config.OUTPUT_TERRAIN_HIST_PNG,
    is_synthetic: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Executes the full terrain analysis workflow:
    1. Slope and aspect calculations.
    2. Roughness via local standard deviation.
    3. Roughness via Terrain Ruggedness Index (TRI).
    4. GeoTIFF exports with lunar CRS and metadata tags.
    5. Distribution histogram figure export.
    """
    px_x = dem_meta["pixel_size_x"]
    px_y = dem_meta["pixel_size_y"]
    nodata_val = dem_meta["nodata"]

    slope, aspect, valid_mask = calculate_slope_and_aspect(
        dem=dem,
        pixel_size_x=px_x,
        pixel_size_y=px_y,
        nodata_val=nodata_val,
    )

    rough_std = calculate_roughness_std(
        dem=dem,
        window_size=config.TERRAIN_WINDOW_SIZE,
        nodata_val=nodata_val,
    )

    rough_tri = calculate_roughness_tri(
        dem=dem,
        nodata_val=nodata_val,
    )

    # Export GeoTIFFs preserving Lunar CRS
    meta_base = {
        "PROJECT": "OrbisLuna",
        "DATA_TYPE": config.SYNTHETIC_LABEL if is_synthetic else "LUNAR LRO LOLA",
        "BODY": "MOON",
    }

    if output_slope:
        io_utils.write_geotiff(
            output_path=output_slope,
            data=slope,
            transform=dem_meta["transform"],
            crs=dem_meta["crs"],
            nodata=config.DEFAULT_NODATA_VALUE,
            tags={**meta_base, "METRIC": "SLOPE", "UNITS": "DEGREES"},
        )

    if output_aspect:
        io_utils.write_geotiff(
            output_path=output_aspect,
            data=aspect,
            transform=dem_meta["transform"],
            crs=dem_meta["crs"],
            nodata=config.DEFAULT_NODATA_VALUE,
            tags={**meta_base, "METRIC": "ASPECT", "UNITS": "DEGREES_FROM_NORTH"},
        )

    if output_rough_std:
        io_utils.write_geotiff(
            output_path=output_rough_std,
            data=rough_std,
            transform=dem_meta["transform"],
            crs=dem_meta["crs"],
            nodata=config.DEFAULT_NODATA_VALUE,
            tags={**meta_base, "METRIC": "ROUGHNESS_STD", "WINDOW_SIZE": str(config.TERRAIN_WINDOW_SIZE), "UNITS": "METERS"},
        )

    if output_rough_tri:
        io_utils.write_geotiff(
            output_path=output_rough_tri,
            data=rough_tri,
            transform=dem_meta["transform"],
            crs=dem_meta["crs"],
            nodata=config.DEFAULT_NODATA_VALUE,
            tags={**meta_base, "METRIC": "ROUGHNESS_TRI", "UNITS": "METERS"},
        )

    if output_hist:
        generate_terrain_histograms(
            slope=slope,
            aspect=aspect,
            rough_std=rough_std,
            rough_tri=rough_tri,
            output_png=output_hist,
            nodata_val=config.DEFAULT_NODATA_VALUE,
            is_synthetic=is_synthetic,
        )

    v_slope = slope[valid_mask]
    v_rstd = rough_std[valid_mask]

    metrics = {
        "slope": slope,
        "aspect": aspect,
        "roughness_std": rough_std,
        "roughness_tri": rough_tri,
        "valid_mask": valid_mask,
        "slope_mean": float(np.mean(v_slope)),
        "slope_max": float(np.max(v_slope)),
        "slope_median": float(np.median(v_slope)),
        "rough_std_mean": float(np.mean(v_rstd)),
        "rough_std_max": float(np.max(v_rstd)),
        "rough_std_median": float(np.median(v_rstd)),
    }

    if verbose:
        print("=" * 65)
        print("TERRAIN ANALYSIS EXECUTION SUMMARY")
        print("=" * 65)
        print(f"Topography Analyzed: {'SYNTHETIC DEMO' if is_synthetic else 'REAL LRO LOLA'}")
        print(f"Pixel Resolution:    {px_x:.2f} m x {px_y:.2f} m")
        print(f"Roughness Window:    {config.TERRAIN_WINDOW_SIZE}x{config.TERRAIN_WINDOW_SIZE} pixels ({config.TERRAIN_WINDOW_SIZE*px_x:.1f} m footprint)")
        print(f"Slope (deg):         Mean: {metrics['slope_mean']:.2f}°, Median: {metrics['slope_median']:.2f}°, Max: {metrics['slope_max']:.2f}°")
        print(f"Roughness Std (m):   Mean: {metrics['rough_std_mean']:.2f} m, Median: {metrics['rough_std_median']:.2f} m, Max: {metrics['rough_std_max']:.2f} m")
        print(f"Slope GeoTIFF:       {output_slope}")
        print(f"Aspect GeoTIFF:      {output_aspect}")
        print(f"Roughness Std TIF:   {output_rough_std}")
        print(f"Roughness TRI TIF:   {output_rough_tri}")
        print(f"Histograms PNG:      {output_hist}")
        print("=" * 65 + "\n")

    return metrics
