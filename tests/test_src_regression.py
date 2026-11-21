import pytest
from pathlib import Path
from src.model import get_crop_disease_model
import torch

def test_src_imports_and_components():
    """Ensure existing src/ pipeline modules remain completely intact and functional."""
    # 1. Model architecture
    model = get_crop_disease_model(num_classes=15, model_name="resnet50", pretrained=False)
    assert model is not None
    dummy = torch.randn(2, 3, 224, 224)
    out = model(dummy)
    assert out.shape == (2, 15)

def test_existing_checkpoint_integrity():
    """Ensure models/best_model.pth remains completely intact."""
    ckpt_path = Path("models/best_model.pth")
    assert ckpt_path.exists(), "models/best_model.pth was moved or deleted!"
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    assert "model_state_dict" in ckpt
    assert "epoch" in ckpt
    assert ckpt["epoch"] == 4
    assert "best_val_loss" in ckpt
    assert "fc.1.weight" in ckpt["model_state_dict"]
    assert ckpt["model_state_dict"]["fc.1.weight"].shape == (15, 2048)
