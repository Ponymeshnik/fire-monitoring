import os
import io
import json
import zipfile
import tempfile
from typing import Optional

from fastapi import FastAPI, Query, UploadFile, File, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .vectorize import mask_to_geojson, read_mask_and_transform
from .report import area_report, report_from_contours
from .prepare_demo import prepare_demo

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CACHE_DIR = os.path.join(BASE_DIR, "demo_cache")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Standard ESRI WGS84 Projection String
WGS84_PRJ = (
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
)

app = FastAPI(
    title="Fire Monitoring Service",
    description="КосмоХакатон 2026: Информационно-аналитический сервис двухэтапного мониторинга природных пожаров (VIIRS, Sentinel-2)",
    version="2.0.0"
)

# Mount static files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def ensure_demo_cache():
    """Ensure demo cache files exist; if not, generate them."""
    tp_path = os.path.join(CACHE_DIR, "thermopoints.geojson")
    cont_path = os.path.join(CACHE_DIR, "contours.geojson")
    rep_path = os.path.join(CACHE_DIR, "report.json")
    if not (os.path.exists(tp_path) and os.path.exists(cont_path) and os.path.exists(rep_path)):
        try:
            prepare_demo()
        except Exception as e:
            print(f"Failed to auto-prepare demo cache: {e}")


def parse_bbox(bbox_str: str):
    """Parses 'min_lon,min_lat,max_lon,max_lat' into float tuple."""
    try:
        parts = [float(x.strip()) for x in bbox_str.split(",")]
        if len(parts) == 4:
            return parts[0], parts[1], parts[2], parts[3]
    except Exception:
        pass
    # Default monitoring AOI bounds
    return 38.3, 44.6, 48.0, 52.7


