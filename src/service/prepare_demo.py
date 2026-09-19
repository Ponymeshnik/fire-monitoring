import os
import json
import shutil
import numpy as np
import pandas as pd
from PIL import Image

from .vectorize import read_mask_and_transform, mask_to_geojson, utm_to_wgs84
from .report import report_from_contours

def prepare_demo():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cache_dir = os.path.join(base_dir, "demo_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    print("Preparing realistic demo cache for КосмоХакатон 2026 Fire Monitoring Service...")
    
    # 1. Copy or verify AOI polygon
    aoi_candidates = [
        os.path.join(base_dir, "..", "Мониторинг DATA", "fire-aoi", "fire_monitoring_aoi.geojson"),
        os.path.join(base_dir, "..", "..", "Мониторинг DATA", "fire-aoi", "fire_monitoring_aoi.geojson"),
        os.path.join(base_dir, "static", "fire_monitoring_aoi.geojson"),
    ]
    aoi_dest = os.path.join(cache_dir, "fire_monitoring_aoi.geojson")
    for cand in aoi_candidates:
        if os.path.exists(cand):
            try:
                shutil.copyfile(cand, aoi_dest)
                print(f"AOI geometry copied from {cand}")
                break
            except Exception as e:
                print(f"Note copying AOI: {e}")
                
    # 2. Vectorize real Burn Severity (BS) masks
    bs_meta_path = os.path.join(base_dir, "train", "bs", "meta.csv")
    bs_masks_dir = os.path.join(base_dir, "train", "bs", "masks")
    
    contours_features = []
    if os.path.exists(bs_meta_path) and os.path.exists(bs_masks_dir):
        bs_meta = pd.read_csv(bs_meta_path)
        # Select representative chips from both UTM 38 and UTM 37 with varied burn sizes
        chips_38 = bs_meta[bs_meta['epsg'] == 32638].sort_values('burn_area_ha', ascending=False).head(5)
        chips_37 = bs_meta[bs_meta['epsg'] == 32637].sort_values('burn_area_ha', ascending=False).head(5)
        selected_bs = pd.concat([chips_38, chips_37])
        
        contour_counter = 0
        for _, row in selected_bs.iterrows():
            chip_id = row['chip_id']
            mask_file = os.path.join(bs_masks_dir, f"{chip_id}_MASK.tif")
            if not os.path.exists(mask_file):
                continue
                
            mask, transform, epsg = read_mask_and_transform(mask_file)
            fc = mask_to_geojson(mask, transform, epsg_in=row['epsg'], chip_id=chip_id)
            
            # Map date into the 2025 monitoring season (April - October)
            date_post = str(row['date_post']) if pd.notna(row['date_post']) else "2019-07-15"
            date_2025 = f"2025-{date_post[5:10]}" if len(date_post) >= 10 else "2025-07-15"
            
            for f in fc.get("features", []):
                # Filter out small noise (< 3.0 ha) and round coords to 5 decimals for snappy web map
                if f["properties"]["area_ha"] < 3.0:
                    continue
                contour_counter += 1
                f["properties"]["contour_id"] = f"contour_{contour_counter:04d}"
                f["properties"]["fire_event_id"] = str(row["fire_event_id"]) if pd.notna(row["fire_event_id"]) else "FE01000"
                f["properties"]["date"] = date_2025
                f["properties"]["satellite"] = "Sentinel-2 MSI"
                f["properties"]["source_chip"] = chip_id
                
                # Round coordinates to 5 decimals (~1.1m precision)
                coords = f["geometry"]["coordinates"]
                rounded_coords = [[[round(pt[0], 5), round(pt[1], 5)] for pt in ring] for ring in coords]
                f["geometry"]["coordinates"] = rounded_coords
                contours_features.append(f)
                
        print(f"Generated {len(contours_features)} burn severity contours from real S2 masks")
    else:
        print("Warning: BS train masks not found, creating synthetic fallback contours")
        contours_features = [
            {
                "type": "Feature",
                "properties": {
                    "contour_id": "contour_0001",
                    "class_id": 2,
                    "severity": "средняя",
                    "area_ha": 450.0,
                    "color": "#FB923C",
                    "date": "2025-06-15",
                    "fire_event_id": "FE00657",
                    "satellite": "Sentinel-2 MSI"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[43.4, 48.4], [43.6, 48.4], [43.6, 48.6], [43.4, 48.6], [43.4, 48.4]]]
                }
            }
        ]

    contours_fc = {
        "type": "FeatureCollection",
        "name": "burned_area_contours",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": contours_features
    }
    with open(os.path.join(cache_dir, "contours.geojson"), "w", encoding="utf-8") as f:
        json.dump(contours_fc, f, ensure_ascii=False, indent=2)

    # 3. Extract real Active Fire (AF) thermopoints from VIIRS chips
    af_meta_path = os.path.join(base_dir, "train", "af", "meta.csv")
    af_masks_dir = os.path.join(base_dir, "train", "af", "masks")
    
    tp_features = []
    if os.path.exists(af_meta_path) and os.path.exists(af_masks_dir):
        af_meta = pd.read_csv(af_meta_path)
        af_fires = af_meta[af_meta['n_fire_px'] > 0].head(18)
        
        np.random.seed(42)
        tp_counter = 0
        for _, row in af_fires.iterrows():
            chip_id = row['chip_id']
            mask_file = os.path.join(af_masks_dir, f"{chip_id}_MASK.tif")
            if not os.path.exists(mask_file):
                continue
                
            img = Image.open(mask_file)
            arr = np.array(img)
            fire_rows, fire_cols = np.where(arr > 0)
            if len(fire_rows) == 0:
                continue
                
            epsg = row['epsg']
            zone = 37 if epsg == 32637 else 38
            x_min = float(row['x_min'])
            y_max = float(row['y_max'])
            gsd = float(row['gsd']) if pd.notna(row['gsd']) else 375.0
            
            acq_orig = str(row['acq_datetime']) if pd.notna(row['acq_datetime']) else "2019-07-15T10:30:00+00:00"
            date_part = acq_orig[5:10] if len(acq_orig) >= 10 else "07-15"
            time_part = acq_orig[10:] if len(acq_orig) > 10 else "T10:30:00Z"
            date_2025 = f"2025-{date_part}"
            datetime_2025 = f"2025-{date_part}{time_part}"
            sat_name = str(row['satellite']) if pd.notna(row['satellite']) else "SNPP"
            
            step = max(1, len(fire_rows) // 6)
            for i in range(0, len(fire_rows), step):
                r, c = int(fire_rows[i]), int(fire_cols[i])
                utm_x = x_min + (c + 0.5) * gsd
                utm_y = y_max - (r + 0.5) * gsd
                lon, lat = utm_to_wgs84(utm_x, utm_y, zone=zone)
                
                tp_counter += 1
                tp_features.append({
                    "type": "Feature",
                    "properties": {
                        "id": f"TP_{tp_counter:04d}",
                        "chip_id": chip_id,
                        "satellite": f"{sat_name} (VIIRS)",
                        "acq_datetime": datetime_2025,
                        "date": date_2025,
                        "confidence": round(float(np.random.uniform(86.0, 99.4)), 1),
                        "brightness_k": round(float(np.random.uniform(328.0, 365.0)), 1),
                        "frp_mw": round(float(np.random.uniform(14.0, 92.5)), 1)
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    }
                })
                
        print(f"Generated {len(tp_features)} active fire hotspots from real VIIRS masks")
    else:
        print("Warning: AF train masks not found, creating synthetic fallback thermopoints")
        tp_features = [
            {
                "type": "Feature",
                "properties": {
                    "id": "TP_0001",
                    "satellite": "SNPP (VIIRS)",
                    "acq_datetime": "2025-06-15T11:20:00Z",
                    "date": "2025-06-15",
                    "confidence": 95.0,
                    "brightness_k": 345.5,
                    "frp_mw": 38.2
                },
                "geometry": {"type": "Point", "coordinates": [43.5, 48.5]}
            }
        ]

    tp_fc = {
        "type": "FeatureCollection",
        "name": "active_fire_hotspots",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": tp_features
    }
    with open(os.path.join(cache_dir, "thermopoints.geojson"), "w", encoding="utf-8") as f:
        json.dump(tp_fc, f, ensure_ascii=False, indent=2)

    # 4. Generate analytics report
    report = report_from_contours(contours_features, len(tp_features))
    report["monitoring_region"] = "Нижнее Поволжье и Подонье"
    report["aoi_area_km2"] = 435273
    report["seasons"] = "2025 (апрель–октябрь)"
    
    with open(os.path.join(cache_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"demo_cache ready: {len(contours_features)} contours, {len(tp_features)} thermopoints, total burned: {report['total_ha']} ha")

if __name__ == "__main__":
    prepare_demo()