import os, json
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping

CACHE = "demo_cache"
os.makedirs(CACHE, exist_ok=True)

# Пример: берём один BS-чип из train и его маску, сохраняем как демо
mask_path = "train/bs/masks/BS_tr_000001_MASK.tif"
with rasterio.open(mask_path) as src:
    mask = src.read(1)
    transform = src.transform

feats = []
for geom, val in shapes(mask.astype(np.uint8), transform=transform):
    if val == 0:
        continue
    feats.append({"type": "Feature", "properties": {"class_id": int(val)}, "geometry": mapping(shape(geom))})
json.dump({"type": "FeatureCollection", "features": feats}, open(f"{CACHE}/contours.geojson", "w", encoding="utf-8"))

# Термоточки — фиктивные, для демо
tp = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"confidence": 0.9}, "geometry": {"type": "Point", "coordinates": [40.0, 48.0]}},
]}
json.dump(tp, open(f"{CACHE}/thermopoints.geojson", "w", encoding="utf-8"))

# Отчёт
px_ha = (20 ** 2) / 10000.0
report = {
    "total_ha": float((mask > 0).sum() * px_ha),
    "sev1_ha": float((mask == 1).sum() * px_ha),
    "sev2_ha": float((mask == 2).sum() * px_ha),
    "sev3_ha": float((mask == 3).sum() * px_ha),
}
json.dump(report, open(f"{CACHE}/report.json", "w", encoding="utf-8"))
print("demo_cache ready")