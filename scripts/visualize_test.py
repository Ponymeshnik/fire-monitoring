import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from src.common.io import read_tif
from src.common.rle import rle_decode

def visualize_test_predictions(sub_path="submission.csv", test_dir="test", out_dir="visualizations/test"):
    os.makedirs(os.path.join(out_dir, "af"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "bs"), exist_ok=True)

    df = pd.read_csv(sub_path)
    print(f"Loaded submission from {sub_path} ({len(df)} rows)")

    # -------------------------------------------------------------
    # 1. Топ чипы активного горения (AF)
    # -------------------------------------------------------------
    af_df = df[df["chip_id"].str.startswith("AF_")].copy()
    af_df["n_px"] = [rle_decode(r, (256, 256)).sum() for r in af_df["rle"].fillna("")]
    top_af = af_df.sort_values("n_px", ascending=False).head(5)

    print("\n[AF] Визуализация топ-5 тестовых чипов с активными пожарами:")
    for _, row in top_af.iterrows():
        cid = row["chip_id"]
        n_px = row["n_px"]
        viirs_path = os.path.join(test_dir, "af", "viirs", f"{cid}_VIIRS_I1-I5.tif")
        if not os.path.exists(viirs_path):
            viirs_path = os.path.join(test_dir, "viirs", f"{cid}_VIIRS_I1-I5.tif")
        if not os.path.exists(viirs_path):
            continue

        v = read_tif(viirs_path)
        I4, I5 = v[3], v[4]
        diff = np.nan_to_num(I4 - I5, nan=0.0)
        I4_clean = np.nan_to_num(I4, nan=280.0)
        pred_mask = rle_decode(row["rle"], (256, 256))

        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        # Снимок 1: Яркостная температура I4 (3.74 мкм)
        im0 = axes[0].imshow(I4_clean, cmap="magma")
        axes[0].set_title(f"VIIRS I4 (3.74 µm) Brightness Temp (K)\n{cid} (Max: {I4_clean.max():.1f} K)", fontsize=10)
        plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

        # Снимок 2: Тепловой контраст (I4 - I5)
        im1 = axes[1].imshow(diff, cmap="inferno")
        axes[1].set_title(f"Thermal Contrast I4 - I5 (K)\n(Hotspot threshold > 12 K)", fontsize=10)
        plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

        # Снимок 3: Детекция модели (наложена на снимок)
        axes[2].imshow(I4_clean, cmap="gray", alpha=0.6)
        axes[2].imshow(np.ma.masked_where(pred_mask == 0, pred_mask), cmap="autumn", alpha=0.9)
        axes[2].set_title(f"Model Detection Overlay\n{n_px} active fire pixels detected", fontsize=10, color="darkred", fontweight="bold")

        for ax in axes:
            ax.axis("off")
        plt.tight_layout()
        save_p = os.path.join(out_dir, "af", f"test_{cid}.png")
        plt.savefig(save_p, dpi=150)
        plt.close()
        print(f"  -> Сохранено: {save_p} ({n_px} пикселей горения)")

    # -------------------------------------------------------------
    # 2. Топ чипы контуров гарей и тяжести поражения (BS)
    # -------------------------------------------------------------
    bs_df = df[df["chip_id"].str.startswith("BS_")].copy()
    bs_df["n_px"] = [rle_decode(r, (512, 512)).sum() for r in bs_df["rle"].fillna("")]
    bs_summary = bs_df.groupby("chip_id")["n_px"].sum().reset_index().sort_values("n_px", ascending=False).head(5)

    cmap_sev = mcolors.ListedColormap(["none", "#FFD700", "#FF8C00", "#8B0000"])
    bounds = [0, 0.5, 1.5, 2.5, 3.5]
    norm_sev = mcolors.BoundaryNorm(bounds, cmap_sev.N)

    print("\n[BS] Визуализация топ-5 тестовых чипов с гарями Sentinel-2:")
    for _, row in bs_summary.iterrows():
        cid = row["chip_id"]
        total_px = row["n_px"]
        pre_path = os.path.join(test_dir, "bs", "sentinel2_pre", f"{cid}_Sentinel-2_pre.tif")
        post_path = os.path.join(test_dir, "bs", "sentinel2_post", f"{cid}_Sentinel-2_post.tif")
        if not os.path.exists(pre_path):
            pre_path = os.path.join(test_dir, "sentinel2_pre", f"{cid}_Sentinel-2_pre.tif")
            post_path = os.path.join(test_dir, "sentinel2_post", f"{cid}_Sentinel-2_post.tif")
        if not (os.path.exists(pre_path) and os.path.exists(post_path)):
            continue

        s2_pre = read_tif(pre_path)
        s2_post = read_tif(post_path)

        # RGB True Color: B4(2), B3(1), B2(0)
        rgb_pre = np.clip(np.stack([s2_pre[2], s2_pre[1], s2_pre[0]], axis=-1) / 3000.0, 0, 1)
        rgb_post = np.clip(np.stack([s2_post[2], s2_post[1], s2_post[0]], axis=-1) / 3000.0, 0, 1)

        # Собираем общую карту тяжести поражения (классы 1, 2, 3)
        chip_rows = bs_df[bs_df["chip_id"] == cid]
        sev_map = np.zeros((512, 512), dtype=np.uint8)
        sev_counts = {}
        for _, cr in chip_rows.iterrows():
            cls = cr["class_id"]
            m = rle_decode(cr["rle"], (512, 512))
            sev_map[m == 1] = cls
            sev_counts[cls] = (m == 1).sum()

        area_ha = total_px * 0.04

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        # Снимок 1: Sentinel-2 До пожара
        axes[0].imshow(rgb_pre)
        axes[0].set_title(f"Sentinel-2 Pre-fire (True Color)\n{cid}", fontsize=10)

        # Снимок 2: Sentinel-2 После пожара
        axes[1].imshow(rgb_post)
        axes[1].set_title(f"Sentinel-2 Post-fire (True Color)\nВизуально виден выгоревший шрам", fontsize=10)

        # Снимок 3: Детекция модели с классами тяжести
        axes[2].imshow(rgb_post, alpha=0.55)
        im_sev = axes[2].imshow(np.ma.masked_where(sev_map == 0, sev_map), cmap=cmap_sev, norm=norm_sev, alpha=0.9)
        axes[2].set_title(
            f"Model Prediction: Burn Scar & Severity\nTotal: {area_ha:.1f} ha (Low: {sev_counts.get(1,0)*0.04:.0f}ha, Med: {sev_counts.get(2,0)*0.04:.0f}ha, High: {sev_counts.get(3,0)*0.04:.0f}ha)",
            fontsize=10, fontweight="bold", color="darkred"
        )

        for ax in axes:
            ax.axis("off")
        plt.tight_layout()
        save_p = os.path.join(out_dir, "bs", f"test_{cid}.png")
        plt.savefig(save_p, dpi=150)
        plt.close()
        print(f"  -> Сохранено: {save_p} (Площадь гари: {area_ha:.1f} га)")

    print(f"\nВсе визуализации успешно сохранены в папку: {out_dir}/")

if __name__ == "__main__":
    visualize_test_predictions()
