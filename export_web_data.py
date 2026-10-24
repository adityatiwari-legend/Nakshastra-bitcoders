"""
Export LunaSafe raster arrays into compact JSON for the interactive Web UI.
Includes real elevation, slope, roughness, PSR, and AI landing sites + boulder hazards.
"""

import json
import math

import config
import io_utils


def _finite_round(value, digits):
    """JSON-safe rounding: non-finite raster values become null (never NaN literals)."""
    f = float(value)
    return round(f, digits) if math.isfinite(f) else None

def _dem_provenance(dem_path, dem_info):
    """Derives honest real-vs-model provenance from raster tags (never filename alone)."""
    tags = dem_info.get("tags") or {}
    site_id = tags.get("SITE")
    if site_id:
        return site_id == "lola_crop"
    if "REAL NASA" in str(tags.get("DATA_TYPE", "")):
        return True
    return bool(dem_path) and "lola" in str(dem_path).lower()


def export_data_bundle(dem_path=None, psr_path=None, psr_reference_path=None):
    from pathlib import Path
    print("Exporting real raster datasets and screening outputs for Web Dashboard...")

    slope_info = io_utils.read_geotiff(config.OUTPUT_SLOPE_TIF)
    rough_info = io_utils.read_geotiff(config.OUTPUT_ROUGHNESS_STD_TIF)
    target_psr_path = Path(psr_path) if psr_path else config.OUTPUT_PSR_BINARY_TIF
    if not target_psr_path.exists():
        target_psr_path = config.SYNTHETIC_PSR_PATH
    psr_info = io_utils.read_geotiff(target_psr_path)

    slope = slope_info["data"]
    rough = rough_info["data"]
    psr = psr_info["data"]
    ny, nx = slope.shape

    # Choose DEM matching the active pipeline outputs dimensions.
    # The explicitly-passed dem_path (from main.py or site switch) has priority;
    # otherwise a grid-matched DEM is selected with tag-based provenance.
    is_real = False
    active_site_dem = config.OUTPUT_DIR / "active_site_dem.tif"
    if dem_path and Path(dem_path).exists():
        dem_info = io_utils.read_geotiff(Path(dem_path))
        is_real = _dem_provenance(dem_path, dem_info)
    elif active_site_dem.exists() and io_utils.read_geotiff(active_site_dem)["data"].shape == (ny, nx):
        dem_info = io_utils.read_geotiff(active_site_dem)
        is_real = _dem_provenance(active_site_dem, dem_info)
    elif config.REAL_DEM_PATH.exists() and io_utils.read_geotiff(config.REAL_DEM_PATH)["data"].shape == (ny, nx):
        dem_info = io_utils.read_geotiff(config.REAL_DEM_PATH)
        is_real = True
    else:
        dem_info = io_utils.read_geotiff(config.SYNTHETIC_DEM_PATH)
        is_real = False

    dem = dem_info["data"]
    
    ny, nx = dem.shape
    b = dem_info["bounds"]

    # Load AI Landing Sites if available
    landing_sites_data = {}
    if config.OUTPUT_LANDING_SITES_JSON.exists():
        with open(config.OUTPUT_LANDING_SITES_JSON, "r", encoding="utf-8") as f:
            landing_sites_data = json.load(f)

    # Load Hazard Classes raster if available
    hazard_classes_flat = []
    if config.OUTPUT_HAZARD_CLASSES_TIF.exists():
        hazard_info = io_utils.read_geotiff(config.OUTPUT_HAZARD_CLASSES_TIF)
        hazard_classes_flat = [int(v) for v in hazard_info["data"].flatten()]

    # Load Reference PSR raster if available.
    # Priority: explicit reference (raw pipeline input) > site's own input mask >
    # dataset-appropriate default. A reference is only included when its grid
    # matches the active bundle (never compare mismatched datasets).
    if psr_reference_path and Path(psr_reference_path).exists():
        psr_ref_path = Path(psr_reference_path)
    elif psr_path and Path(psr_path).exists():
        psr_ref_path = Path(psr_path)
    elif is_real:
        psr_ref_path = config.REAL_PSR_PATH
    else:
        psr_ref_path = config.SYNTHETIC_PSR_PATH
    psr_ref_flat = []
    if psr_ref_path.exists():
        psr_ref_info = io_utils.read_geotiff(psr_ref_path)
        # Guard: only include a reference whose grid matches the active bundle
        if psr_ref_info["data"].shape == (ny, nx):
            psr_ref_flat = [int(v) for v in psr_ref_info["data"].flatten()]

    # Load PSR Polygons GeoJSON if available
    psr_polygons_geojson = None
    if config.OUTPUT_PSR_POLYGONS_GEOJSON.exists():
        with open(config.OUTPUT_PSR_POLYGONS_GEOJSON, "r", encoding="utf-8") as f:
            psr_polygons_geojson = json.load(f)

    # Load Boulder Micro-Hazards if available
    boulder_hazard_flat = []
    if config.OUTPUT_BOULDER_HAZARD_TIF.exists():
        boulder_info = io_utils.read_geotiff(config.OUTPUT_BOULDER_HAZARD_TIF)
        boulder_hazard_flat = [_finite_round(v, 2) for v in boulder_info["data"].flatten()]

    # Load illumination fraction (visibility fraction) if available and grid-matched
    illumination_flat = []
    if config.REAL_ILLUMINATION_PATH.exists():
        try:
            ill_info = io_utils.read_geotiff(config.REAL_ILLUMINATION_PATH)
            if ill_info["data"].shape == (ny, nx):
                illumination_flat = [_finite_round(v, 4) for v in ill_info["data"].flatten()]
        except Exception:
            illumination_flat = []

    # Load Rover Traverse if available
    rover_traverse_data = {}
    if config.OUTPUT_ROVER_ROUTE_JSON.exists():
        try:
            with open(config.OUTPUT_ROVER_ROUTE_JSON, "r", encoding="utf-8") as f:
                rover_traverse_data = json.load(f)
        except Exception:
            pass

    # Resolution-aware roughness thresholds (must match hazard.classify_hazard_surface scaling)
    pixel_size_m = float(abs(dem_info["pixel_size_x"]))
    rt = config.scaled_roughness_thresholds(pixel_size_m)

    bundle = {
        "width": nx,
        "height": ny,
        "pixel_size_x": dem_info["pixel_size_x"],
        "pixel_size_y": dem_info["pixel_size_y"],
        "bounds": {
            "left": b.left,
            "right": b.right,
            "bottom": b.bottom,
            "top": b.top,
        },
        "nodata": config.DEFAULT_NODATA_VALUE,
        "dem": [round(float(v), 2) for v in dem.flatten()],
        "slope": [round(float(v), 2) for v in slope.flatten()],
        "roughness": [round(float(v), 2) for v in rough.flatten()],
        "psr": [int(v) for v in psr.flatten()],
        "psr_reference": psr_ref_flat,
        "psr_polygons": psr_polygons_geojson,
        "hazard_classes": hazard_classes_flat,
        "boulder_hazard": boulder_hazard_flat,
        "illumination": illumination_flat,
        "landing_sites": landing_sites_data.get("top_sites", []),
        "boulder_points": landing_sites_data.get("boulder_points_sample", []),
        "rover_traverse": rover_traverse_data,
        "defaults": {
            "slope_safe_max": config.SLOPE_SAFE_MAX,
            "slope_caution_max": config.SLOPE_CAUTION_MAX,
            "slope_hard_unsafe": config.SLOPE_HARD_UNSAFE_MIN,
            "rough_safe_max": rt["safe_max"],
            "rough_caution_max": rt["caution_max"],
            "rough_hard_unsafe": rt["hard_unsafe_min"],
            "rough_norm_max": rt["norm_max"],
            "rough_scale_factor": rt["scale_factor"],
            "pixel_size_m": pixel_size_m,
            "weight_slope": config.WEIGHT_SLOPE,
            "weight_roughness": config.WEIGHT_ROUGHNESS,
            "weight_shadow": config.WEIGHT_SHADOW,
            "landing_ellipse_radius_m": config.LANDING_ELLIPSE_RADIUS_M,
            "clearance_buffer_m": config.LANDING_CLEARANCE_BUFFER_M,
            "rover_max_slope_deg": config.ROVER_MAX_SLOPE_DEG,
            "rover_speed_mps": config.ROVER_SPEED_MPS,
        }
    }
    
    out_file = config.OUTPUT_DIR / "web_data.json"
    with open(out_file, "w") as f:
        json.dump(bundle, f)
        
    print(f"Exported web data bundle: {out_file} ({out_file.stat().st_size / 1024:.1f} KB)")
    return bundle


