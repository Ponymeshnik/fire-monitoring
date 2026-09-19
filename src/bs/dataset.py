import os
import numpy as np
import torch
from torch.utils.data import Dataset
from .indices import bs_features

class BSDataset(Dataset):
    def __init__(self, root, split="train", chip_ids=None, augment=False):
        self.root = root
        self.split = split
        self.augment = augment
        self.s2_pre = os.path.join(root, "bs", "sentinel2_pre") if os.path.exists(os.path.join(root, "bs", "sentinel2_pre")) else os.path.join(root, "sentinel2_pre")
        self.s2_post = os.path.join(root, "bs", "sentinel2_post") if os.path.exists(os.path.join(root, "bs", "sentinel2_post")) else os.path.join(root, "sentinel2_post")
        self.s1_pre = os.path.join(root, "bs", "sentinel1_pre") if os.path.exists(os.path.join(root, "bs", "sentinel1_pre")) else os.path.join(root, "sentinel1_pre")
        self.s1_post = os.path.join(root, "bs", "sentinel1_post") if os.path.exists(os.path.join(root, "bs", "sentinel1_post")) else os.path.join(root, "sentinel1_post")
        self.aux_dir = os.path.join(root, "bs", "aux") if os.path.exists(os.path.join(root, "bs", "aux")) else os.path.join(root, "aux")
        self.mask_dir = os.path.join(root, "bs", "masks") if os.path.exists(os.path.join(root, "bs", "masks")) else os.path.join(root, "masks")
        if chip_ids is None and os.path.exists(self.s2_pre):
            chip_ids = sorted([f.split("_Sentinel")[0] for f in os.listdir(self.s2_pre)])
        self.ids = chip_ids or []

    def __len__(self):
        return len(self.ids)

    def _read(self, path):
        from src.common.io import read_tif
        return read_tif(path).astype(np.float32)

    def __getitem__(self, idx):
        cid = self.ids[idx]
        s2p = self._read(os.path.join(self.s2_pre, f"{cid}_Sentinel-2_pre.tif"))
        s2q = self._read(os.path.join(self.s2_post, f"{cid}_Sentinel-2_post.tif"))
        s1p = self._read(os.path.join(self.s1_pre, f"{cid}_Sentinel-1_pre.tif"))
        s1q = self._read(os.path.join(self.s1_post, f"{cid}_Sentinel-1_post.tif"))
        aux = self._read(os.path.join(self.aux_dir, f"{cid}_AUX.tif"))
        feats = bs_features(s2p, s2q, s1p, s1q, aux)

        if self.split in ("train", "val"):
            mask = self._read(os.path.join(self.mask_dir, f"{cid}_MASK.tif"))[0].astype(np.int64)
        else:
            mask = np.zeros(feats.shape[1:], dtype=np.int64)

        # Нормализация на CPU только для train (для test выполняется параллельно на GPU)
        if self.split == "train":
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