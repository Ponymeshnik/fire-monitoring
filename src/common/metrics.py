import numpy as np

def _binarize(x):
    return (x > 0).astype(np.uint8)

def f1_af(preds: list, gts: list) -> float:
    """Микро-усреднение F1 по всем AF-чипам."""
    tp = fp = fn = 0
    for p, g in zip(preds, gts):
        p = _binarize(p); g = _binarize(g)
        tp += int(((p == 1) & (g == 1)).sum())
        fp += int(((p == 1) & (g == 0)).sum())
        fn += int(((p == 0) & (g == 1)).sum())
    prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    return 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 1.0

def iou_burn(preds: list, gts: list) -> float:
    """IoU бинарной маски 'класс>=1' по всем BS-чипам, микро-усреднение."""
    tp = fp = fn = 0
    for p, g in zip(preds, gts):
        p = _binarize(p); g = _binarize(g)
        tp += int(((p == 1) & (g == 1)).sum())
        fp += int(((p == 1) & (g == 0)).sum())
        fn += int(((p == 0) & (g == 1)).sum())
    denom = tp + fp + fn
    return tp / denom if denom > 0 else 1.0

def miou_sev(preds: list, gts: list, num_classes: int = 3) -> float:
    """Среднее IoU по классам 1..3 (микро-усреднение TP/FP/FN по пулу)."""
    tps = np.zeros(num_classes + 1, dtype=np.int64)
    fps = np.zeros(num_classes + 1, dtype=np.int64)
    fns = np.zeros(num_classes + 1, dtype=np.int64)
    for p, g in zip(preds, gts):
        for c in range(1, num_classes + 1):
            pc = (p == c)
            gc = (g == c)
            tps[c] += int((pc & gc).sum())
            fps[c] += int((pc & ~gc).sum())
            fns[c] += int((~pc & gc).sum())
    ious = []
    for c in range(1, num_classes + 1):
        denom = tps[c] + fps[c] + fns[c]
        if denom == 0:
            ious.append(1.0)
        else:
            ious.append(tps[c] / denom)
    return float(np.mean(ious))

def score(f1a, ioub, mious):
    return 0.35 * f1a + 0.35 * ioub + 0.30 * mious