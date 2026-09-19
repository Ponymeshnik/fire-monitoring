import numpy as np
from scipy.ndimage import uniform_filter

def af_features(viirs: np.ndarray, aux: np.ndarray) -> np.ndarray:
    """
    viirs: (5, H, W) — I1..I5 (отражения 0..1 и яркостные T, K)
    aux:   (C, H, W) — вспомогательные слои (WorldCover, DEM, углы, метео, valid)
    Возвращает (F, H, W) float32.
    """
    I1, I2, I3, I4, I5 = viirs[0], viirs[1], viirs[2], viirs[3], viirs[4]
    feats = [I1, I2, I3, I4, I5]
    feats.append(I4 - I5)                    # ключевой признак
    feats.append(I3 - I2)                    # блик
    feats.append((I1 - I2) / (I1 + I2 + 1e-6))  # NDVI-подобный
    # контекст: отклонение от среднего фона в окне 21x21
    diff45 = I4 - I5
    m4 = uniform_filter(I4, size=21)
    mdiff = uniform_filter(diff45, size=21)
    feats.append(I4 - m4)
    feats.append(diff45 - mdiff)
    # std фона
    m4sq = uniform_filter(I4 * I4, size=21)
    std4 = np.sqrt(np.maximum(m4sq - m4 * m4, 0))
    feats.append(std4)
    # aux
    for c in range(aux.shape[0]):
        feats.append(aux[c])
    return np.stack(feats, axis=0).astype(np.float32)