import os
import numpy as np
import rasterio
import pandas as pd

def read_tif(path: str) -> np.ndarray:
    with rasterio.open(path) as src:
        arr = src.read()
    return arr  # (C, H, W)

def read_meta(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

def list_chips(folder: str, suffix: str) -> list:
    return sorted([f for f in os.listdir(folder) if f.endswith(suffix)])

def chip_id_from_name(name: str) -> str:
    return name.split("_")[0] + "_" + name.split("_")[1] + "_" + name.split("_")[2]