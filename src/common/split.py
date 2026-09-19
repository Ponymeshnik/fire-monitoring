import numpy as np

class GroupKFold:
    """
    Pure Python / NumPy GroupKFold implementation.
    Partitions dataset by group without requiring scikit-learn.
    """
    def __init__(self, n_splits=4, shuffle=True, seed=42):
        self.n_splits = n_splits
        self.shuffle = shuffle
        self.seed = seed

    def split(self, X, y=None, groups=None):
        if groups is None:
            n = len(X)
            idx = np.arange(n)
            if self.shuffle:
                np.random.default_rng(self.seed).shuffle(idx)
            for i in range(self.n_splits):
                val_idx = idx[i::self.n_splits]
                train_idx = np.setdiff1d(idx, val_idx)
                yield train_idx, val_idx
            return

        groups = np.asarray(groups)
        unique_groups = np.unique(groups)
        if self.shuffle:
            np.random.default_rng(self.seed).shuffle(unique_groups)
        
        # Greedy balance group distribution
        group_to_fold = {}
        fold_counts = np.zeros(self.n_splits, dtype=np.int64)
        
        # Sort groups by size descending for balanced folds
        group_sizes = {g: (groups == g).sum() for g in unique_groups}
        sorted_groups = sorted(unique_groups, key=lambda g: group_sizes[g], reverse=True)
        
        for g in sorted_groups:
            best_fold = int(np.argmin(fold_counts))
            group_to_fold[g] = best_fold
            fold_counts[best_fold] += group_sizes[g]

        indices = np.arange(len(groups))
        for fold in range(self.n_splits):
            val_mask = np.array([group_to_fold[g] == fold for g in groups])
            train_idx = indices[~val_mask]
            val_idx = indices[val_mask]
            yield train_idx, val_idx
