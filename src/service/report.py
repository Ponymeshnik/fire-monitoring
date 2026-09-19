import numpy as np

def area_report(mask, gsd_m=20.0, classes=(1, 2, 3)):
    """
    Accurate burned area calculation based on pixel resolution (GSD).
    For Sentinel-2 standard 20x20 m resolution:
      Pixel area = 20 * 20 = 400 m² = 0.04 ha (400 / 10000).
    
    Parameters:
      mask: 2D numpy array with integer class values (0: background, 1: low, 2: medium, 3: high)
      gsd_m: Ground Sampling Distance in meters (default: 20.0 m)
      classes: Tuple of burn severity class IDs (default: (1, 2, 3))
      
    Returns:
      dict with total_ha, breakdown by severity (ha and %), and pixel counts.
    """
    px_area_ha = (gsd_m ** 2) / 10000.0
    total_px = int((mask > 0).sum())
    total_ha = round(float(total_px * px_area_ha), 2)
    
    sev_names = {1: "слабая", 2: "средняя", 3: "сильная"}
    out = {
        "gsd_m": float(gsd_m),
        "pixel_area_ha": px_area_ha,
        "total_px": total_px,
        "total_ha": total_ha,
    }
    
    breakdown = {}
    for c in classes:
        px = int((mask == c).sum())
        ha = round(float(px * px_area_ha), 2)
        pct = round(float((ha / total_ha * 100.0)) if total_ha > 0 else 0.0, 1)
        out[f"sev{c}_px"] = px
        out[f"sev{c}_ha"] = ha
        out[f"sev{c}_pct"] = pct
        breakdown[sev_names.get(c, str(c))] = {
            "class_id": c,
            "severity": sev_names.get(c, str(c)),
            "pixels": px,
            "area_ha": ha,
            "percentage": pct
        }
        
    out["breakdown"] = breakdown
    out["unit"] = "hectares"
    return out


def report_from_contours(features, total_thermopoints=0):
    """
    Compute summary analytics report directly from a list of GeoJSON features.
    """
    sev1_ha = 0.0
    sev2_ha = 0.0
    sev3_ha = 0.0
    
    for f in features:
        props = f.get("properties", {})
        cid = props.get("class_id", 0)
        ha = float(props.get("area_ha", 0.0))
        if cid == 1:
            sev1_ha += ha
        elif cid == 2:
            sev2_ha += ha
        elif cid == 3:
            sev3_ha += ha
            
    total_ha = round(sev1_ha + sev2_ha + sev3_ha, 2)
    sev1_ha = round(sev1_ha, 2)
    sev2_ha = round(sev2_ha, 2)
    sev3_ha = round(sev3_ha, 2)
    
    sev1_pct = round((sev1_ha / total_ha * 100.0) if total_ha > 0 else 0.0, 1)
    sev2_pct = round((sev2_ha / total_ha * 100.0) if total_ha > 0 else 0.0, 1)
    sev3_pct = round((sev3_ha / total_ha * 100.0) if total_ha > 0 else 0.0, 1)
    
    return {
        "total_ha": total_ha,
        "sev1_ha": sev1_ha,
        "sev2_ha": sev2_ha,
        "sev3_ha": sev3_ha,
        "sev1_pct": sev1_pct,
        "sev2_pct": sev2_pct,
        "sev3_pct": sev3_pct,
        "total_contours": len(features),
        "total_thermopoints": total_thermopoints,
        "breakdown": {
            "слабая": {"class_id": 1, "severity": "слабая", "area_ha": sev1_ha, "percentage": sev1_pct},
            "средняя": {"class_id": 2, "severity": "средняя", "area_ha": sev2_ha, "percentage": sev2_pct},
            "сильная": {"class_id": 3, "severity": "сильная", "area_ha": sev3_ha, "percentage": sev3_pct},
        },
        "unit": "hectares"
    }