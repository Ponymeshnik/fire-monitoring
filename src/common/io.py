import os
import numpy as np
import pandas as pd

def read_tif(path: str) -> np.ndarray:
    try:
        import rasterio
        with rasterio.open(path) as src:
            return src.read()
    except Exception:
        pass
    try:
        import tifffile
        arr = tifffile.imread(path)
        if arr.ndim == 2:
            return arr[np.newaxis, ...]
        elif arr.ndim == 3:
            if arr.shape[2] < arr.shape[0]:
                return np.transpose(arr, (2, 0, 1))
            return arr
    except Exception:
        pass
    from PIL import Image
    im = Image.open(path)
    arr = np.array(im)
    if arr.ndim == 2:
        return arr[np.newaxis, ...]
    elif arr.ndim == 3 and arr.shape[2] < arr.shape[0]:
        return np.transpose(arr, (2, 0, 1))
    return arr

def read_meta(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

def list_chips(folder: str, suffix: str) -> list:
    return sorted([f for f in os.listdir(folder) if f.endswith(suffix)])

def chip_id_from_name(name: str) -> str:
    return name.split("_")[0] + "_" + name.split("_")[1] + "_" + name.split("_")[2]