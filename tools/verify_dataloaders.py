import os
import sys
from pathlib import Path
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset import create_dataloaders


def resolve_data_dir() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser().resolve()
    env_dir = os.environ.get("PLANTVILLAGE_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return PROJECT_ROOT / "data" / "raw" / "PlantVillage"


def main():
    data_dir = resolve_data_dir()
    if not data_dir.exists():
        print(f"Dataset directory not found: {data_dir}")
        sys.exit(1)

    print(f"Initializing DataLoaders from {data_dir}...")
    train_loader, val_loader, test_loader, classes = create_dataloaders(data_dir, batch_size=32)

    print(f"\nSuccessfully loaded {len(classes)} classes.")
    print(f"Sample classes: {classes[:5]}")

    images, labels = next(iter(train_loader))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    images, labels = images.to(device), labels.to(device)

    print(f"Batch image tensor shape : {images.shape}")
    print(f"Batch label tensor shape : {labels.shape}")
    print(f"Tensor device location   : {images.device}")
    print("Data pipeline verification complete.")


if __name__ == "__main__":
    main()
