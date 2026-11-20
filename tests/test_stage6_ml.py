"""
Test Suite for Stage 6 Core AI/ML Baseline Pipelines
====================================================
Tests:
- Grad-CAM heatmap generation, shape invariants, and intensity normalization [0.0, 1.0]
- Grad-CAM image overlay blending
- Classification evaluation metrics helper (accuracy, macro precision/recall/F1, confusion matrix)
- Crop yield baseline training, evaluation metric structure (MAE, RMSE, R²), and inference function
- Weather time-series causal lag feature engineering and chronological split integrity
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import pytest
import torch
import torch.nn as nn

from pipelines.models.cv_explain import GradCAM, compute_classification_metrics
from pipelines.models.yield_baseline import (
    predict_yield,
    prepare_yield_dataset,
    train_and_evaluate_yield_baseline,
)
from pipelines.models.weather_baseline import (
    engineer_time_series_features,
    train_and_evaluate_weather_baseline,
)


# --- 1. Grad-CAM Tests ---

class MockConvNet(nn.Module):
    """Tiny CNN with a named layer matching Grad-CAM targets."""
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, kernel_size=3, padding=1)
        self.layer4 = nn.Sequential(
            nn.Conv2d(8, 16, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        self.gap = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(16, 3)

    def forward(self, x):
        x = self.conv(x)
        x = self.layer4(x)
        x = self.gap(x)
        x = torch.flatten(x, 1)
        return self.fc(x)


def test_gradcam_generation():
    model = MockConvNet()
    cam = GradCAM(model, target_layer=model.layer4)

    dummy_input = torch.randn(1, 3, 64, 64, requires_grad=True)
    heatmap = cam.generate_heatmap(dummy_input, target_class_idx=1)

    assert isinstance(heatmap, np.ndarray)
    assert heatmap.shape == (64, 64)
    assert np.all(heatmap >= 0.0)
    assert np.all(heatmap <= 1.0)
    assert np.isfinite(heatmap).all()

    # Test overlay creation
    pil_img = Image.new("RGB", (64, 64), color=(100, 150, 200))
    blended = cam.overlay_heatmap(pil_img, heatmap)
    assert isinstance(blended, Image.Image)
    assert blended.size == (64, 64)

    cam.remove_hooks()


# --- 2. Classification Evaluation Helper ---

def test_compute_classification_metrics():
    y_true = ["healthy", "healthy", "blight", "blight", "virus"]
    y_pred = ["healthy", "blight", "blight", "blight", "virus"]
    labels = ["healthy", "blight", "virus"]

    metrics = compute_classification_metrics(y_true, y_pred, labels=labels)
    assert metrics["accuracy"] == 0.8
    assert metrics["macro_precision"] > 0.0
    assert metrics["macro_recall"] > 0.0
    assert metrics["macro_f1"] > 0.0
    assert len(metrics["confusion_matrix"]) == 3
    assert metrics["total_samples"] == 5


# --- 3. Crop Yield Baseline Tests ---

def test_crop_yield_baseline_training_and_predict(tmp_path: Path):
    df_sample = pd.DataFrame([
        {"plot_id": f"plot_{i%3}", "crop_type": "Tomato" if i%2==0 else "Potato", "harvest_year": 2010 + i, "yield_kg_per_ha": 15000.0 + i * 250, "area_hectares": 2.0, "ph": 6.5, "moisture_pct": 28.0, "nitrogen_mg_kg": 40.0, "organic_matter_pct": 2.5}
        for i in range(20)
    ])

    model_dir = tmp_path / "models"
    metrics_file = tmp_path / "metrics.json"

    metrics = train_and_evaluate_yield_baseline(
        df=df_sample,
        output_model_dir=model_dir,
        metrics_path=metrics_file,
    )

    assert "best_model" in metrics
    assert "models" in metrics
    assert "ridge_regression" in metrics["models"]
    assert "MAE" in metrics["models"]["ridge_regression"]
    assert "RMSE" in metrics["models"]["ridge_regression"]
    assert "R2" in metrics["models"]["ridge_regression"]

    # Test standalone prediction
    bundle_path = model_dir / "yield_baseline.joblib"
    pred_val = predict_yield(
        {"crop_type": "Tomato", "harvest_year": 2025, "area_hectares": 2.5, "ph": 6.5, "moisture_pct": 28.0},
        model_bundle_path=bundle_path,
    )
    assert isinstance(pred_val, float)
    assert pred_val > 0.0


# --- 4. Weather Time-Series Baseline Tests ---

def test_weather_time_series_baseline(tmp_path: Path):
    dates = pd.date_range("2020-01-01", periods=60, freq="D")
    df_weather = pd.DataFrame({
        "record_date": dates,
        "temperature_c": 22.0 + 3.0 * np.sin(np.linspace(0, 3.14 * 4, 60)),
        "precipitation_mm": 0.5,
        "relative_humidity_pct": 70.0,
        "solar_radiation_mj": 16.0,
        "wind_speed_ms": 2.2,
        "source_id": "TEST_STATION",
    })

    # Test causal feature engineering
    df_feat = engineer_time_series_features(df_weather)
    assert "temp_lag_1" in df_feat.columns
    assert "target_next_day_temp" in df_feat.columns
    assert not df_feat.isna().any().any()

    # Verify no future leakage in feature values: lag_1 on day t must equal temperature on day t-1
    assert df_feat.iloc[1]["temp_lag_1"] == df_feat.iloc[0]["temperature_c"]

    metrics_file = tmp_path / "weather_metrics.json"
    res = train_and_evaluate_weather_baseline(df=df_weather, metrics_path=metrics_file)

    assert "models" in res
    assert "persistence_naive" in res["models"]
    assert "ridge_regression" in res["models"]
    assert "random_forest" in res["models"]
    assert res["models"]["persistence_naive"]["MAE"] >= 0.0
    assert res["models"]["ridge_regression"]["RMSE"] >= 0.0
