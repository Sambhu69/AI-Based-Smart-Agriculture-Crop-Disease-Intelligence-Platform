import torch
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms
from PIL import Image
import numpy as np
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Transform definitions
# ──────────────────────────────────────────────────────────────────────────────

def get_transforms(img_size: int = 224):
    """
    Returns separate train and validation/test transform pipelines.

    Train transforms include data augmentation; val/test transforms do not.
    """
    train_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.2),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    return train_transforms, val_transforms


# ──────────────────────────────────────────────────────────────────────────────
# TransformSubset – gives each split its own independent transform
# ──────────────────────────────────────────────────────────────────────────────

class TransformSubset(torch.utils.data.Dataset):
    """
    Wraps a Subset and applies its own transform independently,
    preventing the transform-leakage bug that occurs when mutating
    Subset.dataset.transform on a shared underlying dataset.
    """
    def __init__(self, subset: Subset, transform):
        self.subset = subset
        self.transform = transform

    def __len__(self):
        return len(self.subset)

    def __getitem__(self, idx):
        img_path, label = self.subset.dataset.imgs[self.subset.indices[idx]]
        img = Image.open(img_path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label


# ──────────────────────────────────────────────────────────────────────────────
# DataLoader factory
# ──────────────────────────────────────────────────────────────────────────────

def create_dataloaders(
    data_dir: str,
    batch_size: int = 32,
    val_split: float = 0.15,
    test_split: float = 0.10,
    img_size: int = 224,
    num_workers: int = 2,
    seed: int = 42,
):
    """
    Creates stratified PyTorch DataLoaders for Train / Validation / Test splits.

    Key properties:
    - Stratified split: every class is proportionally represented in all three
      splits (no class accidentally absent from val/test).
    - Zero transform leakage: each split receives its own independent transform
      via TransformSubset, so training augmentations never bleed into val/test.
    - Reproducible: controlled by ``seed``.
    - Overlap guard: asserts no index is shared across splits.

    Parameters
    ----------
    data_dir : str
        Root directory in ImageFolder format (class-name subfolders).
    batch_size : int
        Mini-batch size for all DataLoaders.
    val_split : float
        Fraction of the full dataset reserved for validation (default 0.15).
    test_split : float
        Fraction of the full dataset reserved for testing (default 0.10).
    img_size : int
        Square pixel dimension images are resized to (default 224).
    num_workers : int
        Worker processes per DataLoader. 2 is a safe default for RTX 4050.
    seed : int
        Random seed for reproducible splits (default 42).
    """
    train_tx, val_tx = get_transforms(img_size=img_size)

    # Load full dataset with transform=None; each TransformSubset applies its own
    full_dataset = datasets.ImageFolder(root=data_dir, transform=None)
    all_labels = np.array([label for _, label in full_dataset.imgs])
    num_classes = len(full_dataset.classes)

    # ── Stratified index split ─────────────────────────────────────────────
    rng = np.random.default_rng(seed)
    train_indices, val_indices, test_indices = [], [], []

    for class_id in range(num_classes):
        class_indices = np.where(all_labels == class_id)[0]
        rng.shuffle(class_indices)

        n_total = len(class_indices)
        n_test  = max(1, round(n_total * test_split))
        n_val   = max(1, round(n_total * val_split))
        n_train = n_total - n_val - n_test

        if n_train < 1:
            raise ValueError(
                f"Class '{full_dataset.classes[class_id]}' has too few samples "
                f"({n_total}) to create a train/val/test split."
            )

        train_indices.extend(class_indices[:n_train].tolist())
        val_indices.extend(class_indices[n_train:n_train + n_val].tolist())
        test_indices.extend(class_indices[n_train + n_val:].tolist())

    # ── Hard overlap guard (RuntimeError survives -O / -OO flags) ────────────
    tv_overlap = set(train_indices) & set(val_indices)
    tt_overlap = set(train_indices) & set(test_indices)
    vt_overlap = set(val_indices)   & set(test_indices)
    if tv_overlap:
        raise RuntimeError(f"Train/val index overlap detected! ({len(tv_overlap)} shared indices)")
    if tt_overlap:
        raise RuntimeError(f"Train/test index overlap detected! ({len(tt_overlap)} shared indices)")
    if vt_overlap:
        raise RuntimeError(f"Val/test index overlap detected! ({len(vt_overlap)} shared indices)")

    logger.info(
        "Dataset splits (stratified) -> "
        f"Train: {len(train_indices)}, Val: {len(val_indices)}, Test: {len(test_indices)}"
    )

    # ── Wrap each split with its own transform ─────────────────────────────
    train_ds = TransformSubset(Subset(full_dataset, train_indices), train_tx)
    val_ds   = TransformSubset(Subset(full_dataset, val_indices),   val_tx)
    test_ds  = TransformSubset(Subset(full_dataset, test_indices),  val_tx)

    # ── DataLoaders optimised for RTX 4050 ────────────────────────────────
    _loader_kwargs = dict(
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=True,
        persistent_workers=(num_workers > 0),
    )
    train_loader = DataLoader(train_ds, shuffle=True,  **_loader_kwargs)
    val_loader   = DataLoader(val_ds,   shuffle=False, **_loader_kwargs)
    test_loader  = DataLoader(test_ds,  shuffle=False, **_loader_kwargs)

    return train_loader, val_loader, test_loader, full_dataset.classes