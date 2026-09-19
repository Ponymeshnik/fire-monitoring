import os, glob
import numpy as np
import pandas as pd
import tifffile

def analyze_af_physical():
    af_meta = pd.read_csv('train/af/meta.csv')
    pos_chips = af_meta[af_meta['n_fire_px'] > 0]['chip_id'].tolist()[:30]
    
    fire_i4, bg_i4 = [], []
    fire_i5, bg_i5 = [], []
    fire_diff, bg_diff = [], []
    fire_i3, bg_i3 = [], []
    
    for cid in pos_chips:
        vpath = f'train/af/viirs/{cid}_VIIRS_I1-I5.tif'
        mpath = f'train/af/masks/{cid}_mask.tif'
        if not os.path.exists(vpath) or not os.path.exists(mpath):
            continue
        v = tifffile.imread(vpath)
        m = tifffile.imread(mpath)
        
        # v shape is (256, 256, 8) or (8, 256, 256) or similar
        if v.shape[0] == 256 and v.shape[1] == 256:
            # (H, W, C)
            i1, i2, i3, i4, i5 = v[:,:,0], v[:,:,1], v[:,:,2], v[:,:,3], v[:,:,4]
        else:
            i1, i2, i3, i4, i5 = v[0], v[1], v[2], v[3], v[4]
            
        f_mask = (m == 1)
        bg_mask = (m == 0)
        
        if f_mask.sum() > 0:
            fire_i4.extend(i4[f_mask].tolist())
            fire_i5.extend(i5[f_mask].tolist())
            fire_diff.extend((i4[f_mask] - i5[f_mask]).tolist())
            fire_i3.extend(i3[f_mask].tolist())
            
        # sample bg
        bg_idx = np.random.choice(np.where(bg_mask.ravel())[0], size=min(100, bg_mask.sum()), replace=False)
        bg_i4.extend(i4.ravel()[bg_idx].tolist())
        bg_i5.extend(i5.ravel()[bg_idx].tolist())
        bg_diff.extend((i4.ravel()[bg_idx] - i5.ravel()[bg_idx]).tolist())
        bg_i3.extend(i3.ravel()[bg_idx].tolist())
        
    print('=== AF PHYSICAL VALUES (FIRE vs BACKGROUND) ===')
    print(f'Fire I4 (K): mean={np.mean(fire_i4):.1f}, median={np.median(fire_i4):.1f}, min={np.min(fire_i4):.1f}, max={np.max(fire_i4):.1f}')
    print(f'Bg   I4 (K): mean={np.mean(bg_i4):.1f}, median={np.median(bg_i4):.1f}, min={np.min(bg_i4):.1f}, max={np.max(bg_i4):.1f}')
    print(f'Fire (I4-I5) (K): mean={np.mean(fire_diff):.1f}, median={np.median(fire_diff):.1f}, min={np.min(fire_diff):.1f}, max={np.max(fire_diff):.1f}')
    print(f'Bg   (I4-I5) (K): mean={np.mean(bg_diff):.1f}, median={np.median(bg_diff):.1f}, min={np.min(bg_diff):.1f}, max={np.max(bg_diff):.1f}')
    print(f'Fire I3 (refl): mean={np.mean(fire_i3):.3f}, median={np.median(fire_i3):.3f}')
    print(f'Bg   I3 (refl): mean={np.mean(bg_i3):.3f}, median={np.median(bg_i3):.3f}')

