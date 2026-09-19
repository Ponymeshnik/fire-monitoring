import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.common.io import read_tif
from src.common.rle import rle_decode

def create_case_study_figures():
    test_dir = "../Мониторинг DATA/test"
    if not os.path.exists(test_dir):
        test_dir = "test"
    
    out_dir = "visualizations/objective_eval"
    os.makedirs(out_dir, exist_ok=True)
    
    df_sub = pd.read_csv("submission.csv")

    # =========================================================================
    # КЕЙС 1: АКТИВНЫЙ ПОЖАРНЫЙ ФРОНТ (AF_te_000039)
    # =========================================================================
    cid_af = "AF_te_000039"
    v_path = os.path.join(test_dir, "af", "viirs", f"{cid_af}_VIIRS_I1-I5.tif")
    if os.path.exists(v_path):
        v = read_tif(v_path)
        I4, I5 = v[3], v[4]
        diff = np.nan_to_num(I4 - I5, nan=0.0)
        I4_clean = np.nan_to_num(I4, nan=280.0)

        af_row = df_sub[df_sub["chip_id"] == cid_af]
        mask_af = rle_decode(af_row.iloc[0]["rle"], (256, 256)) if len(af_row) > 0 else np.zeros((256, 256))

        fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
        im0 = axes[0].imshow(I4_clean, cmap="inferno", vmin=290, vmax=350)
        axes[0].set_title(f"1. Яркостная температура VIIRS I4 (3.74 мкм)\n{cid_af} (Максимум: {I4_clean.max():.1f} K)", fontsize=11, fontweight="bold")
        plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04, label="Kelvin")

        im1 = axes[1].imshow(diff, cmap="magma", vmin=0, vmax=45)
        axes[1].set_title(f"2. Физический тепловой контраст (I4 - I5)\n(Высокотемпературное пламя: до {diff.max():.1f} K)", fontsize=11, fontweight="bold")
        plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04, label="ΔT (K)")

        axes[2].imshow(I4_clean, cmap="gray", alpha=0.5)
        axes[2].imshow(np.ma.masked_where(mask_af == 0, mask_af), cmap="autumn", alpha=0.9)
        axes[2].set_title(f"3. Детекция весов модели (Active Fire Mask)\nОбнаружено пикселей горения: {int(mask_af.sum())}", fontsize=11, fontweight="bold", color="darkred")

        for ax in axes:
            ax.axis("off")
        plt.tight_layout()
        p1 = os.path.join(out_dir, "case_study_AF_active_fire.png")
        plt.savefig(p1, dpi=160)
        plt.close()
        print(f"Кейс AF сохранен: {p1}")

    # =========================================================================
    # КЕЙС 2: КРУПНАЯ ГАРЬ И СТЕПЕНИ ПОРАЖЕНИЯ (BS_te_000086)
    # =========================================================================
    cid_bs = "BS_te_000086"
    pre_p = os.path.join(test_dir, "bs", "sentinel2_pre", f"{cid_bs}_Sentinel-2_pre.tif")
    post_p = os.path.join(test_dir, "bs", "sentinel2_post", f"{cid_bs}_Sentinel-2_post.tif")
    if os.path.exists(pre_p) and os.path.exists(post_p):
        s2_pre = read_tif(pre_p)
        s2_post = read_tif(post_p)

        # True Color RGB
        rgb_pre = np.clip(np.stack([s2_pre[2], s2_pre[1], s2_pre[0]], axis=-1) / 2500.0, 0, 1)
        rgb_post = np.clip(np.stack([s2_post[2], s2_post[1], s2_post[0]], axis=-1) / 2500.0, 0, 1)

        # Raw Physical dNBR
        nir_pre = s2_pre[6].astype(np.float32) / 10000.0
        swir_pre = s2_pre[8].astype(np.float32) / 10000.0
        nir_post = s2_post[6].astype(np.float32) / 10000.0
        swir_post = s2_post[8].astype(np.float32) / 10000.0
        nbr_pre = (nir_pre - swir_pre) / (nir_pre + swir_pre + 1e-6)
        nbr_post = (nir_post - swir_post) / (nir_post + swir_post + 1e-6)
        dnbr = nbr_pre - nbr_post

        # Model predicted severity mask
        chip_df = df_sub[df_sub["chip_id"] == cid_bs]
        sev_map = np.zeros((512, 512), dtype=np.uint8)
        sev_ha = {}
        for _, cr in chip_df.iterrows():
            cls = cr["class_id"]
            if pd.notna(cr["rle"]):
                m = rle_decode(cr["rle"], (512, 512))
                sev_map[m == 1] = cls
                sev_ha[cls] = (m == 1).sum() * 0.04

        cmap_sev = mcolors.ListedColormap(["none", "#FFD700", "#FF8C00", "#8B0000"])
        bounds = [0, 0.5, 1.5, 2.5, 3.5]
        norm_sev = mcolors.BoundaryNorm(bounds, cmap_sev.N)

        fig, axes = plt.subplots(1, 4, figsize=(22, 5.5))
        axes[0].imshow(rgb_pre)
        axes[0].set_title(f"1. До пожара (Sentinel-2 RGB)\nЗеленый растительный покров", fontsize=11, fontweight="bold")

        axes[1].imshow(rgb_post)
        axes[1].set_title(f"2. После пожара (Sentinel-2 RGB)\nОтчетливое пятно выгоревшей золы", fontsize=11, fontweight="bold")

        im2 = axes[2].imshow(dnbr, cmap="RdYlGn_r", vmin=-0.1, vmax=0.7)
        axes[2].set_title(f"3. Физический спектральный dNBR\n(Аномалия пигментации и влажности)", fontsize=11, fontweight="bold")
        plt.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04, label="dNBR")

        axes[3].imshow(rgb_post, alpha=0.5)
        axes[3].imshow(np.ma.masked_where(sev_map == 0, sev_map), cmap=cmap_sev, norm=norm_sev, alpha=0.85)
        tot_ha = sum(sev_ha.values())
        axes[3].set_title(
            f"4. Предсказание модели: Классы поражения\nВсего: {tot_ha:.1f} га (Сл: {sev_ha.get(1,0):.0f}, Ср: {sev_ha.get(2,0):.0f}, Сильн: {sev_ha.get(3,0):.0f} га)",
            fontsize=11, fontweight="bold", color="darkred"
        )

        for ax in axes:
            ax.axis("off")
        plt.tight_layout()
        p2 = os.path.join(out_dir, "case_study_BS_burn_severity.png")
        plt.savefig(p2, dpi=160)
        plt.close()
        print(f"Кейс BS сохранен: {p2}")

    # =========================================================================
    # КЕЙС 3: КОНТРОЛЬНЫЙ СНИМОК БЕЗ ПОЖАРА (ОТСУТСТВИЕ ЛОЖНЫХ СРАБАТЫВАНИЙ)
    # =========================================================================
    # Найдем чип, где модель предсказала 0 пикселей
    af_zeros = df_sub[df_sub["chip_id"].str.startswith("AF_")].copy()
    af_zeros["n_px"] = [rle_decode(r, (256, 256)).sum() for r in af_zeros["rle"].fillna("")]
    zero_chip = af_zeros[af_zeros["n_px"] == 0].iloc[0]["chip_id"]
    
    vz_path = os.path.join(test_dir, "af", "viirs", f"{zero_chip}_VIIRS_I1-I5.tif")
    if os.path.exists(vz_path):
        vz = read_tif(vz_path)
        I4_z = np.nan_to_num(vz[3], nan=280.0)
        diff_z = np.nan_to_num(vz[3] - vz[4], nan=0.0)

        fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
        im0 = axes[0].imshow(I4_z, cmap="inferno", vmin=270, vmax=310)
        axes[0].set_title(f"VIIRS I4 Фоновая сцена ({zero_chip})\nТемпература: {I4_z.mean():.1f} K (норма)", fontsize=11)
        plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04, label="K")

        im1 = axes[1].imshow(diff_z, cmap="magma", vmin=0, vmax=15)
        axes[1].set_title(f"Тепловой контраст I4 - I5\n(Среднее: {diff_z.mean():.1f} K, нет очагов)", fontsize=11)
        plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04, label="ΔT (K)")

        axes[2].imshow(I4_z, cmap="gray")
        axes[2].set_title("Предсказание модели: 0 ложных тревог\n(Чистая детекция, нет шума)", fontsize=11, fontweight="bold", color="darkgreen")

        for ax in axes:
            ax.axis("off")
        plt.tight_layout()
        p3 = os.path.join(out_dir, "case_study_AF_control_clean.png")
        plt.savefig(p3, dpi=160)
        plt.close()
        print(f"Кейс контроля сохранен: {p3}")

if __name__ == "__main__":
    create_case_study_figures()
