"""
LunaSafe Mission Control Full-Stack Web Server
Provides a real-time web interface and REST API to:
1. Control pipeline parameters (slopes, roughness, weights, landing radius)
2. Execute the full end-to-end Python pipeline with live log streaming
3. Perform ultra-fast in-memory recalculations (~20ms) for real-time slider updates
4. Manage datasets (Synthetic Crater, USGS LRO LOLA South Pole, Custom GeoTIFFs)
5. Audit 9-point mathematical safety rules
6. Serve 2D raster arrays, 3D lunar terrain mesh, AI landing recommendations, and publication artifacts
7. Provide direct download endpoints for all GeoTIFFs, Shapefiles, PDFs, and CSVs
"""

import sys
import json
import re
import gzip
import time
import zipfile
import threading
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import mimetypes
mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("model/gltf+json", ".gltf")
import numpy as np

# Set project root
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
import io_utils
import hazard
import ml_recommender
import validate
import export_web_data
import rover_router
import lunar_catalog
import tile_pyramid

VENV_PYTHON = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
PYTHON_BIN = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

# Global state for background tasks, active site and logs
PIPELINE_LOCK = threading.Lock()
PIPELINE_RUNNING = False
PIPELINE_LOGS = []
DOWNLOAD_STATUS = {"running": False, "progress": 0, "message": "Idle", "success": False}
ACTIVE_SITE_ID = "lola_crop"

# ---------------------------------------------------------------------------
# Artifact Hub manifest support
# ---------------------------------------------------------------------------
ARTIFACT_INTERNAL_SKIP = {"web_data.json", "active_site_dem.tif", "artifacts.json"}
ARTIFACT_SIDECAR_SKIP = (".shx", ".dbf", ".prj", ".cpg", ".aux", ".xml", ".ovr")
ARTIFACT_SAVED_ROUTES_DIR = config.OUTPUT_DIR / "saved_routes"

# Curated (title, type, tags) for known pipeline products; others fall back to heuristic.
ARTIFACT_CATALOG = {
    "lunasafe_hazard_map.png": ("4-Panel Hazard Publication Map", "map", ["map", "hazard", "publication", "png"]),
    "lunasafe_hazard_map.pdf": ("4-Panel Hazard Map (Vector PDF)", "map", ["map", "hazard", "publication", "pdf"]),
    "mission_report.pdf": ("PDF Mission Report", "report", ["report", "mission", "certification", "pdf"]),
    "hazard_classes.tif": ("Hazard Classification Raster (0-4)", "raster", ["hazard", "raster", "geotiff", "classes"]),
    "psr_binary.tif": ("Binary PSR Mask Raster", "raster", ["psr", "shadow", "raster", "geotiff"]),
    "slope_deg.tif": ("Horn Slope Raster (deg)", "raster", ["slope", "raster", "geotiff", "topography"]),
    "roughness_std_m.tif": ("Elevation Roughness Raster (m)", "raster", ["roughness", "raster", "geotiff", "topography"]),
    "roughness_tri_m.tif": ("Triangle Roughness Raster (m)", "raster", ["roughness", "raster", "geotiff", "topography"]),
    "aspect_deg.tif": ("Terrain Aspect Raster (deg)", "raster", ["aspect", "raster", "geotiff", "topography"]),
    "boulder_hazard.tif": ("Boulder Micro-Hazard Probability Raster", "raster", ["boulder", "hazard", "raster", "geotiff"]),
    "psr_polygons.geojson": ("PSR Vector Polygons (GeoJSON)", "vector", ["psr", "shadow", "vector", "geojson", "polygons"]),
    "psr_polygons_bundle.zip": ("PSR Shapefile Bundle (ZIP)", "vector", ["psr", "shadow", "vector", "shapefile", "zip"]),
    "hazard_summary.csv": ("Hazard Area Summary Table", "data", ["hazard", "summary", "csv", "table"]),
    "landing_sites.json": ("Candidate Landing Sites Telemetry", "data", ["landing", "sites", "json", "recommendations"]),
    "terrain_histograms.png": ("Terrain Property Histograms", "chart", ["histogram", "statistics", "chart", "png"]),
    "slope_sensitivity.png": ("Slope Threshold Sensitivity Chart", "chart", ["sensitivity", "slope", "chart", "png"]),
    "rover_traverse.json": ("Active Rover Traverse Route", "route", ["rover", "route", "traverse", "json"]),
}

ARTIFACT_PREVIEW_KIND = {
    "png": "image", "jpg": "image", "jpeg": "image", "gif": "image", "webp": "image",
    "pdf": "pdf", "geojson": "geojson", "json": "json", "csv": "csv",
    "tif": "info", "tiff": "info", "zip": "info", "shp": "info",
}


def _artifact_active_dataset_label():
    """Best-effort provenance label for the ACTIVE pipeline outputs."""
    try:
        import rasterio
        hazard_path = config.OUTPUT_HAZARD_CLASSES_TIF
        if hazard_path.exists():
            with rasterio.open(hazard_path) as src:
                tags = src.tags()
            site_id = tags.get("SITE", "")
            if site_id == "lola_crop" or "LOLA" in str(tags.get("DATA_TYPE", "")).upper():
                return "lola_crop"
            if site_id:
                return site_id
    except Exception:
        pass
    return str(RASTER_CACHE.get("dataset_id") or "unknown")


