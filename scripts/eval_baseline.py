import os, sys
sys.path.insert(0, os.path.abspath('.'))
import numpy as np
import pandas as pd
import tifffile
from src.common.metrics import f1_af, iou_burn, miou_sev, score

def evaluate_af_baseline(max_chips=100):
    af_meta = pd.read_csv('train/af/meta.csv')
    cids = af_meta['chip_id'].tolist()[:max_chips]
    preds = []
    gts = []
    for cid in cids:
        vp = f'train/af/viirs/{cid}_VIIRS_I1-I5.tif'
        mp = f'train/af/masks/{cid}_mask.tif'
        if not os.path.exists(vp) or not os.path.exists(mp):
            continue
        v = tifffile.imread(vp)
        m = tifffile.imread(mp)
        if v.ndim == 3 and v.shape[2] >= 5:
            I1, I2, I3, I4, I5 = v[:,:,0], v[:,:,1], v[:,:,2], v[:,:,3], v[:,:,4]
        else:
            I1, I2, I3, I4, I5 = v[0], v[1], v[2], v[3], v[4]
        # Baseline threshold heuristic
        pred = ((I4 > 325.0) & ((I4 - I5) > 12.0) & ((I3 - I2) < 0.25)).astype(np.uint8)
        preds.append(pred)
        gts.append((m > 0).astype(np.uint8))
    f1 = f1_af(preds, gts)
    print(f'AF Baseline Heuristic F1 ({len(preds)} chips): {f1:.4f}')
    return f1

def evaluate_bs_baseline(max_chips=50):
    bs_meta = pd.read_csv('train/bs/meta.csv')
    cids = bs_meta['chip_id'].tolist()[:max_chips]
    preds = []
    gts = []
    for cid in cids:
        prep = f'train/bs/sentinel2_pre/{cid}_Sentinel-2_pre.tif'
        postp = f'train/bs/sentinel2_post/{cid}_Sentinel-2_post.tif'
        mp = f'train/bs/masks/{cid}_mask.tif'
        if not os.path.exists(prep) or not os.path.exists(postp) or not os.path.exists(mp):
            continue
        pre = tifffile.imread(prep)
        post = tifffile.imread(postp)
        m = tifffile.imread(mp)
        
        if pre.ndim == 3 and pre.shape[2] >= 9:
            b8ap, b12p = pre[:,:,6].astype(float), pre[:,:,8].astype(float)
            b8aq, b12q = post[:,:,6].astype(float), post[:,:,8].astype(float)
        else:
            b8ap, b12p = pre[6].astype(float), pre[8].astype(float)
            b8aq, b12q = post[6].astype(float), post[8].astype(float)
            
        nbr_p = (b8ap - b12p) / (b8ap + b12p + 1e-6)
        nbr_q = (b8aq - b12q) / (b8aq + b12q + 1e-6)
        dnbr = nbr_p - nbr_q
        
        pred = np.zeros(dnbr.shape, dtype=np.uint8)
        pred[(dnbr >= 0.10) & (dnbr < 0.27)] = 1
        pred[(dnbr >= 0.27) & (dnbr < 0.44)] = 2
        pred[dnbr >= 0.44] = 3
        
        preds.append(pred)
        gts.append(m.astype(np.uint8))
        
    iou_b = iou_burn(preds, gts)
    mious = miou_sev(preds, gts)
    print(f'BS Baseline Heuristic IoU_burn: {iou_b:.4f}, mIoU_sev: {mious:.4f}')
    return iou_b, mious

if __name__ == '__main__':
    f1 = evaluate_af_baseline(150)
    iou_b, mious = evaluate_bs_baseline(80)
    sc = score(f1, iou_b, mious)
    print(f'Baseline Overall Score: {sc:.4f}')
