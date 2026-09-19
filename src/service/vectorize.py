import io
import math
import numpy as np

try:
    import rasterio
    from rasterio.features import shapes
    from shapely.geometry import shape, mapping
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import scipy.ndimage as ndi
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def utm_to_wgs84(easting: float, northing: float, zone: int = 38, northern: bool = True):
    """
    Standard Karney / USGS mathematical transformation from UTM (easting, northing)
    in given zone to WGS84 (lon, lat) in decimal degrees.
    Accurate to within millimeters, zero external C-dependencies required.
    """
    a = 6378137.0
    f = 1 / 298.257223563
    e = math.sqrt(2 * f - f ** 2)
    e1sq = e ** 2 / (1 - e ** 2)
    k0 = 0.9996
    
    x = easting - 500000.0
    y = northing if northern else northing - 10000000.0
    
    m = y / k0
    mu = m / (a * (1 - e ** 2 / 4 - 3 * e ** 4 / 64 - 5 * e ** 6 / 256))
    
    e1 = (1 - math.sqrt(1 - e ** 2)) / (1 + math.sqrt(1 - e ** 2))
    j1 = 3 * e1 / 2 - 27 * e1 ** 3 / 32
    j2 = 21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32
    j3 = 151 * e1 ** 3 / 96
    j4 = 1097 * e1 ** 4 / 512
    
    fp = mu + j1 * math.sin(2 * mu) + j2 * math.sin(4 * mu) + j3 * math.sin(6 * mu) + j4 * math.sin(8 * mu)
    
    c1 = e1sq * math.cos(fp) ** 2
    t1 = math.tan(fp) ** 2
    r1 = a * (1 - e ** 2) / (1 - e ** 2 * math.sin(fp) ** 2) ** 1.5
    n1 = a / math.sqrt(1 - e ** 2 * math.sin(fp) ** 2)
    d = x / (n1 * k0)
    
    lat = fp - (n1 * math.tan(fp) / r1) * (
        d ** 2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * e1sq) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * e1sq - 3 * c1 ** 2) * d ** 6 / 720
    )
    lon = (
        d - (1 + 2 * t1 + c1) * d ** 3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * e1sq + 24 * t1 ** 2) * d ** 5 / 120
    ) / math.cos(fp)
    
    lon_deg = (zone - 1) * 6 - 180 + 3 + math.degrees(lon)
    lat_deg = math.degrees(lat)
    return round(lon_deg, 6), round(lat_deg, 6)


SEVERITY_NAMES = {
    1: "слабая",
    2: "средняя",
    3: "сильная"
}

SEVERITY_COLORS = {
    1: "#FACC15",  # Gold / Yellow
    2: "#FB923C",  # Orange
    3: "#DC2626"   # Crimson / DarkRed
}


def read_mask_and_transform(file_or_bytes):
    """
    Reads a GeoTIFF mask from filepath or bytes buffer.
    Returns: (mask_array, transform_tuple, epsg_code)
    """
    if HAS_RASTERIO:
        try:
            if isinstance(file_or_bytes, (bytes, bytearray)):
                with rasterio.io.MemoryFile(file_or_bytes) as mem:
                    with mem.open() as src:
                        mask = src.read(1)
                        transform = src.transform
                        epsg = src.crs.to_epsg() if src.crs else 32638
                        return mask, transform, epsg
            else:
                with rasterio.open(file_or_bytes) as src:
                    mask = src.read(1)
                    transform = src.transform
                    epsg = src.crs.to_epsg() if src.crs else 32638
                    return mask, transform, epsg
        except Exception:
            pass

    # Fallback via PIL
    if isinstance(file_or_bytes, (bytes, bytearray)):
        img = Image.open(io.BytesIO(file_or_bytes))
    else:
        img = Image.open(file_or_bytes)
        
    mask = np.array(img, dtype=np.uint8)
    
    # Extract GeoTIFF metadata tags if available
    # Tag 33550: ModelPixelScaleTag (scale_x, scale_y, scale_z)
    # Tag 33922: ModelTiepointTag (I, J, K, X, Y, Z)
    # Tag 34735: GeoKeyDirectoryTag
    scale_x, scale_y = 20.0, 20.0
    origin_x, origin_y = 491520.0, 5386240.0
    epsg = 32638
    
    if hasattr(img, "tag_v2"):
        if 33550 in img.tag_v2:
            sc = img.tag_v2[33550]
            scale_x, scale_y = float(sc[0]), float(sc[1])
        if 33922 in img.tag_v2:
            tp = img.tag_v2[33922]
            origin_x, origin_y = float(tp[3]), float(tp[4])
        if 34735 in img.tag_v2:
            keys = img.tag_v2[34735]
            # Search for EPSG code in geokeys
            for val in keys:
                if val in (32637, 32638, 4326):
                    epsg = val
                    break
                    
    # Affine transform tuple: (a, b, c, d, e, f)
    # x = c + col*a + row*b
    # y = f + col*d + row*e
    transform = (scale_x, 0.0, origin_x, 0.0, -scale_y, origin_y)
    return mask, transform, epsg


