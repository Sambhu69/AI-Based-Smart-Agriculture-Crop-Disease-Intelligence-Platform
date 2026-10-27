# Model Evaluation & Performance Audit Scorecard

**Date:** 2026-10-27 11:18:22
- **Model Architecture:** `resnet50`
- **Checkpoint Path:** `C:\Users\ACER\Intern21\smart-agriculture-platform\models\best_model.pth`
- **Device:** `cuda`
- **Total Test Samples:** `2063` across `15` classes

---

## 1. Executive Summary & Headline Metrics

| Metric | Value | Target Benchmark | Status |
| :--- | :---: | :---: | :---: |
| **Top-1 Accuracy** | `98.98%` | ≥ 90.00% | ✅ Pass |
| **Top-3 Accuracy** | `100.00%` | ≥ 97.00% | ✅ Pass |
| **Top-5 Accuracy** | `100.00%` | ≥ 99.00% | ✅ Pass |
| **Test Cross-Entropy Loss** | `0.0345` | ≤ 0.3500 | ✅ Pass |
| **Macro F1-Score** | `98.50%` | ≥ 88.00% | ✅ Pass |
| **Weighted F1-Score** | `98.99%` | ≥ 90.00% | ✅ Pass |
| **ROC-AUC (OvR Macro)** | `0.9999` | ≥ 0.9500 | ✅ Pass |

## 2. Production Latency & Deployment Readiness

- **Mean Single-Sample Latency:** `6.21 ms`
- **P50 (Median) Latency:** `5.91 ms`
- **P95 Latency:** `8.37 ms`
- **P99 Latency:** `9.00 ms`
- **Inference Throughput:** `160.9 frames/sec (FPS)`

## 3. High-Priority Misclassification Analysis

Top error pairs where the model confused the pathology:

| True Pathology | Misclassified As | Error Count | % of True Class |
| :--- | :--- | :---: | :---: |
| `Tomato_Late_blight` | `Tomato_Early_blight` | 3 | 1.6% |
| `Tomato_Spider_mites_Two_spotted_spider_mite` | `Tomato__Target_Spot` | 3 | 1.8% |
| `Tomato__Target_Spot` | `Tomato_Early_blight` | 3 | 2.1% |
| `Potato___Late_blight` | `Potato___healthy` | 2 | 2.0% |
| `Tomato__Target_Spot` | `Tomato_Spider_mites_Two_spotted_spider_mite` | 2 | 1.4% |

## 4. Per-Class Diagnostic Performance Breakdown

Ranked from lowest to highest F1-Score to highlight classes needing data augmentation or targeted sampling:

| class_id | class_name | precision | recall | f1-score | support |
| :---: | :--- | :---: | :---: | :---: | :---: |
| 4 | Potato___healthy | 0.8824 | 1.0000 | 0.9375 | 15 |
| 6 | Tomato_Early_blight | 0.9327 | 0.9700 | 0.9510 | 100 |
| 11 | Tomato__Target_Spot | 0.9712 | 0.9643 | 0.9677 | 140 |
| 7 | Tomato_Late_blight | 0.9894 | 0.9738 | 0.9815 | 191 |
| 3 | Potato___Late_blight | 1.0000 | 0.9700 | 0.9848 | 100 |
| 10 | Tomato_Spider_mites_Two_spotted_spider_mite | 0.9880 | 0.9821 | 0.9851 | 168 |
| 13 | Tomato__Tomato_mosaic_virus | 0.9737 | 1.0000 | 0.9867 | 37 |
| 8 | Tomato_Leaf_Mold | 0.9896 | 1.0000 | 0.9948 | 95 |
| 0 | Pepper__bell___Bacterial_spot | 0.9901 | 1.0000 | 0.9950 | 100 |
| 1 | Pepper__bell___healthy | 1.0000 | 0.9932 | 0.9966 | 148 |
| 14 | Tomato_healthy | 0.9938 | 1.0000 | 0.9969 | 159 |
| 9 | Tomato_Septoria_leaf_spot | 1.0000 | 0.9944 | 0.9972 | 177 |
| 5 | Tomato_Bacterial_spot | 1.0000 | 1.0000 | 1.0000 | 213 |
| 2 | Potato___Early_blight | 1.0000 | 1.0000 | 1.0000 | 100 |
| 12 | Tomato__Tomato_YellowLeaf__Curl_Virus | 1.0000 | 1.0000 | 1.0000 | 320 |

---
### Diagnostic Visualizations
- Raw Confusion Matrix: `reports/evaluation/confusion_matrix.png`
- Normalized Confusion Matrix (Recall): `reports/evaluation/confusion_matrix_normalized.png`
- Complete Structured Metrics: `reports/evaluation/test_metrics.json`