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
from .fire_spread import (
    build_fire_spread_forecast,
    classify_thermopoint,
    generate_emercom_sitrep,
    calculate_ecological_damage_rub,
    KNOWN_INDUSTRIAL_FLARES
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CACHE_DIR = os.path.join(BASE_DIR, "demo_cache")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Standard ESRI WGS84 Projection String
WGS84_PRJ = (
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
)

app = FastAPI(
    title="Fire Monitoring Service (GIS & Predictive AI)",
    description="КосмоХакатон 2026: Информационно-аналитический комплекс двухэтапного мониторинга, моделирования динамики пожаров (модель Ротермела) и генерации отчетности 1-ЧС",
    version="2.5.0"
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
    """
    Serves the primary flagship Yandex Maps GIS interface with
    spread forecasting, threat exposure, flare filtering, and 1-CHS reporting.
    """
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Fire Monitoring Service Active</h1><p>Visit /query or /health</p>")


@app.get("/yandex", response_class=HTMLResponse)
def yandex_view():
    """Alias to the primary Yandex Maps interface."""
    return index()


@app.get("/health")
def health():
    """Health check endpoint."""
    ensure_demo_cache()
    return {
        "status": "ok",
        "service": "Fire Monitoring Service (Predictive GIS)",
        "version": "2.5.0",
        "primary_engine": "Open-Source GIS (Leaflet 1.9.4 + ESRI World Imagery + OSM)",
        "secondary_engine": "Yandex Maps API 2.1 (Hybrid)",
        "license_cost": "0 RUB (Zero-TCO, 100% Free Open-Source)",
        "deployment_modes": ["Offline / Air-Gapped (ЗСПД МЧС)", "Public Cloud / On-Premise GeoServer"],
        "open_source_stack": [
            "Leaflet 1.9.4 (BSD-2-Clause)",
            "ESRI World Imagery (0 API key required)",
            "OpenStreetMap Standard Cartography",
            "FastAPI / Uvicorn (MIT)",
            "GDAL / Rasterio / Shapely (BSD / MIT)",
            "NumPy / Pandas / SciPy (BSD)"
        ],
        "features": [
            "Active Fire detection (VIIRS 375m)",
            "Burn Severity segmentation (Sentinel-2 dNBR)",
            "Huygens/Rothermel Fire Spread Forecasting (+3h/+6h/+12h)",
            "Industrial Flare & False Alarm Disambiguation",
            "EMERCOM 1-CHS Emergency SitRep Generator"
        ]
    }


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
    filter_flares: bool = Query(False, description="Filter out stationary industrial flares and false alarms")
):
    """
    Query fire monitoring data filtered by spatial bounding box, date interval,
    and optional industrial flare filter.
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

    # 1. Filter and classify thermopoints
    filtered_tp = []
    flares_detected_count = 0
    flares_filtered_count = 0
    wildfires_count = 0

    for feat in tp_data.get("features", []):
        pt = feat.get("geometry", {}).get("coordinates", [])
        if len(pt) >= 2 and is_point_in_bbox(pt[0], pt[1], min_lon, min_lat, max_lon, max_lat):
            props = feat.get("properties", {})
            p_date = props.get("date", "")
            if (not p_date) or (date_from <= p_date <= date_to):
                # Ensure all alias keys exist
                b_k = props.get("brightness_k") or props.get("brightness_temp_k") or 334.2
                frp = props.get("frp_mw") or props.get("frp") or 45.6
                props["brightness_k"] = round(float(b_k), 1)
                props["brightness_temp_k"] = round(float(b_k), 1)
                props["frp_mw"] = round(float(frp), 1)
                props["frp"] = round(float(frp), 1)
                props["confidence"] = round(float(props.get("confidence", 92.5)), 1)
                props["satellite"] = props.get("satellite") or "VIIRS (SNPP 375m)"

                # Run classification: wildfire vs industrial flare vs agricultural burn
                cl = classify_thermopoint(lat=pt[1], lon=pt[0], frp=props["frp_mw"], temp_k=props["brightness_k"])
                props["point_type"] = cl["point_type"]
                props["point_label"] = cl["label"]
                props["is_flare"] = cl["is_flare"]
                props["is_wildfire"] = cl["is_wildfire"]
                props["action_recommendation"] = cl["action_recommendation"]
                if cl.get("facility"):
                    props["facility"] = cl["facility"]

                if cl["is_flare"]:
                    flares_detected_count += 1
                    if filter_flares:
                        flares_filtered_count += 1
                        continue  # Skip appending filtered flare
                else:
                    wildfires_count += 1

                filtered_tp.append(feat)

    # 2. Filter contours
    filtered_cont = []
    for feat in cont_data.get("features", []):
        coords = feat.get("geometry", {}).get("coordinates", [])
        if coords and is_poly_in_bbox(coords, min_lon, min_lat, max_lon, max_lat):
            props = feat.get("properties", {})
            c_date = props.get("date", "")
            if (not c_date) or (date_from <= c_date <= date_to):
                cid = props.get("class_id", 1)
                sev_map = {1: "слабая", 2: "средняя", 3: "сильная"}
                props["severity"] = props.get("severity") or sev_map.get(cid, "средняя")
                props["satellite"] = props.get("satellite") or "Sentinel-2 MSI"
                filtered_cont.append(feat)

    # 3. Dynamic Analytical Report based on filtered results
    dyn_report = report_from_contours(filtered_cont, len(filtered_tp))
    dyn_report["query_bbox"] = [min_lon, min_lat, max_lon, max_lat]
    dyn_report["query_date_from"] = date_from
    dyn_report["query_date_to"] = date_to
    dyn_report["flares_detected_count"] = flares_detected_count
    dyn_report["flares_filtered_count"] = flares_filtered_count
    dyn_report["wildfires_count"] = wildfires_count

    # Calculate preliminary ecological and economic damage in Rubles
    dyn_report["damage_assessment"] = calculate_ecological_damage_rub(
        total_ha=dyn_report["total_ha"],
        sev1_ha=dyn_report["sev1_ha"],
        sev2_ha=dyn_report["sev2_ha"],
        sev3_ha=dyn_report["sev3_ha"]
    )

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


@app.get("/api/forecast")
def get_fire_spread_forecast(
    bbox: str = Query("38.3,44.6,48.0,52.7", description="Bounding box 'min_lon,min_lat,max_lon,max_lat'"),
    wind_speed: float = Query(24.0, description="Wind speed in km/h (10..60)"),
    wind_deg: float = Query(240.0, description="Wind azimuth in degrees (0..360, towards direction)")
):
    """
    Computes Huygens/Rothermel fire spread forecast ellipses for +3h, +6h, +12h
    and evaluates threat exposure for settlements and critical infrastructure.
    """
    ensure_demo_cache()
    tp_path = os.path.join(CACHE_DIR, "thermopoints.geojson")
    if not os.path.exists(tp_path):
        raise HTTPException(503, "Demo cache not ready")

    with open(tp_path, "r", encoding="utf-8") as f:
        tp_data = json.load(f)

    min_lon, min_lat, max_lon, max_lat = parse_bbox(bbox)
    filtered_tp = []
    for feat in tp_data.get("features", []):
        pt = feat.get("geometry", {}).get("coordinates", [])
        if len(pt) >= 2 and is_point_in_bbox(pt[0], pt[1], min_lon, min_lat, max_lon, max_lat):
            filtered_tp.append(feat)

    forecast_result = build_fire_spread_forecast(
        hotspots=filtered_tp,
        wind_speed_kmh=wind_speed,
        wind_azimuth_deg=wind_deg
    )

    return JSONResponse(forecast_result)


@app.get("/api/sitrep")
def get_emercom_sitrep(
    bbox: str = Query("38.3,44.6,48.0,52.7", description="Bounding box 'min_lon,min_lat,max_lon,max_lat'"),
    date_from: str = Query("2025-04-01", description="Start date YYYY-MM-DD"),
    date_to: str = Query("2025-10-31", description="End date YYYY-MM-DD"),
    wind_speed: float = Query(24.0, description="Wind speed in km/h"),
    wind_deg: float = Query(240.0, description="Wind azimuth in degrees")
):
    """
    Generates formal EMERCOM 1-CHS Emergency SitRep document data.
    """
    ensure_demo_cache()
    # Get current query state
    q_res = query(bbox=bbox, date_from=date_from, date_to=date_to, filter_flares=True)
    q_data = json.loads(q_res.body.decode("utf-8"))

    report_data = q_data.get("report", {})
    tp_features = q_data.get("thermopoints", {}).get("features", [])

    spread_data = build_fire_spread_forecast(
        hotspots=tp_features,
        wind_speed_kmh=wind_speed,
        wind_azimuth_deg=wind_deg
    )

    sitrep = generate_emercom_sitrep(
        report_data=report_data,
        query_params={"bbox": bbox, "date_from": date_from, "date_to": date_to},
        spread_data=spread_data
    )

    return JSONResponse(sitrep)


@app.get("/export/geojson")
def export_geojson(layer: str = Query("contours", description="Layer to export: 'contours' or 'thermopoints'")):
    """
    Download GeoJSON file for requested layer ('contours' or 'thermopoints').
    """
    ensure_demo_cache()
    filename = f"{layer}.geojson"
    path = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(path):
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
    """
    ensure_demo_cache()
    geojson_path = os.path.join(CACHE_DIR, f"{layer}.geojson")
    if not os.path.exists(geojson_path):
        geojson_path = os.path.join(CACHE_DIR, "contours.geojson")
        layer = "contours"

    if not os.path.exists(geojson_path):
        raise HTTPException(404, "Export data not ready")

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
    print("Запуск Информационно-аналитического веб-сервиса (Яндекс.Карты + СППР)...")
    print("Карта и Web UI доступны по адресу: http://localhost:8000")
    print("Интерактивная документация Swagger: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run("src.service.app:app", host="0.0.0.0", port=8000, reload=True)