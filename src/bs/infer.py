import os
import numpy as np
import torch
from src.common.rle import rle_encode
from .dataset import BSDataset
from .model import build_bs_model

def infer_bs(data_root, test_dir, weights_dir, device="cuda"):
    import pandas as pd
    sample = pd.read_csv(os.path.join(test_dir, "sample_submission.csv"))
    bs_ids = sample[sample["chip_id"].str.startswith("BS_")]["chip_id"].unique().tolist()

    first_ds = BSDataset(data_root, "test", [bs_ids[0]], augment=False)
    first_ds.s2_pre = os.path.join(test_dir, "sentinel2_pre")
    first_ds.s2_post = os.path.join(test_dir, "sentinel2_post")
    first_ds.s1_pre = os.path.join(test_dir, "sentinel1_pre")
    first_ds.s1_post = os.path.join(test_dir, "sentinel1_post")
    first_ds.aux_dir = os.path.join(test_dir, "aux")
    x, _ = first_ds[0]
    in_ch = x.shape[0]

    models = []
    for f in sorted(os.listdir(weights_dir)):
        if f.startswith("bs_fold") and f.endswith(".pt"):
            m = build_bs_model(in_channels=in_ch).to(device)
            m.load_state_dict(torch.load(os.path.join(weights_dir, f), map_location=device))
            m.eval(); models.append(m)

    rows = []
    for cid in bs_ids:
        ds = BSDataset(data_root, "test", [cid], augment=False)
        ds.s2_pre = os.path.join(test_dir, "sentinel2_pre")
        ds.s2_post = os.path.join(test_dir, "sentinel2_post")
        ds.s1_pre = os.path.join(test_dir, "sentinel1_pre")
        ds.s1_post = os.path.join(test_dir, "sentinel1_post")
        ds.aux_dir = os.path.join(test_dir, "aux")
        x, _ = ds[0]
        x = x.unsqueeze(0).to(device)
        with torch.no_grad():
            probs = torch.stack([torch.softmax(m(x), dim=1) for m in models]).mean(0)
            pred = torch.argmax(probs, dim=1).cpu().numpy()[0].astype(np.uint8)
        for cls in (1, 2, 3):
            m = (pred == cls).astype(np.uint8)
            rows.append({"chip_id": cid, "class_id": cls, "rle": rle_encode(m)})
    return rows