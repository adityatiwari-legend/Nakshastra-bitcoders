"""
LunaSafe PSR (Permanently Shadowed Region) Module
Handles binarization, morphological filtering of small components,
vectorization to GeoJSON/Shapefile, area calculations, and provenance tagging.
Adheres strictly to rules:
- Never label a published PSR mask as 'independently predicted'.
- Never treat NoData as valid PSR.
- Retain native Lunar CRS.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import scipy.ndimage as ndi

import config
import io_utils

try:
    import rasterio
    import rasterio.features
    import geopandas as gpd
    import shapely.geometry as sg
except ImportError:
    rasterio = None
    gpd = None
    sg = None


def binarize_psr(
    raw_psr: np.ndarray,
    threshold: float = config.PSR_BINARIZE_THRESHOLD,
    nodata_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Binarizes raw PSR data into a strict uint8 array (0 or 1).
    Handles boolean, 0/255 uint8, or continuous illumination fractions.
    Guarantees NoData pixels are never marked as valid PSR.
    """
    if raw_psr is None:
        raise ValueError("raw_psr array cannot be None")

    # If already boolean
    if raw_psr.dtype == bool:
        binary = raw_psr.astype(np.uint8)
    elif np.issubdtype(raw_psr.dtype, np.floating):
        # Continuous illumination or shadow fraction
        # If float represents shadow fraction (1.0 = full shadow)
        binary = (raw_psr >= threshold).astype(np.uint8)
    else:
        # Integer values (e.g. 0 and 1, or 0 and 255)
        binary = (raw_psr > 0).astype(np.uint8)

    # Strictly mask out NoData pixels
    if nodata_mask is not None:
        binary[nodata_mask] = 0

    return binary


def clean_psr_mask(
    binary_psr: np.ndarray,
    min_size_pixels: int = config.PSR_MIN_SIZE_PIXELS,
) -> np.ndarray:
    """
    Removes small isolated speckles/components with fewer than min_size_pixels
    using connected component labeling (8-connectivity).
    """
    if min_size_pixels <= 1:
        return binary_psr.copy()

    # 8-connectivity structure
    structure = np.ones((3, 3), dtype=int)
    labeled, num_features = ndi.label(binary_psr, structure=structure)
    
    if num_features == 0:
        return np.zeros_like(binary_psr, dtype=np.uint8)

    # Compute size of each connected component
    component_sizes = np.bincount(labeled.ravel())
    
    # Identify components meeting the size threshold (excluding background 0)
    too_small_mask = component_sizes < min_size_pixels
    too_small_mask[0] = False  # Keep background intact
    
    # Zero out pixels belonging to small components
    cleaned = binary_psr.copy()
    remove_pixels = too_small_mask[labeled]
    cleaned[remove_pixels] = 0

    return cleaned.astype(np.uint8)


def calculate_psr_area(
    binary_psr: np.ndarray,
    pixel_size_x: float,
    pixel_size_y: float,
) -> Dict[str, Any]:
    """
    Computes total PSR pixel count, area in square meters, and area in square kilometers.
    """
    pixel_count = int(np.sum(binary_psr == 1))
    pixel_area_m2 = abs(float(pixel_size_x) * float(pixel_size_y))
    area_m2 = pixel_count * pixel_area_m2
    area_km2 = area_m2 / 1.0e6

    return {
        "pixel_count": pixel_count,
        "pixel_area_m2": pixel_area_m2,
        "area_m2": area_m2,
        "area_km2": area_km2,
    }


def vectorize_psr_to_polygons(
    binary_psr: np.ndarray,
    transform: Any,
    crs: Any,
    min_size_pixels: int = config.PSR_MIN_SIZE_PIXELS,
    provenance: str = config.PSR_PROVENANCE_SYNTHETIC,
) -> Any:
    """
    Converts binary PSR raster connected components into vector polygons.
    Returns a GeoDataFrame with geometries, areas, perimeters, and provenance tags.
    """
    if rasterio is None or gpd is None or sg is None:
        raise ImportError("rasterio, geopandas, and shapely are required for vectorization.")

    shapes_gen = rasterio.features.shapes(
        binary_psr.astype(np.int16),
        mask=(binary_psr == 1),
        transform=transform,
        connectivity=8,
    )

    records = []
    poly_idx = 1
    for geom_dict, val in shapes_gen:
        if val != 1:
            continue
        poly_geom = sg.shape(geom_dict)
        if not poly_geom.is_valid:
            poly_geom = poly_geom.buffer(0)
        if poly_geom.is_empty:
            continue

        poly_area_m2 = poly_geom.area
        poly_area_km2 = poly_area_m2 / 1.0e6
        poly_perim_m = poly_geom.length

        records.append({
            "poly_id": poly_idx,
            "feature": "PSR",
            "area_m2": round(poly_area_m2, 2),
            "area_km2": round(poly_area_km2, 6),
            "perim_m": round(poly_perim_m, 2),
            "provenance": provenance,
            "geometry": poly_geom,
        })
        poly_idx += 1

    if records:
        gdf = gpd.GeoDataFrame(records, crs=crs)
    else:
        # Empty GeoDataFrame with explicit schema
        gdf = gpd.GeoDataFrame(
            columns=["poly_id", "feature", "area_m2", "area_km2", "perim_m", "provenance", "geometry"],
            crs=crs,
        )

    return gdf