def _trace_component_polygon(comp_mask, min_r, max_r, min_c, max_c):
    """
    Traces the outer closed polygon ring for a binary component mask.
    Returns list of (row, col) grid vertices.
    """
    sub = np.pad(comp_mask[min_r:max_r + 1, min_c:max_c + 1], 1, constant_values=False)
    H, W = sub.shape
    edges = {}
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            if not sub[r, c]:
                continue
            if not sub[r - 1, c]:
                edges.setdefault((r - 1, c - 1), []).append((r - 1, c))
            if not sub[r, c + 1]:
                edges.setdefault((r - 1, c), []).append((r, c))
            if not sub[r + 1, c]:
                edges.setdefault((r, c), []).append((r, c - 1))
            if not sub[r, c - 1]:
                edges.setdefault((r, c - 1), []).append((r - 1, c - 1))
                
    loops = []
    starts = [p for p in edges.keys() if edges[p]]
    for start in starts:
        while edges.get(start):
            loop = [start]
            curr = start
            while True:
                nxts = edges.get(curr, [])
                if not nxts:
                    break
                nxt = nxts.pop()
                loop.append(nxt)
                curr = nxt
                if curr == start:
                    break
            if len(loop) > 3 and loop[0] == loop[-1]:
                # Collinear points simplification
                simp = [loop[0]]
                for i in range(1, len(loop) - 1):
                    p0, p1, p2 = simp[-1], loop[i], loop[i + 1]
                    dr1, dc1 = p1[0] - p0[0], p1[1] - p0[1]
                    dr2, dc2 = p2[0] - p1[0], p2[1] - p1[1]
                    if dr1 * dc2 == dr2 * dc1:
                        continue
                    simp.append(p1)
                simp.append(loop[-1])
                world_loop = [(min_r + vr, min_c + vc) for vr, vc in simp]
                loops.append(world_loop)
                
    if not loops:
        return None
    loops.sort(key=len, reverse=True)
    return loops[0]


