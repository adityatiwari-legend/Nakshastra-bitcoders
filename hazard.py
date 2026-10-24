"""
LunaSafe Hazard Classification Module
Implements multi-criteria lunar landing hazard evaluation:
- Normalized criteria: S = min(slope/15, 1), R = min(rough/5, 1), D = shadow fraction (0 for binary mask)
- Multi-criteria score: H = 0.50*S + 0.30*R + 0.20*D
- Hard overrides: slope >= 15 deg or roughness >= 5 m
- Class 1 (Safe): H < 0.25 and slope < 5 deg and roughness < 1.5 m
- Class 2 (Caution): 0.25 <= H < 0.60
- Class 3 (Unsafe): H >= 0.60 or any hard override
- Class 4 (Shadowed-Unknown): PSR pixels that are not already Unsafe
- Class 0 (NoData): invalid / missing pixels. Never treated as Safe!
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd

import config
import io_utils


def compute_hazard_score(
    slope: np.ndarray,
    roughness: np.ndarray,
    shadow_fraction: Optional[np.ndarray] = None,
    valid_mask: Optional[np.ndarray] = None,
    pixel_size_m: Optional[float] = None,
) -> np.ndarray:
    """
    Computes continuous multi-criteria hazard score H:
    H = 0.50*S + 0.30*R + 0.20*D
    where:
      S = min(slope / 15.0, 1.0)
      R = min(roughness / (5.0 * resolution_scale), 1.0)
      D = shadow fraction (0.0 if only a binary PSR mask)

    pixel_size_m: DEM pixel size in meters. When provided, roughness
    normalization is resolution-scaled (see config.scaled_roughness_thresholds).
    """
    if valid_mask is None:
        valid_mask = (slope != config.DEFAULT_NODATA_VALUE) & (roughness != config.DEFAULT_NODATA_VALUE)

    r_norm_max = config.ROUGHNESS_NORM_MAX
    if pixel_size_m is not None:
        r_norm_max = config.scaled_roughness_thresholds(pixel_size_m)["norm_max"]

    # Safe normalization clipping
    s_norm = np.clip(slope / config.SLOPE_NORM_MAX, 0.0, 1.0)
    r_norm = np.clip(roughness / r_norm_max, 0.0, 1.0)

    if shadow_fraction is not None:
        d_norm = np.clip(shadow_fraction.astype(np.float32), 0.0, 1.0)
    else:
        # Default per rule: D = 0 if only a binary PSR mask
        d_norm = np.zeros_like(slope, dtype=np.float32)

    score_h = (
        config.WEIGHT_SLOPE * s_norm
        + config.WEIGHT_ROUGHNESS * r_norm
        + config.WEIGHT_SHADOW * d_norm
    )

    # Set NoData locations to NaN
    score_h[~valid_mask] = np.nan
    return score_h


def classify_hazard_surface(
    slope: np.ndarray,
    roughness: np.ndarray,
    psr_mask: np.ndarray,
    shadow_fraction: Optional[np.ndarray] = None,
    valid_mask: Optional[np.ndarray] = None,
    pixel_size_m: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Applies the deterministic hazard classification rules with hard overrides:
    - Class 0 (NoData): Invalid/missing pixels
    - Class 3 (Unsafe): H >= 0.60 OR slope >= 15° OR roughness >= hard_unsafe_min (resolution-scaled)
    - Class 4 (Shadowed-Unknown): PSR pixels (psr_mask == 1) not already Unsafe
    - Class 1 (Safe): Non-PSR, H < 0.25 AND slope < 5° AND roughness < safe_max (resolution-scaled)
    - Class 2 (Caution): Non-PSR, 0.25 <= H < 0.60

    pixel_size_m: DEM pixel size in meters. When provided, roughness thresholds
    are scaled via config.scaled_roughness_thresholds (linear baseline model).
    At the 20 m synthetic reference this matches the base config values exactly.
    """
    if valid_mask is None:
        valid_mask = (
            (slope != config.DEFAULT_NODATA_VALUE)
            & ~np.isnan(slope)
            & (roughness != config.DEFAULT_NODATA_VALUE)
            & ~np.isnan(roughness)
        )

    if pixel_size_m is not None:
        rt = config.scaled_roughness_thresholds(pixel_size_m)
        rough_safe_max = rt["safe_max"]
        rough_hard_unsafe = rt["hard_unsafe_min"]
    else:
        rough_safe_max = config.ROUGHNESS_SAFE_MAX
        rough_hard_unsafe = config.ROUGHNESS_HARD_UNSAFE_MIN

    # Initialize all as NoData (Class 0)
    hazard_classes = np.full(slope.shape, fill_value=config.CLASS_NODATA, dtype=np.uint8)

    # Compute continuous hazard score H
    score_h = compute_hazard_score(
        slope=slope,
        roughness=roughness,
        shadow_fraction=shadow_fraction,
        valid_mask=valid_mask,
        pixel_size_m=pixel_size_m,
    )

    # Hard overrides
    hard_slope_unsafe = slope >= config.SLOPE_HARD_UNSAFE_MIN
    hard_rough_unsafe = roughness >= rough_hard_unsafe
    hard_override = hard_slope_unsafe | hard_rough_unsafe

    # Unsafe condition (Class 3)
    is_unsafe = valid_mask & ((score_h >= config.SCORE_UNSAFE_MIN) | hard_override)
    hazard_classes[is_unsafe] = config.CLASS_UNSAFE

    # PSR pixels (psr_mask == 1)
    is_psr = (psr_mask == 1) & valid_mask

    # Class 4 (Shadowed-Unknown): PSR pixels that are not already Unsafe
    is_shadowed_unknown = is_psr & ~is_unsafe
    hazard_classes[is_shadowed_unknown] = config.CLASS_SHADOWED_UNKNOWN

    # For remaining illuminated / non-PSR valid pixels:
    non_psr_valid = valid_mask & ~is_psr & ~is_unsafe

    # Class 1 (Safe): H < 0.25 AND slope < 5 deg AND roughness < scaled safe_max
    is_safe = (
        non_psr_valid
        & (score_h < config.SCORE_SAFE_MAX)
        & (slope < config.SLOPE_SAFE_MAX)
        & (roughness < rough_safe_max)
    )
    hazard_classes[is_safe] = config.CLASS_SAFE

    # Class 2 (Caution): All remaining non-PSR valid pixels (0.25 <= H < 0.60 or intermediate)
    is_caution = non_psr_valid & ~is_safe
    hazard_classes[is_caution] = config.CLASS_CAUTION

    # Ensure NoData pixels are strictly Class 0
    hazard_classes[~valid_mask] = config.CLASS_NODATA

    return hazard_classes, score_h


