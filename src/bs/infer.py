import os
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from src.common.rle import rle_encode
from .dataset import BSDataset
from .model import build_bs_model

def infer_bs(data_root, test_dir, weights_dir, device="cuda"):
    device = "cuda" if (device == "cuda" and torch.cuda.is_available()) else ("cuda" if torch.cuda.is_available() else "cpu")
    sample = pd.read_csv(os.path.join(test_dir, "sample_submission.csv"))
    bs_ids = sample[sample["chip_id"].str.startswith("BS_")]["chip_id"].unique().tolist()

    ds = BSDataset(test_dir, "test", bs_ids, augment=False)

    models = []
    if os.path.exists(weights_dir):
        for f in sorted(os.listdir(weights_dir)):
            if f.startswith("bs_fold") and f.endswith(".pt"):
                weight_path = os.path.join(weights_dir, f)
                try:
                    in_ch = ds[0][0].shape[0]
                    m = build_bs_model(in_channels=in_ch).to(device)
                    m.load_state_dict(torch.load(weight_path, map_location=device))
                    m.eval()
                    models.append(m)
                except Exception as e:
                    print(f"Warning loading {f}: {e}")

    rows = []
    if len(models) > 0:
        dl = DataLoader(ds, batch_size=8, shuffle=False, num_workers=0)
        idx = 0
        with torch.no_grad():
            for x, _ in dl:
                x = x.to(device)
                with torch.cuda.amp.autocast(enabled=(device == "cuda")):
                    probs = torch.stack([torch.softmax(m(x), dim=1) for m in models]).mean(0)
                preds = torch.argmax(probs, dim=1).cpu().numpy().astype(np.uint8)
                for b in range(preds.shape[0]):
                    cid = bs_ids[idx]
                    idx += 1
                    for cls in (1, 2, 3):
                        m = (preds[b] == cls).astype(np.uint8)
                        rows.append({"chip_id": cid, "class_id": cls, "rle": rle_encode(m)})
    else:
        # Heuristic fallback по спектральному индексу dNBR (Sentinel-2 B8A и B12)
        for cid in bs_ids:
            pre_p = os.path.join(ds.s2_pre, f"{cid}_Sentinel-2_pre.tif")
            post_p = os.path.join(ds.s2_post, f"{cid}_Sentinel-2_post.tif")
            if os.path.exists(pre_p) and os.path.exists(post_p):
                p_arr = ds._read(pre_p)
                q_arr = ds._read(post_p)
                # B8A: index 6, B12: index 8
                b8ap, b12p = p_arr[6], p_arr[8]
                b8aq, b12q = q_arr[6], q_arr[8]
                nbr_p = (b8ap - b12p) / (b8ap + b12p + 1e-6)
                nbr_q = (b8aq - b12q) / (b8aq + b12q + 1e-6)
                dnbr = nbr_p - nbr_q
                pred = np.zeros(dnbr.shape, dtype=np.uint8)
                pred[(dnbr >= 0.10) & (dnbr < 0.27)] = 1
                pred[(dnbr >= 0.27) & (dnbr < 0.44)] = 2
                pred[dnbr >= 0.44] = 3
            else:
                pred = np.zeros((512, 512), dtype=np.uint8)
            for cls in (1, 2, 3):
                m = (pred == cls).astype(np.uint8)
                rows.append({"chip_id": cid, "class_id": cls, "rle": rle_encode(m)})

    return rows