def mask_to_geojson(mask, transform, crs="EPSG:4326", epsg_in=32638, chip_id=""):
    """
    Vectorize 2D mask into GeoJSON FeatureCollection.
    Each feature contains:
      - contour_id: unique ID string
      - class_id: 1, 2, or 3
      - severity: 'слабая' / 'средняя' / 'сильная'
      - area_ha: area in hectares (20x20 m = 0.04 ha/pixel)
      - color: hex color code
    Coordinates are transformed to WGS84 (EPSG:4326 [lon, lat]) for Leaflet display.
    """
    feats = []
    px_area_ha = 0.04  # standard 20m pixel = 400m² = 0.04 ha
    
    # Check if transform is rasterio Affine object or tuple
    if hasattr(transform, "a"):
        a, b, c, d, e, f = transform.a, transform.b, transform.c, transform.d, transform.e, transform.f
    elif isinstance(transform, (list, tuple)) and len(transform) >= 6:
        a, b, c, d, e, f = transform[0], transform[1], transform[2], transform[3], transform[4], transform[5]
    else:
        a, b, c, d, e, f = 20.0, 0.0, 491520.0, 0.0, -20.0, 5386240.0

    zone = 37 if (epsg_in == 32637 or (isinstance(epsg_in, str) and "32637" in epsg_in)) else 38
    is_utm = (epsg_in in (32637, 32638) or (isinstance(epsg_in, str) and ("32637" in epsg_in or "32638" in epsg_in)) or c > 180.0)

    # Method 1: Use rasterio.features.shapes if available
    if HAS_RASTERIO:
        try:
            counter = 0
            for geom, val in shapes(mask.astype(np.uint8), transform=transform):
                val = int(val)
                if val == 0:
                    continue
                counter += 1
                poly_shape = shape(geom)
                # Compute area in hectares
                geom_coords = geom.get("coordinates", [])
                
                # Transform coordinates if in UTM
                transformed_coords = []
                for ring in geom_coords:
                    ring_pts = []
                    for pt in ring:
                        x, y = pt[0], pt[1]
                        if is_utm:
                            lon, lat = utm_to_wgs84(x, y, zone=zone)
                            ring_pts.append([lon, lat])
                        else:
                            ring_pts.append([round(x, 6), round(y, 6)])
                    transformed_coords.append(ring_pts)
                    
                area_ha = round(float(poly_shape.area / 10000.0) if is_utm else float(len(ring) * px_area_ha), 2)
                if area_ha < 0.04:
                    area_ha = 0.04
                    
                feats.append({
                    "type": "Feature",
                    "properties": {
                        "contour_id": f"contour_{chip_id}_{val}_{counter}" if chip_id else f"contour_{val}_{counter}",
                        "class_id": val,
                        "severity": SEVERITY_NAMES.get(val, f"Класс {val}"),
                        "area_ha": area_ha,
                        "color": SEVERITY_COLORS.get(val, "#DC2626")
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": transformed_coords
                    }
                })
            if feats:
                return {
                    "type": "FeatureCollection",
                    "crs": {"type": "name", "properties": {"name": crs}},
                    "features": feats
                }
        except Exception:
            feats = []

    # Method 2: Fast pure-Python / numpy / scipy connected-components vectorizer
    counter = 0
    for val in [1, 2, 3]:
        bin_m = (mask == val)
        if not bin_m.any():
            continue
            
        if HAS_SCIPY:
            labeled, num = ndi.label(bin_m)
            comp_ids = range(1, num + 1)
        else:
            labeled = bin_m.astype(np.int32)
            comp_ids = [1]
            
        for comp_id in comp_ids:
            comp = (labeled == comp_id)
            px_count = int(comp.sum())
            if px_count < 3:
                continue
            counter += 1
            
            by, bx = np.where(comp)
            min_r, max_r = int(by.min()), int(by.max())
            min_c, max_c = int(bx.min()), int(bx.max())
            
            loop = _trace_component_polygon(comp, min_r, max_r, min_c, max_c)
            if not loop:
                continue
                
            ring_coords = []
            for r, col in loop:
                # Pixel corner coordinate to world coordinate
                x = c + col * a + r * b
                y = f + col * d + r * e
                if is_utm:
                    lon, lat = utm_to_wgs84(x, y, zone=zone)
                    ring_coords.append([lon, lat])
                else:
                    ring_coords.append([round(x, 6), round(y, 6)])
                    
            area_ha = round(px_count * px_area_ha, 2)
            feats.append({
                "type": "Feature",
                "properties": {
                    "contour_id": f"contour_{chip_id}_{val}_{counter}" if chip_id else f"contour_{val}_{counter}",
                    "class_id": val,
                    "severity": SEVERITY_NAMES.get(val, f"Класс {val}"),
                    "area_ha": area_ha,
                    "color": SEVERITY_COLORS.get(val, "#DC2626")
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ring_coords]
                }
            })

    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": crs}},
        "features": feats
    }