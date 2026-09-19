import os
import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset
from .indices import bs_features

class BSDataset(Dataset):
    def __init__(self, root, split="train", chip_ids=None, augment=False):
        self.root = root
        self.split = split
        self.augment = augment
        self.s2_pre = os.path.join(root, "bs", "sentinel2_pre")
        self.s2_post = os.path.join(root, "bs", "sentinel2_post")
        self.s1_pre = os.path.join(root, "bs", "sentinel1_pre")
        self.s1_post = os.path.join(root, "bs", "sentinel1_post")
        self.aux_dir = os.path.join(root, "bs", "aux")
        self.mask_dir = os.path.join(root, "bs", "masks")
        if chip_ids is None:
            chip_ids = sorted([f.split("_Sentinel")[0] for f in os.listdir(self.s2_pre)])
        self.ids = chip_ids

    def __len__(self):
        return len(self.ids)

    def _read(self, path):
        with rasterio.open(path) as src:
            return src.read().astype(np.float32)

    def __getitem__(self, idx):
        cid = self.ids[idx]
        s2p = self._read(os.path.join(self.s2_pre, f"{cid}_Sentinel-2_pre.tif"))
        s2q = self._read(os.path.join(self.s2_post, f"{cid}_Sentinel-2_post.tif"))
        s1p = self._read(os.path.join(self.s1_pre, f"{cid}_Sentinel-1_pre.tif"))
        s1q = self._read(os.path.join(self.s1_post, f"{cid}_Sentinel-1_post.tif"))
        aux = self._read(os.path.join(self.aux_dir, f"{cid}_AUX.tif"))
        feats = bs_features(s2p, s2q, s1p, s1q, aux)

        if self.split == "train":
            mask = self._read(os.path.join(self.mask_dir, f"{cid}_MASK.tif"))[0].astype(np.int64)
        else:
            mask = np.zeros(feats.shape[1:], dtype=np.int64)

        # нормализация
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

        return torch.from_numpy(feats.copy()), torch.from_numpy(mask.copy())