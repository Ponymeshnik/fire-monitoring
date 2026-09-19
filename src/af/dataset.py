import os
import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset
from .features import af_features

class AFDataset(Dataset):
    def __init__(self, root, split="train", chip_ids=None, augment=False):
        self.root = root
        self.split = split
        self.augment = augment
        self.viirs_dir = os.path.join(root, "af", "viirs")
        self.aux_dir = os.path.join(root, "af", "aux")
        self.mask_dir = os.path.join(root, "af", "masks")
        if chip_ids is None:
            chip_ids = sorted([f.split("_VIIRS")[0] for f in os.listdir(self.viirs_dir)])
        self.ids = chip_ids

    def __len__(self):
        return len(self.ids)

    def _read(self, path):
        with rasterio.open(path) as src:
            return src.read().astype(np.float32)

    def __getitem__(self, idx):
        cid = self.ids[idx]
        viirs = self._read(os.path.join(self.viirs_dir, f"{cid}_VIIRS_I1-I5.tif"))
        aux = self._read(os.path.join(self.aux_dir, f"{cid}_AUX.tif"))
        feats = af_features(viirs, aux)  # (F, H, W)
        if self.split == "train":
            mask = self._read(os.path.join(self.mask_dir, f"{cid}_MASK.tif"))[0]
            mask = (mask > 0).astype(np.float32)
        else:
            mask = np.zeros(feats.shape[1:], dtype=np.float32)

        # Нормализация: per-chip z-score по каждому каналу
        mu = feats.mean(axis=(1, 2), keepdims=True)
        sd = feats.std(axis=(1, 2), keepdims=True) + 1e-6
        feats = (feats - mu) / sd

        if self.augment and self.split == "train":
            if np.random.rand() < 0.5:
                feats = feats[:, :, ::-1]; mask = mask[:, ::-1]
            if np.random.rand() < 0.5:
                feats = feats[:, ::-1, :]; mask = mask[::-1, :]
            k = np.random.randint(4)
            if k:
                feats = np.rot90(feats, k, axes=(1, 2)); mask = np.rot90(mask, k)

        return torch.from_numpy(feats.copy()), torch.from_numpy(mask.copy()).unsqueeze(0)