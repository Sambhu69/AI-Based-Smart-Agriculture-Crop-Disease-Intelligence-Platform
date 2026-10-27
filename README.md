<div align="center">

# 🌿 AI-Based Smart Agriculture: Crop Disease Intelligence Platform

### Production-grade deep learning pipeline for automated crop disease detection & classification

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CUDA](https://img.shields.io/badge/CUDA-Enabled-76B900?style=for-the-badge&logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-system-architecture)
- [Model Performance](#-model-performance)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Dataset](#-dataset)
- [Training Pipeline](#-training-pipeline)
- [Evaluation & Audit](#-evaluation--audit)
- [Tech Stack](#-tech-stack)

---

## 🌾 Overview

A **production-grade, end-to-end machine learning platform** that enables real-time detection and classification of crop leaf diseases using computer vision and deep learning. Built for deployment on edge devices, cloud infrastructure, and direct API consumption.

### What it does

Upload a photograph of a crop leaf — the system returns a ranked list of disease diagnoses with softmax confidence scores in milliseconds, powered by a fine-tuned **ResNet-50** model achieving **98.98% test accuracy** across 15 disease classes.

### Supported Crops & Diseases

| Crop | Conditions Detected |
|------|-------------------|
| 🌶️ **Pepper (Bell)** | Bacterial Spot, Healthy |
| 🥔 **Potato** | Early Blight, Late Blight, Healthy |
| 🍅 **Tomato** | Bacterial Spot, Early Blight, Late Blight, Leaf Mold, Septoria Leaf Spot, Spider Mites, Target Spot, Tomato Mosaic Virus, Yellow Leaf Curl Virus, Healthy |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   INFERENCE REQUEST FLOW                         │
│                                                                  │
│  Client ──► POST /predict  ──► MIME + Size Validation           │
│                                       │                          │
│                               PIL RGB Decode                     │
│                                       │                          │
│                          Resize 224×224 + ImageNet Norm          │
│                                       │                          │
│                         ResNet-50 Forward Pass (CUDA)            │
│                                       │                          │
│                          Softmax → Top-k Ranking                 │
│                                       │                          │
│  Client ◄── JSON Response ◄── Structured Prediction Payload     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────── Training Pipeline ───────────────────────────┐
│                                                                  │
│  PlantVillage Dataset (20,632 images)                           │
│       │                                                          │
│       ▼                                                          │
│  Stratified Split (75% Train / 15% Val / 10% Test)             │
│  + Zero-leakage TransformSubset                                 │
│       │                                                          │
│       ▼                                                          │
│  ResNet-50 (ImageNet pretrained) + Custom Classification Head   │
│  AdamW Optimizer + ReduceLROnPlateau + Mixed Precision (AMP)   │
│       │                                                          │
│       ▼                                                          │
│  Best Model Checkpoint → models/best_model.pth                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Model Performance

> Evaluated on a fully held-out, **untouched test set of 2,063 images** — never seen during training or validation.

| Metric | Score | Benchmark | Status |
|--------|-------|-----------|--------|
| **Top-1 Accuracy** | **98.98%** | ≥ 90.00% | ✅ Pass |
| **Top-3 Accuracy** | **100.00%** | ≥ 97.00% | ✅ Pass |
| **Top-5 Accuracy** | **100.00%** | ≥ 99.00% | ✅ Pass |
| **Test Loss (Cross-Entropy)** | **0.0345** | ≤ 0.3500 | ✅ Pass |
| **Macro F1-Score** | **98.50%** | ≥ 88.00% | ✅ Pass |
| **Weighted F1-Score** | **98.99%** | ≥ 90.00% | ✅ Pass |
| **ROC-AUC (OvR Macro)** | **0.9999** | ≥ 0.9500 | ✅ Pass |

### Inference Latency (NVIDIA GeForce RTX 4050 Laptop GPU)

| Metric | Value |
|--------|-------|
| Mean Latency | 6.80 ms |
| P50 (Median) | 6.42 ms |
| P95 Latency | 9.35 ms |
| P99 Latency | 10.77 ms |
| Throughput | **147.1 FPS** |

### Top Misclassifications (21 total errors across 2,063 samples)

| True Pathology | Confused With | Count |
|----------------|--------------|-------|
| Tomato Late Blight | Tomato Early Blight | 3 (1.6%) |
| Tomato Spider Mites | Tomato Target Spot | 3 (1.8%) |
| Tomato Target Spot | Tomato Early Blight | 3 (2.1%) |

---

## 📁 Project Structure

```
smart-agriculture-platform/
│
├── 📁 src/                         # Core source modules
│   ├── dataset.py                  # Stratified DataLoaders, zero-leakage transforms
│   ├── model.py                    # ResNet-50 / EfficientNet-B0 transfer learning
│   ├── train.py                    # Full training loop with AMP, checkpointing
│   ├── evaluate.py                 # Comprehensive test audit (ROC-AUC, Top-k, heatmaps)
│   └── api.py                      # FastAPI inference service with lifespan management
│
├── 📁 models/                      # Saved model checkpoints (.gitignored)
│   └── best_model.pth              # Best validation checkpoint
│
├── 📁 data/                        # Dataset directory (.gitignored)
│   ├── raw/PlantVillage/           # Original downloaded dataset
│   └── processed/PlantVillage/     # Class-organised dataset for ImageFolder
│
├── 📁 reports/evaluation/          # Auto-generated audit artifacts
│   ├── evaluation_summary.md       # Executive performance scorecard
│   ├── test_metrics.json           # Machine-readable metrics for CI/CD
│   ├── classification_report.csv   # Per-class precision/recall/F1
│   ├── confusion_matrix.png        # Raw count heatmap
│   └── confusion_matrix_normalized.png  # Recall-normalized heatmap
│
├── 📁 notebooks/                   # Exploratory & validation notebooks
│   ├── 01_eda.ipynb
│   └── 02_data_validation.ipynb
│
├── 📁 tests/                       # API integration test suite
│   └── test_api.py                 # 5 endpoint tests (health, classes, predict, errors)
│
├── 📁 configs/                     # Hyperparameter configuration files
├── 📁 experiments/                 # Experiment logs and results
├── 📁 docs/                        # Additional documentation
│
├── find_outliers.py                # Statistical outlier detection pipeline
├── requirements.txt                # Project dependencies
└── README.md                       # This file
```

---

## ⚡ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Sambhu69/AI-Based-Smart-Agriculture-Crop-Disease-Intelligence-Platform.git
cd AI-Based-Smart-Agriculture-Crop-Disease-Intelligence-Platform
```

### 2. Set Up Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Prepare Dataset

Download the [PlantVillage dataset](https://www.kaggle.com/datasets/emmarex/plantdisease) and organize it under `data/processed/PlantVillage/` in `ImageFolder` format (one subfolder per class):

```
data/processed/PlantVillage/
├── Pepper__bell___Bacterial_spot/
├── Pepper__bell___healthy/
├── Potato___Early_blight/
│   ... (15 classes total)
└── Tomato_healthy/
```

### 4. Train the Model

```bash
python -m src.train
```

> Training runs for 5 epochs by default on GPU. Best checkpoint is auto-saved to `models/best_model.pth`.

### 5. Evaluate on Test Set

```bash
python src/evaluate.py
```

Generates a full audit report in `reports/evaluation/` including confusion matrix heatmaps, per-class metrics, and an executive scorecard.

### 6. Launch the Inference API

```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## 🔌 API Reference

### `GET /health` — Service Health Check

```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda",
  "num_classes": 15,
  "checkpoint_epoch": 4,
  "best_val_loss": 0.023131
}
```

### `GET /classes` — List Supported Disease Classes

```json
{
  "num_classes": 15,
  "classes": ["Pepper__bell___Bacterial_spot", "Pepper__bell___healthy", "..."]
}
```

### `POST /predict` — Classify a Leaf Image

**Request:** `multipart/form-data` with a JPEG/PNG/WebP image file (max 10 MB)

**Query parameter:** `top_k` (1–10, default 3)

**Response:**
```json
{
  "filename": "leaf.jpg",
  "primary_prediction": {
    "rank": 1,
    "class_name": "Tomato_healthy",
    "confidence": 0.9998,
    "confidence_pct": "99.98%"
  },
  "top_k_predictions": [
    { "rank": 1, "class_name": "Tomato_healthy", "confidence": 0.9998, "confidence_pct": "99.98%" },
    { "rank": 2, "class_name": "Tomato_Late_blight", "confidence": 0.0001, "confidence_pct": "0.01%" },
    { "rank": 3, "class_name": "Tomato_Septoria_leaf_spot", "confidence": 0.0001, "confidence_pct": "0.01%" }
  ],
  "inference_device": "cuda",
  "inference_time_ms": 6.82
}
```

**Error Responses:**

| Code | Reason |
|------|--------|
| `400` | Unsupported file type or file exceeds 10 MB |
| `422` | File cannot be decoded as a valid image |
| `503` | Model not ready (startup failure) |

---

## 📦 Dataset

| Property | Value |
|----------|-------|
| Dataset | [PlantVillage](https://www.kaggle.com/datasets/emmarex/plantdisease) |
| Total Images | 20,632 |
| Train Split | 15,474 (75%) |
| Validation Split | 3,095 (15%) |
| Test Split | 2,063 (10%) |
| Split Strategy | Stratified per class (reproducible, seed=42) |
| Image Size | 224 × 224 px |
| Normalization | ImageNet (μ=[0.485,0.456,0.406], σ=[0.229,0.224,0.225]) |

> ⚠️ The `data/` directory is excluded from version control due to size. Use the Kaggle link above to download the dataset.

---

## 🧠 Training Pipeline

### Model Architecture

- **Backbone:** ResNet-50 (ImageNet pretrained)
- **Fine-tuning strategy:** Frozen backbone → Unfreeze `layer4` + classification head
- **Classification head:** `Dropout(0.3)` → `Linear(2048 → 15)`
- **Supports:** ResNet-50, EfficientNet-B0 (configurable via `--model-name`)

### Training Configuration

| Hyperparameter | Value |
|---------------|-------|
| Optimizer | AdamW |
| Learning Rate | 1e-4 |
| Weight Decay | 1e-3 |
| Scheduler | ReduceLROnPlateau (patience=2, factor=0.5) |
| Batch Size | 32 |
| Epochs | 5 |
| Precision | Mixed (AMP — `torch.amp.autocast`) |
| Seed | 42 (fully reproducible) |

### Data Augmentation (Training only)

- Random Horizontal Flip (p=0.5)
- Random Vertical Flip (p=0.2)
- Random Rotation (±15°)
- Color Jitter (brightness, contrast, saturation ±0.2)

---

## 🔬 Evaluation & Audit

Run the full evaluation suite against the held-out test set:

```bash
# Standard evaluation
python src/evaluate.py

# Custom checkpoint / output dir
python src/evaluate.py --checkpoint models/best_model.pth --output-dir reports/my_run

# Skip latency benchmarking
python src/evaluate.py --skip-latency
```

**Generated artifacts in `reports/evaluation/`:**

| File | Description |
|------|-------------|
| `evaluation_summary.md` | Executive scorecard with pass/fail benchmarks |
| `test_metrics.json` | Full structured metrics for CI/CD integration |
| `classification_report.csv` | Per-class precision, recall, F1, support |
| `confusion_matrix.png` | Raw count confusion matrix heatmap |
| `confusion_matrix_normalized.png` | Recall-normalized per-class confusion matrix |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Deep Learning** | PyTorch 2.x, torchvision, CUDA |
| **Model Architecture** | ResNet-50 (transfer learning) |
| **Training** | Mixed Precision (AMP), AdamW, ReduceLROnPlateau |
| **Inference API** | FastAPI 0.162+, Uvicorn, Pydantic v2 |
| **Image Processing** | Pillow (PIL), torchvision transforms |
| **Evaluation** | scikit-learn, seaborn, matplotlib, pandas |
| **Testing** | Python asyncio, FastAPI test utilities |
| **Python** | 3.12+ |

---

## 📈 Evaluation Report Snapshot

> Auto-generated from `python src/evaluate.py`

```
=======================================================================
PERFORMANCE AUDIT RESULTS SUMMARY
=======================================================================
Test Samples Audited : 2,063
Test Loss            : 0.0345
Top-1 Accuracy       : 98.98%
Top-3 Accuracy       : 100.00%
Top-5 Accuracy       : 100.00%
Macro F1-Score       : 98.50%
Weighted F1-Score    : 98.99%
ROC-AUC (OvR Macro)  : 0.9999
Single-Image Latency : 6.80 ms (147.1 FPS)
=======================================================================
```

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ❤️ for smart, sustainable agriculture

**[⭐ Star this repo](https://github.com/Sambhu69/AI-Based-Smart-Agriculture-Crop-Disease-Intelligence-Platform)** if you find it useful!

</div>
