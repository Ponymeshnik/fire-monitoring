import os
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from src.common.rle import rle_encode
from .dataset import AFDataset
from .model import build_af_model

def infer_af(data_root, test_dir, out_csv, weights_dir, device="cuda"):
    device = "cuda" if (device == "cuda" and torch.cuda.is_available()) else ("cuda" if torch.cuda.is_available() else "cpu")
    sample = pd.read_csv(os.path.join(test_dir, "sample_submission.csv"))
    af_ids = sample[sample["chip_id"].str.startswith("AF_")]["chip_id"].tolist()

    ds = AFDataset(test_dir, "test", af_ids, augment=False)

    models = []
    if os.path.exists(weights_dir):
        for f in sorted(os.listdir(weights_dir)):
            if f.startswith("af_fold") and f.endswith(".pt"):
                weight_path = os.path.join(weights_dir, f)
                try:
                    m = build_af_model(in_channels=16).to(device)
                    m.load_state_dict(torch.load(weight_path, map_location=device))
                    m.eval()
                    models.append(m)
                except Exception as e:
                    print(f"Warning loading {f}: {e}")

    rows = []
    if len(models) > 0:
        dl = DataLoader(ds, batch_size=32, shuffle=False, num_workers=0)
        idx = 0
        with torch.no_grad():
            for x, _ in dl:
                x = x.to(device)
                is_hot = (x[:, 3] > 325.0) & (x[:, 5] > 12.0) & (x[:, 6] < 0.25)
                mu = x.mean(dim=(2, 3), keepdim=True)
                sd = x.std(dim=(2, 3), keepdim=True) + 1e-6
                x = (x - mu) / sd
                with torch.cuda.amp.autocast(enabled=(device == "cuda")):
                    probs = torch.stack([torch.sigmoid(m(x)) for m in models]).mean(0)
                preds = ((probs[:, 0] > 0.35) | is_hot).cpu().numpy().astype(np.uint8)
                for b in range(preds.shape[0]):
                    cid = af_ids[idx]
                    idx += 1
                    rows.append({"chip_id": cid, "class_id": 1, "rle": rle_encode(preds[b])})
    else:
        # Heuristic fallback (физический порог детекции VIIRS I4 / I5)
        for cid in af_ids:
            viirs_path = os.path.join(ds.viirs_dir, f"{cid}_VIIRS_I1-I5.tif")
            if os.path.exists(viirs_path):
                v = ds._read(viirs_path)
                I1, I2, I3, I4, I5 = v[0], v[1], v[2], v[3], v[4]
                fire_mask = ((I4 > 325.0) & ((I4 - I5) > 12.0) & ((I3 - I2) < 0.25)).astype(np.uint8)
            else:
                fire_mask = np.zeros((256, 256), dtype=np.uint8)
            rows.append({"chip_id": cid, "class_id": 1, "rle": rle_encode(fire_mask)})

    df = pd.DataFrame(rows)
    if out_csv:
        out_dir = os.path.dirname(os.path.abspath(out_csv))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        df.to_csv(out_csv, index=False)
    return df