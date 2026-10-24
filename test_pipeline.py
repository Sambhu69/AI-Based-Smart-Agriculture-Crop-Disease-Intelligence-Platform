import torch
from src.dataset import create_dataloaders
from pathlib import Path

def main():
    # Path to your PlantVillage dataset
    DATA_DIR = Path(r"C:\Users\ACER\Intern21\smart-agriculture-platform\data\raw\PlantVillage")

    print("Initializing DataLoaders...")
    train_loader, val_loader, test_loader, classes = create_dataloaders(DATA_DIR, batch_size=32)

    print(f"\nSuccessfully loaded {len(classes)} classes!")
    print(f"Sample Classes: {classes[:5]}")

    # Fetch a single batch and test GPU tensor transfer
    print("\nTesting batch fetching and GPU transfer on RTX 4050...")
    images, labels = next(iter(train_loader))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    images, labels = images.to(device), labels.to(device)

    print(f"Batch Image Tensor Shape : {images.shape}")  # Expected: torch.Size([32, 3, 224, 224])
    print(f"Batch Label Tensor Shape : {labels.shape}")  # Expected: torch.Size([32])
    print(f"Tensor Device Location   : {images.device}") # Expected: cuda:0
    print("Data pipeline verification complete and successful!")

if __name__ == '__main__':
    main()