def generate_hazard_summary_table(
    hazard_classes: np.ndarray,
    pixel_size_x: float,
    pixel_size_y: float,
) -> pd.DataFrame:
    """
    Builds a structured statistics table detailing pixel counts, area in km2,
    and area percentages for each hazard class.
    """
    pixel_area_m2 = abs(float(pixel_size_x) * float(pixel_size_y))
    total_pixels = hazard_classes.size
    valid_pixels = np.sum(hazard_classes != config.CLASS_NODATA)

    rows = []
    all_class_ids = [
        config.CLASS_SAFE,
        config.CLASS_CAUTION,
        config.CLASS_UNSAFE,
        config.CLASS_SHADOWED_UNKNOWN,
        config.CLASS_NODATA,
    ]

    for cid in all_class_ids:
        cname = config.CLASS_NAMES.get(cid, f"Class {cid}")
        count = int(np.sum(hazard_classes == cid))
        area_m2 = count * pixel_area_m2
        area_km2 = area_m2 / 1.0e6
        pct_total = (count / total_pixels) * 100.0 if total_pixels > 0 else 0.0
        
        if cid == config.CLASS_NODATA:
            pct_valid = 0.0
        else:
            pct_valid = (count / valid_pixels) * 100.0 if valid_pixels > 0 else 0.0

        rows.append({
            "class_id": cid,
            "class_name": cname,
            "pixel_count": count,
            "area_m2": round(area_m2, 2),
            "area_km2": round(area_km2, 4),
            "pct_valid_terrain": round(pct_valid, 2),
            "pct_total_raster": round(pct_total, 2),
        })

    df = pd.DataFrame(rows)
    return df


