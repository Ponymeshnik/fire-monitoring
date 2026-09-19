import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import argparse
import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from src.common.seed import set_seed
from src.common.io import read_tif
from src.common.metrics import f1_af, iou_burn, miou_sev, score
from src.common.split import GroupKFold
from src.af.dataset import AFDataset
from src.af.model import build_af_model
from src.bs.dataset import BSDataset
from src.bs.model import build_bs_model

def evaluate_af(data_root="train", weights_path="weights/af/af_fold0.pt", out_dir="visualizations/af", n_vis=5):
    os.makedirs(out_dir, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    meta_p = os.path.join(data_root, "af", "meta_af.csv")
    if not os.path.exists(meta_p):
        meta_p = os.path.join(data_root, "af", "meta.csv")
    meta = pd.read_csv(meta_p)

    groups = meta["acq_datetime"].astype(str).str[:10].values if "acq_datetime" in meta.columns else np.arange(len(meta))
    gkf = GroupKFold(n_splits=4, seed=42)
    _, val_idx = next(gkf.split(meta, groups=groups))
    val_ids = meta.iloc[val_idx]["chip_id"].tolist()

    ds_va = AFDataset(data_root, "val", val_ids, augment=False)
    model = build_af_model(in_channels=16).to(device)
    if os.path.exists(weights_path):
        model.load_state_dict(torch.load(weights_path, map_location=device))
        print(f"[AF] Loaded weights from {weights_path}")
    else:
        print(f"[AF] Weights not found at {weights_path}, using heuristic")

    model.eval()
    preds, gts = [], []
    saved_vis = 0

    with torch.no_grad():
        for i in range(len(ds_va)):
            x, y = ds_va[i]
            cid = ds_va.ids[i]
            x_gpu = x.unsqueeze(0).to(device)
            is_hot = (x_gpu[:, 3] > 325.0) & (x_gpu[:, 5] > 12.0) & (x_gpu[:, 6] < 0.25)
            mu = x_gpu.mean(dim=(2, 3), keepdim=True)
            sd = x_gpu.std(dim=(2, 3), keepdim=True) + 1e-6
            x_gpu = (x_gpu - mu) / sd

            with torch.cuda.amp.autocast(enabled=(device == "cuda")):
                out = model(x_gpu)
            p = ((torch.sigmoid(out)[:, 0] > 0.35) | is_hot).cpu().numpy().astype(np.uint8)[0]
            gt = y.numpy()[0].astype(np.uint8)

            preds.append(p)
            gts.append(gt)

            # Сохранение визуализации для чипов, где есть горение
            if gt.sum() > 0 and saved_vis < n_vis:
                saved_vis += 1
                viirs_raw = ds_va._read(os.path.join(ds_va.viirs_dir, f"{cid}_VIIRS_I1-I5.tif"))
                I4 = viirs_raw[3]
                I5 = viirs_raw[4]
                diff = I4 - I5

                fig, axes = plt.subplots(1, 3, figsize=(15, 5))
                # 1. Thermal radiance (I4 - I5)
                im0 = axes[0].imshow(diff, cmap="inferno")
                axes[0].set_title(f"VIIRS I4 - I5 (K)\n{cid}", fontsize=11)
                plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

                # 2. Ground Truth
                axes[1].imshow(diff, cmap="gray", alpha=0.6)
                axes[1].imshow(np.ma.masked_where(gt == 0, gt), cmap="spring", alpha=0.9)
                axes[1].set_title(f"Ground Truth ({gt.sum()} px)", fontsize=11)

                # 3. Model Prediction
                axes[2].imshow(diff, cmap="gray", alpha=0.6)
                axes[2].imshow(np.ma.masked_where(p == 0, p), cmap="autumn", alpha=0.9)
                tp = int(((p == 1) & (gt == 1)).sum())
                axes[2].set_title(f"Prediction (TP={tp}, Pred={p.sum()})", fontsize=11)

                for ax in axes:
                    ax.axis("off")
                plt.tight_layout()
                fig_path = os.path.join(out_dir, f"af_val_{cid}.png")
                plt.savefig(fig_path, dpi=150)
                plt.close()

    f1 = f1_af(preds, gts)
    print(f"[AF] Validation Set: {len(val_ids)} chips | F1 Score = {f1:.4f}")
    return f1

def evaluate_bs(data_root="train", weights_path="weights/bs/bs_fold0.pt", out_dir="visualizations/bs", n_vis=5):
    os.makedirs(out_dir, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    meta_p = os.path.join(data_root, "bs", "meta_bs.csv")
    if not os.path.exists(meta_p):
        meta_p = os.path.join(data_root, "bs", "meta.csv")
    meta = pd.read_csv(meta_p)

    groups = meta["fire_event_id"].values
    gkf = GroupKFold(n_splits=4, seed=42)
    _, val_idx = next(gkf.split(meta, groups=groups))
    val_ids = meta.iloc[val_idx]["chip_id"].tolist()

    ds_va = BSDataset(data_root, "val", val_ids, augment=False)
    model = build_bs_model(in_channels=37).to(device)
    if os.path.exists(weights_path):
        model.load_state_dict(torch.load(weights_path, map_location=device))
        print(f"[BS] Loaded weights from {weights_path}")
    else:
        print(f"[BS] Weights not found at {weights_path}")

    model.eval()
    preds, gts = [], []
    saved_vis = 0

    cmap_sev = mcolors.ListedColormap(["none", "#FFD700", "#FF8C00", "#8B0000"])
    bounds = [0, 0.5, 1.5, 2.5, 3.5]
    norm_sev = mcolors.BoundaryNorm(bounds, cmap_sev.N)

    with torch.no_grad():
        for i in range(len(ds_va)):
            x, y = ds_va[i]
            cid = ds_va.ids[i]
            x_gpu = x.unsqueeze(0).to(device)
            mu = x_gpu.mean(dim=(2, 3), keepdim=True)
            sd = x_gpu.std(dim=(2, 3), keepdim=True) + 1e-6
            x_gpu = (x_gpu - mu) / sd

            with torch.cuda.amp.autocast(enabled=(device == "cuda")):
                out = model(x_gpu)
            p = torch.argmax(out, dim=1).cpu().numpy().astype(np.uint8)[0]
            gt = y.numpy().astype(np.uint8)

            preds.append(p)
            gts.append(gt)

            # Сохранение визуализации для чипов с гарью
            if (gt > 0).sum() > 500 and saved_vis < n_vis:
                saved_vis += 1
                s2_post = ds_va._read(os.path.join(ds_va.s2_post, f"{cid}_Sentinel-2_post.tif"))
                # RGB B4(2), B3(1), B2(0)
                rgb = np.stack([s2_post[2], s2_post[1], s2_post[0]], axis=-1)
                rgb = np.clip(rgb / 3000.0, 0, 1)

                fig, axes = plt.subplots(1, 3, figsize=(18, 6))
                axes[0].imshow(rgb)
                axes[0].set_title(f"Sentinel-2 Post RGB (B4,B3,B2)\n{cid}", fontsize=11)

                axes[1].imshow(rgb, alpha=0.6)
                axes[1].imshow(np.ma.masked_where(gt == 0, gt), cmap=cmap_sev, norm=norm_sev, alpha=0.85)
                axes[1].set_title(f"Ground Truth Severity\n(Total burned: {(gt > 0).sum() * 0.04:.1f} ha)", fontsize=11)

                axes[2].imshow(rgb, alpha=0.6)
                axes[2].imshow(np.ma.masked_where(p == 0, p), cmap=cmap_sev, norm=norm_sev, alpha=0.85)
                axes[2].set_title(f"Predicted Severity\n(Total burned: {(p > 0).sum() * 0.04:.1f} ha)", fontsize=11)

                for ax in axes:
                    ax.axis("off")
                plt.tight_layout()
                fig_path = os.path.join(out_dir, f"bs_val_{cid}.png")
                plt.savefig(fig_path, dpi=150)
                plt.close()

    iou_b = iou_burn(preds, gts)
    mious = miou_sev(preds, gts)
    sc = 0.35 * iou_b + 0.30 * mious
    print(f"[BS] Validation Set: {len(val_ids)} chips | IoU_burn = {iou_b:.4f} | mIoU_sev = {mious:.4f} | BS Score = {sc:.4f}")
    return iou_b, mious, sc

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="train")
    parser.add_argument("--n-vis", type=int, default=5, help="Number of visualization images to save per module")
    args = parser.parse_args()

    set_seed(42)
    print("=" * 60)
    print("  ОЦЕНКА КАЧЕСТВА МОДЕЛЕЙ И ГЕНЕРАЦИЯ ВИЗУАЛИЗАЦИЙ")
    print("=" * 60)

    f1 = evaluate_af(data_root=args.data_root, n_vis=args.n_vis)
    print("-" * 60)
    iou_b, mious, sc = evaluate_bs(data_root=args.data_root, n_vis=args.n_vis)
    print("=" * 60)

    total_score = score(f1, iou_b, mious)
    print(f"ИТОГОВАЯ КОМПОЗИТНАЯ МЕТРИКА ХАКАТОНА:")
    print(f"Score = 0.35 * F1_af ({f1:.4f}) + 0.35 * IoU_burn ({iou_b:.4f}) + 0.30 * mIoU_sev ({mious:.4f})")
    print(f"--> FINAL SCORE = {total_score:.4f} <--")
    print("=" * 60)
    print(f"Визуальные сравнения сохранены в:")
    print(f"  - visualizations/af/")
    print(f"  - visualizations/bs/")

if __name__ == "__main__":
    main()