def _artifact_entry_for(path: Path, dataset_label: str, saved: bool = False):
    """Build a manifest entry for one artifact file, or None if it should be skipped."""
    name = path.name
    if name in ARTIFACT_INTERNAL_SKIP:
        return None
    low = name.lower()
    if low.endswith(ARTIFACT_SIDECAR_SKIP):
        return None
    if not path.is_file():
        return None

    ext = low.rsplit(".", 1)[-1] if "." in low else ""
    title, atype, tags = ARTIFACT_CATALOG.get(low, (None, None, None))
    if title is None:
        stem = path.stem.replace("_", " ").strip().title()
        if low.startswith("route_") and low.endswith(".json"):
            atype, title = "route", f"Saved Rover Route — {stem}"
            tags = ["rover", "route", "traverse", "json", "saved"]
        elif ext in ("tif", "tiff"):
            atype, title = "raster", f"{stem} (GeoTIFF)"
            tags = ["raster", "geotiff"]
        elif ext == "png":
            atype, title = "map" if "map" in low else "chart", stem
            tags = [ext]
        elif ext == "pdf":
            atype, title = "report", stem
            tags = ["pdf"]
        elif ext == "csv":
            atype, title = "data", stem
            tags = ["csv"]
        elif ext in ("geojson", "json"):
            atype, title = "vector" if ext == "geojson" else "data", stem
            tags = [ext]
        elif ext == "shp":
            atype, title = "vector", f"{stem} (Shapefile)"
            tags = ["shapefile", "vector"]
        elif ext == "zip":
            atype, title = "vector", stem
            tags = ["zip"]
        else:
            atype, title = "data", stem
            tags = [ext] if ext else ["file"]

    stat = path.stat()
    ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(stat.st_mtime))

    # Saved routes carry their own recorded dataset; pipeline outputs use the active label.
    entry_dataset = dataset_label
    if atype == "route" and low.endswith(".json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if isinstance(meta, dict) and meta.get("_hub", {}).get("dataset"):
                entry_dataset = meta["_hub"]["dataset"]
        except Exception:
            pass

    rel = path.relative_to(config.OUTPUT_DIR).as_posix()
    thumbnail = f"/outputs/{rel}" if ext == "png" else None
    # mission_report.pdf regenerates on-demand via the download handler — keep that path.
    download = "/api/download/mission_report.pdf" if low == "mission_report.pdf" else f"/outputs/{rel}"
    return {
        "id": rel,
        "filename": name,
        "title": title,
        "type": atype,
        "dataset": entry_dataset,
        "date": ts,
        "size_bytes": stat.st_size,
        "tags": tags,
        "preview_kind": ARTIFACT_PREVIEW_KIND.get(ext, "info"),
        "thumbnail_url": thumbnail,
        "download_url": download,
        "saved": saved,
    }


def build_artifacts_manifest():
    """Scan outputs/ + saved_routes/ and return (manifest_dict). Also persists artifacts.json."""
    dataset_label = _artifact_active_dataset_label()
    entries = []

    if config.OUTPUT_DIR.exists():
        for p in sorted(config.OUTPUT_DIR.iterdir()):
            e = _artifact_entry_for(p, dataset_label)
            if e:
                entries.append(e)

    if ARTIFACT_SAVED_ROUTES_DIR.exists():
        for p in sorted(ARTIFACT_SAVED_ROUTES_DIR.glob("*.json")):
            e = _artifact_entry_for(p, dataset_label, saved=True)
            if e:
                # title from hub metadata when present
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    hub = meta.get("_hub", {}) if isinstance(meta, dict) else {}
                    if hub.get("title"):
                        e["title"] = hub["title"]
                    if hub.get("tags"):
                        e["tags"] = hub["tags"]
                    if hub.get("date"):
                        e["date"] = hub["date"]
                except Exception:
                    pass
                entries.append(e)

    manifest = {
        "status": "SUCCESS",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "active_dataset": dataset_label,
        "count": len(entries),
        "artifacts": entries,
    }
    try:
        with open(config.OUTPUT_DIR / "artifacts.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
    except Exception:
        pass
    return manifest

# In-memory raster cache for 60 FPS recalculation.
# The outputs/ rasters define the ACTIVE dataset; the DEM is selected to match
# their grid exactly. Mixing rasters from different datasets is rejected.
RASTER_CACHE = {
    "loaded": False,
    "dem": None,
    "slope": None,
    "roughness": None,
    "psr": None,
    "meta": None,
    "transform": None,
    "dataset_id": None,      # "lola_crop" | "synthetic" | site_id from catalog
    "dataset_name": None,    # human-readable provenance label
    "is_synthetic": True,
    "pixel_size_m": None,
    "shape": None,
}


def _describe_dem(dem_info, dem_path=None):
    """Derives honest provenance labels for a chosen DEM raster."""
    tags = dem_info.get("tags") or {}
    site_id = tags.get("SITE")
    if site_id:
        from lunar_catalog import LUNAR_SITES
        if site_id == "lola_crop":
            return "lola_crop", "REAL NASA LRO LOLA (South Pole)", False
        if site_id.startswith("artemis_"):
            site_name = LUNAR_SITES.get(site_id, {}).get("name", site_id)
            return site_id, f"REAL NASA LRO LOLA — {site_name} (Artemis III Candidate)", False
        site_name = LUNAR_SITES.get(site_id, {}).get("name", site_id)
        return site_id, f"{site_name} (Procedural Site Model)", True
    if "REAL NASA" in str(tags.get("DATA_TYPE", "")):
        return "lola_crop", "REAL NASA LRO LOLA (South Pole)", False
    if dem_path is not None and Path(dem_path) == config.SYNTHETIC_DEM_PATH:
        return "synthetic", "SYNTHETIC DEMO", True
    return "synthetic", "SYNTHETIC DEMO", True


def load_raster_cache():
    """Caches a CONSISTENT raster tuple in memory for instant recalculation.

    The pipeline outputs (slope, roughness, cleaned PSR) are the authoritative
    active dataset. A DEM is loaded only if its grid matches those outputs.
    Mismatched datasets are rejected loudly instead of silently mixed.
    """
    try:
        slope_path = config.OUTPUT_SLOPE_TIF
        rough_path = config.OUTPUT_ROUGHNESS_STD_TIF
        psr_path = config.OUTPUT_PSR_BINARY_TIF

        if not (slope_path.exists() and rough_path.exists() and psr_path.exists()):
            print("[Raster Cache] Pipeline outputs missing; run the pipeline once first.")
            return False

        slope_info = io_utils.read_geotiff(slope_path)
        rough_info = io_utils.read_geotiff(rough_path)
        psr_info = io_utils.read_geotiff(psr_path)

        shape = slope_info["data"].shape
        if rough_info["data"].shape != shape or psr_info["data"].shape != shape:
            print("[Raster Cache] REJECTED: outputs/ rasters have inconsistent grids. Re-run the pipeline.")
            return False

        # Candidate DEMs in priority order; only a grid-exact match is accepted.
        candidates = [
            config.OUTPUT_DIR / "active_site_dem.tif",
            config.REAL_DEM_PATH,
            config.SYNTHETIC_DEM_PATH,
        ]
        dem_info = None
        dem_info_path = None
        for dem_path in candidates:
            if dem_path.exists():
                cand = io_utils.read_geotiff(dem_path)
                if cand["data"].shape == shape:
                    dem_info = cand
                    dem_info_path = dem_path
                    break
        if dem_info is None:
            print(
                f"[Raster Cache] REJECTED: no DEM matches the active outputs grid {shape}. "
                "Re-run the pipeline to regenerate consistent outputs."
            )
            return False

        dataset_id, dataset_name, is_synthetic = _describe_dem(dem_info, dem_info_path)

        RASTER_CACHE["dem"] = dem_info["data"]
        RASTER_CACHE["slope"] = slope_info["data"]
        RASTER_CACHE["roughness"] = rough_info["data"]
        RASTER_CACHE["psr"] = psr_info["data"]
        RASTER_CACHE["meta"] = dem_info.get("profile", {})
        RASTER_CACHE["transform"] = dem_info.get("transform")
        RASTER_CACHE["dataset_id"] = dataset_id
        RASTER_CACHE["dataset_name"] = dataset_name
        RASTER_CACHE["is_synthetic"] = is_synthetic
        RASTER_CACHE["pixel_size_m"] = float(abs(dem_info["pixel_size_x"]))
        RASTER_CACHE["shape"] = tuple(shape)
        RASTER_CACHE["loaded"] = True
        tile_pyramid.TILE_CACHE.clear()
        print(f"[Raster Cache] Loaded consistent dataset '{dataset_name}' grid={shape[1]}x{shape[0]} px={RASTER_CACHE['pixel_size_m']} m/px")
        return True
    except Exception as e:
        print(f"[Raster Cache] Could not load cache: {e}")
        return False


def get_tile_layer_raster(layer_name: str) -> Optional[np.ndarray]:
    """Retrieves or derives the base 2D raster array for tile pyramid generation."""
    norm = layer_name.lower().strip()
    if norm not in tile_pyramid.ALLOWED_LAYERS:
        return None

    if not RASTER_CACHE["loaded"]:
        if not load_raster_cache():
            return None

    if norm in ("hazard", "hazard_classes"):
        if config.OUTPUT_HAZARD_CLASSES_TIF.exists():
            try:
                hz = io_utils.read_geotiff(config.OUTPUT_HAZARD_CLASSES_TIF)["data"]
                if hz.shape == RASTER_CACHE.get("shape"):
                    return hz
            except Exception:
                pass
        slope = RASTER_CACHE.get("slope")
        rough = RASTER_CACHE.get("roughness")
        psr = RASTER_CACHE.get("psr")
        if slope is not None and rough is not None and psr is not None:
            hz_classes, _ = hazard.classify_hazard_surface(
                slope=slope, roughness=rough, psr_mask=psr,
                pixel_size_m=RASTER_CACHE.get("pixel_size_m"),
            )
            return hz_classes
        return None

    if norm in ("psr", "psr_mask"):
        return RASTER_CACHE.get("psr")

    if norm in ("elevation", "dem"):
        return RASTER_CACHE.get("dem")

    if norm == "slope":
        return RASTER_CACHE.get("slope")

    if norm == "roughness":
        return RASTER_CACHE.get("roughness")

    if norm == "score":
        slope = RASTER_CACHE.get("slope")
        rough = RASTER_CACHE.get("roughness")
        psr = RASTER_CACHE.get("psr")
        if slope is not None and rough is not None and psr is not None:
            _, score_h = hazard.classify_hazard_surface(
                slope=slope, roughness=rough, psr_mask=psr,
                pixel_size_m=RASTER_CACHE.get("pixel_size_m"),
            )
            return score_h
        return None

    if norm == "illumination":
        if config.REAL_ILLUMINATION_PATH.exists():
            try:
                ill = io_utils.read_geotiff(config.REAL_ILLUMINATION_PATH)["data"]
                if ill.shape == RASTER_CACHE.get("shape"):
                    return ill
            except Exception:
                pass
        return None

    return None


class LunaSafeHandler(SimpleHTTPRequestHandler):
    # HTTP/1.1 keep-alive: all response paths set Content-Length, so browsers
    # reuse the connection instead of paying a TCP handshake per asset.
    protocol_version = "HTTP/1.1"
    """Handles REST API and static web content for LunaSafe Mission Control."""

    def __init__(self, *args, **kwargs):
        # Serve files from project directory or web/
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        # Root route: serve web/index.html
        if path in ("/", "/index.html"):
            self.serve_file(ROOT_DIR / "web" / "index.html", "text/html; charset=utf-8")
            return
        elif path == "/favicon.ico" or path == "/favicon.svg":
            self.serve_favicon()
            return
        elif path == "/styles.css":
            self.serve_file(ROOT_DIR / "web" / "styles.css", "text/css; charset=utf-8",
                            cache="public, max-age=60, must-revalidate")
            return
        elif path == "/app.js":
            self.serve_file(ROOT_DIR / "web" / "app.js", "application/javascript; charset=utf-8",
                            cache="public, max-age=60, must-revalidate")
            return
        elif path == "/hazard_core.js":
            self.serve_file(ROOT_DIR / "web" / "hazard_core.js", "application/javascript; charset=utf-8",
                            cache="public, max-age=60, must-revalidate")
            return
        elif path == "/worker.js":
            self.serve_file(ROOT_DIR / "web" / "worker.js", "application/javascript; charset=utf-8",
                            cache="public, max-age=60, must-revalidate")
            return
        elif path == "/lunar_moon.js":
            self.serve_file(ROOT_DIR / "web" / "lunar_moon.js", "application/javascript; charset=utf-8",
                            cache="public, max-age=60, must-revalidate")
            return

        # Health & Status API Routes
        if path == "/health" or path == "/api/health":
            self.handle_api_health()
            return
        elif path == "/api/status":
            self.handle_api_status()
            return
        elif path == "/api/data":
            self.handle_api_data(urllib.parse.parse_qs(url.query))
            return
        elif path == "/api/logs":
            self.handle_api_logs()
            return
        elif path == "/api/download-lola-status":
            self.send_json(DOWNLOAD_STATUS)
            return
        elif path == "/api/psr-validation":
            self.handle_api_psr_validation()
            return
        elif path == "/api/sites":
            self.handle_api_sites()
            return
        elif path == "/api/site-preview":
            self.handle_api_site_preview(urllib.parse.parse_qs(url.query))
            return
        elif path == "/api/data-sources":
            self.handle_api_data_sources()
            return
        elif path == "/api/psr-targets":
            self.handle_api_psr_targets()
            return
        elif path == "/api/rover-route":
            self.handle_api_rover_route()
            return
        elif path == "/api/regions":
            self.handle_api_regions()
            return
        elif path.startswith("/api/tiles/"):
            self.handle_api_tile(path[len("/api/tiles/"):])
            return
        elif path == "/api/illumination-time":
            self.handle_api_illumination_time(binary=False)
            return
        elif path == "/api/illumination-time.bin":
            self.handle_api_illumination_time(binary=True)
            return
        elif path.startswith("/api/download/"):
            filename = path.replace("/api/download/", "")
            self.handle_api_download(filename)
            return
        elif path == "/api/artifacts":
            self.handle_api_artifacts()
            return

        elif path.startswith("/vendor/"):
            rel_path = path.lstrip("/")
            file_path = ROOT_DIR / "web" / rel_path
            if file_path.exists() and file_path.is_file():
                mime, _ = mimetypes.guess_type(str(file_path))
                self.serve_file(file_path, mime or "application/javascript",
                                cache="public, max-age=86400, must-revalidate")
                return

        elif path.startswith("/assets/") or path.startswith("/web/assets/"):
            rel = path.replace("/web/assets/", "").replace("/assets/", "")
            file_path = ROOT_DIR / "web" / "assets" / rel
            if not (file_path.exists() and file_path.is_file()):
                file_path = ROOT_DIR / "assets" / rel
            if file_path.exists() and file_path.is_file():
                mime, _ = mimetypes.guess_type(str(file_path))
                if file_path.suffix.lower() == ".glb":
                    mime = "model/gltf-binary"
                elif file_path.suffix.lower() == ".gltf":
                    mime = "model/gltf+json"
                self.serve_file(file_path, mime or "application/octet-stream",
                                cache="public, max-age=86400, must-revalidate")
                return

        # Direct outputs serving (images/maps/PDFs)
        if path.startswith("/outputs/"):
            rel_path = path.lstrip("/")
            file_path = ROOT_DIR / rel_path
            if file_path.exists() and file_path.is_file():
                mime, _ = mimetypes.guess_type(str(file_path))
                self.serve_file(file_path, mime or "application/octet-stream",
                                cache="public, max-age=60, must-revalidate")
                return

        # Fallback to standard file serving
        super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/api/run-pipeline":
            self.handle_api_run_pipeline()
        elif path == "/api/recalculate":
            self.handle_api_recalculate()
        elif path == "/api/audit":
            self.handle_api_audit()
        elif path == "/api/sites":
            self.handle_api_sites()
        elif path == "/api/select-site":
            self.handle_api_select_site()
        elif path == "/api/rover-route":
            self.handle_api_rover_route()
        elif path == "/api/artifacts/save-route":
            self.handle_api_artifacts_save_route()
        elif path == "/api/artifacts/upload":
            self.handle_api_artifacts_upload()
        elif path == "/api/download-lola":
            self.handle_api_download_lola()
        elif path == "/api/upload-raster":
            self.handle_api_upload_raster()
        elif path == "/api/validate-geotiff":
            self.handle_api_validate_geotiff()
        elif path == "/api/load-offline-demo":
            self.handle_api_load_offline_demo()
        else:
            self.send_error(404, "Endpoint not found")

    def serve_favicon(self):
        """Serves a small SVG mission-control favicon (avoids 404 noise)."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<rect width="32" height="32" rx="6" fill="#0b1220"/>'
            '<circle cx="16" cy="16" r="9" fill="#1f2b3d" stroke="#60a5fa" stroke-width="1.5"/>'
            '<circle cx="12.5" cy="13" r="1.6" fill="#334155"/>'
            '<circle cx="19" cy="18.5" r="1.2" fill="#334155"/>'
            '<circle cx="16.5" cy="9.5" r="1.0" fill="#334155"/>'
            '</svg>'
        ).encode("utf-8")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(svg)))
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            self.wfile.write(svg)
        except Exception:
            pass

    # --- Phase 5: compression, conditional requests, cache policy -------------
    _GZIP_TYPES = (
        "text/html", "text/css", "text/plain", "text/csv",
        "application/json", "application/javascript", "application/xml",
        "image/svg+xml",
    )
    _GZIP_CACHE = {}  # (path, mtime, size) -> gzip bytes; bounded below

    def _emit_bytes(self, content, content_type, cache, etag=None, gzip_key=None,
                    code=200, extra=None):
        """Sends framed bytes with gzip (when accepted) and optional ETag/304.

        Replaces hand-rolled response code so every static/JSON response gets:
        - Content-Encoding: gzip for text-like payloads > 1 KiB (big first-load win)
        - Vary: Accept-Encoding so proxies/browsers cache per-encoding
        - ETag + If-None-Match -> 304 Not Modified (zero-byte repeat loads)
        """
        base_ct = (content_type or "").split(";")[0].strip().lower()
        want_gzip = (
            base_ct in self._GZIP_TYPES
            and len(content) > 1024
            and "gzip" in (self.headers.get("Accept-Encoding") or "")
        )
        if etag and want_gzip:
            full_etag = etag[:-1] + "-gz\""
        else:
            full_etag = etag
        if code == 200 and full_etag:
            inm = self.headers.get("If-None-Match") or ""
            candidate_tags = [t.strip() for t in inm.split(",") if t.strip()]
            if full_etag in candidate_tags or etag in candidate_tags:
                try:
                    self.send_response(304)
                    self.send_header("ETag", full_etag)
                    self.send_header("Cache-Control", cache)
                    self.send_header("Vary", "Accept-Encoding")
                    self.end_headers()
                except Exception:
                    pass
                return
        body = content
        if want_gzip:
            gz = self._GZIP_CACHE.get(gzip_key) if gzip_key else None
            if gz is None:
                gz = gzip.compress(content, 6)
                if gzip_key:
                    if len(self._GZIP_CACHE) > 64:
                        self._GZIP_CACHE.clear()
                    self._GZIP_CACHE[gzip_key] = gz
            body = gz
        try:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            if full_etag:
                self.send_header("ETag", full_etag)
            if want_gzip:
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
            for hk, hv in (extra or {}).items():
                self.send_header(hk, hv)
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_error(500, f"Error sending response: {e}")

    def serve_file(self, file_path: Path, content_type: str,
                   cache="no-cache, must-revalidate"):
        if not file_path.exists():
            self.send_error(404, f"File not found: {file_path.name}")
            return
        try:
            st = file_path.stat()
            with open(file_path, "rb") as f:
                content = f.read()
            etag = 'W/"%x-%x"' % (int(st.st_mtime), st.st_size)
            gzip_key = (str(file_path), int(st.st_mtime), int(st.st_size))
            self._emit_bytes(content, content_type, cache, etag=etag, gzip_key=gzip_key)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def send_json(self, data, code=200):
        body = json.dumps(data).encode("utf-8")
        self._emit_bytes(body, "application/json", "no-cache", code=code,
                         extra={"Access-Control-Allow-Origin": "*"})

    def read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                return {}
            raw_data = self.wfile if False else self.rfile.read(content_length)
            return json.loads(raw_data.decode("utf-8"))
        except Exception:
            return {}

    def handle_api_health(self):
        state = "running" if PIPELINE_RUNNING else "connected"
        if RASTER_CACHE.get("loaded"):
            dataset = "lola" if RASTER_CACHE["dataset_id"] == "lola_crop" else str(RASTER_CACHE.get("dataset_id"))
        else:
            dataset = "unloaded"
        self.send_json({
            "status": state,
            "pipeline_running": PIPELINE_RUNNING,
            "active_dataset": dataset,
            "timestamp": time.time(),
        })

    def get_current_raster_metadata(self):
        """Reports metadata of the ACTIVELY LOADED dataset (not merely present input files)."""
        if RASTER_CACHE.get("loaded"):
            dem = RASTER_CACHE["dem"]
            ny, nx = dem.shape
            return {
                "dataset_name": RASTER_CACHE["dataset_name"],
                "source": "NASA Planetary Data System (LRO LOLA GDR)" if not RASTER_CACHE["is_synthetic"] else "Procedural Lunar Model",
                "crs": "Moon South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)",
                "pixel_size_m": round(float(RASTER_CACHE["pixel_size_m"]), 1),
                "grid_size": f"{nx} × {ny} px",
                "total_pixels": int(nx * ny),
                "nodata_val": -9999.0,
                "is_synthetic": bool(RASTER_CACHE["is_synthetic"]),
            }

        is_real = config.REAL_DEM_PATH.exists() and config.REAL_PSR_PATH.exists()
        dem_path = config.REAL_DEM_PATH if is_real else config.SYNTHETIC_DEM_PATH
        if not dem_path.exists():
            return {
                "dataset_name": "Synthetic Crater Topography (Demo Benchmark)",
                "source": "Synthetic Procedural Lunar Crater Model",
                "crs": "Moon South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)",
                "pixel_size_m": 20.0,
                "grid_size": "200 × 200 px",
                "total_pixels": 40000,
                "nodata_val": -9999.0,
                "is_synthetic": True,
            }
        try:
            info = io_utils.read_geotiff(dem_path)
            data = info["data"]
            ny, nx = data.shape
            px_x = abs(info.get("pixel_size_x", 20.0 if not is_real else 240.0))
            nodata_val = info.get("nodata")
            if nodata_val is None:
                nodata_val = -9999.0
            return {
                "dataset_name": "Real NASA LRO LOLA DEM (80°S – 90°S)" if is_real else "Synthetic Crater Topography (Demo Benchmark)",
                "source": "NASA Planetary Data System (LRO LOLA GDR)" if is_real else "Synthetic Procedural Lunar Crater Model",
                "crs": "Moon South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)",
                "pixel_size_m": round(float(px_x), 1),
                "grid_size": f"{nx} × {ny} px",
                "total_pixels": int(nx * ny),
                "nodata_val": float(nodata_val),
                "is_synthetic": not is_real,
            }
        except Exception:
            return {
                "dataset_name": "Real NASA LRO LOLA DEM" if is_real else "Synthetic Crater Topography",
                "source": "NASA PDS LOLA" if is_real else "Synthetic Demo",
                "crs": "Moon South Pole Polar Stereographic (IAU 2015)",
                "pixel_size_m": 240.0 if is_real else 20.0,
                "grid_size": "250 × 250 px" if is_real else "200 × 200 px",
                "total_pixels": 62500 if is_real else 40000,
                "nodata_val": -9999.0,
                "is_synthetic": not is_real,
            }

    def handle_api_status(self):
        # Honest provenance: report what the ACTIVE OUTPUTS actually contain,
        # not merely which input files exist on disk.
        if RASTER_CACHE.get("loaded"):
            active_dataset = RASTER_CACHE["dataset_name"]
            is_synthetic = bool(RASTER_CACHE["is_synthetic"])
        else:
            # Infer from the outputs grid before any cache load
            active_dataset = "OUTPUTS NOT LOADED"
            is_synthetic = True
            try:
                if config.OUTPUT_SLOPE_TIF.exists():
                    out_shape = io_utils.read_geotiff(config.OUTPUT_SLOPE_TIF)["data"].shape
                    if config.REAL_DEM_PATH.exists() and io_utils.read_geotiff(config.REAL_DEM_PATH)["data"].shape == out_shape:
                        active_dataset = "REAL NASA LRO LOLA (South Pole)"
                        is_synthetic = False
                    else:
                        active_dataset = "SYNTHETIC DEMO"
            except Exception:
                pass

        has_outputs = config.OUTPUT_HAZARD_CLASSES_TIF.exists() and config.OUTPUT_MAP_4PANEL_PNG.exists()
        raster_meta = self.get_current_raster_metadata()

        # Load real metrics from outputs/hazard_summary.csv if available
        summary_data = {}
        csv_path = config.OUTPUT_HAZARD_SUMMARY_CSV
        if csv_path.exists():
            try:
                import csv
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = row.get("class_name", "").lower()
                        summary_data[name] = {
                            "pixel_count": int(row.get("pixel_count", 0)),
                            "area_km2": float(row.get("area_km2", 0.0)),
                            "pct_valid_terrain": float(row.get("pct_valid_terrain", 0.0)),
                            "pct_total_raster": float(row.get("pct_total_raster", 0.0))
                        }
            except Exception:
                pass

        status = {
            "status": "ONLINE",
            "active_dataset": active_dataset,
            "is_synthetic": is_synthetic,
            "pipeline_running": PIPELINE_RUNNING,
            "crs": "Moon South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)",
            "has_outputs": has_outputs,
            "map_png_available": config.OUTPUT_MAP_4PANEL_PNG.exists(),
            "map_pdf_available": config.OUTPUT_MAP_4PANEL_PDF.exists(),
            "synthetic_ready": config.SYNTHETIC_DEM_PATH.exists(),
            "real_lola_ready": config.REAL_DEM_PATH.exists(),
            "inputs_available": {
                "real_lola_dem": config.REAL_DEM_PATH.exists(),
                "real_lola_psr": config.REAL_PSR_PATH.exists(),
                "synthetic": config.SYNTHETIC_DEM_PATH.exists(),
            },
            "cache_loaded": bool(RASTER_CACHE.get("loaded")),
            "summary_data": summary_data,
            "raster_metadata": raster_meta,
            "timestamp": time.time(),
        }
        self.send_json(status)

    def handle_api_data(self, query):
        """Raster bundle for the web UI.

        Phase 5: `?parts=core` omits the two large toggle-only rasters
        (illumination, boulder_hazard) so first paint parses ~33% less JSON;
        the frontend fetches the extras right after boot and merges them.
        The default (no param) keeps the full bundle for compatibility.
        """
        json_file = config.OUTPUT_DIR / "web_data.json"
        if not json_file.exists():
            # Export data bundle on the fly
            export_web_data.export_data_bundle()

        if not json_file.exists():
            self.send_error(500, "Unable to load or export raster web data bundle.")
            return

        st = json_file.stat()
        file_etag = 'W/"%x-%x"' % (int(st.st_mtime), st.st_size)
        parts = (query.get("parts") or [""])[0]
        raw = json_file.read_text(encoding="utf-8")
        # Strict JSON: browsers reject Python's non-standard NaN/Infinity literals.
        if "NaN" in raw or "Infinity" in raw:
            raw = re.sub(r"\bNaN\b|\b-Infinity\b|\bInfinity\b", "null", raw)

        if parts == "core":
            try:
                bundle = json.loads(raw)
            except ValueError:
                self.send_error(500, "Data bundle contains invalid JSON.")
                return
            for key in ("illumination", "boulder_hazard"):
                bundle.pop(key, None)
            bundle["deferred_parts"] = ["illumination", "boulder_hazard"]
            body = json.dumps(bundle, separators=(",", ":")).encode("utf-8")
            self._emit_bytes(body, "application/json; charset=utf-8",
                             "no-cache, must-revalidate", etag=file_etag,
                             gzip_key=("data-core", int(st.st_mtime), int(st.st_size)))
            return

        if parts == "extras":
            # Companion to parts=core: the deferred rasters fetched right after
            # first paint so the boot JSON parse stays small.
            try:
                bundle = json.loads(raw)
            except ValueError:
                self.send_error(500, "Data bundle contains invalid JSON.")
                return
            extras = {"status": "SUCCESS"}
            for key in ("illumination", "boulder_hazard", "boulder_points"):
                if key in bundle:
                    extras[key] = bundle[key]
            body = json.dumps(extras, separators=(",", ":")).encode("utf-8")
            self._emit_bytes(body, "application/json; charset=utf-8",
                             "no-cache, must-revalidate", etag=file_etag,
                             gzip_key=("data-extras", int(st.st_mtime), int(st.st_size)))
            return
        self._emit_bytes(raw.encode("utf-8"), "application/json; charset=utf-8",
                         "no-cache, must-revalidate", etag=file_etag,
                         gzip_key=("data-full", int(st.st_mtime), int(st.st_size)))

    def handle_api_logs(self):
        with PIPELINE_LOCK:
            data = {
                "running": PIPELINE_RUNNING,
                "logs": PIPELINE_LOGS[-150:],  # last 150 lines
                "total_lines": len(PIPELINE_LOGS),
            }
        self.send_json(data)

    def handle_api_run_pipeline(self):
        global PIPELINE_RUNNING
        with PIPELINE_LOCK:
            if PIPELINE_RUNNING:
                self.send_json({"status": "BUSY", "message": "Pipeline already running in background"}, 409)
                return
            PIPELINE_RUNNING = True
            PIPELINE_LOGS.clear()

        body = self.read_json_body()

        # Update config thresholds in memory if passed
        if "slope_safe_max" in body:
            config.SLOPE_SAFE_MAX = float(body["slope_safe_max"])
        if "slope_caution_max" in body:
            config.SLOPE_CAUTION_MAX = float(body["slope_caution_max"])
        if "slope_hard_unsafe" in body:
            config.SLOPE_HARD_UNSAFE_MIN = float(body["slope_hard_unsafe"])
        if "rough_safe_max" in body:
            config.ROUGHNESS_SAFE_MAX = float(body["rough_safe_max"])
        if "rough_caution_max" in body:
            config.ROUGHNESS_CAUTION_MAX = float(body["rough_caution_max"])
        if "rough_hard_unsafe" in body:
            config.ROUGHNESS_HARD_UNSAFE_MIN = float(body["rough_hard_unsafe"])
        if "weight_slope" in body:
            config.WEIGHT_SLOPE = float(body["weight_slope"])
        if "weight_roughness" in body:
            config.WEIGHT_ROUGHNESS = float(body["weight_roughness"])
        if "weight_shadow" in body:
            config.WEIGHT_SHADOW = float(body["weight_shadow"])
        if "landing_ellipse_radius_m" in body:
            config.LANDING_ELLIPSE_RADIUS_M = float(body["landing_ellipse_radius_m"])
        if "clearance_buffer_m" in body:
            config.LANDING_CLEARANCE_BUFFER_M = float(body["clearance_buffer_m"])

        # Default to REAL data when it is available (matches main.py CLI behavior).
        # The body may explicitly force the synthetic benchmark.
        real_available = config.REAL_DEM_PATH.exists() and config.REAL_PSR_PATH.exists()
        use_synthetic = bool(body.get("force_synthetic", not real_available))

        def worker():
            global PIPELINE_RUNNING, ACTIVE_SITE_ID
            try:
                cmd = [PYTHON_BIN, "main.py"]
                if use_synthetic:
                    cmd.append("--force-synthetic")

                process = subprocess.Popen(
                    cmd,
                    cwd=str(ROOT_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )

                for line in iter(process.stdout.readline, ""):
                    clean_line = line.strip()
                    if clean_line:
                        with PIPELINE_LOCK:
                            PIPELINE_LOGS.append(clean_line)

                process.stdout.close()
                process.wait()

                with PIPELINE_LOCK:
                    PIPELINE_LOGS.append(f"[Server] Pipeline finished with exit code {process.returncode}")

                # Refresh web_data.json and cache (main.py already exported an
                # explicit bundle; re-export with the SAME dataset for safety)
                dem_for_export = config.SYNTHETIC_DEM_PATH if use_synthetic else (
                    config.REAL_DEM_PATH if config.REAL_DEM_PATH.exists() else config.SYNTHETIC_DEM_PATH
                )
                export_web_data.export_data_bundle(dem_path=dem_for_export)
                load_raster_cache()

                # Synchronize the active site id with the regenerated outputs
                if RASTER_CACHE.get("loaded"):
                    ACTIVE_SITE_ID = RASTER_CACHE["dataset_id"]

            except Exception as ex:
                with PIPELINE_LOCK:
                    PIPELINE_LOGS.append(f"[Server ERROR] {ex}")
            finally:
                with PIPELINE_LOCK:
                    PIPELINE_RUNNING = False

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        self.send_json({"status": "STARTED", "message": "Pipeline initiated in background thread"})

    def handle_api_recalculate(self):
        """Instantaneous ~20ms in-memory recalculation."""
        body = self.read_json_body()

        if not RASTER_CACHE["loaded"]:
            loaded = load_raster_cache()
            if not loaded:
                self.send_json({"status": "ERROR", "message": "Raster cache not ready; run pipeline once."}, 400)
                return

        # Extract parameters
        slope_safe = float(body.get("slope_safe_max", config.SLOPE_SAFE_MAX))
        slope_caution = float(body.get("slope_caution_max", config.SLOPE_CAUTION_MAX))
        slope_hard = float(body.get("slope_hard_unsafe", config.SLOPE_HARD_UNSAFE_MIN))

        rough_safe = float(body.get("rough_safe_max", config.ROUGHNESS_SAFE_MAX))
        rough_caution = float(body.get("rough_caution_max", config.ROUGHNESS_CAUTION_MAX))
        rough_hard = float(body.get("rough_hard_unsafe", config.ROUGHNESS_HARD_UNSAFE_MIN))

        w_slope = float(body.get("weight_slope", config.WEIGHT_SLOPE))
        w_rough = float(body.get("weight_roughness", config.WEIGHT_ROUGHNESS))
        w_shadow = float(body.get("weight_shadow", config.WEIGHT_SHADOW))

        ellipse_radius = float(body.get("landing_ellipse_radius_m", config.LANDING_ELLIPSE_RADIUS_M))
        clearance_buf = float(body.get("clearance_buffer_m", config.LANDING_CLEARANCE_BUFFER_M))

        # Temporarily update config thresholds
        config.SLOPE_SAFE_MAX = slope_safe
        config.SLOPE_CAUTION_MAX = slope_caution
        config.SLOPE_HARD_UNSAFE_MIN = slope_hard
        config.ROUGHNESS_SAFE_MAX = rough_safe
        config.ROUGHNESS_CAUTION_MAX = rough_caution
        config.ROUGHNESS_HARD_UNSAFE_MIN = rough_hard
        config.WEIGHT_SLOPE = w_slope
        config.WEIGHT_ROUGHNESS = w_rough
        config.WEIGHT_SHADOW = w_shadow

        slope = RASTER_CACHE["slope"]
        roughness = RASTER_CACHE["roughness"]
        psr_mask = RASTER_CACHE["psr"]
        dem = RASTER_CACHE["dem"]
        transform = RASTER_CACHE["transform"]

        # 1. Deterministic classification
        hazard_classes, score_h = hazard.classify_hazard_surface(
            slope=slope,
            roughness=roughness,
            psr_mask=psr_mask,
            pixel_size_m=RASTER_CACHE.get("pixel_size_m"),
        )

        # 2. Area breakdown
        total_px = hazard_classes.size
        valid_px = int((hazard_classes != 0).sum())
        safe_px = int((hazard_classes == 1).sum())
        caution_px = int((hazard_classes == 2).sum())
        unsafe_px = int((hazard_classes == 3).sum())
        shadow_px = int((hazard_classes == 4).sum())
        nodata_px = int((hazard_classes == 0).sum())

        if transform is not None and abs(transform.a) > 0:
            px_size = abs(transform.a)
        else:
            px_size = config.SYNTHETIC_PIXEL_SIZE_M
        px_area_km2 = (px_size * px_size) / 1e6

        summary = {
            "safe": {"pixels": safe_px, "area_km2": round(safe_px * px_area_km2, 4), "pct": round(safe_px / max(valid_px, 1) * 100, 2)},
            "caution": {"pixels": caution_px, "area_km2": round(caution_px * px_area_km2, 4), "pct": round(caution_px / max(valid_px, 1) * 100, 2)},
            "unsafe": {"pixels": unsafe_px, "area_km2": round(unsafe_px * px_area_km2, 4), "pct": round(unsafe_px / max(valid_px, 1) * 100, 2)},
            "shadowed_unknown": {"pixels": shadow_px, "area_km2": round(shadow_px * px_area_km2, 4), "pct": round(shadow_px / max(valid_px, 1) * 100, 2)},
            "nodata": {"pixels": nodata_px, "area_km2": round(nodata_px * px_area_km2, 4), "pct": round(nodata_px / total_px * 100, 2)},
            "valid_pixels": valid_px,
            "total_pixels": total_px,
        }

        # 3. AI Landing Sites Re-evaluation
        ai_result = ml_recommender.recommend_landing_sites(
            hazard_classes=hazard_classes,
            dem_data=dem,
            slope_data=slope,
            roughness_data=roughness,
            psr_mask=psr_mask,
            transform=transform,
            ellipse_radius_m=ellipse_radius,
            clearance_buffer_m=clearance_buf,
            top_k=3,
            pixel_size_m=px_size,
        )

        # 4. Rule consistency verification
        audit_res = validate.verify_rule_consistency(
            hazard_classes=hazard_classes,
            slope=slope,
            roughness=roughness,
            psr_mask=psr_mask,
            score_h=score_h,
            pixel_size_m=px_size,
        )

        # 5. Sensitivity Analysis computation (bars at 5°, 10°, 15° and unsafe curve vs slope)
        # Roughness thresholds are resolution-scaled exactly like
        # classify_hazard_surface above (BUG-041: raw 20 m-reference values made
        # these charts degenerate at 240 m/px — nearly every pixel satisfies
        # roughness >= 5.0 m, which flattened the curve and equalized the bars).
        sens_px_m = RASTER_CACHE.get("pixel_size_m")
        if sens_px_m:
            sens_rt = config.scaled_roughness_thresholds(sens_px_m)
            rough_safe_eff = sens_rt["safe_max"]
            rough_hard_eff = sens_rt["hard_unsafe_min"]
        else:
            rough_safe_eff = rough_safe
            rough_hard_eff = rough_hard

        valid_mask = (slope != config.DEFAULT_NODATA_VALUE) & ~np.isnan(slope)
        sensitivity_bars = []
        for t in [5.0, 10.0, 15.0]:
            # t is the scenario's HARD-UNSAFE slope limit: each bar answers
            # "how would the class split look if slopes >= t were hard-Unsafe"
            # (bars[t].unsafe_km2 is then identical to the curve point at t).
            hard_ov = (slope >= t) | (roughness >= rough_hard_eff)
            uns = valid_mask & ((score_h >= config.SCORE_UNSAFE_MIN) | hard_ov)
            ps = (psr_mask == 1) & valid_mask & ~uns
            non_p = valid_mask & ~uns & ~(psr_mask == 1)
            sf = non_p & (score_h < config.SCORE_SAFE_MAX) & (slope < slope_safe) & (roughness < rough_safe_eff)
            ct = non_p & ~sf
            sensitivity_bars.append({
                "threshold": t,
                "safe_km2": round(float(np.sum(sf) * px_area_km2), 2),
                "caution_km2": round(float(np.sum(ct) * px_area_km2), 2),
                "unsafe_km2": round(float(np.sum(uns) * px_area_km2), 2),
                "shadow_km2": round(float(np.sum(ps) * px_area_km2), 2),
            })

        unsafe_curve = []
        for s_t in [3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0, 17.0, 20.0, 25.0]:
            u_mask = valid_mask & ((score_h >= config.SCORE_UNSAFE_MIN) | (slope >= s_t) | (roughness >= rough_hard_eff))
            unsafe_curve.append({
                "slope_deg": s_t,
                "unsafe_km2": round(float(np.sum(u_mask) * px_area_km2), 2),
                "unsafe_pct": round(float(np.sum(u_mask) / max(valid_px, 1) * 100), 1),
            })

        response = {
            "status": "SUCCESS",
            "summary": summary,
            "landing_sites": ai_result.get("top_sites", []),
            "hazard_classes_flat": [int(v) for v in hazard_classes.flatten()],
            "rule_audit": {
                "is_consistent": audit_res["is_consistent"],
                "total_violations": audit_res["total_violations"],
                "violations": audit_res["detailed_violations"],
            },
            "sensitivity": {
                "bars": sensitivity_bars,
                "curve": unsafe_curve,
            },
        }
        tile_pyramid.TILE_CACHE.clear()
        self.send_json(response)

    def handle_api_audit(self):
        if not RASTER_CACHE["loaded"]:
            load_raster_cache()

        if not RASTER_CACHE["loaded"]:
            self.send_json({"status": "ERROR", "message": "Data not loaded"}, 400)
            return

        hazard_classes, score_h = hazard.classify_hazard_surface(
            slope=RASTER_CACHE["slope"],
            roughness=RASTER_CACHE["roughness"],
            psr_mask=RASTER_CACHE["psr"],
            pixel_size_m=RASTER_CACHE.get("pixel_size_m"),
        )

        audit = validate.verify_rule_consistency(
            hazard_classes=hazard_classes,
            slope=RASTER_CACHE["slope"],
            roughness=RASTER_CACHE["roughness"],
            psr_mask=RASTER_CACHE["psr"],
            score_h=score_h,
            pixel_size_m=RASTER_CACHE.get("pixel_size_m"),
        )

        detailed = audit["detailed_violations"]
        rough_safe_applied = audit.get("rough_safe_max_applied", config.ROUGHNESS_SAFE_MAX)
        rough_hard_applied = audit.get("rough_hard_unsafe_applied", config.ROUGHNESS_HARD_UNSAFE_MIN)
        rules_meta = [
            ("Rule 1", "Safe slope limit: slope must be strictly below safe threshold (< 5.0°)", detailed.get("rule1_safe_slope_exceeded", 0)),
            ("Rule 2", f"Safe roughness limit: surface micro-relief must be below {rough_safe_applied:.1f} m (resolution-scaled)", detailed.get("rule2_safe_roughness_exceeded", 0)),
            ("Rule 3", "Safe hazard score limit: composite screening score H < 0.25", detailed.get("rule3_safe_score_exceeded", 0)),
            ("Rule 4", "Safe PSR exclusion: safe landing zone strictly outside permanent shadow", detailed.get("rule4_safe_pixel_in_psr", detailed.get("rule4_safe_in_psr", 0))),
            ("Rule 5", "Hard slope override: steep terrain (>= 15°) strictly classified as Unsafe (Class 3)", detailed.get("rule5_hard_slope_not_unsafe", 0)),
            ("Rule 6", f"Hard roughness override: high roughness (>= {rough_hard_applied:.1f} m, resolution-scaled) strictly classified as Unsafe (Class 3)", detailed.get("rule6_hard_roughness_not_unsafe", 0)),
            ("Rule 7", "High score override: multi-criteria index H >= 0.60 strictly classified as Unsafe (Class 3)", detailed.get("rule7_high_score_not_unsafe", 0)),
            ("Rule 8", "PSR conservation: cold-trap shadow pixels strictly Class 4 or 3, never Safe or Caution", detailed.get("rule8_psr_pixel_marked_safe_or_caution", 0)),
            ("Rule 9", "NoData integrity: missing altimetry pixels strictly Class 0, never classified as surface", detailed.get("rule9_nodata_misclassified_as_surface", 0)),
        ]
        rule_results = [
            {
                "rule_id": r_id,
                "description": desc,
                "violations": v_count,
                "passed": v_count == 0,
            }
            for r_id, desc, v_count in rules_meta
        ]

        self.send_json({
            "status": "PASSED" if audit["total_violations"] == 0 else "FAILED",
            "total_violations": audit["total_violations"],
            "rule_results": rule_results,
            "total_pixels": audit.get("audited_pixels", hazard_classes.size),
            "valid_pixels": audit.get("valid_surface_pixels", int(np.sum(hazard_classes != 0))),
        })

    def handle_api_download_lola(self):
        if DOWNLOAD_STATUS["running"]:
            self.send_json({"status": "BUSY", "message": "Ingestion already in progress"}, 409)
            return

        def download_worker():
            DOWNLOAD_STATUS["running"] = True
            DOWNLOAD_STATUS["progress"] = 0
            DOWNLOAD_STATUS["message"] = "Preparing NASA LRO LOLA South Pole dataset..."
            DOWNLOAD_STATUS["success"] = False

            try:
                # 1. If GeoTIFFs already exist, finish immediately
                if config.REAL_DEM_PATH.exists() and config.REAL_PSR_PATH.exists():
                    DOWNLOAD_STATUS["progress"] = 100
                    DOWNLOAD_STATUS["message"] = "NASA LRO LOLA South Pole dataset ready (60 km × 60 km, 240 m/px)!"
                    DOWNLOAD_STATUS["success"] = True
                    return

                # 2. If local JP2 archive is present, convert directly
                jp2_path = config.DATA_DIR / 'ldem_75s_240m.jp2'
                if jp2_path.exists() and jp2_path.stat().st_size > 5000000:
                    DOWNLOAD_STATUS["progress"] = 60
                    DOWNLOAD_STATUS["message"] = "Converting NASA PDS polar altimetry to GeoTIFF..."
                    import prepare_lola_dataset
                    prepare_lola_dataset.convert_real_lola_to_geotiff()
                    DOWNLOAD_STATUS["progress"] = 100
                    DOWNLOAD_STATUS["message"] = "NASA LRO LOLA South Pole dataset ready (60 km × 60 km, 240 m/px)!"
                    DOWNLOAD_STATUS["success"] = True
                    return

                # 3. Download from verified NASA PDS archive
                pds_url = "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/ldem_75s_240m.jp2"
                DOWNLOAD_STATUS["message"] = "Connecting to NASA PDS LOLA archive..."
                req = urllib.request.Request(pds_url, headers={"User-Agent": "OrbisLuna-Downloader/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp, open(jp2_path, "wb") as out:
                    total_size = int(resp.headers.get("Content-Length", 10768000))
                    downloaded = 0
                    block_size = 64 * 1024
                    while True:
                        buf = resp.read(block_size)
                        if not buf:
                            break
                        out.write(buf)
                        downloaded += len(buf)
                        pct = int(downloaded / total_size * 80)
                        DOWNLOAD_STATUS["progress"] = min(pct, 80)
                        DOWNLOAD_STATUS["message"] = f"Downloaded {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB"

                # 4. Convert downloaded JP2 to GeoTIFFs
                DOWNLOAD_STATUS["progress"] = 90
                DOWNLOAD_STATUS["message"] = "Georeferencing into Lunar Polar Stereographic GeoTIFF..."
                import prepare_lola_dataset
                prepare_lola_dataset.convert_real_lola_to_geotiff()

                DOWNLOAD_STATUS["progress"] = 100
                DOWNLOAD_STATUS["message"] = "NASA LRO LOLA South Pole dataset ready (60 km × 60 km, 240 m/px)!"
                DOWNLOAD_STATUS["success"] = True

            except Exception as e:
                DOWNLOAD_STATUS["message"] = f"Ingestion error: {e}"
                DOWNLOAD_STATUS["success"] = False
            finally:
                DOWNLOAD_STATUS["running"] = False

        threading.Thread(target=download_worker, daemon=True).start()
        self.send_json({"status": "STARTED", "message": "NASA LRO LOLA ingestion initiated"})

    def handle_api_upload_raster(self):
        """Allows uploading custom DEM or PSR GeoTIFF."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(content_length)
            dest = config.DATA_DIR / "custom_upload.tif"
            with open(dest, "wb") as f:
                f.write(data)
            self.send_json({"status": "SUCCESS", "filename": dest.name, "path": str(dest)})
        except Exception as e:
            self.send_json({"status": "ERROR", "message": str(e)}, 500)

    def handle_api_psr_validation(self):
        """Returns truthful PSR metrics if independent reference is loaded, or an explicit truthful explanation if not loaded."""
        url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(url.query)
        benchmark_mode = "benchmark" in qs

        ref_path = config.DATA_DIR / "independent_psr_reference.tif"
        candidate_path = config.OUTPUT_PSR_BINARY_TIF
        if not candidate_path.exists():
            candidate_path = config.REAL_PSR_PATH if config.REAL_PSR_PATH.exists() else config.SYNTHETIC_PSR_PATH

        if benchmark_mode:
            if candidate_path.exists():
                c_info = io_utils.read_geotiff(candidate_path)
                c_shape = c_info["data"].shape
                if config.REAL_PSR_PATH.exists() and io_utils.read_geotiff(config.REAL_PSR_PATH)["data"].shape == c_shape:
                    ref_path = config.REAL_PSR_PATH
                else:
                    ref_path = config.SYNTHETIC_PSR_PATH
            else:
                ref_path = config.REAL_PSR_PATH if config.REAL_PSR_PATH.exists() else config.SYNTHETIC_PSR_PATH

        if ref_path.exists() and candidate_path.exists():
            try:
                c_info = io_utils.read_geotiff(candidate_path)
                r_info = io_utils.read_geotiff(ref_path)
                is_real_ref = "lola" in str(ref_path).lower()
                ref_label = ("NASA PDS LOLA South Pole PSR Baseline (Reference Benchmark)" if is_real_ref else "Synthetic Lunar Model Ground Truth (Benchmark)") if benchmark_mode else "Independent Ground-Truth Altimetry Catalog"
                metrics = validate.compute_psr_metrics(
                    c_info["data"],
                    r_info["data"],
                    reference_name=ref_label,
                    is_independent=not benchmark_mode,
                )
                metrics["reference_loaded"] = True
                metrics["status"] = "LOADED"
                self.send_json(metrics)
                return
            except Exception as e:
                print(f"[PSR Validation Error] {e}")

        # If no independent reference is loaded
        self.send_json({
            "status": "UNLOADED",
            "reference_loaded": False,
            "reference_source": "None",
            "provenance_note": (
                "No independent ground-truth reference loaded. The current PSR layer is derived from "
                "topographic depression thresholding and solar grazing ray interception. Ground-truth "
                "polar ice deposit boundaries require in-situ rover prospecting (VIPER/Artemis) or "
                "validated laser reflectometry ground-truth catalogs. (Rule: Never show invented accuracy numbers)."
            ),
            "precision": None,
            "recall": None,
            "iou": None,
            "f1_score": None,
        })

    def handle_api_validate_geotiff(self):
        """Validates uploaded or target GeoTIFF files: checks CRS, dimensions, pixel size, NoData value, and grid alignment."""
        body = self.read_json_body()
        file_type = body.get("type", "dem")
        filename = body.get("filename", "")

        target = config.DATA_DIR / filename if filename else (config.REAL_DEM_PATH if config.REAL_DEM_PATH.exists() else config.SYNTHETIC_DEM_PATH)
        if file_type == "psr":
            target = config.DATA_DIR / filename if filename else (config.REAL_PSR_PATH if config.REAL_PSR_PATH.exists() else config.SYNTHETIC_PSR_PATH)

        try:
            info = io_utils.read_geotiff(target)
            data = info["data"]
            ny, nx = data.shape
            px_x = abs(info.get("pixel_size_x", 0.0))
            nodata = info.get("nodata", -9999.0)

            valid_pixels = data[data != nodata] if nodata is not None else data
            valid_pixels = valid_pixels[~np.isnan(valid_pixels)] if np.issubdtype(data.dtype, np.floating) else valid_pixels
            min_val = float(np.min(valid_pixels)) if valid_pixels.size > 0 else 0.0
            max_val = float(np.max(valid_pixels)) if valid_pixels.size > 0 else 0.0

            # --- REAL validation checks (no fabricated pass results) ---
            crs_str = str(info["crs"]) if info["crs"] is not None else ""

            # 1. Lunar CRS: must be defined and must NOT be an Earth datum
            earth_signatures = ["EPSG:4326", "EPSG:3857", "EPSG:4269", "WGS 84", "WGS_1984", "NAD83", "ETRS89"]
            crs_is_earth = any(sig.lower() in crs_str.lower() for sig in earth_signatures)
            crs_is_lunar = ("1737400" in crs_str) or ("moon" in crs_str.lower())
            crs_valid = (len(crs_str) > 0) and (not crs_is_earth) and crs_is_lunar

            # 2. Georeferencing: transform must not be identity (pixel-space)
            transform = info.get("transform")
            try:
                georef_valid = transform is not None and not (
                    transform.a == 1.0 and transform.e == -1.0 and transform.c == 0.0 and transform.f == 0.0
                ) and abs(transform.a) > 0
            except Exception:
                georef_valid = False

            # 3. NoData definition
            nodata_defined = info.get("nodata") is not None

            checks = {
                "file_readable": True,
                "filename": target.name,
                "dimensions": f"{nx} × {ny} pixels",
                "pixel_size": f"{px_x:.1f} m/px" if px_x > 0 else "UNDEFINED",
                "crs_valid": bool(crs_valid),
                "crs_name": (
                    "Moon South Pole Polar Stereographic (IAU 2015 Sphere R=1,737,400m)" if crs_valid
                    else ("Earth datum detected — REJECTED for lunar data" if crs_is_earth else "Missing or non-lunar CRS")
                ),
                "georeferenced": bool(georef_valid),
                "nodata_defined": bool(nodata_defined),
                "nodata_value": float(nodata) if nodata is not None else -9999.0,
                "min_val": round(min_val, 2),
                "max_val": round(max_val, 2),
                "all_passed": bool(crs_valid and georef_valid and nodata_defined and px_x > 0),
            }
            self.send_json({"status": "SUCCESS", "checks": checks})
        except Exception as e:
            self.send_json({"status": "ERROR", "message": str(e)}, 400)

    def handle_api_load_offline_demo(self):
        """Switches to precomputed offline demo mode directly loading outputs/ without long processing."""
        try:
            load_raster_cache()
            self.send_json({
                "status": "SUCCESS",
                "message": "Offline demo dataset loaded directly from outputs/. All telemetry, 2D layers, and 3D terrain active.",
                "is_offline": True,
            })
        except Exception as e:
            self.send_json({"status": "ERROR", "message": str(e)}, 500)

    def handle_api_download(self, filename: str):
        """Serves output files or bundles Shapefile / Mission Report."""
        out_dir = config.OUTPUT_DIR

        if filename == "mission_report.pdf":
            import mission_report
            report_path = out_dir / "mission_report.pdf"
            # Regenerate when missing OR older than any key pipeline input,
            # so the PDF always matches the active dataset (never stale).
            input_paths = [
                config.OUTPUT_HAZARD_CLASSES_TIF,
                config.OUTPUT_HAZARD_SUMMARY_CSV,
                config.OUTPUT_MAP_4PANEL_PNG,
            ]
            needs_regen = not report_path.exists()
            if not needs_regen:
                report_mtime = report_path.stat().st_mtime
                needs_regen = any(
                    p.exists() and p.stat().st_mtime > report_mtime
                    for p in input_paths
                )
            if needs_regen:
                mission_report.generate_pdf_mission_report(report_path)
            self.send_file_attachment(report_path, "application/pdf")
            return

        if filename == "psr_shapefile.zip":
            # Bundle all Shapefile components into a ZIP
            zip_path = out_dir / "psr_polygons_bundle.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                    f = out_dir / f"psr_polygons{ext}"
                    if f.exists():
                        zf.write(f, f.name)
            self.send_file_attachment(zip_path, "application/zip")
            return

        target = out_dir / filename
        if not target.exists():
            self.send_error(404, f"Requested download artifact not found: {filename}")
            return

        mime, _ = mimetypes.guess_type(str(target))
        self.send_file_attachment(target, mime or "application/octet-stream")

    def handle_api_artifacts(self):
        """Serves the Artifact Hub manifest (scans outputs/ + saved_routes/, persists artifacts.json)."""
        try:
            manifest = build_artifacts_manifest()
            self.send_json(manifest)
        except Exception as e:
            print(f"[Artifacts ERROR] {e}")
            self.send_json({"status": "ERROR", "message": f"Failed to build artifact manifest: {e}", "artifacts": []}, 500)

    def handle_api_artifacts_save_route(self):
        """Persists the currently computed Rover Traverse route into outputs/saved_routes/ for the Hub."""
        body = self.read_json_body()
        route = body.get("route")
        if not isinstance(route, dict) or not route.get("waypoints"):
            self.send_json({"status": "ERROR", "message": "No route payload with waypoints supplied."}, 400)
            return
        if route.get("status") != "SUCCESS":
            self.send_json({"status": "ERROR", "message": "Only SUCCESS routes can be saved to the Artifact Hub."}, 400)
            return
        try:
            ARTIFACT_SAVED_ROUTES_DIR.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            safe_label = str(body.get("label") or "traverse").strip().replace(" ", "_")
            safe_label = "".join(c for c in safe_label if c.isalnum() or c in ("_", "-"))[:48] or "traverse"
            fname = f"route_{safe_label}_{ts}.json"
            dest = ARTIFACT_SAVED_ROUTES_DIR / fname
            payload = dict(route)
            payload["_hub"] = {
                "title": str(body.get("title") or f"Saved Rover Traverse — {safe_label}"),
                "label": safe_label,
                "dataset": _artifact_active_dataset_label(),
                "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "tags": ["rover", "route", "traverse", "json", "saved"],
                "waypoint_count": len(route.get("waypoints", [])),
            }
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            entry = _artifact_entry_for(dest, payload["_hub"]["dataset"], saved=True)
            if entry:
                entry["title"] = payload["_hub"]["title"]
                entry["tags"] = payload["_hub"]["tags"]
            self.send_json({"status": "SUCCESS", "filename": fname, "entry": entry})
        except Exception as e:
            print(f"[Artifacts Save Route ERROR] {e}")
            self.send_json({"status": "ERROR", "message": f"Failed to save route: {e}"}, 500)

    def handle_api_artifacts_upload(self):
        """Accepts a client-uploaded artifact file (base64 JSON) into outputs/saved_routes/."""
        body = self.read_json_body()
        filename = str(body.get("filename") or "").strip()
        b64 = body.get("content_b64")
        if not filename or not b64:
            self.send_json({"status": "ERROR", "message": "filename and content_b64 are required."}, 400)
            return
        # Sanitize: no path separators, no quotes/HTML-breaking chars, reasonable extension set
        filename = filename.replace("\\", "/").split("/")[-1]
        filename = "".join(c for c in filename if c.isalnum() or c in ("_", "-", ".", " ", "(", ")"))
        allowed = (".json", ".geojson", ".csv", ".txt", ".pdf", ".png")
        if not filename.lower().endswith(allowed):
            self.send_json({"status": "ERROR", "message": f"Upload not allowed for extension of '{filename}'."}, 400)
            return
        try:
            import base64 as b64mod
            data = b64mod.b64decode(b64)
            if len(data) > 20 * 1024 * 1024:
                self.send_json({"status": "ERROR", "message": "Upload exceeds 20 MB limit."}, 400)
                return
            ARTIFACT_SAVED_ROUTES_DIR.mkdir(parents=True, exist_ok=True)
            dest = ARTIFACT_SAVED_ROUTES_DIR / filename
            # avoid overwrite
            stem, suffix = dest.stem, dest.suffix
            n = 1
            while dest.exists():
                dest = ARTIFACT_SAVED_ROUTES_DIR / f"{stem}_{n}{suffix}"
                n += 1
            dest.write_bytes(data)
            entry = _artifact_entry_for(dest, _artifact_active_dataset_label(), saved=True)
            self.send_json({"status": "SUCCESS", "filename": dest.name, "entry": entry})
        except Exception as e:
            self.send_json({"status": "ERROR", "message": f"Upload failed: {e}"}, 500)

    def send_file_attachment(self, file_path: Path, content_type: str):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Content-Disposition", f'attachment; filename="{file_path.name}"')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading artifact file: {e}")

    def handle_api_sites(self):
        """Returns catalog of available lunar sites and active site ID."""
        self.send_json({
            "status": "SUCCESS",
            "active_site": ACTIVE_SITE_ID,
            "sites": lunar_catalog.get_catalog_summary(),
        })

    def handle_api_site_preview(self, query):
        """Returns 3D mesh topography and reconnaissance metadata for a specified lunar site."""
        site_id = (query.get("site_id") or [ACTIVE_SITE_ID])[0].strip()

        # Resolve against catalog
        site_meta = lunar_catalog.LUNAR_SITES.get(site_id)
        resolved_id = site_id
        if not site_meta:
            for k, v in lunar_catalog.LUNAR_SITES.items():
                if k.lower() == site_id.lower() or v.get("name", "").lower() == site_id.lower() or site_id.lower() in v.get("name", "").lower():
                    resolved_id = k
                    site_meta = v
                    break
        if not site_meta:
            resolved_id = ACTIVE_SITE_ID if ACTIVE_SITE_ID in lunar_catalog.LUNAR_SITES else "lola_crop"
            site_meta = lunar_catalog.LUNAR_SITES.get(resolved_id, {})

        if not hasattr(self, "_site_preview_cache"):
            self._site_preview_cache = {}

        if resolved_id in self._site_preview_cache:
            cached = dict(self._site_preview_cache[resolved_id])
            cached["is_active"] = (resolved_id == ACTIVE_SITE_ID)
            self.send_json(cached)
            return

        try:
            dem, psr, transform, crs = lunar_catalog.generate_site_terrain(resolved_id)
            stride = 1
            if dem.shape[0] > 70:
                stride = max(1, dem.shape[0] // 64)
                dem = dem[::stride, ::stride]
                if psr is not None:
                    psr = psr[::stride, ::stride]

            valid_mask = (dem != config.DEFAULT_NODATA_VALUE) & ~np.isnan(dem)
            valid_elev = dem[valid_mask] if np.any(valid_mask) else np.array([0.0], dtype=np.float32)
            min_e = float(valid_elev.min())
            max_e = float(valid_elev.max())
            clean_dem = np.where(valid_mask, dem, min_e).round(1).tolist()
            psr_pct = float((psr > 0).mean() * 100.0) if psr is not None else 0.0

            cell_spacing_m = float(abs(transform[0])) * stride if transform else 40.0 * stride
            dy, dx = np.gradient(np.where(valid_mask, dem, min_e))
            slope_deg = np.degrees(np.arctan(np.sqrt(dx*dx + dy*dy) / max(cell_spacing_m, 1.0)))
            mean_slope = float(slope_deg.mean())

            clean_psr = (psr > 0).astype(int).tolist() if psr is not None else [[0]*len(clean_dem[0]) for _ in range(len(clean_dem))]

            result = {
                "status": "SUCCESS",
                "site_id": resolved_id,
                "name": site_meta.get("name", resolved_id),
                "category": site_meta.get("category", "Artemis Exploration Target"),
                "description": site_meta.get("description", "Calibrated lunar south polar terrain model with authentic topography and cold-trap distribution."),
                "scientific_value": site_meta.get("scientific_value", "High-priority lunar volatile exploration target with strategic line-of-sight communications."),
                "terrain_type": site_meta.get("terrain_type", "Complex impact crater and polar ridge terrain"),
                "center_lat": site_meta.get("center_lat", -89.9),
                "center_lon": site_meta.get("center_lon", 0.0),
                "diameter_km": site_meta.get("diameter_km", 25.0),
                "depth_m": round(max_e - min_e, 1),
                "rim_elevation_m": round(max_e, 1),
                "floor_elevation_m": round(min_e, 1),
                "min_elev": round(min_e, 1),
                "max_elev": round(max_e, 1),
                "relief_m": round(max_e - min_e, 1),
                "mean_slope_deg": round(mean_slope, 1),
                "psr_pct": round(psr_pct, 1),
                "grid_w": len(clean_dem[0]) if clean_dem else 0,
                "grid_h": len(clean_dem),
                "dem": clean_dem,
                "psr": clean_psr,
                "is_synthetic": (resolved_id == "synthetic"),
                "source": "NASA Planetary Data System (LRO LOLA 240m/px)" if resolved_id != "synthetic" else "Procedural Benchmark Model",
                "is_active": (resolved_id == ACTIVE_SITE_ID)
            }
            self._site_preview_cache[resolved_id] = result
            self.send_json(result)
        except Exception as e:
            self.send_error(500, f"Error generating site preview: {e}")

    def handle_api_data_sources(self):
        """Returns the public dataset registry (config.PUBLIC_DATASETS) with live local-file status."""
        import hashlib as _hashlib

        def _sha256_short(path):
            try:
                h = _hashlib.sha256()
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                return h.hexdigest()[:16] + "..."
            except Exception:
                return None

        datasets = []
        for ds in config.PUBLIC_DATASETS:
            entry = dict(ds)
            local = ds.get("local_path")
            if local:
                p = Path(local) if Path(local).is_absolute() else config.BASE_DIR / local
                entry["local_exists"] = p.exists()
                if p.exists():
                    entry["local_size_bytes"] = p.stat().st_size
                    entry["sha256_short"] = _sha256_short(p)
                    # Honest status: file present on disk
                    entry["status"] = "downloaded"
                else:
                    entry["local_exists"] = False
                    entry["status"] = ds.get("status", "available")
            else:
                entry["local_exists"] = False
            datasets.append(entry)

        # Artemis III official region metadata for the panel
        artemis_regions = [
            {
                "site_id": rid,
                "name": r["name"],
                "center_lat": r["center_lat"],
                "center_lon": r["center_lon"],
            }
            for rid, r in config.ARTEMIS_III_REGIONS.items()
        ]

        self.send_json({
            "status": "SUCCESS",
            "datasets": datasets,
            "artemis_iii_regions": artemis_regions,
            "active_site": ACTIVE_SITE_ID,
            "hazard_thresholds": {
                "slope_safe_max_deg": config.SLOPE_SAFE_MAX,
                "slope_caution_max_deg": config.SLOPE_CAUTION_MAX,
                "slope_hard_unsafe_deg": config.SLOPE_HARD_UNSAFE_MIN,
                "note": "Roughness thresholds are resolution-scaled (config.scaled_roughness_thresholds); see README Data Sources section.",
            },
        })

    def handle_api_regions(self):
        """Artemis III official candidate regions for the Phase 4 regions panel/map."""
        from lunar_catalog import LUNAR_SITES

        regions = []
        for rid, r in config.ARTEMIS_III_REGIONS.items():
            site = LUNAR_SITES.get(rid, {})
            regions.append({
                "site_id": rid,
                "name": r["name"],
                "center_lat": r["center_lat"],
                "center_lon": r["center_lon"],
                "in_catalog": rid in LUNAR_SITES,
                "is_real_data": bool(site.get("is_real_data", rid.startswith("artemis_"))),
                "selected": rid == ACTIVE_SITE_ID,
            })
        self.send_json({
            "status": "SUCCESS",
            "regions": regions,
            "geojson_url": "/outputs/web/artemis_iii_regions.geojson",
            "source": "Official Artemis III candidate regions — Wueller et al. 2026, Table A1 CLS coordinate means",
        })

    def handle_api_tile(self, rel):
        """Serves multi-scale tile pyramid metadata and 256x256 float32 XYZ tiles.

        URL shapes:
          /api/tiles/<layer>/meta (or meta.json) -> {tileSize, maxZ, width, height, dtype, tiles_x, tiles_y}
          /api/tiles/<layer>/<z>/<x>/<y> -> 256x256 raw float32 bytes with edge NoData padding
        """
        parts = [p for p in rel.split("/") if p]

        if len(parts) == 2 and parts[1] in ("meta", "meta.json"):
            layer = parts[0].lower()
            if layer not in tile_pyramid.ALLOWED_LAYERS:
                self.send_json({"status": "ERROR", "message": f"Unknown tile layer '{layer}'"}, code=400)
                return
            base_arr = get_tile_layer_raster(layer)
            if base_arr is None:
                self.send_json({"status": "ERROR", "message": f"Data not available for layer '{layer}'"}, code=404)
                return
            meta = tile_pyramid.TILE_CACHE.get_meta(layer, base_arr)
            self.send_json(meta, code=200)
            return

        if len(parts) == 4:
            layer, zs, xs, ys = parts
            layer_norm = layer.lower()
            if layer_norm not in tile_pyramid.ALLOWED_LAYERS:
                self.send_json({"status": "ERROR", "message": f"Unknown tile layer '{layer}'"}, code=400)
                return
            try:
                z, x, y = int(zs), int(xs), int(ys)
            except ValueError:
                self.send_json({"status": "ERROR", "message": "Tile coordinates must be integers"}, code=400)
                return

            base_arr = get_tile_layer_raster(layer_norm)
            if base_arr is None:
                self.send_json({"status": "ERROR", "message": f"Data not available for layer '{layer}'"}, code=404)
                return

            tile_bytes = tile_pyramid.TILE_CACHE.get_tile(layer_norm, base_arr, z, x, y)
            if tile_bytes is None:
                self.send_json({"status": "ERROR", "message": "Tile out of range"}, code=404)
                return

            self._emit_bytes(tile_bytes, "application/octet-stream", cache="public, max-age=3600, must-revalidate")
            return

        self.send_json({"status": "ERROR", "message": "Malformed tile URL"}, code=404)

    def handle_api_illumination_time(self, binary=False):
        """Analytic diurnal illumination frames for the Phase 4 time slider.

        GET /api/illumination-time       -> JSON meta (schedule, model label)
        GET /api/illumination-time.bin   -> raw uint8 [frames*H*W] bytes
        Computed on demand from the ACTIVE dataset DEM and cached on disk.
        MODEL ONLY: the published LPSR mask remains the authoritative PSR product.
        """
        if not RASTER_CACHE.get("loaded"):
            load_raster_cache()
        if not RASTER_CACHE.get("loaded") or RASTER_CACHE.get("dem") is None:
            self.send_json({
                "status": "ERROR",
                "message": "No active raster dataset — run the pipeline first.",
            }, code=503)
            return

        import illumination_time
        from lunar_catalog import LUNAR_SITES

        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        try:
            frames = int((qs.get("frames") or [str(illumination_time.DEFAULT_FRAMES)])[0])
        except (TypeError, ValueError):
            frames = illumination_time.DEFAULT_FRAMES
        frames = max(8, min(48, frames))

        lat = float(LUNAR_SITES.get(ACTIVE_SITE_ID, {}).get("center_lat", -89.0))
        try:
            bin_path, meta = illumination_time.compute_or_get(
                dem=RASTER_CACHE["dem"],
                pixel_size_m=float(RASTER_CACHE.get("pixel_size_m") or 20.0),
                latitude_deg=lat,
                dataset_id=str(RASTER_CACHE.get("dataset_id") or "unknown"),
                frames=frames,
                nodata=config.DEFAULT_NODATA_VALUE,
                psr_mask=RASTER_CACHE.get("psr"),
            )
        except Exception as e:
            self.send_json({"status": "ERROR", "message": f"Illumination model failed: {e}"}, code=500)
            return

        if binary:
            try:
                content = bin_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "max-age=3600")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f"Error reading frames: {e}")
            return

        meta = dict(meta)
        meta["active_site"] = ACTIVE_SITE_ID
        meta["bin_url"] = "/api/illumination-time.bin?frames=" + str(frames)
        self.send_json({"status": "SUCCESS", **meta})

    def handle_api_select_site(self):
        """Switches active lunar terrain model to a specified site from the catalog."""
        global ACTIVE_SITE_ID
        body = self.read_json_body()
        site_id = body.get("site_id", "lola_crop")
        if site_id not in lunar_catalog.LUNAR_SITES:
            self.send_error(400, f"Unknown site_id '{site_id}'")
            return

        ACTIVE_SITE_ID = site_id
        try:
            # Generate / load site rasters
            dem_path, psr_path = lunar_catalog.save_site_dataset(site_id)
            dem_info = io_utils.read_geotiff(dem_path)
            psr_info = io_utils.read_geotiff(psr_path)

            # Recompute terrain metrics (real data flag matches site provenance)
            import terrain
            _is_real_site = site_id in ("lola_crop",) or site_id.startswith("artemis_")
            terrain_res = terrain.process_terrain_pipeline(
                dem=dem_info["data"],
                dem_meta=dem_info,
                output_slope=config.OUTPUT_SLOPE_TIF,
                output_aspect=config.OUTPUT_ASPECT_TIF,
                output_rough_std=config.OUTPUT_ROUGHNESS_STD_TIF,
                output_rough_tri=config.OUTPUT_ROUGHNESS_TRI_TIF,
                output_hist=config.OUTPUT_TERRAIN_HIST_PNG,
                is_synthetic=not _is_real_site,
                verbose=False,
            )

            # Recompute hazard surface
            hazard_classes, score_h = hazard.classify_hazard_surface(
                slope=terrain_res["slope"],
                roughness=terrain_res["roughness_std"],
                psr_mask=psr_info["data"],
                pixel_size_m=float(abs(dem_info.get("pixel_size_x", 20.0))),
            )
            io_utils.write_geotiff(
                output_path=config.OUTPUT_HAZARD_CLASSES_TIF,
                data=hazard_classes,
                transform=dem_info["transform"],
                crs=dem_info["crs"],
                nodata=config.CLASS_NODATA,
                tags={"PROJECT": "OrbisLuna", "SITE": site_id},
            )

            # Persist active site rasters for web dashboard & 3D mesh
            active_site_dem_path = config.OUTPUT_DIR / "active_site_dem.tif"
            io_utils.write_geotiff(
                output_path=active_site_dem_path,
                data=dem_info["data"],
                transform=dem_info["transform"],
                crs=dem_info["crs"],
                nodata=config.DEFAULT_NODATA_VALUE,
                tags={"PROJECT": "OrbisLuna", "SITE": site_id},
            )
            io_utils.write_geotiff(
                output_path=config.OUTPUT_PSR_BINARY_TIF,
                data=psr_info["data"],
                transform=dem_info["transform"],
                crs=dem_info["crs"],
                nodata=0,
                tags={"PROJECT": "OrbisLuna", "SITE": site_id},
            )

            # Vectorize active site PSR to GeoJSON so 3D raised outlines & 2D overlays match the site exactly
            try:
                import psr
                psr_gdf = psr.vectorize_psr_to_polygons(
                    binary_psr=psr_info["data"],
                    transform=dem_info["transform"],
                    crs=dem_info["crs"],
                    min_size_pixels=config.PSR_MIN_SIZE_PIXELS,
                    provenance=config.PSR_PROVENANCE_PUBLISHED if _is_real_site else config.PSR_PROVENANCE_SYNTHETIC,
                )
                if config.OUTPUT_PSR_POLYGONS_GEOJSON:
                    config.OUTPUT_PSR_POLYGONS_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
                    psr_gdf.to_file(config.OUTPUT_PSR_POLYGONS_GEOJSON, driver="GeoJSON")
            except Exception as pe:
                print(f"[Warning] Site switch PSR vectorization: {pe}")

            # Update in-memory raster cache
            RASTER_CACHE["dem"] = dem_info["data"]
            RASTER_CACHE["slope"] = terrain_res["slope"]
            RASTER_CACHE["roughness"] = terrain_res["roughness_std"]
            RASTER_CACHE["psr"] = psr_info["data"]
            RASTER_CACHE["meta"] = dem_info.get("profile", {})
            RASTER_CACHE["transform"] = dem_info.get("transform")
            RASTER_CACHE["dataset_id"] = site_id
            if site_id == "lola_crop":
                RASTER_CACHE["dataset_name"] = "REAL NASA LRO LOLA (South Pole)"
            elif site_id.startswith("artemis_"):
                _reg_name = lunar_catalog.LUNAR_SITES[site_id]["name"]
                RASTER_CACHE["dataset_name"] = f"REAL NASA LRO LOLA — {_reg_name} (Artemis III Candidate)"
            else:
                RASTER_CACHE["dataset_name"] = lunar_catalog.LUNAR_SITES[site_id]["name"] + " (Procedural Site Model)"
            RASTER_CACHE["is_synthetic"] = not (site_id in ("lola_crop",) or site_id.startswith("artemis_"))
            RASTER_CACHE["pixel_size_m"] = float(abs(dem_info["transform"].a)) if dem_info.get("transform") else config.SYNTHETIC_PIXEL_SIZE_M
            RASTER_CACHE["shape"] = tuple(dem_info["data"].shape)
            RASTER_CACHE["loaded"] = True

            # Re-evaluate landing sites
            px_size = abs(dem_info["transform"].a) if dem_info["transform"] else 20.0
            ai_res = ml_recommender.recommend_landing_sites(
                hazard_classes=hazard_classes,
                dem_data=dem_info["data"],
                slope_data=terrain_res["slope"],
                roughness_data=terrain_res["roughness_std"],
                psr_mask=psr_info["data"],
                transform=dem_info["transform"],
                ellipse_radius_m=config.LANDING_ELLIPSE_RADIUS_M,
                clearance_buffer_m=config.LANDING_CLEARANCE_BUFFER_M,
                pixel_size_m=px_size,
            )
            with open(config.OUTPUT_LANDING_SITES_JSON, "w", encoding="utf-8") as f:
                json.dump(ai_res, f, indent=2)

            # Re-evaluate rover route for active site
            try:
                top_sites = ai_res.get("top_sites", [])
                start_rc = (top_sites[0]["row"], top_sites[0]["col"]) if top_sites else (dem_info["data"].shape[0] // 2, 15)
                psr_targets = rover_router.find_psr_science_targets(
                    hazard_classes=hazard_classes,
                    psr_mask=psr_info["data"],
                    slope_deg=terrain_res["slope"],
                    dem=dem_info["data"],
                    top_n=1,
                    start_rc=start_rc,
                    pixel_size_m=px_size,
                )
                goal_rc = (psr_targets[0]["row"], psr_targets[0]["col"]) if psr_targets else (dem_info["data"].shape[0] // 2, dem_info["data"].shape[1] // 2)
                new_route = rover_router.find_optimal_rover_path(
                    dem=dem_info["data"],
                    slope_deg=terrain_res["slope"],
                    roughness_m=terrain_res["roughness_std"],
                    hazard_classes=hazard_classes,
                    psr_mask=psr_info["data"],
                    start_rc=start_rc,
                    goal_rc=goal_rc,
                    pixel_size_m=px_size,
                    transform=dem_info["transform"],
                )
                with open(config.OUTPUT_ROVER_ROUTE_JSON, "w", encoding="utf-8") as f:
                    json.dump(new_route, f, indent=2)
            except Exception as re:
                print(f"[Warning] Site switch rover calculation: {re}")

            # Update exported data bundle with exact site DEM and PSR
            export_web_data.export_data_bundle(dem_path=dem_path, psr_path=psr_path)
            tile_pyramid.TILE_CACHE.clear()

            self.send_json({
                "status": "SUCCESS",
                "active_site": ACTIVE_SITE_ID,
                "site_info": lunar_catalog.LUNAR_SITES[site_id],
                "message": f"Successfully activated lunar site model: {lunar_catalog.LUNAR_SITES[site_id]['name']}",
            })
        except Exception as e:
            self.send_error(500, f"Error switching lunar site: {e}")

    def handle_api_rover_route(self):
        """Calculates optimal rover traverse path and battery simulation."""
        body = self.read_json_body()
        if not RASTER_CACHE.get("loaded"):
            if not load_raster_cache():
                self.send_error(400, "Raster cache not loaded; run the pipeline once first")
                return

        try:
            dem = RASTER_CACHE["dem"]
            slope = RASTER_CACHE["slope"]
            roughness = RASTER_CACHE["roughness"]
            psr_mask = RASTER_CACHE["psr"]
            transform = RASTER_CACHE.get("transform")
            px_size = RASTER_CACHE.get("pixel_size_m") or (
                abs(transform.a) if transform and abs(transform.a) > 0 else config.SYNTHETIC_PIXEL_SIZE_M
            )

            hazard_classes, _ = hazard.classify_hazard_surface(slope, roughness, psr_mask, pixel_size_m=px_size)

            # Determine start coordinate
            start_in = body.get("start")
            if start_in and len(start_in) == 2:
                start_rc = (int(start_in[1]), int(start_in[0]))  # [col, row] -> (row, col)
            else:
                ai_sites = ml_recommender.recommend_landing_sites(
                    hazard_classes, dem, slope, roughness, psr_mask, transform, pixel_size_m=px_size
                )
                top_sites = ai_sites.get("top_sites", [])
                if top_sites:
                    start_rc = (top_sites[0]["row"], top_sites[0]["col"])
                else:
                    start_rc = (dem.shape[0] // 2, 15)

            # Determine goal coordinate
            goal_in = body.get("goal")
            avoid_psr = bool(body.get("avoid_psr", False))
            if goal_in and len(goal_in) == 2:
                goal_rc = (int(goal_in[1]), int(goal_in[0]))  # [col, row] -> (row, col)
            elif avoid_psr:
                # Avoid-PSR mode: auto goal must be sunlit safe terrain, not a cold trap.
                # Pick the Class-1 (Safe) pixel closest to the safe-terrain centroid
                # (central sunlit highland — a reasonable science drive target).
                safe_mask = (hazard_classes == config.CLASS_SAFE) & (psr_mask == 0) & np.isfinite(slope)
                if np.any(safe_mask):
                    rs, cs = np.nonzero(safe_mask)
                    cr, cc = float(np.mean(rs)), float(np.mean(cs))
                    d2 = (rs - cr) ** 2 + (cs - cc) ** 2
                    idx = int(np.argmin(d2))
                    goal_rc = (int(rs[idx]), int(cs[idx]))
                else:
                    goal_rc = (dem.shape[0] // 2, dem.shape[1] // 2)
            else:
                psr_targets = rover_router.find_psr_science_targets(hazard_classes, psr_mask, slope, dem, top_n=1, start_rc=start_rc, pixel_size_m=px_size)
                if psr_targets:
                    goal_rc = (psr_targets[0]["row"], psr_targets[0]["col"])
                else:
                    goal_rc = (dem.shape[0] // 2, dem.shape[1] // 2)

            options = {
                "max_slope_deg": float(body.get("max_slope_deg", config.ROVER_MAX_SLOPE_DEG)),
                "weight_slope": float(body.get("weight_slope", 2.5)),
                "weight_roughness": float(body.get("weight_roughness", 1.5)),
                "weight_shadow": float(body.get("weight_shadow", 2.0)),
                "weight_clearance": float(body.get("weight_clearance", 2.0)),
                "rover_speed_mps": float(body.get("rover_speed_mps", config.ROVER_SPEED_MPS)),
                "battery_capacity_wh": float(body.get("battery_capacity_wh", config.ROVER_BATTERY_CAPACITY_WH)),
                "avoid_psr": bool(body.get("avoid_psr", False)),
                "avoid_unsafe": bool(body.get("avoid_unsafe", False)),
            }

            route_res = rover_router.find_optimal_rover_path(
                dem=dem,
                slope_deg=slope,
                roughness_m=roughness,
                hazard_classes=hazard_classes,
                psr_mask=psr_mask,
                start_rc=start_rc,
                goal_rc=goal_rc,
                pixel_size_m=px_size,
                transform=transform,
                options=options,
            )

            try:
                with open(config.OUTPUT_ROVER_ROUTE_JSON, "w", encoding="utf-8") as f:
                    json.dump(route_res, f, indent=2)
            except Exception:
                pass

            self.send_json(route_res)
        except Exception as e:
            print(f"[Rover Route ERROR] {e}")
            self.send_json({
                "status": "ERROR",
                "message": f"Rover route computation failed: {e}",
            }, 500)

    def handle_api_psr_targets(self):
        """Returns candidate volatile cold trap sampling targets inside PSRs."""
        if not RASTER_CACHE.get("loaded"):
            load_raster_cache()
        if not RASTER_CACHE.get("loaded"):
            self.send_json({"targets": []})
            return

        dem = RASTER_CACHE["dem"]
        slope = RASTER_CACHE["slope"]
        roughness = RASTER_CACHE["roughness"]
        psr_mask = RASTER_CACHE["psr"]
        hazard_classes, _ = hazard.classify_hazard_surface(slope, roughness, psr_mask, pixel_size_m=RASTER_CACHE.get("pixel_size_m"))
        targets = rover_router.find_psr_science_targets(hazard_classes, psr_mask, slope, dem, top_n=5)
        self.send_json({"status": "SUCCESS", "targets": targets})


OrbisLunaHandler = LunaSafeHandler


def run_server(port=8050):
    global ACTIVE_SITE_ID
    # Preload raster cache
    load_raster_cache()
    # Keep the site selector in sync with the actually loaded dataset
    if RASTER_CACHE.get("loaded") and RASTER_CACHE.get("dataset_id") in lunar_catalog.LUNAR_SITES:
        ACTIVE_SITE_ID = RASTER_CACHE["dataset_id"]

    ThreadingHTTPServer.allow_reuse_address = True
    ports_to_try = [port, 8050, 8055, 8090, 8000]
    httpd = None
    for p in ports_to_try:
        try:
            server_address = ("", p)
            httpd = ThreadingHTTPServer(server_address, OrbisLunaHandler)
            port = p
            break
        except OSError:
            continue
    if httpd is None:
        raise OSError(f"Could not bind to any port in {ports_to_try}")

    print("\n" + "=" * 70)
    print(" ORBISLUNA MISSION CONTROL WEB SERVER ONLINE")
    print("=" * 70)
    print(f" URL: http://localhost:{port}")
    print(" Lunar CRS: IAU 2015 Moon South Pole Polar Stereographic")
    print(" Endpoints: 2D Canvas, 3D WebGL Mesh, Rover Router, Multi-Site Catalog")
    print("=" * 70 + "\n")
    return httpd, port


if __name__ == "__main__":
    server, port = run_server(8050)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down OrbisLuna web server...")
        server.server_close()
