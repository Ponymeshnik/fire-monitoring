import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping

def mask_to_geojson(mask, transform, crs="EPSG:4326"):
    feats = []
    for geom, val in shapes(mask.astype(np.uint8), transform=transform):
        if val == 0:
            continue
        feats.append({
            "type": "Feature",
            "properties": {"class_id": int(val)},
            "geometry": mapping(shape(geom)),
        })
    return {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": crs}}, "features": feats}