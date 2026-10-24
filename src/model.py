import torch
import torch.nn as nn
import torchvision.models as models
from typing import Literal
import logging
logger = logging.getLogger(__name__)

def get_crop_disease_model(num_classes: int = 16, model_name: Literal["resnet50", "efficientnet_b0"] = "resnet50", pretrained: bool = True, freeze_backbone: bool = True, dropout: float = 0.3) -> torch.nn.Module:
    """
    Constructs a transfer learning model for crop disease classification
    optimized for local GPU execution.
    """
    logger.info(f"Initializing model architecture: {model_name.upper()} (Pretrained={pretrained})")
    
    if model_name == "resnet50":
        weights = models.ResNet50_Weights.DEFAULT if pretrained else None
        model = models.resnet50(weights=weights)
        
        # Optionally freeze backbone layers
        if freeze_backbone:
            # Freeze all parameters first
            for param in model.parameters():
                param.requires_grad = False
            # Unfreeze the last block and classifier for ResNet-50
            for param in model.layer4.parameters():
                param.requires_grad = True
            
        # Replace the final fully connected classification layer
        in_features = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(in_features, num_classes)
        )
        
    elif model_name == "efficientnet_b0":
        weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        model = models.efficientnet_b0(weights=weights)
        
        # Optionally freeze backbone layers for EfficientNet
        if freeze_backbone:
            for param in model.parameters():
                param.requires_grad = False
            # Unfreeze the final MBConv block (last feature layer)
            for param in model.features[-1].parameters():
                param.requires_grad = True

        # Replace the final classifier
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(in_features, num_classes)
        )
    else:
        raise ValueError(f"Unsupported model architecture: {model_name}")
        
    return model

if __name__ == "__main__":
    # Quick architecture sanity check
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    net = get_crop_disease_model(num_classes=16, model_name="resnet50").to(device)
    
    # Test forward pass with a dummy tensor matching our batch shape
    dummy_input = torch.randn(4, 3, 224, 224).to(device)
    output = net(dummy_input)
    print(f"Model sanity check passed! Output tensor shape: {output.shape}") # Expected: torch.Size([4, 16])