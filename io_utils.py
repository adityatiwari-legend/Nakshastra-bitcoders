"""
LunaSafe IO & Preprocessing Module
Handles loading, metadata inspection, georeferencing, grid alignment,
and synthetic lunar data generation.
Adheres strictly to Lunar CRS preservation (no Earth EPSG assignment).
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np

import config

try:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import from_origin
    from rasterio.warp import reproject, Resampling
except ImportError:
    rasterio = None
    CRS = None
    from_origin = None
    reproject = None
    Resampling = None


def generate_synthetic_crater_topography(
    shape: Tuple[int, int] = config.SYNTHETIC_DEM_SHAPE,
    pixel_size: float = config.SYNTHETIC_PIXEL_SIZE_M,
    radius: float = config.SYNTHETIC_CRATER_RADIUS_M,
    depth: float = config.SYNTHETIC_CRATER_DEPTH_M,
    rim_height: float = config.SYNTHETIC_CRATER_RIM_HEIGHT_M,
    base_elevation: float = config.SYNTHETIC_REGIONAL_ELEVATION_M,
    nodata_val: float = config.DEFAULT_NODATA_VALUE,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generates a realistic synthetic lunar impact crater DEM and corresponding PSR mask.
    
    Topographic components:
    - Regional undulating lunar terrain
    - Raised circular crater rim
    - Steep inner crater walls (~10-25 deg)
    - Flat, sheltered crater floor (<5 deg slope, smooth)
    - Permanently shadowed region (PSR) on the southern/south-western floor
    - Edge NoData margin to test pipeline safety
    
    Returns:
        dem: 2D float32 elevation grid (meters)
        psr: 2D uint8 PSR mask (1 = shadowed, 0 = illuminated)
        valid_mask: 2D boolean mask (True for valid pixels, False for NoData)
    """
    ny, nx = shape
    # Coordinate system centered on crater (0, 0) in Lunar Polar Stereographic
    x = (np.arange(nx) - nx / 2.0) * pixel_size
    y = (np.arange(ny) - ny / 2.0) * pixel_size
    xx, yy = np.meshgrid(x, y)
    r = np.sqrt(xx**2 + yy**2)
    
    # Base terrain: gentle regional slope and undulating waves
    regional_terrain = (
        base_elevation
        + 15.0 * np.sin(xx / 500.0) * np.cos(yy / 600.0)
        + 0.005 * xx
    )

    dem = np.copy(regional_terrain)
    floor_radius = radius * 0.45
    
    # 1. Crater floor (r <= floor_radius): Flat, slightly concave
    floor_mask = r <= floor_radius
    dem[floor_mask] = (
        base_elevation - depth
        + 10.0 * (r[floor_mask] / floor_radius)**2
        + np.random.RandomState(42).normal(0.0, 0.4, np.sum(floor_mask))
    )
    
    # 2. Crater inner walls (floor_radius < r <= radius): Steep slope
    wall_mask = (r > floor_radius) & (r <= radius)
    wall_fraction = (r[wall_mask] - floor_radius) / (radius - floor_radius)
    wall_elev = (
        (base_elevation - depth + 10.0)
        + (depth + rim_height - 10.0) * (wall_fraction**1.5)
        + np.random.RandomState(43).normal(0.0, 2.2, np.sum(wall_mask))
    )
    dem[wall_mask] = wall_elev
    
    # 3. Outer rim and continuous ejecta blanket (radius < r <= radius * 2.2)
    ejecta_mask = (r > radius) & (r <= radius * 2.2)
    ejecta_fraction = (r[ejecta_mask] - radius) / (radius * 1.2)
    ejecta_decay = rim_height * np.exp(-3.0 * ejecta_fraction)
    dem[ejecta_mask] = regional_terrain[ejecta_mask] + ejecta_decay + np.random.RandomState(44).normal(0.0, 1.2, np.sum(ejecta_mask))
    
    # Micro-roughness across all valid lunar surface
    dem += np.random.RandomState(45).normal(0.0, 0.3, size=shape)
    
    # 4. Realistic synthetic PSR:
    # Crater floor shielded from low-elevation solar illumination
    psr = np.zeros(shape, dtype=np.uint8)
    psr_condition = (r <= floor_radius * 1.05) & (yy <= 50.0)
    psr[psr_condition] = 1

    # 5. Border collar of NoData pixels to test pipeline NoData safety
    valid_mask = np.ones(shape, dtype=bool)
    border_width = 4
    valid_mask[:border_width, :] = False
    valid_mask[-border_width:, :] = False
    valid_mask[:, :border_width] = False
    valid_mask[:, -border_width:] = False
    
    dem[~valid_mask] = nodata_val
    psr[~valid_mask] = 0

    return dem.astype(np.float32), psr.astype(np.uint8), valid_mask


