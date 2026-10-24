"""
Tests for 3D model terrain alignment, PSR vectorization, and synthetic model removal.
Verifies:
1. Default model is 'lola_crop' (NASA LOLA) and not synthetic.
2. Synthetic benchmark is removed from public catalog summary and UI dropdown.
3. Real NASA models (LOLA crop + Artemis candidates) are fully preserved.
4. Site switching vectorizes matching PSR polygons within true terrain bounds.
"""

import config
import io_utils
import lunar_catalog
import psr
import web_server


def test_default_active_site_is_lola_crop():
    assert web_server.ACTIVE_SITE_ID == "lola_crop"


def test_catalog_summary_excludes_synthetic():
    summary = lunar_catalog.get_catalog_summary()
    site_ids = [s["site_id"] for s in summary]
    assert "synthetic" not in site_ids
    # Real models must be preserved
    assert "lola_crop" in site_ids
    assert "artemis_mons_mouton" in site_ids
    assert "artemis_peak_cabeus_b" in site_ids
    assert "artemis_slater_plain" in site_ids
    assert "artemis_nobile_rim_2" in site_ids
    assert "artemis_haworth" in site_ids
    assert "shackleton" in site_ids


def test_index_html_removes_synthetic():
    html_path = config.BASE_DIR / "web" / "index.html"
    content = html_path.read_text(encoding="utf-8")
    assert '<option value="synthetic"' not in content
    assert 'id="cardSynthetic"' not in content
    assert 'REAL NASA LOLA' in content


def test_lola_crop_psr_polygons_in_bounds():
    """NASA LOLA blue lines must remain correct and within LOLA crop bounds."""
    dem_info = io_utils.read_geotiff(config.REAL_DEM_PATH)
    psr_info = io_utils.read_geotiff(config.REAL_PSR_PATH)
    b = dem_info["bounds"]

    gdf = psr.vectorize_psr_to_polygons(
        binary_psr=psr_info["data"],
        transform=dem_info["transform"],
        crs=dem_info["crs"],
        min_size_pixels=config.PSR_MIN_SIZE_PIXELS,
        provenance=config.PSR_PROVENANCE_PUBLISHED,
    )
    assert len(gdf) > 0
    # Every polygon must be within LOLA bounds
    for geom in gdf.geometry:
        minx, miny, maxx, maxy = geom.bounds
        assert minx >= b.left - 1.0
        assert maxx <= b.right + 1.0
        assert miny >= b.bottom - 1.0
        assert maxy <= b.top + 1.0


def test_artemis_sites_psr_polygons_in_bounds():
    """Artemis site PSR polygons must match the active site's own geographic bounds."""
    for site_id in ["artemis_mons_mouton", "artemis_peak_cabeus_b", "artemis_slater_plain"]:
        dem_path, psr_path = lunar_catalog.save_site_dataset(site_id)
        dem_info = io_utils.read_geotiff(dem_path)
        psr_info = io_utils.read_geotiff(psr_path)
        b = dem_info["bounds"]

        gdf = psr.vectorize_psr_to_polygons(
            binary_psr=psr_info["data"],
            transform=dem_info["transform"],
            crs=dem_info["crs"],
            min_size_pixels=config.PSR_MIN_SIZE_PIXELS,
            provenance=config.PSR_PROVENANCE_PUBLISHED,
        )
        assert len(gdf) > 0, f"Expected PSR polygons for {site_id}"
        for geom in gdf.geometry:
            minx, miny, maxx, maxy = geom.bounds
            assert minx >= b.left - 1.0, f"{site_id} minx {minx} outside left {b.left}"
            assert maxx <= b.right + 1.0, f"{site_id} maxx {maxx} outside right {b.right}"
            assert miny >= b.bottom - 1.0, f"{site_id} miny {miny} outside bottom {b.bottom}"
            assert maxy <= b.top + 1.0, f"{site_id} maxy {maxy} outside top {b.top}"
