import numpy as np

def nbr(b8a, b12):
    return (b8a - b12) / (b8a + b12 + 1e-6)

def ndvi(b4, b8a):
    return (b8a - b4) / (b8a + b4 + 1e-6)

def ndwi(b3, b8a):
    return (b3 - b8a) / (b3 + b8a + 1e-6)

def bs_features(s2_pre, s2_post, s1_pre, s1_post, aux):
    """
    s2_pre/post: (10, H, W) — B2..B12 + SCL
    s1_pre/post: (2, H, W) — VV, VH
    aux: (C, H, W) — DEM, slope, aspect, landcover
    """
    b2p, b3p, b4p, b5p, b6p, b7p, b8ap, b11p, b12p, sclp = s2_pre
    b2q, b3q, b4q, b5q, b6q, b7q, b8aq, b11q, b12q, sclq = s2_post
    vvp, vhp = s1_pre[0], s1_pre[1]
    vvq, vhq = s1_post[0], s1_post[1]

    nbr_p = nbr(b8ap, b12p)
    nbr_q = nbr(b8aq, b12q)
    dnbr = nbr_p - nbr_q
    rdnbr = dnbr / np.sqrt(np.abs(nbr_p) + 1e-6)
    ndvi_p = ndvi(b4p, b8ap)
    ndvi_q = ndvi(b4q, b8aq)
    ndwi_p = ndwi(b3p, b8ap)
    ndwi_q = ndwi(b3q, b8aq)

    feats = [
        b2p, b3p, b4p, b5p, b6p, b7p, b8ap, b11p, b12p,
        b2q, b3q, b4q, b5q, b6q, b7q, b8aq, b11q, b12q,
        nbr_p, nbr_q, dnbr, rdnbr,
        ndvi_p, ndvi_q, ndwi_p, ndwi_q,
        vvp, vhp, vvq, vhq,
        vvq - vvp, vhq - vhp,
        sclp, sclq,
    ]
    for c in range(aux.shape[0]):
        feats.append(aux[c])
    return np.stack(feats, axis=0).astype(np.float32)