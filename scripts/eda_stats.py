import os, glob
import pandas as pd
import numpy as np

af_meta = pd.read_csv('train/af/meta.csv')
bs_meta = pd.read_csv('train/bs/meta.csv')
test_meta = pd.read_csv('test/meta.csv')

print('=== AF TRAIN METADATA ===')
print('Total AF chips:', len(af_meta))
pos_af = af_meta[af_meta['n_fire_px'] > 0]
neg_af = af_meta[af_meta['n_fire_px'] == 0]
print(f'Positive chips: {len(pos_af)} ({len(pos_af)/len(af_meta)*100:.2f}%)')
print(f'Negative chips: {len(neg_af)} ({len(neg_af)/len(af_meta)*100:.2f}%)')
total_pixels_af = len(af_meta) * 256 * 256
total_fire_pixels = af_meta['n_fire_px'].sum()
print(f'Total pixels: {total_pixels_af}, Total fire pixels: {int(total_fire_pixels)} ({total_fire_pixels/total_pixels_af*100:.5f}%)')
print(f'Fire pixels per positive chip: median={pos_af["n_fire_px"].median():.1f}, mean={pos_af["n_fire_px"].mean():.1f}, min={pos_af["n_fire_px"].min():.0f}, max={pos_af["n_fire_px"].max():.0f}')
print('Satellites:\n', af_meta['satellite'].value_counts())
af_meta['year'] = pd.to_datetime(af_meta['acq_datetime']).dt.year
af_meta['month'] = pd.to_datetime(af_meta['acq_datetime']).dt.month
print('Years:\n', af_meta['year'].value_counts().sort_index())
print('Months:\n', af_meta['month'].value_counts().sort_index())

print('\n=== BS TRAIN METADATA ===')
print('Total BS chips:', len(bs_meta))
s1 = bs_meta['sev1_px'].sum()
s2 = bs_meta['sev2_px'].sum()
s3 = bs_meta['sev3_px'].sum()
tot_burn_px = s1 + s2 + s3
total_pixels_bs = len(bs_meta) * 512 * 512
print(f'Total BS pixels: {total_pixels_bs}, Burn pixels: {int(tot_burn_px)} ({tot_burn_px / total_pixels_bs*100:.2f}%)')
print(f'Severity 1 (слабая): {int(s1)} ({s1/tot_burn_px*100:.2f}%)')
print(f'Severity 2 (средняя): {int(s2)} ({s2/tot_burn_px*100:.2f}%)')
print(f'Severity 3 (сильная): {int(s3)} ({s3/tot_burn_px*100:.2f}%)')
print(f'Burn area ha: sum={bs_meta["burn_area_ha"].sum():.1f} ha, median={bs_meta["burn_area_ha"].median():.1f} ha, mean={bs_meta["burn_area_ha"].mean():.1f} ha')
print(f'Cloud frac: median={bs_meta["cloud_frac"].median()*100:.2f}%, p90={bs_meta["cloud_frac"].quantile(0.9)*100:.2f}%, max={bs_meta["cloud_frac"].max()*100:.2f}%')
print(f'Valid frac: median={bs_meta["valid_frac"].median()*100:.2f}%, min={bs_meta["valid_frac"].min()*100:.2f}%')

bs_meta['dt_pre'] = pd.to_datetime(bs_meta['date_pre'])
bs_meta['dt_post'] = pd.to_datetime(bs_meta['date_post'])
bs_meta['interval_days'] = (bs_meta['dt_post'] - bs_meta['dt_pre']).dt.days
print(f'Pre-post interval (days): median={bs_meta["interval_days"].median():.1f}, min={bs_meta["interval_days"].min()}, max={bs_meta["interval_days"].max()}')

print('\n=== TEST METADATA ===')
print('Test chips total:', len(test_meta))
print(test_meta['kind'].value_counts())