def write_geotiff(
    output_path: Path,
    data: np.ndarray,
    transform: Any,
    crs: Any,
    nodata: Optional[float] = config.DEFAULT_NODATA_VALUE,
    tags: Optional[Dict[str, str]] = None,
) -> None:
    """
    Writes a 2D numpy array to a georeferenced GeoTIFF preserving Lunar CRS.
    """
    if rasterio is None:
        raise ImportError("rasterio is required to write GeoTIFF rasters.")
        
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    height, width = data.shape
    dtype = data.dtype
    
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": dtype,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "compress": "lzw",
    }
    
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data, 1)
        if tags:
            dst.update_tags(**tags)


def read_geotiff(file_path: Path) -> Dict[str, Any]:
    """
    Reads a GeoTIFF raster, extracts lunar georeference metadata, extent, and data array.
    """
    if rasterio is None:
        raise ImportError("rasterio is required to read GeoTIFF rasters.")
        
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Raster file not found: {file_path}")
        
    with rasterio.open(file_path) as src:
        data = src.read(1)
        crs = src.crs
        transform = src.transform
        nodata = src.nodata
        bounds = src.bounds
        res = src.res
        profile = src.profile.copy()
        tags = src.tags()
        
    return {
        "path": file_path,
        "data": data,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "bounds": bounds,
        "pixel_size_x": float(res[0]),
        "pixel_size_y": float(res[1]),
        "shape": data.shape,
        "dtype": str(data.dtype),
        "profile": profile,
        "tags": tags,
    }


def inspect_raster(file_path: Path, verbose: bool = True) -> Dict[str, Any]:
    """
    Inspects a raster and prints CRS, pixel size, extent, dtype, and NoData.
    Fails loudly if an Earth EPSG is assigned to lunar data.
    """
    info = read_geotiff(file_path)
    crs_str = str(info["crs"]) if info["crs"] is not None else "UNDEFINED"
    
    # Strictly enforce Lunar CRS rule: Never assign an Earth EPSG code to lunar data!
    earth_epsg_signatures = ["EPSG:4326", "EPSG:3857", "EPSG:4269", "WGS 84", "WGS_1984"]
    for earth_sig in earth_epsg_signatures:
        if earth_sig.lower() in crs_str.lower():
            raise ValueError(
                f"LUNAR CRS VIOLATION in {file_path.name}: Earth reference '{earth_sig}' detected! "
                "Lunar rasters must retain native Lunar CRS (e.g. Lunar South Pole Stereographic)."
            )

    data = info["data"]
    nodata = info["nodata"]
    
    if nodata is not None and not np.isnan(nodata):
        valid_mask = data != nodata
    elif nodata is not None and np.isnan(nodata):
        valid_mask = ~np.isnan(data)
    else:
        valid_mask = np.ones(data.shape, dtype=bool)
        
    valid_count = int(np.sum(valid_mask))
    total_count = data.size
    nodata_count = total_count - valid_count
    
    valid_min = float(np.min(data[valid_mask])) if valid_count > 0 else float("nan")
    valid_max = float(np.max(data[valid_mask])) if valid_count > 0 else float("nan")
    
    summary = {
        **info,
        "valid_count": valid_count,
        "nodata_count": nodata_count,
        "valid_min": valid_min,
        "valid_max": valid_max,
        "is_synthetic": "SYNTHETIC" in str(info.get("tags", {})).upper() or "synthetic" in str(file_path).lower(),
    }
    
    if verbose:
        b = info["bounds"]
        border = "=" * 70
        print(border)
        print(f"RASTER INSPECTION: {Path(file_path).name}")
        print(border)
        print(f"CRS:             {crs_str}")
        print(f"Pixel Size:      X = {info['pixel_size_x']:.2f} m, Y = {info['pixel_size_y']:.2f} m")
        print(f"Dimensions:      Height = {info['shape'][0]}, Width = {info['shape'][1]} (Total: {total_count:,} px)")
        print(f"Extent [Bounds]: Left: {b.left:,.2f}, Bottom: {b.bottom:,.2f}, Right: {b.right:,.2f}, Top: {b.top:,.2f}")
        print(f"Data Type:       {info['dtype']}")
        print(f"NoData Value:    {nodata}")
        print(f"Value Range:     Min = {valid_min:.2f}, Max = {valid_max:.2f}")
        print(f"Pixel Breakdown: Valid: {valid_count:,} ({valid_count/total_count*100:.1f}%) | NoData: {nodata_count:,} ({nodata_count/total_count*100:.1f}%)")
        if summary["is_synthetic"]:
            print(f"Banner:          *** {config.SYNTHETIC_LABEL} ***")
        if info["tags"]:
            print(f"Tags:            {info['tags']}")
        print(border + "\n")
        
    return summary


