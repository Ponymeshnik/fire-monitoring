import os
import numpy as np
import torch
from torch.utils.data import DataLoader
from src.common.rle import rle_encode
from .dataset import AFDataset
from .model import build_af_model

def infer_af(data_root, test_dir, out_csv, weights_dir, device="cuda"):
    import pandas as pd
    sample = pd.read_csv(os.path.join(test_dir, "sample_submission.csv"))
    af_ids = sample[sample["chip_id"].str.startswith("AF_")]["chip_id"].tolist()

    ds = AFDataset(data_root, "test", af_ids, augment=False)
    # временно подменяем пути на тестовые
    ds.viirs_dir = os.path.join(test_dir, "viirs")
    ds.aux_dir = os.path.join(test_dir, "aux")
    dl = DataLoader(ds, batch_size=8, shuffle=False, num_workers=4)

    first = next(iter(dl))[0]
    model = build_af_model(in_channels=first.shape[1]).to(device)
    # ансамбль
    models = []
    for f in sorted(os.listdir(weights_dir)):
        if f.startswith("af_fold") and f.endswith(".pt"):
            m = build_af_model(in_channels=first.shape[1]).to(device)
            m.load_state_dict(torch.load(os.path.join(weights_dir, f), map_location=device))
            m.eval(); models.append(m)

    rows = []
    with torch.no_grad():
        for x, _ in dl:
            x = x.to(device)
            probs = torch.stack([torch.sigmoid(m(x)) for m in models]).mean(0)
            preds = (probs > 0.5).cpu().numpy().astype(np.uint8)[:, 0]
            for i, cid in enumerate(ds.ids):
                # ds.ids мог быть пересортирован; сопоставим по индексу
                pass
    # Проще: перебрать по одному
    for cid in af_ids:
        ds_one = AFDataset(data_root, "test", [cid], augment=False)
        ds_one.viirs_dir = os.path.join(test_dir, "viirs")
        ds_one.aux_dir = os.path.join(test_dir, "aux")
        x, _ = ds_one[0]
        x = x.unsqueeze(0).to(device)
        with torch.no_grad():
            probs = torch.stack([torch.sigmoid(m(x)) for m in models]).mean(0)
        pred = (probs > 0.5).cpu().numpy().astype(np.uint8)[0, 0]
        rows.append({"chip_id": cid, "class_id": 1, "rle": rle_encode(pred)})
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    return df