def process_hazard_pipeline(
    slope: np.ndarray,
    roughness: np.ndarray,
    psr_mask: np.ndarray,
    dem_meta: Dict[str, Any],
    shadow_fraction: Optional[np.ndarray] = None,
    output_tif: Path = config.OUTPUT_HAZARD_CLASSES_TIF,
    output_csv: Path = config.OUTPUT_HAZARD_SUMMARY_CSV,
    is_synthetic: bool = True,
    verbose: bool = True,
) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """
    Executes the complete hazard classification workflow:
    1. Evaluates multi-criteria matrix and hard overrides.
    2. Classifies surface into Safe, Caution, Unsafe, Shadowed-Unknown, NoData.
    3. Exports GeoTIFF preserving Lunar CRS.
    4. Generates and exports comprehensive CSV summary table.
    5. Formats and prints verification walkthrough.
    """
    px_x = dem_meta["pixel_size_x"]
    px_y = dem_meta["pixel_size_y"]
    pixel_size_m = float(abs(px_x))

    hazard_classes, score_h = classify_hazard_surface(
        slope=slope,
        roughness=roughness,
        psr_mask=psr_mask,
        shadow_fraction=shadow_fraction,
        pixel_size_m=pixel_size_m,
    )

    # Export GeoTIFF
    if output_tif:
        tags = {
            "PROJECT": "LunaSafe",
            "DATA_TYPE": config.SYNTHETIC_LABEL if is_synthetic else "LUNAR LRO LOLA",
            "BODY": "MOON",
            "PRODUCT": "HAZARD_CLASSIFICATION",
            "CLASSES": "0=NoData,1=Safe,2=Caution,3=Unsafe,4=Shadowed-Unknown",
        }
        io_utils.write_geotiff(
            output_path=output_tif,
            data=hazard_classes,
            transform=dem_meta["transform"],
            crs=dem_meta["crs"],
            nodata=config.CLASS_NODATA,
            tags=tags,
        )

    # Generate Summary Table
    df_summary = generate_hazard_summary_table(
        hazard_classes=hazard_classes,
        pixel_size_x=px_x,
        pixel_size_y=px_y,
    )

    if output_csv:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df_summary.to_csv(output_csv, index=False)

    if verbose:
        print("=" * 80)
        print("LUNAR SURFACE HAZARD CLASSIFICATION SUMMARY")
        print("=" * 80)
        print(f"Topography Analyzed: {'SYNTHETIC DEMO' if is_synthetic else 'REAL LRO LOLA'}")
        print(f"Raster Footprint:    {hazard_classes.shape[1]*px_x/1000:.2f} km x {hazard_classes.shape[0]*px_y/1000:.2f} km ({hazard_classes.size:,} pixels)")
        print("-" * 80)
        header = f"{'Class ID':<9} | {'Class Name':<18} | {'Pixels':<9} | {'Area (km2)':<11} | {'% Valid':<9} | {'% Total':<9}"
        print(header)
        print("-" * 80)
        for _, r in df_summary.iterrows():
            cid_str = f"Class {int(r['class_id'])}"
            print(f"{cid_str:<9} | {r['class_name']:<18} | {int(r['pixel_count']):<9,d} | {r['area_km2']:<11.4f} | {r['pct_valid_terrain']:<8.2f}% | {r['pct_total_raster']:<8.2f}%")
        print("=" * 80)
        if output_tif:
            print(f"Hazard GeoTIFF:      {output_tif}")
        if output_csv:
            print(f"Summary CSV:         {output_csv}")
        print("=" * 80 + "\n")

    return hazard_classes, score_h, df_summary
