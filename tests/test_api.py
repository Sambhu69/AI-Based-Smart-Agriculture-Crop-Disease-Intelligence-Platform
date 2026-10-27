"""
Integration Tests for Crop Disease FastAPI Inference Service
============================================================
Module: tests.test_api

Run with:
    python -m pytest tests/test_api.py -v
Or directly:
    python tests/test_api.py
"""

import sys
from pathlib import Path
import asyncio
import io

_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from src.api import _load_model, _state, health_check, list_classes, predict_crop_disease
from fastapi import UploadFile, HTTPException

def setup_module():
    """Initializes the model once for test execution."""
    _state.model, _state.class_names, _state.checkpoint_meta = _load_model()
    _state.device = getattr(_state.model, "_inference_device")

def test_health_endpoint():
    async def _test():
        health = await health_check()
        assert health.status == "healthy"
        assert health.model_loaded is True
        assert health.num_classes == 15
        assert health.checkpoint_epoch == 4
        assert health.best_val_loss is not None
    asyncio.run(_test())

def test_classes_endpoint():
    async def _test():
        classes = await list_classes()
        assert classes.num_classes == 15
        assert "Tomato_healthy" in classes.classes
        assert "Potato___Early_blight" in classes.classes
    asyncio.run(_test())

def test_predict_real_image():
    async def _test():
        sample_dir = _ROOT_DIR / "data" / "processed" / "PlantVillage" / "Tomato_healthy"
        sample_img_path = next(sample_dir.glob("*.JPG"))
        with open(sample_img_path, "rb") as f:
            img_bytes = f.read()

        upload_file = UploadFile(
            file=io.BytesIO(img_bytes),
            filename=sample_img_path.name,
            headers={"content-type": "image/jpeg"},
        )

        pred = await predict_crop_disease(file=upload_file, top_k=3)
        assert pred.primary_prediction.class_name == "Tomato_healthy"
        assert pred.primary_prediction.confidence > 0.8
        assert len(pred.top_k_predictions) == 3
        assert pred.inference_time_ms > 0
    asyncio.run(_test())

def test_predict_invalid_mime():
    async def _test():
        upload_file = UploadFile(
            file=io.BytesIO(b"fake txt"),
            filename="test.txt",
            headers={"content-type": "text/plain"},
        )
        try:
            await predict_crop_disease(file=upload_file)
            assert False, "Should have raised HTTPException for invalid MIME"
        except HTTPException as exc:
            assert exc.status_code == 400
    asyncio.run(_test())

def test_predict_corrupted_image():
    async def _test():
        upload_file = UploadFile(
            file=io.BytesIO(b"corrupted image bytes"),
            filename="fake.jpg",
            headers={"content-type": "image/jpeg"},
        )
        try:
            await predict_crop_disease(file=upload_file)
            assert False, "Should have raised HTTPException for corrupted image"
        except HTTPException as exc:
            assert exc.status_code == 422
    asyncio.run(_test())

if __name__ == "__main__":
    setup_module()
    print("Running test_health_endpoint()...")
    test_health_endpoint()
    print("Running test_classes_endpoint()...")
    test_classes_endpoint()
    print("Running test_predict_real_image()...")
    test_predict_real_image()
    print("Running test_predict_invalid_mime()...")
    test_predict_invalid_mime()
    print("Running test_predict_corrupted_image()...")
    test_predict_corrupted_image()
    print("\nALL 5 TESTS PASSED SUCCESSFULLY!")