def check_grid_alignment(
    grid_a: Dict[str, Any],
    grid_b: Dict[str, Any],
    tol: float = 1e-4,
) -> Tuple[bool, str]:
    """
    Checks whether two rasters share the exact same grid geometry:
    CRS, dimensions (shape), affine transform (pixel size and origin).
    """
    # 1. Check dimensions
    if grid_a["shape"] != grid_b["shape"]:
        return False, f"Shape mismatch: {grid_a['shape']} vs {grid_b['shape']}"
        
    # 2. Check CRS
    crs_a = str(grid_a["crs"])
    crs_b = str(grid_b["crs"])
    if crs_a != crs_b:
        # Check if rasterio crs equals
        if grid_a["crs"] != grid_b["crs"]:
            return False, f"CRS mismatch: {crs_a} vs {crs_b}"
            
    # 3. Check transform
    t_a = list(grid_a["transform"])[:6]
    t_b = list(grid_b["transform"])[:6]
    for idx, (val_a, val_b) in enumerate(zip(t_a, t_b)):
        if abs(val_a - val_b) > tol:
            return False, f"Affine transform parameter {idx} mismatch: {val_a} vs {val_b}"
            
    return True, "Grids perfectly aligned."


def align_psr_to_dem(
    psr_path: Path,
    dem_meta: Dict[str, Any],
    output_path: Optional[Path] = None,
    fail_on_mismatch: bool = False,
    verbose: bool = True,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Aligns the PSR mask raster to the exact DEM grid.
    If fail_on_mismatch is True and grids differ, raises a loud ValueError.
    If fail_on_mismatch is False, resamples/reprojects PSR onto DEM grid using Nearest-Neighbor.
    """
    psr_meta = inspect_raster(psr_path, verbose=verbose)
    aligned, reason = check_grid_alignment(dem_meta, psr_meta)
    
    if aligned:
        if verbose:
            print(f"[OK] PSR grid already matches DEM grid: {reason}")
        return psr_meta["data"], psr_meta

    # Grids do not match!
    if fail_on_mismatch:
        raise ValueError(
            f"GRID MISMATCH ERROR: DEM ({dem_meta['path'].name}) and PSR ({psr_path.name}) grids do not match!\n"
            f"Reason: {reason}\n"
            f"DEM Shape: {dem_meta['shape']}, PSR Shape: {psr_meta['shape']}\n"
            f"DEM Transform: {dem_meta['transform']}\n"
            f"PSR Transform: {psr_meta['transform']}\n"
            f"DEM CRS: {dem_meta['crs']}\n"
            f"PSR CRS: {psr_meta['crs']}"
        )

    if verbose:
        print(f"[ALIGNING] Grid mismatch detected ({reason}). Reprojecting PSR mask to match DEM grid via nearest-neighbor...")

    # Validate spatial intersection
    dem_b = dem_meta["bounds"]
    psr_b = psr_meta["bounds"]
    no_overlap = (
        psr_b.right < dem_b.left or psr_b.left > dem_b.right or
        psr_b.top < dem_b.bottom or psr_b.bottom > dem_b.top
    )
    if no_overlap:
        raise ValueError(
            f"SPATIAL EXTENT ERROR: PSR raster extent {psr_b} does not overlap DEM extent {dem_b}!"
        )

    # Allocate destination array with DEM shape and uint8 dtype
    dem_shape = dem_meta["shape"]
    aligned_psr = np.zeros(dem_shape, dtype=np.uint8)
    
    with rasterio.open(psr_path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=aligned_psr,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dem_meta["transform"],
            dst_crs=dem_meta["crs"],
            resampling=Resampling.nearest,
        )

    # Create aligned profile
    aligned_meta = {
        "path": output_path or psr_path,
        "data": aligned_psr,
        "crs": dem_meta["crs"],
        "transform": dem_meta["transform"],
        "nodata": None,
        "bounds": dem_meta["bounds"],
        "pixel_size_x": dem_meta["pixel_size_x"],
        "pixel_size_y": dem_meta["pixel_size_y"],
        "shape": aligned_psr.shape,
        "dtype": str(aligned_psr.dtype),
        "tags": {**psr_meta.get("tags", {}), "ALIGNED_TO_DEM": str(dem_meta["path"].name)},
    }

    if output_path:
        write_geotiff(
            output_path=output_path,
            data=aligned_psr,
            transform=dem_meta["transform"],
            crs=dem_meta["crs"],
            nodata=None,
            tags=aligned_meta["tags"],
        )
        if verbose:
            print(f"[SAVED] Aligned PSR raster saved to: {output_path}")

    return aligned_psr, aligned_meta


def load_and_align_datasets(
    dem_path: Optional[Path] = None,
    psr_path: Optional[Path] = None,
    fail_on_mismatch: bool = False,
    verbose: bool = True,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any], Dict[str, Any]]:
    """
    Loads DEM and PSR rasters. If paths are not provided or files do not exist,
    automatically generates and loads synthetic data labeled SYNTHETIC DEMO.
    Fails loudly if fail_on_mismatch is True and grids do not match.
    """
    # Check if real paths exist, fallback to synthetic
    if dem_path is None or not Path(dem_path).exists():
        if verbose:
            print(f"[INFO] DEM not found at specified path. Utilizing synthetic dataset: {config.SYNTHETIC_DEM_PATH}")
        if not config.SYNTHETIC_DEM_PATH.exists() or not config.SYNTHETIC_PSR_PATH.exists():
            create_and_save_synthetic_dataset()
        dem_path = config.SYNTHETIC_DEM_PATH

    if psr_path is None or not Path(psr_path).exists():
        if verbose:
            print(f"[INFO] PSR mask not found at specified path. Utilizing synthetic dataset: {config.SYNTHETIC_PSR_PATH}")
        if not config.SYNTHETIC_PSR_PATH.exists():
            create_and_save_synthetic_dataset()
        psr_path = config.SYNTHETIC_PSR_PATH

    dem_meta = inspect_raster(dem_path, verbose=verbose)
    psr_data, psr_meta = align_psr_to_dem(
        psr_path=psr_path,
        dem_meta=dem_meta,
        fail_on_mismatch=fail_on_mismatch,
        verbose=verbose,
    )

    return dem_meta["data"], psr_data, dem_meta, psr_meta


def create_and_save_synthetic_dataset(
    dem_path: Path = config.SYNTHETIC_DEM_PATH,
    psr_path: Path = config.SYNTHETIC_PSR_PATH,
    shape: Tuple[int, int] = config.SYNTHETIC_DEM_SHAPE,
    pixel_size: float = config.SYNTHETIC_PIXEL_SIZE_M,
) -> Tuple[Path, Path]:
    """
    Generates synthetic DEM & PSR rasters with Moon South Pole Stereographic projection
    and saves them with SYNTHETIC DEMO metadata tags.
    """
    if rasterio is None:
        raise ImportError("rasterio is required for synthetic dataset generation.")
        
    dem_arr, psr_arr, _ = generate_synthetic_crater_topography(shape=shape, pixel_size=pixel_size)
    
    ny, nx = shape
    west = - (nx / 2.0) * pixel_size
    north = (ny / 2.0) * pixel_size
    
    transform = from_origin(west, north, pixel_size, pixel_size)
    lunar_crs = CRS.from_string(config.LUNAR_SOUTH_POLE_PROJ4)
    
    meta_tags = {
        "PROJECT": "LunaSafe",
        "DATA_TYPE": config.SYNTHETIC_LABEL,
        "BODY": "MOON",
        "DESCRIPTION": "Synthetic Lunar Crater and PSR for Pipeline Validation",
    }
    
    write_geotiff(
        output_path=dem_path,
        data=dem_arr,
        transform=transform,
        crs=lunar_crs,
        nodata=config.DEFAULT_NODATA_VALUE,
        tags=meta_tags,
    )
    
    write_geotiff(
        output_path=psr_path,
        data=psr_arr,
        transform=transform,
        crs=lunar_crs,
        nodata=None,
        tags=meta_tags,
    )
    
    return dem_path, psr_path
