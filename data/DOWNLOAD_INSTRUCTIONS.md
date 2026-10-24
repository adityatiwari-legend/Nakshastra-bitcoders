# Lunar Public Dataset Download Guide (Phase 3)

This guide describes how to obtain the real public lunar datasets used by LunaSafe's
preprocessing pipeline (`preprocess_lunar_data.py`) and where to place them.

> [!IMPORTANT]
> Checksums below are SHA-256 of the exact files the pipeline expects.
> `preprocess_lunar_data.py` downloads these automatically and verifies checksums.
> Use this guide only for manual/offline installation.

---

## Target Placement

| Product | Target Path | Role |
| :--- | :--- | :--- |
| LDEM_75S_240M (JP2 + LBL) | `data/ldem_75s_240m.jp2` | Elevation (slope, roughness, 3D terrain) |
| LPSR_65S_240M (JP2 + LBL) | `data/external/LPSR_65S_240M_201608.jp2` | **Published** PSR mask (Mazarico et al. 2011) |
| AVGVISIB_65S_240M (JP2 + LBL) | `data/external/AVGVISIB_65S_240M_201608.jp2` | Illumination fraction (0 = PSR … 1 = fully lit) |

---

## 1. LRO LOLA South Polar DEM (LDEM_75S_240M)

- **Publisher**: NASA PDS Geosciences Node (Washington University in St. Louis)
- **URL (JP2)**: `https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/ldem_75s_240m.jp2`
- **URL (LBL)**: `https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/ldem_75s_240m_jp2.lbl`
- **Version**: V2.1 (product 2017-06-15), 3812×3812 px, 240 m/px, int16
- **Scaling**: DN × 0.5 = meters above R = 1737.4 km (see LBL `SCALING_FACTOR`)
- **SHA-256**: `a0ebbad0a2650c742ed2d4ec1314aa095f869ba800f817b1b72eeb9194345c36`
- **License**: NASA PDS — unrestricted; credit LRO/LOLA team.

Manual download (PowerShell):
```powershell
Invoke-WebRequest -Uri "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/ldem_75s_240m.jp2" -OutFile "data\ldem_75s_240m.jp2"
```

---

## 2. Mazarico et al. (2011) LPSR Permanent Shadow Map

- **Publisher**: MIT / NASA GSFC (Mazarico, Smith et al.)
- **URL**: `https://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/LPSR_65S_240M_201608.jp2`
  (URLs are case-sensitive; the `.JP2` uppercase form also resolves.)
- **Version**: V1.05 (product 2016-09-15), 6420×6420 px, 240 m/px
- **Scaling**: DN ±20000 → binary; raw DN > 0 = PSR (see LBL)
- **SHA-256**: `d0807d1b7d16c13e6e037ce9a9d82efb375cd2065da3f8beeed3f97157deaf94`
- **Citation**: Mazarico, E., et al. (2011). Illumination conditions of the lunar polar regions. *JGR Planets*, 116, E00H17.
- **License**: NASA PDS / MIT — credit Mazarico et al. (2011).

Manual download:
```powershell
Invoke-WebRequest -Uri "https://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/LPSR_65S_240M_201608.jp2" -OutFile "data\external\LPSR_65S_240M_201608.jp2"
```

---

## 3. Mazarico et al. (2011) AVGVISIB Average Solar-Disc Visibility

- **Publisher**: MIT / NASA GSFC (Mazarico, Smith et al.)
- **URL**: `https://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/AVGVISIB_65S_240M_201608.jp2`
- **Version**: V1.05 (product 2016-09-15), 6420×6420 px, 240 m/px
- **Scaling**: DN × 0.00004 → visibility fraction [0, ~0.93] (see LBL)
- **SHA-256**: `4ccaf5ef7cdfc35bbff4d28e0d9b1051d9d56a66181cda633e71bfd42237dd49`
- **Citation**: Mazarico, E., et al. (2011). Illumination conditions of the lunar polar regions. *JGR Planets*, 116, E00H17.

Manual download:
```powershell
Invoke-WebRequest -Uri "https://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/AVGVISIB_65S_240M_201608.jp2" -OutFile "data\external\AVGVISIB_65S_240M_201608.jp2"
```

---

## 4. After Placement — Run the Pipeline

```powershell
.venv\Scripts\python.exe preprocess_lunar_data.py --skip-download   # verify + process local files
```

The pipeline will:
1. Verify all three SHA-256 checksums.
2. Crop the DEM to the south-pole ROI (250×250 px @ 240 m).
3. Reproject LPSR + AVGVISIB onto the DEM grid.
4. Derive binary PSR from the **published** LPSR product (never invent PSR).
5. Compute illumination fraction, slope, roughness; classify hazard with resolution-scaled thresholds.
6. Export GeoTIFFs (`data/lola_south_pole_dem.tif`, `data/lola_psr_mask.tif`, `outputs/*`) and web-ready compact JSON / GeoJSON / XYZ tiles.

---

## 5. Documented-Only Datasets (NOT bundled; manual access only)

These datasets are registered in `config.PUBLIC_DATASETS` with exact access steps.
LunaSafe never claims these files are present locally.

### Diviner Lunar Radiometer (NASA PDS PPI / UCLA)
- **URL**: `https://pds-ppi.igpp.ucla.edu/diviner/`
- **Role**: Surface temperature context (not required for hazard classes).
- **Steps**: Browse "Calibrated Data" or derived polar products under PDS PPI. Exact file
  selection depends on epoch/resolution; no single canonical "polar temperature" file exists.
  Place any downloaded GeoTIFF/IMG under `data/external/` and register it in `config.PUBLIC_DATASETS`.

### Chandrayaan-2 OHRC / TMC-2 (ISRO PRADAN)
- **URL**: `https://wwwpradan.gov.in/`
- **Role**: High-resolution stereo context (0.32 m OHRC / 5 m TMC-2).
- **Steps**: PRADAN requires institutional registration and per-dataset approval — no anonymous
  download exists. (1) Create account at https://wwwpradan.gov.in, (2) select Chandrayaan-2 →
  OHRC/TMC-2, (3) submit request, (4) place downloaded file under `data/external/` and register it.
  LunaSafe never claims these files are present.

### Moon Trek (NASA GSFC)
- **URL**: `https://trek.nasa.gov/moon/`
- **Role**: Optional visual basemap reference only (not used in hazard math).
- **Steps**: Moon Trek is a visualization portal, not a bulk-download API. Use it for manual
  context checks. Hazard/PSR math in LunaSafe uses the PDS/MIT JP2 products above, never scraped tiles.

### LROC NAC Permanent Shadow (South Pole) shapefile
- **URL**: `https://lroc.sese.asu.edu/posts/polar-shadows/`
- **Role**: Independent PSR comparison baseline.
- **Steps**: The ZIP currently returns **403** to non-browser clients. Download manually via a
  browser if needed, then place under `data/external/`. The MIT LPSR raster (Section 2) is the
  primary PSR source used in all hazard classification.

---

## 6. Pre-Flight Check

```powershell
.venv\Scripts\python.exe -c "import io_utils; io_utils.inspect_raster('data/lola_south_pole_dem.tif')"
```

Confirms native Lunar polar stereographic projection (Moon2000, R = 1737.4 km), dimensions,
pixel size, and zero Earth EPSG contamination.

Check dataset registry status live:
```powershell
Invoke-RestMethod http://localhost:8050/api/data-sources
```
