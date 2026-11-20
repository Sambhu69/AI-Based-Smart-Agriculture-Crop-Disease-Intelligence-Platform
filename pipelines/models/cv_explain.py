"""
Computer Vision Explainability (Grad-CAM) & Classification Evaluation Utility
=============================================================================
Provides:
1. GradCAM: Gradient-weighted Class Activation Mapping for PyTorch ResNet-50
   (targeting `layer4`), producing normalized 2D heatmaps and image overlays
   without modifying model weights or checkpoints.
2. compute_classification_metrics: Helper evaluating accuracy, macro precision,
   macro recall, macro F1, and confusion matrix given ground-truth and predictions.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix


class GradCAM:
    """
    Computes Gradient-weighted Class Activation Mapping (Grad-CAM) for CNNs.
    Default target layer is `model.layer4` for ResNet-50.
    """

    def __init__(self, model: torch.nn.Module, target_layer: Optional[torch.nn.Module] = None):
        self.model = model
        self.model.eval()
        self.target_layer = target_layer if target_layer is not None else getattr(model, "layer4", None)
        if self.target_layer is None:
            raise ValueError("Target layer could not be determined automatically. Please supply target_layer explicitly.")

        self.gradients: Optional[torch.Tensor] = None
        self.activations: Optional[torch.Tensor] = None
        self._handles: List[Any] = []
        self._register_hooks()

    def _register_hooks(self) -> None:
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0].detach()

        h1 = self.target_layer.register_forward_hook(forward_hook)
        h2 = self.target_layer.register_full_backward_hook(backward_hook)
        self._handles.extend([h1, h2])

    def generate_heatmap(
        self,
        input_tensor: torch.Tensor,
        target_class_idx: Optional[int] = None,
    ) -> np.ndarray:
        """
        Generates a 2D float32 heatmap normalized to [0.0, 1.0].
        input_tensor: Tensor of shape [1, 3, H, W]
        """
        if input_tensor.dim() != 4 or input_tensor.size(0) != 1:
            raise ValueError(f"input_tensor must have shape [1, 3, H, W], got {input_tensor.shape}")

        self.model.zero_grad()
        logits = self.model(input_tensor)

        if target_class_idx is None:
            target_class_idx = int(torch.argmax(logits, dim=1).item())

        score = logits[0, target_class_idx]
        score.backward()

        if self.gradients is None or self.activations is None:
            raise RuntimeError("Gradients or activations were not captured during backward pass.")

        # Global average pooling of gradients: [1, C, 1, 1]
        pooled_gradients = torch.mean(self.gradients, dim=[0, 2, 3], keepdim=True)
        # Weighted combination of activation maps
        cam = torch.sum(pooled_gradients * self.activations, dim=1, keepdim=True)
        # ReLU to emphasize features with a positive influence
        cam = F.relu(cam)

        # Upsample to match input spatial dimensions (H, W)
        cam = F.interpolate(
            cam,
            size=(input_tensor.size(2), input_tensor.size(3)),
            mode="bilinear",
            align_corners=False,
        )

        heatmap = cam.squeeze().cpu().numpy()
        # Min-max normalization
        heatmap_min = float(np.min(heatmap))
        heatmap_max = float(np.max(heatmap))
        if heatmap_max > heatmap_min:
            heatmap = (heatmap - heatmap_min) / (heatmap_max - heatmap_min)
        else:
            heatmap = np.zeros_like(heatmap)

        return heatmap.astype(np.float32)

    def overlay_heatmap(
        self,
        original_image: Union[Image.Image, np.ndarray],
        heatmap: np.ndarray,
        alpha: float = 0.5,
        colormap: str = "viridis",
    ) -> Image.Image:
        """
        Blends heatmap onto original RGB PIL image or array.
        """
        import matplotlib.pyplot as plt

        if isinstance(original_image, np.ndarray):
            pil_img = Image.fromarray(original_image).convert("RGB")
        else:
            pil_img = original_image.convert("RGB")

        # Resize heatmap if dimensions differ
        if heatmap.shape != (pil_img.height, pil_img.width):
            heatmap_img = Image.fromarray((heatmap * 255).astype(np.uint8)).resize(
                (pil_img.width, pil_img.height), Image.Resampling.BILINEAR
            )
            heatmap_arr = np.array(heatmap_img) / 255.0
        else:
            heatmap_arr = heatmap

        cmap = plt.get_cmap(colormap)
        colored_heatmap = (cmap(heatmap_arr)[:, :, :3] * 255).astype(np.uint8)
        colored_heatmap_pil = Image.fromarray(colored_heatmap)

        blended = Image.blend(pil_img, colored_heatmap_pil, alpha=alpha)
        return blended

    def remove_hooks(self) -> None:
        """Cleans up registered PyTorch hooks."""
        for h in self._handles:
            h.remove()
        self._handles.clear()

    def __del__(self):
        self.remove_hooks()


def compute_classification_metrics(
    y_true: List[Union[str, int]],
    y_pred: List[Union[str, int]],
    labels: Optional[List[Union[str, int]]] = None,
) -> Dict[str, Any]:
    """
    Computes standard classification evaluation metrics including:
    - Accuracy
    - Macro-averaged Precision, Recall, F1
    - Confusion Matrix array
    """
    acc = float(accuracy_score(y_true, y_pred))
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="macro", zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    return {
        "accuracy": round(acc, 4),
        "macro_precision": round(float(prec), 4),
        "macro_recall": round(float(rec), 4),
        "macro_f1": round(float(f1), 4),
        "total_samples": len(y_true),
        "confusion_matrix": cm.tolist(),
        "labels": [str(l) for l in labels] if labels is not None else None,
    }