def export_tile_pyramid(output_dir=None, layers=("hazard",)):
    """Pre-generates multi-scale 256x256 float32 tile pyramids on disk."""
    import math
    from pathlib import Path
    import numpy as np
    import tile_pyramid

    target_dir = Path(output_dir) if output_dir else (config.OUTPUT_DIR / "web" / "tiles")

    layer_sources = {}
    if config.OUTPUT_HAZARD_CLASSES_TIF.exists():
        layer_sources["hazard"] = io_utils.read_geotiff(config.OUTPUT_HAZARD_CLASSES_TIF)["data"]
    if config.OUTPUT_SLOPE_TIF.exists():
        layer_sources["slope"] = io_utils.read_geotiff(config.OUTPUT_SLOPE_TIF)["data"]

    for layer_name in layers:
        base_arr = layer_sources.get(layer_name)
        if base_arr is None:
            continue
        norm_layer = layer_name.lower().strip()
        layer_dir = target_dir / norm_layer
        layer_dir.mkdir(parents=True, exist_ok=True)

        max_z, levels = tile_pyramid.build_pyramid(base_arr, norm_layer, tile_pyramid.TILE_SIZE)
        level_0 = levels[0]
        tiles_x0 = max(1, math.ceil(level_0.shape[1] / float(tile_pyramid.TILE_SIZE)))
        tiles_y0 = max(1, math.ceil(level_0.shape[0] / float(tile_pyramid.TILE_SIZE)))

        meta = {
            "status": "SUCCESS",
            "layer": norm_layer,
            "tileSize": tile_pyramid.TILE_SIZE,
            "maxZ": max_z,
            "width": base_arr.shape[1],
            "height": base_arr.shape[0],
            "dtype": "float32",
            "tiles_x": tiles_x0,
            "tiles_y": tiles_y0,
        }
        with open(layer_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        is_cont = norm_layer not in tile_pyramid.CATEGORICAL_LAYERS
        for z, arr_z in levels.items():
            tx = max(1, math.ceil(arr_z.shape[1] / float(tile_pyramid.TILE_SIZE)))
            ty = max(1, math.ceil(arr_z.shape[0] / float(tile_pyramid.TILE_SIZE)))
            for x in range(tx):
                for y in range(ty):
                    tile = tile_pyramid.slice_tile(arr_z, x, y, is_continuous=is_cont, tile_size=tile_pyramid.TILE_SIZE)
                    if tile is not None:
                        tile_path = layer_dir / f"{z}_{x}_{y}.f32"
                        with open(tile_path, "wb") as f:
                            f.write(tile.astype(np.float32).tobytes())

    return target_dir


if __name__ == "__main__":
    export_data_bundle()

