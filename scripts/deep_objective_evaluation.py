import os
import sys
import glob
import numpy as np
import pandas as pd
import torch
import tifffile
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.common.io import read_tif
from src.common.rle import rle_decode

def run_objective_evaluation():
    print("=" * 70)
    print(" ОБЪЕКТИВНАЯ ОЦЕНКА ВЕСОВ МОДЕЛИ НА НОВЫХ (НЕВИДАННЫХ) СНИМКАХ")
    print("=" * 70)

    test_dir = "../Мониторинг DATA/test"
    if not os.path.exists(test_dir):
        test_dir = "test"
    
    sub_path = "submission.csv"
    if not os.path.exists(sub_path):
        print("submission.csv not found! Running fast inference...")
        import subprocess
        subprocess.run(["python", "-m", "src.inference.predict", "--test_dir", test_dir, "--out_csv", "submission.csv"], check=True)
    
    df_sub = pd.read_csv(sub_path)
    print(f"Загружены предсказания модели из {sub_path} ({len(df_sub)} записей)")

    out_dir = "visualizations/objective_eval"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "af"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "bs"), exist_ok=True)

    # =========================================================================
    # 1. МОДУЛЬ AF (ACTIVE FIRE - VIIRS 375m): ФИЗИЧЕСКАЯ ВЕРИФИКАЦИЯ
    # =========================================================================
    print("\n" + "-" * 70)
    print("1. АНАЛИЗ МОДУЛЯ ДЕТЕКЦИИ АКТИВНОГО ГОРЕНИЯ (VIIRS I1-I5)")
    print("-" * 70)

    af_rows = df_sub[df_sub["chip_id"].str.startswith("AF_")].copy()
    print(f"Всего тестовых чипов AF: {len(af_rows)}")

    # Сбор физической телеметрии по всем чипам
    fire_pixels_total = 0
    chips_with_fire = 0
    
    af_pixel_records = []
    af_chip_summary = []

    for _, row in af_rows.iterrows():
        cid = row["chip_id"]
        rle = str(row["rle"]) if pd.notna(row["rle"]) else ""
        mask = rle_decode(rle, (256, 256)) if rle else np.zeros((256, 256), dtype=np.uint8)
        
        viirs_path = os.path.join(test_dir, "af", "viirs", f"{cid}_VIIRS_I1-I5.tif")
        if not os.path.exists(viirs_path):
            viirs_path = os.path.join(test_dir, "viirs", f"{cid}_VIIRS_I1-I5.tif")
        if not os.path.exists(viirs_path):
            continue

        v = read_tif(viirs_path)
        # v shape: (8, 256, 256): I1, I2, I3, I4, I5, SolarZenith, ScanAngle, ValidMask
        I4 = v[3] # 3.74 um brightness temperature (K)
        I5 = v[4] # 11.45 um brightness temperature (K)
        diff = I4 - I5
        sza = v[5] # Solar Zenith Angle (degrees)

        n_fire = int(mask.sum())
        fire_pixels_total += n_fire
        if n_fire > 0:
            chips_with_fire += 1

        # Background stats (non-fire valid pixels)
        bg_mask = (mask == 0) & (~np.isnan(I4)) & (~np.isnan(I5)) & (I4 > 200)
        fire_mask = (mask == 1) & (~np.isnan(I4)) & (~np.isnan(I5))

        bg_i4_mean = float(np.mean(I4[bg_mask])) if np.any(bg_mask) else 290.0
        bg_i4_std = float(np.std(I4[bg_mask])) if np.any(bg_mask) else 5.0
        bg_diff_mean = float(np.mean(diff[bg_mask])) if np.any(bg_mask) else 0.0

        if n_fire > 0 and np.any(fire_mask):
            fire_i4_vals = I4[fire_mask]
            fire_diff_vals = diff[fire_mask]
            fire_sza_vals = sza[fire_mask]

            z_scores = (fire_i4_vals - bg_i4_mean) / (bg_i4_std + 1e-5)

            af_chip_summary.append({
                "chip_id": cid,
                "n_fire": n_fire,
                "fire_i4_max": float(np.max(fire_i4_vals)),
                "fire_i4_mean": float(np.mean(fire_i4_vals)),
                "fire_diff_mean": float(np.mean(fire_diff_vals)),
                "bg_i4_mean": bg_i4_mean,
                "bg_diff_mean": bg_diff_mean,
                "mean_z_score": float(np.mean(z_scores)),
                "mean_sza": float(np.mean(fire_sza_vals))
            })

            # Save sample of pixels for distribution
            sub_idx = np.random.choice(len(fire_i4_vals), size=min(100, len(fire_i4_vals)), replace=False)
            for idx in sub_idx:
                af_pixel_records.append({
                    "type": "Fire (Predicted)",
                    "I4": float(fire_i4_vals[idx]),
                    "I5": float(I5[fire_mask][idx]),
                    "diff": float(fire_diff_vals[idx]),
                    "z_score": float(z_scores[idx])
                })
        
        # Sample background pixels
        if np.any(bg_mask):
            bg_indices = np.where(bg_mask)
            sub_bg = np.random.choice(len(bg_indices[0]), size=min(20, len(bg_indices[0])), replace=False)
            for b_idx in sub_bg:
                r, c = bg_indices[0][b_idx], bg_indices[1][b_idx]
                af_pixel_records.append({
                    "type": "Background (Non-fire)",
                    "I4": float(I4[r, c]),
                    "I5": float(I5[r, c]),
                    "diff": float(diff[r, c]),
                    "z_score": float((I4[r, c] - bg_i4_mean) / (bg_i4_std + 1e-5))
                })

    df_af_summary = pd.DataFrame(af_chip_summary)
    df_af_pixels = pd.DataFrame(af_pixel_records)

    print(f"Чипов с обнаруженным горением: {chips_with_fire} из {len(af_rows)} ({chips_with_fire/len(af_rows)*100:.1f}%)")
    print(f"Всего обнаружено активных пикселей горения: {fire_pixels_total}")
    
    if len(df_af_summary) > 0:
        print("\nФизические факты по обнаруженным пикселям горения:")
        print(f" - Средняя температура I4 (3.74 мкм): {df_af_pixels[df_af_pixels['type']=='Fire (Predicted)']['I4'].mean():.2f} K (фон: {df_af_pixels[df_af_pixels['type']=='Background (Non-fire)']['I4'].mean():.2f} K)")
        print(f" - Максимальная температура I4: {df_af_pixels[df_af_pixels['type']=='Fire (Predicted)']['I4'].max():.2f} K (367 K - физический предел насыщения детектора VIIRS)")
        print(f" - Средний тепловой контраст (I4 - I5): {df_af_pixels[df_af_pixels['type']=='Fire (Predicted)']['diff'].mean():.2f} K (фон: {df_af_pixels[df_af_pixels['type']=='Background (Non-fire)']['diff'].mean():.2f} K)")
        print(f" - Средний Z-Score аномалии над фоном: {df_af_pixels[df_af_pixels['type']=='Fire (Predicted)']['z_score'].mean():.2f} сигм")

    # =========================================================================
    # 2. МОДУЛЬ BS (BURN SEVERITY - SENTINEL-2 / SENTINEL-1): ФИЗИЧЕСКАЯ ВЕРИФИКАЦИЯ
    # =========================================================================
    print("\n" + "-" * 70)
    print("2. АНАЛИЗ МОДУЛЯ ОЦЕНКИ ПЛОЩАДЕЙ И ТЯЖЕСТИ ГАРЕЙ (SENTINEL-2)")
    print("-" * 70)

    bs_rows = df_sub[df_sub["chip_id"].str.startswith("BS_")].copy()
    unique_bs_chips = sorted(bs_rows["chip_id"].unique())
    print(f"Всего тестовых чипов BS: {len(unique_bs_chips)}")

    bs_pixel_records = []
    bs_chip_summary = []

    for cid in unique_bs_chips:
        pre_path = os.path.join(test_dir, "bs", "sentinel2_pre", f"{cid}_Sentinel-2_pre.tif")
        post_path = os.path.join(test_dir, "bs", "sentinel2_post", f"{cid}_Sentinel-2_post.tif")
        if not os.path.exists(pre_path):
            pre_path = os.path.join(test_dir, "sentinel2_pre", f"{cid}_Sentinel-2_pre.tif")
            post_path = os.path.join(test_dir, "sentinel2_post", f"{cid}_Sentinel-2_post.tif")
        if not (os.path.exists(pre_path) and os.path.exists(post_path)):
            continue

        s2_pre = read_tif(pre_path) # B2, B3, B4, B5, B6, B7, B8A, B11, B12, SCL
        s2_post = read_tif(post_path)

        # NIR: B8A (index 6), SWIR2: B12 (index 8), Red: B4 (index 2)
        nir_pre = s2_pre[6].astype(np.float32) / 10000.0
        swir_pre = s2_pre[8].astype(np.float32) / 10000.0
        red_pre = s2_pre[2].astype(np.float32) / 10000.0

        nir_post = s2_post[6].astype(np.float32) / 10000.0
        swir_post = s2_post[8].astype(np.float32) / 10000.0
        red_post = s2_post[2].astype(np.float32) / 10000.0

        # Physical Spectral Indices
        nbr_pre = (nir_pre - swir_pre) / (nir_pre + swir_pre + 1e-6)
        nbr_post = (nir_post - swir_post) / (nir_post + swir_post + 1e-6)
        dnbr = nbr_pre - nbr_post

        ndvi_pre = (nir_pre - red_pre) / (nir_pre + red_pre + 1e-6)
        ndvi_post = (nir_post - red_post) / (nir_post + red_post + 1e-6)
        dndvi = ndvi_pre - ndvi_post

        # Read model prediction mask
        chip_df = bs_rows[bs_rows["chip_id"] == cid]
        sev_mask = np.zeros((512, 512), dtype=np.uint8)
        for _, cr in chip_df.iterrows():
            c_cls = cr["class_id"]
            if pd.notna(cr["rle"]):
                m = rle_decode(cr["rle"], (512, 512))
                sev_mask[m == 1] = c_cls

        total_burn_px = int((sev_mask > 0).sum())
        c1_px = int((sev_mask == 1).sum())
        c2_px = int((sev_mask == 2).sum())
        c3_px = int((sev_mask == 3).sum())

        area_ha = total_burn_px * 0.04

        bs_chip_summary.append({
            "chip_id": cid,
            "total_ha": area_ha,
            "c1_ha": c1_px * 0.04,
            "c2_ha": c2_px * 0.04,
            "c3_ha": c3_px * 0.04,
            "mean_dnbr_burn": float(np.mean(dnbr[sev_mask > 0])) if total_burn_px > 0 else 0.0,
            "mean_dnbr_bg": float(np.mean(dnbr[sev_mask == 0]))
        })

        # Sample pixels for index distribution across severity classes
        for cls_id, cls_name in [(0, "0: Не гарь"), (1, "1: Слабая"), (2, "2: Средняя"), (3, "3: Сильная")]:
            c_mask = (sev_mask == cls_id)
            if np.any(c_mask):
                idx_coords = np.where(c_mask)
                sample_size = min(60 if cls_id > 0 else 20, len(idx_coords[0]))
                sub = np.random.choice(len(idx_coords[0]), size=sample_size, replace=False)
                for s in sub:
                    r, c = idx_coords[0][s], idx_coords[1][s]
                    bs_pixel_records.append({
                        "chip_id": cid,
                        "class_id": cls_id,
                        "class_name": cls_name,
                        "dNBR": float(dnbr[r, c]),
                        "dNDVI": float(dndvi[r, c]),
                        "NBR_pre": float(nbr_pre[r, c]),
                        "NBR_post": float(nbr_post[r, c]),
                        "NIR_pre": float(nir_pre[r, c]),
                        "NIR_post": float(nir_post[r, c]),
                        "SWIR_pre": float(swir_pre[r, c]),
                        "SWIR_post": float(swir_post[r, c])
                    })

    df_bs_summary = pd.DataFrame(bs_chip_summary)
    df_bs_pixels = pd.DataFrame(bs_pixel_records)

    total_detected_ha = df_bs_summary["total_ha"].sum()
    chips_with_scars = (df_bs_summary["total_ha"] > 0).sum()
    print(f"Чипов с обнаруженными гарями: {chips_with_scars} из {len(unique_bs_chips)} ({chips_with_scars/len(unique_bs_chips)*100:.1f}%)")
    print(f"Суммарная площадь выявленных гарей: {total_detected_ha:.1f} га")
    print(f" - Класс 1 (Слабая степень): {df_bs_summary['c1_ha'].sum():.1f} га ({df_bs_summary['c1_ha'].sum()/total_detected_ha*100:.1f}%)")
    print(f" - Класс 2 (Средняя степень): {df_bs_summary['c2_ha'].sum():.1f} га ({df_bs_summary['c2_ha'].sum()/total_detected_ha*100:.1f}%)")
    print(f" - Класс 3 (Сильная степень): {df_bs_summary['c3_ha'].sum():.1f} га ({df_bs_summary['c3_ha'].sum()/total_detected_ha*100:.1f}%)")

    print("\nФизическая спектральная дифференциация классов модели (dNBR и dNDVI):")
    cls_stats = df_bs_pixels.groupby("class_name")[["dNBR", "dNDVI", "NIR_post", "SWIR_post"]].agg(["mean", "std"])
    print(cls_stats)

    # =========================================================================
    # 3. ПОСТРОЕНИЕ СТАТИСТИЧЕСКИХ ГРАФИКОВ ФИЗИЧЕСКОЙ ДОСТОВЕРНОСТИ
    # =========================================================================
    # График 1: Физическое распределение I4 и контраста (I4 - I5) для AF
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fire_i4 = df_af_pixels[df_af_pixels["type"] == "Fire (Predicted)"]["I4"]
    bg_i4 = df_af_pixels[df_af_pixels["type"] == "Background (Non-fire)"]["I4"]
    axes[0].hist(bg_i4, bins=40, density=True, alpha=0.6, color="#2ca02c", label="Background (Non-fire)")
    axes[0].hist(fire_i4, bins=40, density=True, alpha=0.6, color="#d62728", label="Fire (Predicted)")
    axes[0].set_title("Распределение температуры VIIRS I4 (3.74 мкм)\nФон vs Детекции модели", fontweight="bold")
    axes[0].set_xlabel("Яркостная температура I4 (Kelvin)")
    axes[0].axvline(320.0, color="darkred", linestyle="--", label="Порог термоаномалии (320 K)")
    axes[0].legend()

    fire_diff = df_af_pixels[df_af_pixels["type"] == "Fire (Predicted)"]["diff"]
    bg_diff = df_af_pixels[df_af_pixels["type"] == "Background (Non-fire)"]["diff"]
    axes[1].boxplot([bg_diff, fire_diff], labels=["Background", "Fire (Predicted)"], patch_artist=True)
    axes[1].set_title("Тепловой контраст (I4 - I5)\n(Критерий истинности горения)", fontweight="bold")
    axes[1].set_ylabel("Контраст I4 - I5 (Kelvin)")
    axes[1].axhline(12.0, color="darkred", linestyle="--", label="Порог горения (> 12 K)")
    axes[1].legend()

    plt.tight_layout()
    af_plot_p = os.path.join(out_dir, "af_physical_verification.png")
    plt.savefig(af_plot_p, dpi=160)
    plt.close()
    print(f"\nГрафик физической верификации AF сохранен: {af_plot_p}")

    # График 2: Физическое распределение dNBR и dNDVI по классам степени поражения BS
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    classes = ["0: Не гарь", "1: Слабая", "2: Средняя", "3: Сильная"]
    dnbr_data = [df_bs_pixels[df_bs_pixels["class_name"] == c]["dNBR"].dropna() for c in classes]
    dndvi_data = [df_bs_pixels[df_bs_pixels["class_name"] == c]["dNDVI"].dropna() for c in classes]

    axes[0].boxplot(dnbr_data, labels=classes, patch_artist=True)
    axes[0].set_title("Спектральный индекс выгорания dNBR по классам\n(Монотонный рост подтверждает адекватность модели)", fontweight="bold")
    axes[0].set_xlabel("Класс тяжести поражения")
    axes[0].set_ylabel("Разностный индекс dNBR (NIR vs SWIR2)")
    axes[0].axhline(0.1, color="orange", linestyle=":", label="Порог ожога (0.10)")
    axes[0].axhline(0.27, color="crimson", linestyle=":", label="Порог сильного выгорания (0.27)")
    axes[0].legend()

    axes[1].boxplot(dndvi_data, labels=classes, patch_artist=True)
    axes[1].set_title("Потеря фотосинтезирующей биомассы (dNDVI)", fontweight="bold")
    axes[1].set_xlabel("Класс тяжести поражения")
    axes[1].set_ylabel("Снижение вегетационного индекса (dNDVI)")

    plt.tight_layout()
    bs_plot_p = os.path.join(out_dir, "bs_physical_verification.png")
    plt.savefig(bs_plot_p, dpi=160)
    plt.close()
    print(f"График физической верификации BS сохранен: {bs_plot_p}")

    # Сохраняем сводные CSV таблицы фактов
    df_af_summary.to_csv(os.path.join(out_dir, "af_telemetry_summary.csv"), index=False)
    df_bs_summary.to_csv(os.path.join(out_dir, "bs_telemetry_summary.csv"), index=False)
    print("Сводные таблицы фактов сохранены.")

if __name__ == "__main__":
    run_objective_evaluation()
