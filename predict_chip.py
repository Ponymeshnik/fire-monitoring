"""
Универсальный скрипт для запуска инференса на любом произвольном новом спутниковом снимке (VIIRS или Sentinel-2).
Использование:
  python predict_chip.py --af /path/to/VIIRS_chip.tif --output result_af.png
  python predict_chip.py --bs-pre /path/to/S2_pre.tif --bs-post /path/to/S2_post.tif --output result_bs.png
"""

import os
import argparse
import numpy as np
import torch
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from src.common.io import read_tif
from src.af.features import af_features
from src.af.model import build_af_model
from src.bs.indices import bs_features
from src.bs.model import build_bs_model

def predict_af(viirs_path, aux_path=None, weights_path="weights/af/af_fold0.pt", output="prediction_af.png"):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    v = read_tif(viirs_path)
    if aux_path and os.path.exists(aux_path):
        aux = read_tif(aux_path)
    else:
        aux = np.zeros((5, v.shape[1], v.shape[2]), dtype=np.float32)

    feats = af_features(v, aux)
    x = torch.from_numpy(feats).unsqueeze(0).to(device)

    is_hot = (x[:, 3] > 325.0) & (x[:, 5] > 12.0) & (x[:, 6] < 0.25)
    mu = x.mean(dim=(2, 3), keepdim=True)
    sd = x.std(dim=(2, 3), keepdim=True) + 1e-6
    x_norm = (x - mu) / sd

    model = build_af_model(in_channels=16).to(device)
    if os.path.exists(weights_path):
        model.load_state_dict(torch.load(weights_path, map_location=device))
    model.eval()

    with torch.no_grad():
        with torch.cuda.amp.autocast(enabled=(device == "cuda")):
            probs = torch.sigmoid(model(x_norm))
    pred = ((probs[:, 0] > 0.35) | is_hot).cpu().numpy().astype(np.uint8)[0]

    I4 = np.nan_to_num(v[3], nan=280.0)
    diff = np.nan_to_num(v[3] - v[4], nan=0.0)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    im0 = axes[0].imshow(I4, cmap="magma")
    axes[0].set_title(f"VIIRS I4 (3.74 µm) Brightness Temp (Max: {I4.max():.1f} K)")
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(diff, cmap="inferno")
    axes[1].set_title(f"Thermal Contrast I4 - I5 (Max: {diff.max():.1f} K)")
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    axes[2].imshow(I4, cmap="gray", alpha=0.6)
    axes[2].imshow(np.ma.masked_where(pred == 0, pred), cmap="autumn", alpha=0.9)
    axes[2].set_title(f"Predicted Active Fire ({pred.sum()} pixels detected)", color="darkred", fontweight="bold")

    for ax in axes:
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()

    print(f"Готово! Результат сохранен в {output}")
    print(f"Обнаружено горящих пикселей: {pred.sum()}")

