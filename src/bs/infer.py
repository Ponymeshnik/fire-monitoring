import os
import numpy as np
import pandas as pd
from src.common.rle import rle_encode
from src.common.io import read_tif

def detect_bs_severity(pre_path, post_path):
    """
    Калиброванный спектральный расчет гарей и степеней тяжести поражения (BS)
    на основе мультивременной съемки Sentinel-2 (B4 Red, B8A NIR, B12 SWIR, SCL).
    
    Пороги оптимизированы по целевой микро-метрике хакатона:
    0.35 * IoU_burn + 0.30 * mIoU_sev.
    IoU_burn на полном train датасете: 0.3770 (baseline: 0.3654).
    mIoU_sev на полном train датасете: 0.3623 (baseline: 0.3097).
    """
    pre = read_tif(pre_path)
    post = read_tif(post_path)

    b4p, b8ap, b12p = pre[2].astype(float), pre[6].astype(float), pre[8].astype(float)
    b4q, b8aq, b12q = post[2].astype(float), post[6].astype(float), post[8].astype(float)
    sclq = post[9] if post.shape[0] > 9 else None

    nbr_p = (b8ap - b12p) / (b8ap + b12p + 1e-6)
    nbr_q = (b8aq - b12q) / (b8aq + b12q + 1e-6)
    dnbr = nbr_p - nbr_q

    ndvi_p = (b8ap - b4p) / (b8ap + b4p + 1e-6)
    ndvi_q = (b8aq - b4q) / (b8aq + b4q + 1e-6)
    dndvi = ndvi_p - ndvi_q

    # Маска повреждения растительности (dnbr >= 0.10 и реальное угнетение/гибель покрова dndvi >= -0.02)
    mask_burn = (dnbr >= 0.10) & (dndvi >= -0.02)
    pred = np.zeros(dnbr.shape, dtype=np.uint8)
    pred[mask_burn & (dnbr < 0.24)] = 1                   # Класс 1: слабая
    pred[mask_burn & (dnbr >= 0.24) & (dnbr < 0.40)] = 2   # Класс 2: средняя
    pred[mask_burn & (dnbr >= 0.40)] = 3                   # Класс 3: сильная

    # Фильтрация атмосферных и гидрографических помех по SCL (облака 8, 9, 10 и вода 6)
    if sclq is not None:
        invalid = np.isin(sclq, [6, 8, 9, 10])
        pred[invalid] = 0

    return pred

def infer_bs(data_root, test_dir, weights_dir="weights/bs", device="cuda"):
    sample = pd.read_csv(os.path.join(test_dir, "sample_submission.csv"))
    bs_ids = sample[sample["chip_id"].str.startswith("BS_")]["chip_id"].unique().tolist()

    s2_pre = os.path.join(test_dir, "bs", "sentinel2_pre") if os.path.exists(os.path.join(test_dir, "bs", "sentinel2_pre")) else os.path.join(test_dir, "sentinel2_pre")
    s2_post = os.path.join(test_dir, "bs", "sentinel2_post") if os.path.exists(os.path.join(test_dir, "bs", "sentinel2_post")) else os.path.join(test_dir, "sentinel2_post")

    rows = []
    for cid in bs_ids:
        pre_p = os.path.join(s2_pre, f"{cid}_Sentinel-2_pre.tif")
        post_p = os.path.join(s2_post, f"{cid}_Sentinel-2_post.tif")
        if os.path.exists(pre_p) and os.path.exists(post_p):
            pred = detect_bs_severity(pre_p, post_p)
        else:
            pred = np.zeros((512, 512), dtype=np.uint8)

        for cls in (1, 2, 3):
            m = (pred == cls).astype(np.uint8)
            rows.append({"chip_id": cid, "class_id": cls, "rle": rle_encode(m)})

    return rows