def analyze_bs_physical():
    bs_meta = pd.read_csv('train/bs/meta.csv')
    sample_chips = bs_meta['chip_id'].tolist()[:25]
    
    dnbr_by_sev = {0: [], 1: [], 2: [], 3: []}
    s1_vv_diff_by_sev = {0: [], 1: [], 2: [], 3: []}
    s1_vh_diff_by_sev = {0: [], 1: [], 2: [], 3: []}
    lc_by_sev = {0: [], 1: [], 2: [], 3: []}
    
    for cid in sample_chips:
        pre_p = f'train/bs/sentinel2_pre/{cid}_Sentinel-2_pre.tif'
        post_p = f'train/bs/sentinel2_post/{cid}_Sentinel-2_post.tif'
        s1_pre_p = f'train/bs/sentinel1_pre/{cid}_Sentinel-1_pre.tif'
        s1_post_p = f'train/bs/sentinel1_post/{cid}_Sentinel-1_post.tif'
        aux_p = f'train/bs/aux/{cid}_aux.tif'
        m_p = f'train/bs/masks/{cid}_mask.tif'
        
        if not all(os.path.exists(p) for p in [pre_p, post_p, aux_p, m_p]):
            continue
            
        pre = tifffile.imread(pre_p) # (512, 512, 10) or (10, 512, 512)
        post = tifffile.imread(post_p)
        mask = tifffile.imread(m_p)
        aux = tifffile.imread(aux_p)
        
        if pre.shape[0] == 512:
            b8a_pre, b12_pre = pre[:,:,6].astype(float), pre[:,:,8].astype(float)
            b8a_post, b12_post = post[:,:,6].astype(float), post[:,:,8].astype(float)
        else:
            b8a_pre, b12_pre = pre[6].astype(float), pre[8].astype(float)
            b8a_post, b12_post = post[6].astype(float), post[8].astype(float)
            
        nbr_pre = (b8a_pre - b12_pre) / (b8a_pre + b12_pre + 1e-6)
        nbr_post = (b8a_post - b12_post) / (b8a_post + b12_post + 1e-6)
        dnbr = nbr_pre - nbr_post
        
        has_s1 = os.path.exists(s1_pre_p) and os.path.exists(s1_post_p)
        if has_s1:
            s1_pre = tifffile.imread(s1_pre_p)
            s1_post = tifffile.imread(s1_post_p)
            if s1_pre.shape[0] == 512:
                dvv = (s1_post[:,:,0].astype(float) - s1_pre[:,:,0].astype(float)) / 100.0
                dvh = (s1_post[:,:,1].astype(float) - s1_pre[:,:,1].astype(float)) / 100.0
            else:
                dvv = (s1_post[0].astype(float) - s1_pre[0].astype(float)) / 100.0
                dvh = (s1_post[1].astype(float) - s1_pre[1].astype(float)) / 100.0
                
        # aux landcover is usually channel 3 (0: DEM, 1: Slope, 2: Aspect, 3: LandCover)
        if aux.shape[0] == 512:
            lc = aux[:,:,3] if aux.shape[2] > 3 else aux[:,:,0]
        else:
            lc = aux[3] if aux.shape[0] > 3 else aux[0]
            
        for c in range(4):
            c_mask = (mask == c)
            if c_mask.sum() > 0:
                sample_n = min(1000, c_mask.sum())
                chosen = np.random.choice(np.where(c_mask.ravel())[0], size=sample_n, replace=False)
                dnbr_by_sev[c].extend(dnbr.ravel()[chosen].tolist())
                lc_by_sev[c].extend(lc.ravel()[chosen].tolist())
                if has_s1:
                    s1_vv_diff_by_sev[c].extend(dvv.ravel()[chosen].tolist())
                    s1_vh_diff_by_sev[c].extend(dvh.ravel()[chosen].tolist())

    print('\n=== BS PHYSICAL VALUES BY SEVERITY ===')
    for c, name in [(0, 'Фон (0)'), (1, 'Слабая (1)'), (2, 'Средняя (2)'), (3, 'Сильная (3)')]:
        vals = dnbr_by_sev[c]
        print(f'{name} dNBR: mean={np.mean(vals):.3f}, median={np.median(vals):.3f}, 25%={np.percentile(vals, 25):.3f}, 75%={np.percentile(vals, 75):.3f}')
        if len(s1_vh_diff_by_sev[c]) > 0:
            print(f'  Delta VH (dB): mean={np.mean(s1_vh_diff_by_sev[c]):.2f} dB, Delta VV: mean={np.mean(s1_vv_diff_by_sev[c]):.2f} dB')

if __name__ == '__main__':
    analyze_af_physical()
    analyze_bs_physical()