def process_and_export_psr(
    raw_psr: np.ndarray,
    dem_meta: Dict[str, Any],
    output_tif: Optional[Path] = config.OUTPUT_PSR_BINARY_TIF,
    output_geojson: Optional[Path] = config.OUTPUT_PSR_POLYGONS_GEOJSON,
    output_shp: Optional[Path] = config.OUTPUT_PSR_POLYGONS_SHP,
    is_synthetic: bool = True,
    verbose: bool = True,
) -> Tuple[np.ndarray, Dict[str, Any], Any]:
    """
    Full PSR processing pipeline:
    1. Binarizes raw mask with NoData exclusion.
    2. Removes small components / isolated speckles.
    3. Calculates total PSR area in km2.
    4. Exports GeoTIFF preserving Lunar CRS.
    5. Exports vector GeoJSON and Shapefile.
    6. Displays execution summary with area in km2.
    """
    # Identify NoData mask from DEM
    dem_data = dem_meta["data"]
    nodata_val = dem_meta["nodata"]
    if nodata_val is not None and not np.isnan(nodata_val):
        nodata_mask = (dem_data == nodata_val)
    elif nodata_val is not None and np.isnan(nodata_val):
        nodata_mask = np.isnan(dem_data)
    else:
        nodata_mask = np.zeros(dem_data.shape, dtype=bool)

    # 1. Binarize
    binary_psr = binarize_psr(raw_psr, nodata_mask=nodata_mask)

    # 2. Clean small components
    cleaned_psr = clean_psr_mask(binary_psr, min_size_pixels=config.PSR_MIN_SIZE_PIXELS)

    # 3. Compute area metrics
    area_metrics = calculate_psr_area(
        cleaned_psr,
        pixel_size_x=dem_meta["pixel_size_x"],
        pixel_size_y=dem_meta["pixel_size_y"],
    )

    provenance_tag = config.PSR_PROVENANCE_SYNTHETIC if is_synthetic else config.PSR_PROVENANCE_PUBLISHED

    # 4. Export GeoTIFF
    if output_tif:
        tags = {
            "PROJECT": "OrbisLuna",
            "DATA_TYPE": config.SYNTHETIC_LABEL if is_synthetic else "LUNAR LRO LOLA",
            "PSR_PROVENANCE": provenance_tag,
            "PSR_AREA_KM2": f"{area_metrics['area_km2']:.4f}",
            "PSR_PIXELS": str(area_metrics["pixel_count"]),
        }
        io_utils.write_geotiff(
            output_path=output_tif,
            data=cleaned_psr,
            transform=dem_meta["transform"],
            crs=dem_meta["crs"],
            nodata=None,
            tags=tags,
        )

    # 5. Vectorize & export vector formats
    gdf = vectorize_psr_to_polygons(
        binary_psr=cleaned_psr,
        transform=dem_meta["transform"],
        crs=dem_meta["crs"],
        min_size_pixels=config.PSR_MIN_SIZE_PIXELS,
        provenance=provenance_tag,
    )

    if output_geojson:
        output_geojson.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(output_geojson, driver="GeoJSON")

    if output_shp:
        output_shp.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(output_shp, driver="ESRI Shapefile")

    if verbose:
        print("=" * 65)
        print("PSR PROCESSING & AREA METRICS SUMMARY")
        print("=" * 65)
        print(f"Data Provenance:     {provenance_tag}")
        print(f"Total PSR Pixels:    {area_metrics['pixel_count']:,} px")
        print(f"Pixel Resolution:    {dem_meta['pixel_size_x']:.2f} m x {dem_meta['pixel_size_y']:.2f} m")
        print(f"Total PSR Area:      {area_metrics['area_km2']:.4f} km2 ({area_metrics['area_m2']:,.2f} m2)")
        print(f"Delineated Polygons: {len(gdf)}")
        if output_tif:
            print(f"GeoTIFF Output:      {output_tif}")
        if output_geojson:
            print(f"GeoJSON Output:      {output_geojson}")
        if output_shp:
            print(f"Shapefile Output:    {output_shp}")
        print("=" * 65 + "\n")

    return cleaned_psr, area_metrics, gdf