def is_point_in_bbox(lon: float, lat: float, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> bool:
    return (min_lon <= lon <= max_lon) and (min_lat <= lat <= max_lat)


def is_poly_in_bbox(coords, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> bool:
    """Check if polygon AABB intersects the query bbox."""
    try:
        outer_ring = coords[0]
        lons = [p[0] for p in outer_ring]
        lats = [p[1] for p in outer_ring]
        p_min_lon, p_max_lon = min(lons), max(lons)
        p_min_lat, p_max_lat = min(lats), max(lats)
        return not (p_max_lon < min_lon or p_min_lon > max_lon or p_max_lat < min_lat or p_min_lat > max_lat)
    except Exception:
        return True


@app.on_event("startup")
def startup_event():
    ensure_demo_cache()


@app.get("/", response_class=HTMLResponse)
def index():
    """Serves the interactive Leaflet Web GIS application."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Fire Monitoring Service Active</h1><p>Visit /query or /health</p>")


@app.get("/yandex", response_class=HTMLResponse)
def yandex_view():
    """Serves the interactive Yandex Maps GIS application."""
    yandex_path = os.path.join(STATIC_DIR, "yandex.html")
    if os.path.exists(yandex_path):
        return FileResponse(yandex_path)
    return HTMLResponse("<h1>Yandex Maps Interface Loading...</h1>")


@app.get("/health")
def health():
    """Health check endpoint."""
    ensure_demo_cache()
    return {"status": "ok", "service": "Fire Monitoring Service", "version": "2.0.0"}


@app.get("/api/aoi")
def get_aoi():
    """Serves the monitoring AOI GeoJSON geometry."""
    candidates = [
        os.path.join(CACHE_DIR, "fire_monitoring_aoi.geojson"),
        os.path.join(BASE_DIR, "..", "Мониторинг DATA", "fire-aoi", "fire_monitoring_aoi.geojson"),
        os.path.join(BASE_DIR, "..", "..", "Мониторинг DATA", "fire-aoi", "fire_monitoring_aoi.geojson"),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise HTTPException(404, "AOI GeoJSON file not found")


@app.get("/query")
def query(
    bbox: str = Query("38.3,44.6,48.0,52.7", description="Bounding box 'min_lon,min_lat,max_lon,max_lat'"),
    date_from: str = Query("2025-04-01", description="Start date YYYY-MM-DD"),
    date_to: str = Query("2025-10-31", description="End date YYYY-MM-DD"),
):
    """
    Query fire monitoring data filtered by spatial bounding box and date interval.
    Returns: {"thermopoints": FeatureCollection, "contours": FeatureCollection, "report": {...}}
    """
    ensure_demo_cache()
    tp_path = os.path.join(CACHE_DIR, "thermopoints.geojson")
    cont_path = os.path.join(CACHE_DIR, "contours.geojson")

    if not (os.path.exists(tp_path) and os.path.exists(cont_path)):
        raise HTTPException(503, "Demo cache not ready. Run prepare_demo.py")

    with open(tp_path, "r", encoding="utf-8") as f:
        tp_data = json.load(f)
    with open(cont_path, "r", encoding="utf-8") as f:
        cont_data = json.load(f)

    min_lon, min_lat, max_lon, max_lat = parse_bbox(bbox)

    # 1. Filter thermopoints
    filtered_tp = []
    for feat in tp_data.get("features", []):
        pt = feat.get("geometry", {}).get("coordinates", [])
        if len(pt) >= 2 and is_point_in_bbox(pt[0], pt[1], min_lon, min_lat, max_lon, max_lat):
            p_date = feat.get("properties", {}).get("date", "")
            if (not p_date) or (date_from <= p_date <= date_to):
                filtered_tp.append(feat)

    # 2. Filter contours
    filtered_cont = []
    for feat in cont_data.get("features", []):
        coords = feat.get("geometry", {}).get("coordinates", [])
        if coords and is_poly_in_bbox(coords, min_lon, min_lat, max_lon, max_lat):
            c_date = feat.get("properties", {}).get("date", "")
            if (not c_date) or (date_from <= c_date <= date_to):
                filtered_cont.append(feat)

    # 3. Dynamic Analytical Report based on filtered results
    dyn_report = report_from_contours(filtered_cont, len(filtered_tp))
    dyn_report["query_bbox"] = [min_lon, min_lat, max_lon, max_lat]
    dyn_report["query_date_from"] = date_from
    dyn_report["query_date_to"] = date_to

    return JSONResponse({
        "thermopoints": {
            "type": "FeatureCollection",
            "name": "thermopoints",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": filtered_tp,
        },
        "contours": {
            "type": "FeatureCollection",
            "name": "contours",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": filtered_cont,
        },
        "report": dyn_report,
    })


@app.get("/export/geojson")
def export_geojson(layer: str = Query("contours", description="Layer to export: 'contours' or 'thermopoints'")):
    """
    Download GeoJSON file for requested layer ('contours' or 'thermopoints').
    """
    ensure_demo_cache()
    filename = f"{layer}.geojson"
    path = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(path):
        # Fallback to contours
        path = os.path.join(CACHE_DIR, "contours.geojson")
        filename = "contours.geojson"
        if not os.path.exists(path):
            raise HTTPException(404, f"Layer {layer} not found in cache")

    return FileResponse(
        path,
        media_type="application/geo+json",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/export/shapefile")
def export_shapefile(layer: str = Query("contours", description="Layer to export: 'contours' or 'thermopoints'")):
    """
    Downloadable zipped ESRI Shapefile (or GeoJSON fallback if geopandas/fiona not available).
    If geopandas is available, generates native shapefile zip.
    If not, bundles GeoJSON with ESRI .prj and README in a clean zip package.
    """
    ensure_demo_cache()
    geojson_path = os.path.join(CACHE_DIR, f"{layer}.geojson")
    if not os.path.exists(geojson_path):
        geojson_path = os.path.join(CACHE_DIR, "contours.geojson")
        layer = "contours"

    if not os.path.exists(geojson_path):
        raise HTTPException(404, "Export data not ready")

    # Check if geopandas is available for ESRI Shapefile export
    has_geopandas = False
    try:
        import geopandas as gpd
        has_geopandas = True
    except ImportError:
        has_geopandas = False

    if has_geopandas:
        try:
            gdf = gpd.read_file(geojson_path)
            with tempfile.TemporaryDirectory() as tmpdir:
                shp_base = os.path.join(tmpdir, f"fire_{layer}")
                gdf.to_file(f"{shp_base}.shp", driver="ESRI Shapefile", encoding="utf-8")
                
                zip_io = io.BytesIO()
                with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
                    for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                        fp = f"{shp_base}{ext}"
                        if os.path.exists(fp):
                            zf.write(fp, arcname=f"fire_{layer}{ext}")
                zip_io.seek(0)
                return StreamingResponse(
                    zip_io,
                    media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="fire_{layer}_shapefile.zip"'}
                )
        except Exception as e:
            print(f"Geopandas shapefile export fallback: {e}")

    # Fallback: Package GeoJSON + .prj + Readme into standard GIS zip archive
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(geojson_path, arcname=f"fire_{layer}.geojson")
        zf.writestr(f"fire_{layer}.prj", WGS84_PRJ)
        readme_content = (
            f"КосмоХакатон 2026: Мониторинг природных пожаров\n"
            f"Слой: {layer}\n"
            f"Формат: GeoJSON + ESRI WGS84 Projection (.prj)\n"
            f"Координатная система: EPSG:4326 (WGS 84)\n"
            f"Атрибуты контуров: contour_id, class_id, severity (слабая/средняя/сильная), area_ha\n"
        )
        zf.writestr("README.txt", readme_content)

    zip_io.seek(0)
    return StreamingResponse(
        zip_io,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="fire_{layer}_export.zip"'}
    )


@app.post("/upload_mask")
async def upload_mask(file: UploadFile = File(...), gsd: float = Query(20.0, description="Ground sampling distance in meters")):
    """
    Accepts GeoTIFF mask file, returns vectorized GeoJSON contours and area analytics report.
    """
    content = await file.read()
    try:
        mask, transform, epsg = read_mask_and_transform(content)
    except Exception as e:
        raise HTTPException(400, f"Failed to decode GeoTIFF mask: {e}")

    geojson = mask_to_geojson(mask, transform, epsg_in=epsg, chip_id="uploaded")
    report = area_report(mask, gsd_m=gsd)
    return {"contours": geojson, "report": report}


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Запуск Информационно-аналитического веб-сервиса...")
    print("Карта и Web UI доступны по адресу: http://localhost:8000")
    print("Интерактивная документация Swagger: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run("src.service.app:app", host="0.0.0.0", port=8000, reload=True)