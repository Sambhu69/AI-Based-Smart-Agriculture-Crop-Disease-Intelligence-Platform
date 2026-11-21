import pytest
import torch
from pathlib import Path
from PIL import Image
import io
from app.services.disease_service import DiseaseInferenceService
from app.core.config import settings

def test_disease_service_initialization():
    service = DiseaseInferenceService()
    assert service.model is not None
    assert len(service.class_names) == 15
    assert service.architecture == "resnet50"
    assert service.model_version == "1.1.0"
    assert "Tomato_healthy" in service.class_to_idx
    assert service.idx_to_class[service.class_to_idx["Tomato_healthy"]] == "Tomato_healthy"

def test_disease_service_preprocessing():
    service = DiseaseInferenceService()
    img = Image.new("RGB", (300, 300), color=(120, 200, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    tensor = service.preprocess(img_bytes)
    assert tensor.shape == (1, 3, 224, 224)

def test_disease_service_predict_real_image():
    service = DiseaseInferenceService()
    sample_dir = Path("data/processed/PlantVillage/Tomato_healthy")
    if not sample_dir.exists():
        pytest.skip("Processed dataset not available on disk")

    sample_img_path = next(sample_dir.glob("*.JPG"))
    with open(sample_img_path, "rb") as f:
        img_bytes = f.read()

    result = service.predict(img_bytes, top_k=3)
    assert result["primary_prediction"]["class_name"] == "Tomato_healthy"
    assert result["primary_prediction"]["confidence"] > 0.8
    assert len(result["top_k_predictions"]) == 3
    assert result["model_version"] == "1.1.0"
    assert result["model_architecture"] == "resnet50"
    assert result["epistemic_type"] == "predicted"
    assert result["inference_time_ms"] > 0
