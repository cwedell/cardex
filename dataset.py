"""
dataset.py

Provides CarGenerationDataset — a PyTorch Dataset that reads dataset_manifest.csv
and serves (image_tensor, label_idx) pairs.

Quick usage:
    from dataset import CarGenerationDataset
    import torchvision.transforms as T

    transform = T.Compose([
        T.RandomResizedCrop(224),
        T.RandomHorizontalFlip(),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    train_ds = CarGenerationDataset(
        manifest_path="dataset_manifest.csv",
        root=".",            # project root; rel_path values in CSV are relative to this
        split="train",
        transform=transform,
    )

    from torch.utils.data import DataLoader, WeightedRandomSampler
    loader = DataLoader(
        train_ds,
        batch_size=64,
        sampler=WeightedRandomSampler(train_ds.get_class_weights(), len(train_ds)),
        num_workers=4,
        pin_memory=True,
    )
    # NOTE on Windows: wrap DataLoader usage in `if __name__ == "__main__":` guard.
"""

import csv
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset


class CarGenerationDataset(Dataset):
    """
    Dataset backed by dataset_manifest.csv produced by build_manifest.py.

    Args:
        manifest_path: Path to dataset_manifest.csv.
        root: Project root directory. rel_path values in the CSV are joined
              to this path to get absolute image paths.
        split: One of 'train', 'val', 'test', or None (load all rows).
        transform: torchvision transform (or any callable) applied to each
                   PIL image before returning.
        label_filter: Optional list of label strings. Only rows whose 'label'
                      is in this list are loaded. Indices are remapped to
                      0..K-1 for the K filtered labels.
        skip_missing: If True, silently skip rows where the image file does
                      not exist on disk. If False (default), the missing file
                      will raise RuntimeError on the first __getitem__ call.
    """

    def __init__(
        self,
        manifest_path,
        root,
        split=None,
        transform=None,
        label_filter=None,
        skip_missing=False,
    ):
        self.root = Path(root)
        self.transform = transform
        self.samples = []   # list of (abs_path: Path, label_idx: int)
        self.classes = []   # sorted list of label strings present in this dataset

        self._load(manifest_path, split, label_filter, skip_missing)

    # ------------------------------------------------------------------
    # Internal

    def _load(self, manifest_path, split, label_filter, skip_missing):
        filter_set = set(label_filter) if label_filter else None
        raw = []  # list of (abs_path, label_str)

        with open(manifest_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if split is not None and row["split"] != split:
                    continue
                if filter_set is not None and row["label"] not in filter_set:
                    continue
                abs_path = self.root / row["rel_path"]
                if skip_missing and not abs_path.exists():
                    continue
                raw.append((abs_path, row["label"], int(row["label_idx"])))

        if not raw:
            self.samples = []
            self.classes = []
            self.class_to_idx = {}
            return

        if filter_set is not None:
            # Remap indices to be contiguous 0..K-1 for the filtered subset
            seen_labels = sorted({lbl for _, lbl, _ in raw})
            remap = {lbl: i for i, lbl in enumerate(seen_labels)}
            self.samples = [(p, remap[lbl]) for p, lbl, _ in raw]
            self.classes = seen_labels
        else:
            self.samples = [(p, idx) for p, _, idx in raw]
            # Reconstruct the class list from what's actually in this split.
            # Sort by index so classes[i] == label for index i.
            idx_to_label = {}
            for _, lbl, idx in raw:
                idx_to_label[idx] = lbl
            self.classes = [idx_to_label[i] for i in sorted(idx_to_label)]

        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}

    # ------------------------------------------------------------------
    # Dataset interface

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label_idx = self.samples[idx]
        try:
            img = Image.open(path).convert("RGB")
        except Exception as exc:
            raise RuntimeError(f"Failed to load image {path}: {exc}") from exc
        if self.transform is not None:
            img = self.transform(img)
        return img, label_idx

    # ------------------------------------------------------------------
    # Helpers

    def get_class_weights(self) -> torch.Tensor:
        """
        Returns a 1-D float tensor of per-sample inverse-frequency weights,
        suitable for use with torch.utils.data.WeightedRandomSampler.

        This compensates for the extreme class imbalance present in the
        VMMRdb dataset (hundreds of classes with fewer than 20 images).

        Example:
            sampler = WeightedRandomSampler(
                weights=train_ds.get_class_weights(),
                num_samples=len(train_ds),
                replacement=True,
            )
        """
        from collections import Counter
        counts = Counter(idx for _, idx in self.samples)
        weights = torch.tensor(
            [1.0 / counts[idx] for _, idx in self.samples],
            dtype=torch.float,
        )
        return weights

    def __repr__(self):
        return (
            f"CarGenerationDataset("
            f"n_samples={len(self)}, "
            f"n_classes={len(self.classes)})"
        )
