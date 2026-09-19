import numpy as np

def rle_encode(mask: np.ndarray) -> str:
    """
    mask: 2D uint8/бool массив (H, W). 1-based, построчно слева-направо, сверху-вниз.
    Возвращает строку 'start len start len ...' или '' если пикселей нет.
    """
    pixels = mask.flatten(order="C")
    pixels = np.concatenate([[0], pixels, [0]])
    runs = np.where(pixels[1:] != pixels[:-1])[0] + 1
    runs[1::2] -= runs[::2]
    if len(runs) == 0:
        return ""
    pairs = [f"{runs[i]} {runs[i+1]}" for i in range(0, len(runs), 2)]
    return " ".join(pairs)

def rle_decode(rle: str, shape) -> np.ndarray:
    """
    rle: строка 'start len start len ...' (1-based). shape=(H,W).
    """
    h, w = shape
    mask = np.zeros(h * w, dtype=np.uint8)
    if rle is None or (isinstance(rle, float) and np.isnan(rle)) or str(rle).strip() == "":
        return mask.reshape(h, w)
    s = str(rle).strip().split()
    if len(s) == 0:
        return mask.reshape(h, w)
    starts = np.array(s[0::2], dtype=np.int64) - 1  # 1-based → 0-based
    lengths = np.array(s[1::2], dtype=np.int64)
    for st, ln in zip(starts, lengths):
        mask[st:st + ln] = 1
    return mask.reshape(h, w)