"""
Backward-compatible entry point for converting the real NASA PDS LOLA South Pole
JP2 dataset into georeferenced GeoTIFFs.

Phase 3: delegates to preprocess_lunar_data.py so the PSR mask comes from the
PUBLISHED Mazarico et al. (2011) LPSR product (not a DEM-threshold proxy) and
illumination fraction is exported alongside the DEM.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
import config  # noqa: E402


def convert_real_lola_to_geotiff() -> bool:
    """Runs the Phase 3 preprocessing pipeline (DEM + published PSR + illumination)."""
    from preprocess_lunar_data import run_pipeline

    if not config.LOLA_DEM_JP2_PATH.exists():
        raise FileNotFoundError(f"Missing {config.LOLA_DEM_JP2_PATH}")

    summary = run_pipeline(skip_download=False, verbose=True)
    if summary.get("status") != "SUCCESS":
        raise RuntimeError(f"Preprocessing pipeline failed: {summary.get('error')}")
    print(f"DEM:  {summary['outputs']['dem']}")
    print(f"PSR:  {summary['outputs']['psr']} (published Mazarico et al. 2011)")
    print(f"ILL:  {summary['outputs']['illumination']}")
    return True


if __name__ == "__main__":
    convert_real_lola_to_geotiff()
