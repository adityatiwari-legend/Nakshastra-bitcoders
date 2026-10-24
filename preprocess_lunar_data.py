"""
Reproducible preprocessing pipeline for real public lunar datasets (Phase 3).

Sources (all public, cited in config.PUBLIC_DATASETS):
  - LRO LOLA LDEM_75S_240M (NASA PDS Geosciences) — elevation
  - Mazarico et al. (2011) LPSR_65S_240M — published PSR mask
  - Mazarico et al. (2011) AVGVISIB_65S_240M — illumination fraction

Pipeline steps (deterministic, checksum-verified downloads):
  1. Download raw JP2s if missing; verify SHA-256 against config.
  2. Crop the LOLA DEM to the south-pole ROI (config.POLE_CROP_SIZE_PX).
  3. Reproject LPSR + AVGVISIB onto the DEM grid (nearest / bilinear).
  4. Derive binary PSR from the published LPSR product (never invent PSR).
  5. Compute illumination fraction (0 = permanent shadow .. 1 = fully lit).
  6. Compute slope + roughness via terrain.py; classify hazard via hazard.py.
  7. Export GeoTIFFs + web-ready assets (compact JSON, GeoJSON, XYZ tiles).

Run:
  .venv/Scripts/python.exe preprocess_lunar_data.py
  .venv/Scripts/python.exe preprocess_lunar_data.py --skip-download   # offline
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.windows import Window

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
import config  # noqa: E402
import io_utils  # noqa: E402
import terrain  # noqa: E402
import hazard  # noqa: E402


# ---------------------------------------------------------------------------
# Step 1 — download + checksum
# ---------------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_download(url: str, dest: Path, expected_sha256: str, skip_download: bool = False) -> Path:
    """Download dest from url if missing; always verify SHA-256 when file exists."""
    if dest.exists():
        digest = sha256_of(dest).lower()
        if digest == expected_sha256.lower():
            print(f"[OK] {dest.name}: checksum verified ({digest[:12]}...)")
            return digest
        raise RuntimeError(
            f"CHECKSUM MISMATCH for {dest}\n  expected {expected_sha256}\n  actual   {digest}\n"
            "  Delete the file and re-run to re-download."
        )

    if skip_download:
        raise FileNotFoundError(
            f"{dest} missing and --skip-download was set. "
            f"Download manually from:\n  {url}\nthen place at:\n  {dest}"
        )

    print(f"[DOWNLOAD] {dest.name} <- {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)  # noqa: S310 — public NASA/MIT URLs from config
    tmp.replace(dest)
    digest = sha256_of(dest).lower()
    if digest != expected_sha256.lower():
        raise RuntimeError(
            f"CHECKSUM MISMATCH after download of {dest}\n"
            f"  expected {expected_sha256}\n  actual   {digest}"
        )
    print(f"[OK] {dest.name}: downloaded + checksum verified ({digest[:12]}...)")
    return digest


# ---------------------------------------------------------------------------
# Step 2–5 — grid alignment, PSR, illumination
# ---------------------------------------------------------------------------

def _lunar_stereo_crs(lon_0: float = 0.0) -> CRS:
    return CRS.from_string(
        f"+proj=stere +lat_0=-90 +lon_0={lon_0} +k=1 +x_0=0 +y_0=0 "
        "+R=1737400 +units=m +no_defs"
    )


def crop_dem_roi(
    jp2_path: Path = config.LOLA_DEM_JP2_PATH,
    crop_size: int = config.POLE_CROP_SIZE_PX,
) -> Tuple[np.ndarray, Any, CRS]:
    """Crops the LOLA DEM around the south pole; returns (elev_m, transform, crs).

    PDS label LDEM_75S_240M: DN * SCALING_FACTOR(0.5) = meters above R=1737.4 km.
    """
    with rasterio.open(jp2_path) as src:
        row0 = (src.height - crop_size) // 2
        col0 = (src.width - crop_size) // 2
        window = Window(col0, row0, crop_size, crop_size)
        raw = src.read(1, window=window)
        transform = rasterio.windows.transform(window, src.transform)
        crs = src.crs
    elev = raw.astype(np.float32) * config.LOLA_DEM_DN_SCALE
    return elev, transform, crs


def align_raster_to_grid(
    src_path: Path,
    dst_shape: Tuple[int, int],
    dst_transform: Any,
    dst_crs: CRS,
    resampling: Resampling = Resampling.nearest,
    src_crs_override: Optional[CRS] = None,
) -> np.ndarray:
    """Reprojects any source raster onto the active DEM grid."""
    with rasterio.open(src_path) as src:
        source = src.read(1)
        src_transform = src.transform
        src_crs = src_crs_override or src.crs
    destination = np.zeros(dst_shape, dtype=np.float64)
    reproject(
        source=source,
        destination=destination,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=resampling,
    )
    return destination


def derive_psr_from_lpsr(
    lpsr_jp2: Path = config.LPSR_JP2_PATH,
    dem_shape: Optional[Tuple[int, int]] = None,
    dem_transform: Any = None,
    dem_crs: Optional[CRS] = None,
) -> np.ndarray:
    """Binary PSR from the published Mazarico et al. (2011) LPSR product.

    PDS label LPSR_65S_240M: DN=+20000 -> shadow, DN=-20000 -> illuminated.
    This is a PUBLISHED product — never label it 'independently predicted'.
    """
    raw = align_raster_to_grid(
        lpsr_jp2, dem_shape, dem_transform, dem_crs,
        resampling=Resampling.nearest,
    )
    return (raw > 0).astype(np.uint8)


def derive_illumination_fraction(
    avgvisib_jp2: Path = config.AVGVISIB_JP2_PATH,
    dem_shape: Optional[Tuple[int, int]] = None,
    dem_transform: Any = None,
    dem_crs: Optional[CRS] = None,
) -> np.ndarray:
    """Average solar-disc visibility fraction in [0, 1].

    PDS label AVGVISIB_65S_240M: value = DN * 0.00004; 0 = permanent shadow.
    Fraction of timesteps with any solar-disc illumination (Mazarico 2011).
    """
    raw = align_raster_to_grid(
        avgvisib_jp2, dem_shape, dem_transform, dem_crs,
        resampling=Resampling.bilinear,
    )
    frac = raw.astype(np.float32) * config.AVGVISIB_DN_SCALE
    return np.clip(frac, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Step 6–7 — hazard classification + exports
# ---------------------------------------------------------------------------

def export_xyz_tiles(
    arr: np.ndarray,
    out_dir: Path,
    tile_size: int = 256,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
) -> int:
    """Writes a minimal single-z XYZ tile pyramid (z=0 only) as raw .bin + meta.

    The grid is small (250x250), so one z=0 tile set is sufficient. Tiles are
    float32 arrays (no lossy quantization); the frontend can normalize.
    Returns the number of tiles written.
    """
    from math import ceil

    out_dir.mkdir(parents=True, exist_ok=True)
    h, w = arr.shape
    ntx = ceil(w / tile_size)
    nty = ceil(h / tile_size)
    padded = np.zeros((nty * tile_size, ntx * tile_size), dtype=np.float32)
    padded[:h, :w] = arr.astype(np.float32)
    for ty in range(nty):
        for tx in range(ntx):
            tile = padded[ty * tile_size:(ty + 1) * tile_size,
                          tx * tile_size:(tx + 1) * tile_size]
            tile.tofile(out_dir / f"0_{tx}_{ty}.f32")
    meta = {
        "minzoom": 0, "maxzoom": 0, "tile_size": tile_size,
        "tiles_x": ntx, "tiles_y": nty,
        "grid_width": int(w), "grid_height": int(h),
        "dtype": "float32",
        "value_min": float(np.nanmin(arr)) if vmin is None else float(vmin),
        "value_max": float(np.nanmax(arr)) if vmax is None else float(vmax),
        "note": "Row-major float32 tile arrays in Lunar Polar Stereographic grid space.",
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return ntx * nty


def export_artemis_regions_geojson(out_path: Path) -> Path:
    """Writes the nine official Artemis III candidate regions as a GeoJSON Point FC."""
    features = []
    for region_id, meta in config.ARTEMIS_III_REGIONS.items():
        features.append({
            "type": "Feature",
            "properties": {
                "region_id": region_id,
                "name": meta["name"],
                "center_lat": meta["center_lat"],
                "center_lon": meta["center_lon"],
                "source": "NASA Artemis III down-select (Oct 2024); centers = mean of Wueller et al. (2026) Table A1 CLS coordinates",
                "official": True,
                "removed_2024": False,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [meta["center_lon"], meta["center_lat"]],
            },
        })
    fc = {"type": "FeatureCollection", "features": features}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(fc, indent=2))
    return out_path


def run_pipeline(skip_download: bool = False, verbose: bool = True) -> Dict[str, Any]:
    """Executes the full Phase 3 preprocessing pipeline. Returns a summary dict."""
    summary: Dict[str, Any] = {"status": "SUCCESS", "steps": [], "outputs": {}}

    # --- Step 1: downloads -------------------------------------------------
    checksums = {}
    try:
        checksums["lola_dem"] = ensure_download(
            config.LOLA_DEM_JP2_URL, config.LOLA_DEM_JP2_PATH,
            config.LOLA_DEM_JP2_SHA256, skip_download,
        )
        checksums["lpsr"] = ensure_download(
            config.LPSR_JP2_URL, config.LPSR_JP2_PATH,
            config.LPSR_JP2_SHA256, skip_download,
        )
        checksums["avgvisib"] = ensure_download(
            config.AVGVISIB_JP2_URL, config.AVGVISIB_JP2_PATH,
            config.AVGVISIB_JP2_SHA256, skip_download,
        )
        summary["steps"].append("download+checksum: OK")
    except Exception as e:
        summary["status"] = "ERROR"
        summary["error"] = str(e)
        return summary
    summary["checksums"] = checksums

    # --- Step 2: DEM crop --------------------------------------------------
    elev, transform, crs = crop_dem_roi()
    ny, nx = elev.shape
    nodata = config.DEFAULT_NODATA_VALUE
    valid = np.isfinite(elev) & (elev != 0.0)
    elev[~valid] = nodata
    if verbose:
        print(f"[DEM] crop {nx}x{ny} px, valid={int(valid.sum())}/{valid.size}, "
              f"elev range=[{elev[valid].min():.0f}, {elev[valid].max():.0f}] m")

    dem_meta = {
        "data": elev, "transform": transform, "crs": crs,
        "pixel_size_x": abs(transform.a), "pixel_size_y": abs(transform.e),
        "nodata": nodata, "shape": elev.shape,
    }

    io_write = io_utils.write_geotiff
    io_write(
        output_path=config.REAL_DEM_PATH,
        data=elev, transform=transform, crs=crs, nodata=nodata,
        tags={
            "PROJECT": "LunaSafe", "BODY": "MOON",
            "DATA_TYPE": "REAL NASA LRO LOLA",
            "SOURCE_PRODUCT": "LDEM_75S_240M V2.1 (PDS)",
            "SOURCE_URL": config.LOLA_DEM_JP2_URL,
            "SHA256": checksums["lola_dem"],
            "SITE": "lola_crop",
        },
    )
    summary["outputs"]["dem"] = str(config.REAL_DEM_PATH)
    summary["steps"].append("dem crop+geotiff: OK")

    # --- Step 3–5: PSR + illumination from published products --------------
    psr = derive_psr_from_lpsr(
        dem_shape=(ny, nx), dem_transform=transform, dem_crs=crs,
    )
    psr[~valid] = 0  # never mark NoData as PSR
    illum = derive_illumination_fraction(
        dem_shape=(ny, nx), dem_transform=transform, dem_crs=crs,
    )
    illum[~valid] = np.nan
    if verbose:
        print(f"[PSR] published LPSR pixels: {int(psr.sum())}/{psr.size} "
              f"({100.0 * psr.sum() / psr.size:.2f}%)")
        print(f"[ILLUM] mean visibility fraction (valid): {np.nanmean(illum):.4f}")

    io_write(
        output_path=config.REAL_PSR_PATH,
        data=psr, transform=transform, crs=crs, nodata=None,
        tags={
            "PROJECT": "LunaSafe", "BODY": "MOON",
            "DATA_TYPE": "PUBLISHED LRO LOLA PSR (Mazarico et al. 2011)",
            "PSR_PROVENANCE": config.PSR_PROVENANCE_PUBLISHED,
            "SOURCE_PRODUCT": "LPSR_65S_240M_201608 V1.05",
            "SOURCE_URL": config.LPSR_JP2_URL,
            "SHA256": checksums["lpsr"],
            "SITE": "lola_crop",
        },
    )
    # Also write the canonical outputs/psr_binary.tif consumed by tests, web_server, mission_report
    io_write(
        output_path=config.OUTPUT_PSR_BINARY_TIF,
        data=psr, transform=transform, crs=crs, nodata=None,
        tags={
            "PROJECT": "LunaSafe", "BODY": "MOON",
            "DATA_TYPE": "PUBLISHED LRO LOLA PSR (Mazarico et al. 2011)",
            "PSR_PROVENANCE": config.PSR_PROVENANCE_PUBLISHED,
            "SOURCE_PRODUCT": "LPSR_65S_240M_201608 V1.05",
            "SITE": "lola_crop",
        },
    )
    io_write(
        output_path=config.REAL_ILLUMINATION_PATH,
        data=illum.astype(np.float32), transform=transform, crs=crs, nodata=None,
        tags={
            "PROJECT": "LunaSafe", "BODY": "MOON",
            "DATA_TYPE": "PUBLISHED ILLUMINATION FRACTION (Mazarico et al. 2011)",
            "SOURCE_PRODUCT": "AVGVISIB_65S_240M_201608 V1.05",
            "SOURCE_URL": config.AVGVISIB_JP2_URL,
            "SHA256": checksums["avgvisib"],
            "SITE": "lola_crop",
        },
    )
    summary["outputs"]["psr"] = str(config.REAL_PSR_PATH)
    summary["outputs"]["illumination"] = str(config.REAL_ILLUMINATION_PATH)
    summary["steps"].append("psr+illumination: OK")

    # --- Step 6: terrain + hazard ------------------------------------------
    terrain_res = terrain.process_terrain_pipeline(
        dem=elev, dem_meta=dem_meta,
        output_slope=config.OUTPUT_SLOPE_TIF,
        output_aspect=config.OUTPUT_ASPECT_TIF,
        output_rough_std=config.OUTPUT_ROUGHNESS_STD_TIF,
        output_rough_tri=config.OUTPUT_ROUGHNESS_TRI_TIF,
        output_hist=config.OUTPUT_TERRAIN_HIST_PNG,
        is_synthetic=False,
        verbose=verbose,
    )
    hazard_classes, score_h = hazard.classify_hazard_surface(
        slope=terrain_res["slope"],
        roughness=terrain_res["roughness_std"],
        psr_mask=psr,
        shadow_fraction=(1.0 - illum).astype(np.float32),
        pixel_size_m=float(abs(dem_meta["pixel_size_x"])),
    )
    io_write(
        output_path=config.OUTPUT_HAZARD_CLASSES_TIF,
        data=hazard_classes, transform=transform, crs=crs,
        nodata=config.CLASS_NODATA,
        tags={
            "PROJECT": "LunaSafe", "BODY": "MOON",
            "DATA_TYPE": "REAL NASA LRO LOLA",
            "PRODUCT": "HAZARD_CLASSIFICATION",
            "SITE": "lola_crop",
            "CLASSES": "0=NoData,1=Safe,2=Caution,3=Unsafe,4=Shadowed-Unknown",
        },
    )
    df_summary = hazard.generate_hazard_summary_table(
        hazard_classes, dem_meta["pixel_size_x"], dem_meta["pixel_size_y"]
    )
    config.OUTPUT_HAZARD_SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_summary.to_csv(config.OUTPUT_HAZARD_SUMMARY_CSV, index=False)
    summary["steps"].append("terrain+hazard: OK")
    if verbose:
        print(df_summary.to_string(index=False))

    # --- Step 7: web-ready assets -------------------------------------------
    web_dir = config.OUTPUT_DIR / "web"
    n_tiles = export_xyz_tiles(hazard_classes.astype(np.float32), web_dir / "tiles" / "hazard")
    n_tiles += export_xyz_tiles(illum, web_dir / "tiles" / "illumination", vmin=0.0, vmax=1.0)
    # Compact JSON cost grid for the traverse tool (downsampled-friendly: full res here, small grid)
    cost_compact = {
        "crs": "lunar_south_pole_stereographic_R1737400",
        "width": nx, "height": ny,
        "pixel_size_m": float(dem_meta["pixel_size_x"]),
        "hazard_classes": [int(v) for v in hazard_classes.flatten()],
        "illumination": [round(float(v), 4) for v in np.nan_to_num(illum, nan=0.0).flatten()],
        "psr": [int(v) for v in psr.flatten()],
        "thresholds": {
            "slope_safe_max": config.SLOPE_SAFE_MAX,
            "slope_caution_max": config.SLOPE_CAUTION_MAX,
            "slope_hard_unsafe": config.SLOPE_HARD_UNSAFE_MIN,
            "rough_safe_max": config.ROUGHNESS_SAFE_MAX,
            "rough_hard_unsafe": config.ROUGHNESS_HARD_UNSAFE_MIN,
        },
        "sources": [
            {"id": "lola_dem_75s", "role": "elevation", "sha256": checksums["lola_dem"]},
            {"id": "lpsr_psr", "role": "psr", "sha256": checksums["lpsr"]},
            {"id": "avgvisib_illum", "role": "illumination", "sha256": checksums["avgvisib"]},
        ],
    }
    cost_path = web_dir / "cost_grid.json"
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    cost_path.write_text(json.dumps(cost_compact, separators=(",", ":")))
    regions_path = export_artemis_regions_geojson(web_dir / "artemis_iii_regions.geojson")
    summary["outputs"]["tiles"] = str(web_dir / "tiles")
    summary["outputs"]["tiles_written"] = n_tiles
    summary["outputs"]["cost_grid"] = str(cost_path)
    summary["outputs"]["artemis_regions"] = str(regions_path)
    summary["steps"].append("web assets: OK")

    if verbose:
        print("=" * 65)
        print("PREPROCESS PIPELINE COMPLETE")
        for s in summary["steps"]:
            print(f"  - {s}")
        print("=" * 65)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LunaSafe Phase 3 real-data preprocessing")
    parser.add_argument("--skip-download", action="store_true",
                        help="Fail instead of downloading (offline mode)")
    args = parser.parse_args()
    result = run_pipeline(skip_download=args.skip_download)
    if result["status"] != "SUCCESS":
        print(f"PIPELINE ERROR: {result.get('error')}", file=sys.stderr)
        sys.exit(1)
