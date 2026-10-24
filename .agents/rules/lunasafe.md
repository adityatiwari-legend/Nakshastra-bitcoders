# LunaSafe project rules

Project: Lunar PSR mapping and surface hazard classification (hackathon Problem Statement 02).

Always:
- Python 3.10+, in a local .venv. Pin versions in requirements.txt.
- Libraries: numpy, scipy, rasterio, scikit-image, geopandas, shapely, matplotlib.
- Keep the source lunar CRS from the input rasters. Never assign an Earth EPSG code to lunar data.
- All thresholds and paths live in config.py. No magic numbers elsewhere.
- Never treat NoData as Safe. Never label a published PSR mask as "independently predicted".
- Every module must run on synthetic data (a fake crater DEM plus a dark crater floor) when real data is missing, and label those outputs "SYNTHETIC DEMO".
- Modules: config.py, io_utils.py, psr.py, terrain.py, hazard.py, mapping.py, validate.py, main.py, tests/.
- After writing code, run it and the tests yourself. Do not report success until the commands pass.
- Outputs go in outputs/ (GeoTIFF, GeoJSON, PNG, PDF, CSV).
- Ask me before downloading files larger than 500 MB.

Hazard rules (defaults, editable in config.py):
- Slope: Safe <5 deg, Caution 5 to <10, Unsafe >=10, hard Unsafe >=15
- Roughness (local elevation std dev): Safe <1.5 m, Caution 1.5 to <3, Unsafe >=3, hard Unsafe >=5. Recalibrate for DEM resolution.
- Score H = 0.50*S + 0.30*R + 0.20*D, with S = min(slope/15,1), R = min(rough/5,1), D = shadow fraction (0 if only a binary PSR mask)
- Class 1 Safe: H<0.25 and slope<5 and roughness<1.5
- Class 2 Caution: 0.25 <= H < 0.60
- Class 3 Unsafe: H>=0.60 or any hard override
- Class 4 Shadowed-Unknown: PSR pixels that are not already Unsafe
- Class 0 NoData