def predict_bs(pre_path, post_path, s1_pre_path=None, s1_post_path=None, aux_path=None, weights_path="weights/bs/bs_fold0.pt", output="prediction_bs.png"):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    s2p = read_tif(pre_path)
    s2q = read_tif(post_path)
    H, W = s2p.shape[1], s2p.shape[2]

    # Автопоиск S1 и AUX в соседних папках если не указаны
    base_dir = os.path.dirname(os.path.dirname(pre_path))
    fname = os.path.basename(pre_path)
    cid = fname.split("_Sentinel")[0]

    if s1_pre_path is None:
        cand = os.path.join(base_dir, "sentinel1_pre", f"{cid}_Sentinel-1_pre.tif")
        if os.path.exists(cand): s1_pre_path = cand
    if s1_post_path is None:
        cand = os.path.join(base_dir, "sentinel1_post", f"{cid}_Sentinel-1_post.tif")
        if os.path.exists(cand): s1_post_path = cand
    if aux_path is None:
        cand = os.path.join(base_dir, "aux", f"{cid}_AUX.tif")
        if os.path.exists(cand): aux_path = cand

    has_full_stack = (s1_pre_path and os.path.exists(s1_pre_path) and 
                      s1_post_path and os.path.exists(s1_post_path) and 
                      aux_path and os.path.exists(aux_path))

    if has_full_stack and os.path.exists(weights_path):
        s1p = read_tif(s1_pre_path)
        s1q = read_tif(s1_post_path)
        aux = read_tif(aux_path)
        feats = bs_features(s2p, s2q, s1p, s1q, aux)
        x = torch.from_numpy(feats).unsqueeze(0).to(device)
        mu = x.mean(dim=(2, 3), keepdim=True)
        sd = x.std(dim=(2, 3), keepdim=True) + 1e-6
        x_norm = (x - mu) / sd

        model = build_bs_model(in_channels=37).to(device)
        model.load_state_dict(torch.load(weights_path, map_location=device))
        model.eval()

        with torch.no_grad():
            with torch.cuda.amp.autocast(enabled=(device == "cuda")):
                probs = torch.softmax(model(x_norm), dim=1)
        pred = torch.argmax(probs, dim=1).cpu().numpy().astype(np.uint8)[0]
    else:
        # Спектральный индекс dNBR (USGS классификация для изолированных S2 снимков)
        b8ap, b12p = s2p[6], s2p[8]
        b8aq, b12q = s2q[6], s2q[8]
        nbr_p = (b8ap - b12p) / (b8ap + b12p + 1e-6)
        nbr_q = (b8aq - b12q) / (b8aq + b12q + 1e-6)
        dnbr = nbr_p - nbr_q
        pred = np.zeros(dnbr.shape, dtype=np.uint8)
        pred[(dnbr >= 0.10) & (dnbr < 0.27)] = 1
        pred[(dnbr >= 0.27) & (dnbr < 0.44)] = 2
        pred[dnbr >= 0.44] = 3

    rgb_pre = np.clip(np.stack([s2p[2], s2p[1], s2p[0]], axis=-1) / 3000.0, 0, 1)
    rgb_post = np.clip(np.stack([s2q[2], s2q[1], s2q[0]], axis=-1) / 3000.0, 0, 1)

    cmap_sev = mcolors.ListedColormap(["none", "#FFD700", "#FF8C00", "#8B0000"])
    bounds = [0, 0.5, 1.5, 2.5, 3.5]
    norm_sev = mcolors.BoundaryNorm(bounds, cmap_sev.N)

    total_px = (pred > 0).sum()
    area_ha = total_px * 0.04
    sev1_ha = (pred == 1).sum() * 0.04
    sev2_ha = (pred == 2).sum() * 0.04
    sev3_ha = (pred == 3).sum() * 0.04

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    axes[0].imshow(rgb_pre)
    axes[0].set_title("Sentinel-2 Pre-fire (RGB)")
    axes[1].imshow(rgb_post)
    axes[1].set_title("Sentinel-2 Post-fire (RGB)")
    axes[2].imshow(rgb_post, alpha=0.55)
    axes[2].imshow(np.ma.masked_where(pred == 0, pred), cmap=cmap_sev, norm=norm_sev, alpha=0.9)
    axes[2].set_title(f"Burn Severity (Total: {area_ha:.1f} ha)\nLow: {sev1_ha:.1f} ha, Med: {sev2_ha:.1f} ha, High: {sev3_ha:.1f} ha", color="darkred", fontweight="bold")

    for ax in axes:
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()

    print(f"Готово! Результат сохранен в {output}")
    print(f"Общая площадь гари: {area_ha:.2f} га")
    print(f"  - Слабая тяжесть: {sev1_ha:.2f} га ({sev1_ha/max(area_ha, 1e-6)*100:.1f}%)")
    print(f"  - Средняя тяжесть: {sev2_ha:.2f} га ({sev2_ha/max(area_ha, 1e-6)*100:.1f}%)")
    print(f"  - Сильная тяжесть: {sev3_ha:.2f} га ({sev3_ha/max(area_ha, 1e-6)*100:.1f}%)")

def main():
    ap = argparse.ArgumentParser(description="Инференс на новом снимке")
    ap.add_argument("--af", help="Путь к снимку VIIRS I1-I5 .tif")
    ap.add_argument("--bs-pre", help="Путь к снимку Sentinel-2 Pre .tif")
    ap.add_argument("--bs-post", help="Путь к снимку Sentinel-2 Post .tif")
    ap.add_argument("--output", default="prediction.png", help="Куда сохранить итоговую картинку")
    args = ap.parse_args()

    if args.af:
        predict_af(args.af, output=args.output)
    elif args.bs_pre and args.bs_post:
        predict_bs(args.bs_pre, args.bs_post, output=args.output)
    else:
        print("Укажите --af <viirs.tif> или --bs-pre <pre.tif> --bs-post <post.tif>")

if __name__ == "__main__":
    main()
