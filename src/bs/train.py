import os, yaml, argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
try:
    from sklearn.model_selection import GroupKFold
except ImportError:
    from src.common.split import GroupKFold
import pandas as pd
from tqdm import tqdm

from src.common.seed import set_seed
from src.common.metrics import iou_burn, miou_sev
from .dataset import BSDataset
from .model import build_bs_model

def ce_dice(logits, targets, num_classes=4):
    ce = nn.functional.cross_entropy(logits, targets)
    probs = torch.softmax(logits, dim=1)
    dice = 0.0
    for c in range(1, num_classes):
        pc = probs[:, c]
        gc = (targets == c).float()
        num = 2 * (pc * gc).sum() + 1e-6
        den = pc.sum() + gc.sum() + 1e-6
        dice += 1 - num / den
    return ce + dice / (num_classes - 1)

def train_one(cfg, fold, train_ids, val_ids):
    set_seed(cfg["seed"] + fold)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ds_tr = BSDataset(cfg["data_root"], "train", train_ids, augment=True)
    ds_va = BSDataset(cfg["data_root"], "train", val_ids, augment=False)
    batch_size = cfg.get("batch_size", 4)
    dl_tr = DataLoader(ds_tr, batch_size=batch_size, shuffle=True, num_workers=0)
    dl_va = DataLoader(ds_va, batch_size=batch_size, shuffle=False, num_workers=0)

    in_channels = ds_tr[0][0].shape[0]
    model = build_bs_model(in_channels=in_channels).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=1e-4)
    epochs = cfg.get("epochs", 30)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    scaler = torch.cuda.amp.GradScaler(enabled=(device == "cuda"))

    best = -1.0
    for epoch in range(epochs):
        model.train()
        for x, y in tqdm(dl_tr, desc=f"BS fold{fold} ep{epoch}"):
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            with torch.cuda.amp.autocast(enabled=(device == "cuda")):
                logits = model(x)
                loss = ce_dice(logits, y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
        sched.step()

        model.eval()
        preds, gts = [], []
        with torch.no_grad():
            for x, y in dl_va:
                x = x.to(device)
                with torch.cuda.amp.autocast(enabled=(device == "cuda")):
                    out = model(x)
                p = torch.argmax(out, dim=1).cpu().numpy().astype(np.uint8)
                preds.append(p); gts.append(y.numpy().astype(np.uint8))
        iou_b = iou_burn(preds, gts)
        mious = miou_sev(preds, gts)
        sc = 0.35 * iou_b + 0.30 * mious
        print(f"BS fold{fold} ep{epoch} IoU_burn={iou_b:.4f} mIoU_sev={mious:.4f} score_part={sc:.4f}")
        if sc >= best or epoch == 0:
            best = max(best, sc)
            os.makedirs(cfg["weights_dir"], exist_ok=True)
            torch.save(model.state_dict(), os.path.join(cfg["weights_dir"], f"bs_fold{fold}.pt"))
    return best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/bs.yaml")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--fold", type=int, default=None, help="Train only specified fold (e.g. 0)")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    if args.epochs is not None:
        cfg["epochs"] = args.epochs
    if args.batch_size is not None:
        cfg["batch_size"] = args.batch_size

    meta_p = os.path.join(cfg["data_root"], "bs", "meta_bs.csv")
    if not os.path.exists(meta_p):
        meta_p = os.path.join(cfg["data_root"], "bs", "meta.csv")
    meta = pd.read_csv(meta_p)
    groups = meta["fire_event_id"].values
    gkf = GroupKFold(n_splits=cfg["n_folds"])
    scores = []
    for fold, (tr, va) in enumerate(gkf.split(meta, groups=groups)):
        if args.fold is not None and fold != args.fold:
            continue
        tr_ids = meta.iloc[tr]["chip_id"].tolist()
        va_ids = meta.iloc[va]["chip_id"].tolist()
        scores.append(train_one(cfg, fold, tr_ids, va_ids))
    print("BS CV mean score_part:", np.mean(scores))

if __name__ == "__main__":
    main()