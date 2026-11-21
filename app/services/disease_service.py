import io
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

import torch
import torch.nn.functional as F
from PIL import Image, UnidentifiedImageError
from torchvision import transforms

from app.core.config import settings
from app.core.logging import logger
from src.model import get_crop_disease_model

class DiseaseInferenceService:
    """
    Self-contained crop disease inference service.
    Encapsulates:
    - Preprocessing configuration
    - Self-contained class mapping (does not depend on raw/processed dataset dirs)
    - Full backward compatibility with existing models/best_model.pth checkpoints
    - Model architecture and version provenance
    """

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        model_version: Optional[str] = None,
        architecture: Optional[str] = None,
        device: Optional[str] = None,
        class_names: Optional[List[str]] = None,
    ):
        self.checkpoint_path = Path(checkpoint_path or settings.MODEL_CHECKPOINT_PATH)
        self.model_version = model_version or settings.MODEL_VERSION
        self.architecture = architecture or settings.MODEL_ARCHITECTURE
        
        # Determine device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Preprocessing transforms (ImageNet normalization)
        self.preprocessing_config = {
            "image_size": (settings.IMAGE_SIZE, settings.IMAGE_SIZE),
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
        }
        self.transforms = transforms.Compose([
            transforms.Resize(self.preprocessing_config["image_size"]),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=self.preprocessing_config["mean"],
                std=self.preprocessing_config["std"],
            ),
        ])

        # Self-contained class mapping
        self.class_names = class_names or list(settings.DEFAULT_CLASS_NAMES)
        self.class_to_idx = {name: i for i, name in enumerate(self.class_names)}
        self.idx_to_class = {i: name for i, name in enumerate(self.class_names)}

        self.model: Optional[torch.nn.Module] = None
        self.checkpoint_metadata: Dict[str, Any] = {}
        self.load_model()

    def load_model(self) -> None:
        """Loads weights and resolves checkpoint metadata with backward compatibility."""
        logger.info(f"Loading {self.architecture} model for {len(self.class_names)} classes on {self.device}")
        
        # Instantiate architecture
        self.model = get_crop_disease_model(
            num_classes=len(self.class_names),
            model_name=self.architecture,
            pretrained=False,
            freeze_backbone=False,
        ).to(self.device)

        if not self.checkpoint_path.exists():
            logger.warning(f"Checkpoint not found at {self.checkpoint_path}. Service will run unweighted.")
            self.model.eval()
            return

        checkpoint = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)

        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.checkpoint_metadata = {
                "epoch": checkpoint.get("epoch"),
                "best_val_loss": checkpoint.get("best_val_loss"),
                "model_version": checkpoint.get("model_version", self.model_version),
                "architecture": checkpoint.get("architecture", self.architecture),
                "class_names": checkpoint.get("class_names", self.class_names),
            }
            # If checkpoint had stored class_names, respect them
            if "class_names" in checkpoint:
                self.class_names = checkpoint["class_names"]
                self.class_to_idx = {name: i for i, name in enumerate(self.class_names)}
                self.idx_to_class = {i: name for i, name in enumerate(self.class_names)}
        elif isinstance(checkpoint, dict):
            # Raw state dict
            self.model.load_state_dict(checkpoint)
            self.checkpoint_metadata = {"raw_state_dict": True}
        else:
            raise TypeError(f"Unsupported checkpoint format: {type(checkpoint)}")

        self.model.eval()
        logger.info("Model weights loaded successfully.")

    def preprocess(self, image_bytes: bytes) -> torch.Tensor:
        """Validates and preprocesses image bytes into [1, 3, 224, 224] tensor."""
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except UnidentifiedImageError:
            raise ValueError("The provided file could not be decoded as an image.")
        except Exception as exc:
            raise ValueError(f"Image decode error: {exc}")

        tensor = self.transforms(image).unsqueeze(0).to(self.device)
        return tensor

    def predict(self, image_bytes: bytes, top_k: int = 3) -> Dict[str, Any]:
        """Runs model inference and returns structured predictions with provenance."""
        if self.model is None:
            raise RuntimeError("Model is not initialized.")

        tensor = self.preprocess(image_bytes)

        t0 = time.perf_counter()
        with torch.no_grad():
            logits = self.model(tensor)
            probs = F.softmax(logits, dim=1).squeeze(0)
        inference_time_ms = round((time.perf_counter() - t0) * 1000, 2)

        k = min(top_k, len(self.class_names))
        top_probs, top_indices = torch.topk(probs, k=k)

        top_predictions = []
        for rank, (p, idx) in enumerate(zip(top_probs.tolist(), top_indices.tolist()), start=1):
            c_name = self.idx_to_class[idx]
            top_predictions.append({
                "rank": rank,
                "class_name": c_name,
                "confidence": round(p, 4),
                "confidence_pct": f"{p * 100:.2f}%",
            })

        return {
            "primary_prediction": top_predictions[0],
            "top_k_predictions": top_predictions,
            "inference_time_ms": inference_time_ms,
            "inference_device": str(self.device),
            "model_version": self.model_version,
            "model_architecture": self.architecture,
            "epistemic_type": "predicted",
        }

# Singleton instance for modular backend
disease_service = DiseaseInferenceService()
