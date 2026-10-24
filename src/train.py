import sys
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from tqdm import tqdm
import logging

# Ensure the src/ directory is on sys.path so local modules resolve correctly
# regardless of whether this is run as `python -m src.train` or `python src/train.py`
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from dataset import create_dataloaders
from model import get_crop_disease_model


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def train_model(
    data_dir: str,
    epochs: int = 10,
    batch_size: int = 32,
    lr: float = 1e-4,
    model_name: str = "resnet50",
    seed: int = 42,
):
    # ── Reproducibility ───────────────────────────────────────────────────
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    
    if device.type == "cuda":
        logger.info(f"GPU Name: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM Allocated: {torch.cuda.memory_allocated(0) / 1e9:.2f} GB")

    # 1. Load DataLoaders
    logger.info("Initializing DataLoaders from processed dataset...")
    train_loader, val_loader, test_loader, classes = create_dataloaders(
        data_dir=data_dir,
        batch_size=batch_size,
        seed=seed,          # pass the same seed so dataset split is also reproducible
    )
    num_classes = len(classes)
    logger.info(f"Loaded {num_classes} classes: {classes}")

    # 2. Initialize Model
    model = get_crop_disease_model(
        num_classes=num_classes,
        model_name=model_name,
        pretrained=True,
        freeze_backbone=True
    ).to(device)

    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_total     = sum(p.numel() for p in model.parameters())
    logger.info(f"Trainable params: {n_trainable:,} / {n_total:,} ({100*n_trainable/n_total:.1f}%)")

    # 3. Loss, Optimizer & Scheduler
    criterion = nn.CrossEntropyLoss()
    # Optimize only parameters that require gradients (unfrozen layers + classification head)
    optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=lr, weight_decay=1e-3)
    # Mixed-precision scaler (device_type required in PyTorch >= 2.0)
    _device_type = "cuda" if device.type == "cuda" else "cpu"
    scaler = torch.amp.GradScaler(_device_type)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=2, factor=0.5)

    best_val_loss = float('inf')
    # Resolve models dir relative to this file so it's always in the project root
    models_dir = Path(__file__).resolve().parent.parent / "models"
    models_dir.mkdir(exist_ok=True)
    best_model_path = models_dir / "best_model.pth"

    logger.info("Starting training loop...")

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0

        # Training Phase
        train_pbar = tqdm(train_loader, desc=f"Epoch [{epoch+1}/{epochs}] Train", leave=False)
        for images, labels in train_pbar:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            with torch.amp.autocast(_device_type):
                outputs = model(images)
                loss = criterion(outputs, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total_train += labels.size(0)
            correct_train += predicted.eq(labels).sum().item()

            train_pbar.set_postfix(loss=f"{loss.item():.4f}")

        epoch_train_loss = running_loss / total_train
        epoch_train_acc = correct_train / total_train

        # Validation Phase
        model.eval()
        val_loss = 0.0
        correct_val = 0
        total_val = 0

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * images.size(0)
                _, predicted = outputs.max(1)
                total_val += labels.size(0)
                correct_val += predicted.eq(labels).sum().item()

        epoch_val_loss = val_loss / total_val
        epoch_val_acc = correct_val / total_val

        scheduler.step(epoch_val_loss)

        logger.info(
            f"Epoch [{epoch+1}/{epochs}] | "
            f"Train Loss: {epoch_train_loss:.4f} | Train Acc: {epoch_train_acc*100:.2f}% | "
            f"Val Loss: {epoch_val_loss:.4f} | Val Acc: {epoch_val_acc*100:.2f}%"
        )

        # Save Best Checkpoint
        if epoch_val_loss < best_val_loss:
            best_val_loss = epoch_val_loss
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "best_val_loss": best_val_loss
            }, best_model_path)
            logger.info(f"--> Saved new best model checkpoint to {best_model_path}")

    logger.info("Training complete!")

if __name__ == "__main__":
    DATA_PATH = r"C:\Users\ACER\Intern21\smart-agriculture-platform\data\processed\PlantVillage"
    train_model(data_dir=DATA_PATH, epochs=5, batch_size=32, lr=1e-4)