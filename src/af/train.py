import os, yaml, argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.model_selection import GroupKFold
import pandas as pd
from tqdm import tqdm

from src.common.seed import set_seed
from src.common.metrics import f1_af
from .dataset import AFDataset
from .model import build_af_model

def focal_loss(logits, targets, alpha=0.75, gamma=2.0):
    bce = nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
    p = torch.sigmoid(logits)
    pt = p * targets + (1 - p) * (1 - targets)
    w = alpha * targets + (1 - alpha) * (1 - targets)
    return (w * (1 - pt) ** gamma * bce).mean()

def dice_loss(logits, targets, eps=1e-6):
    p = torch.sigmoid(logits)
    num = 2 * (p * targets).sum(dim=(1, 2, 3)) + eps
    den = p.sum(dim=(1, 2, 3)) + targets.sum(dim=(1, 2, 3)) + eps
    return 1 - (num / den).mean()

def train_one(cfg, fold, train_ids, val_ids):
    set_seed(cfg["seed"] + fold)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ds_tr = AFDataset(cfg["data_root"], "train", train_ids, augment=True)
    ds_va = AFDataset(cfg["data_root"], "train", val_ids, augment=False)
    dl_tr = DataLoader(ds_tr, batch_size=cfg["batch_size"], shuffle=True, num_workers=4, pin_memory=True)
    dl_va = DataLoader(ds_va, batch_size=cfg["batch_size"], shuffle=False, num_workers=4, pin_memory=True)

    model = build_af_model(in_channels=None).to(device)
    # in_channels определим на первом батче
    first = next(iter(dl_tr))[0]
    model = build_af_model(in_channels=first.shape[1]).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg["epochs"])

    best = 0.0
    for epoch in range(cfg["epochs"]):
        model.train()
        for x, y in tqdm(dl_tr, desc=f"AF fold{fold} ep{epoch}"):
            x, y = x.to(device), y.to(device)
            logits = model(x)
            loss = focal_loss(logits, y) + dice_loss(logits, y)
            opt.zero_grad(); loss.backward(); opt.step()
        sched.step()

        model.eval()
        preds, gts = [], []
        with torch.no_grad():
            for x, y in dl_va:
                x = x.to(device)
                p = (torch.sigmoid(model(x)) > 0.5).cpu().numpy().astype(np.uint8)
                preds.append(p[:, 0]); gts.append(y.numpy()[:, 0].astype(np.uint8))
        f1 = f1_af(preds, gts)
        print(f"AF fold{fold} ep{epoch} F1={f1:.4f}")
        if f1 > best:
            best = f1
            os.makedirs(cfg["weights_dir"], exist_ok=True)
            torch.save(model.state_dict(), os.path.join(cfg["weights_dir"], f"af_fold{fold}.pt"))
    return best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/af.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    meta = pd.read_csv(os.path.join(cfg["data_root"], "af", "meta_af.csv"))
    groups = meta["fire_event_id"].values
    gkf = GroupKFold(n_splits=cfg["n_folds"])
    scores = []
    for fold, (tr, va) in enumerate(gkf.split(meta, groups=groups)):
        tr_ids = meta.iloc[tr]["chip_id"].tolist()
        va_ids = meta.iloc[va]["chip_id"].tolist()
        scores.append(train_one(cfg, fold, tr_ids, va_ids))
    print("AF CV mean F1:", np.mean(scores))

if __name__ == "__main__":
    main()