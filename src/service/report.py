import numpy as np

def area_report(mask, gsd_m, classes=(1, 2, 3)):
    px_area_ha = (gsd_m ** 2) / 10000.0
    out = {}
    for c in classes:
        out[f"sev{c}_ha"] = float((mask == c).sum() * px_area_ha)
    out["total_ha"] = float((mask > 0).sum() * px_area_ha)
    return out