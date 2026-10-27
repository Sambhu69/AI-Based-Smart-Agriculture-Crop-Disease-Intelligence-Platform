"""
Rigorous Production-Grade Evaluation and Model Audit Script
===========================================================
Module: src.evaluate

Audits trained crop disease models against an untouched, held-out test split.
Computes comprehensive classification metrics, Top-k accuracy, ROC-AUC, 
per-class diagnostic performance, confusion matrices, failure analysis, 
and inference latency benchmarks.

Outputs structured audit artifacts (JSON, CSV, PNG heatmaps, and Markdown scorecard)
to the reports directory.
"""

import os
import sys
import time
import json
import logging
import argparse
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

# Ensure non-interactive matplotlib backend and writable cache
os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from tqdm import tqdm
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
    top_k_accuracy_score,
    accuracy_score,
)

# ── Dynamic module resolution ──────────────────────────────────────────────────
_CURRENT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CURRENT_DIR.parent
if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from dataset import create_dataloaders
    from model import get_crop_disease_model
except ImportError:
    from src.dataset import create_dataloaders
    from src.model import get_crop_disease_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("evaluate")


def set_seed(seed: int = 42) -> None:
    """Enforces deterministic behavior for evaluation reproducibility."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def load_evaluation_checkpoint(
    checkpoint_path: Path,
    model: nn.Module,
    device: torch.device
) -> Dict[str, Any]:
    """
    Loads saved model weights into the target architecture with metadata extraction.
    Supports both raw state dictionaries and structured training checkpoint dicts.
    """
    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"Checkpoint not found at: {checkpoint_path}. "
            f"Please ensure training completed and saved weights to models/best_model.pth."
        )

    logger.info(f"Loading checkpoint weights from: {checkpoint_path}")
    try:
        # PyTorch >= 2.4 default weights_only=True may reject custom classes
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    except Exception as e:
        logger.warning(f"Standard torch.load failed ({e}). Retrying with default loader...")
        checkpoint = torch.load(checkpoint_path, map_location=device)

    meta: Dict[str, Any] = {}
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
        meta["epoch"] = checkpoint.get("epoch", "N/A")
        meta["best_val_loss"] = checkpoint.get("best_val_loss", None)
        logger.info(
            f"Successfully restored checkpoint (Epoch: {meta['epoch']}, "
            f"Best Val Loss: {meta['best_val_loss'] if meta['best_val_loss'] is not None else 'N/A'})"
        )
    elif isinstance(checkpoint, dict):
        model.load_state_dict(checkpoint)
        logger.info("Successfully loaded state dictionary.")
    else:
        raise TypeError(f"Unexpected checkpoint format loaded from {checkpoint_path}")

    return meta


def compute_roc_auc_ovr(
    all_labels: np.ndarray,
    all_probs: np.ndarray,
    num_classes: int
) -> Tuple[Optional[float], Optional[float]]:
    """
    Computes One-vs-Rest (OvR) Macro and Weighted ROC-AUC scores.
    Gracefully handles edge cases where some classes might not appear in small batches.
    """
    present_classes = np.unique(all_labels)
    if len(present_classes) < 2:
        return None, None

    try:
        if len(present_classes) == num_classes:
            roc_macro = float(roc_auc_score(all_labels, all_probs, multi_class="ovr", average="macro"))
            roc_weighted = float(roc_auc_score(all_labels, all_probs, multi_class="ovr", average="weighted"))
            return roc_macro, roc_weighted
        else:
            # Subset probabilities for classes present in test split
            sub_probs = all_probs[:, present_classes]
            # Re-normalize subset probabilities to sum to 1
            sub_probs = sub_probs / np.sum(sub_probs, axis=1, keepdims=True)
            roc_macro = float(roc_auc_score(all_labels, sub_probs, multi_class="ovr", average="macro", labels=present_classes))
            roc_weighted = float(roc_auc_score(all_labels, sub_probs, multi_class="ovr", average="weighted", labels=present_classes))
            return roc_macro, roc_weighted
    except Exception as exc:
        logger.warning(f"ROC-AUC computation skipped: {exc}")
        return None, None


def benchmark_inference_latency(
    model: nn.Module,
    device: torch.device,
    img_size: int = 224,
    warmup_iters: int = 20,
    test_iters: int = 100,
) -> Dict[str, float]:
    """
    Benchmarks single-image inference latency (batch_size=1) and throughput.
    Uses CUDA synchronization for microsecond precision when GPU is present.
    """
    logger.info("Benchmarking single-sample inference latency and throughput...")
    dummy_input = torch.randn(1, 3, img_size, img_size, device=device)
    model.eval()

    # GPU warmup to initialize kernels and power states
    with torch.inference_mode():
        for _ in range(warmup_iters):
            _ = model(dummy_input)
            if device.type == "cuda":
                torch.cuda.synchronize()

    # Latency timing loop
    latencies_ms: List[float] = []
    with torch.inference_mode():
        for _ in range(test_iters):
            if device.type == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            _ = model(dummy_input)
            if device.type == "cuda":
                torch.cuda.synchronize()
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

    latencies_arr = np.array(latencies_ms)
    mean_lat = float(np.mean(latencies_arr))
    p50_lat = float(np.median(latencies_arr))
    p95_lat = float(np.percentile(latencies_arr, 95))
    p99_lat = float(np.percentile(latencies_arr, 99))
    fps = float(1000.0 / mean_lat) if mean_lat > 0 else 0.0

    return {
        "mean_latency_ms": round(mean_lat, 2),
        "median_p50_latency_ms": round(p50_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "p99_latency_ms": round(p99_lat, 2),
        "throughput_fps": round(fps, 1),
    }


def plot_and_save_confusion_matrices(
    cm: np.ndarray,
    classes: List[str],
    output_dir: Path
) -> Tuple[Path, Path]:
    """Generates and saves raw count and recall-normalized confusion matrix heatmaps."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "confusion_matrix.png"
    norm_path = output_dir / "confusion_matrix_normalized.png"

    num_classes = len(classes)
    fig_dim = max(10, int(num_classes * 0.75))

    # 1. Raw Count Heatmap
    plt.figure(figsize=(fig_dim, fig_dim))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=classes,
        yticklabels=classes,
        cbar=True,
    )
    plt.title("Confusion Matrix (Raw Counts) - Held-Out Test Set", fontsize=14, pad=15)
    plt.xlabel("Predicted Class", fontsize=12)
    plt.ylabel("True Class", fontsize=12)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    plt.savefig(raw_path, dpi=300)
    plt.close()

    # 2. Normalized Heatmap (Recall / Class Accuracy)
    with np.errstate(all="ignore"):
        row_sums = cm.sum(axis=1, keepdims=True)
        cm_norm = np.divide(cm.astype(float), row_sums, out=np.zeros_like(cm, dtype=float), where=row_sums != 0)

    plt.figure(figsize=(fig_dim, fig_dim))
    sns.heatmap(
        cm_norm,
        annot=True,
        fmt=".2f",
        cmap="Greens",
        xticklabels=classes,
        yticklabels=classes,
        cbar=True,
        vmin=0.0,
        vmax=1.0,
    )
    plt.title("Normalized Confusion Matrix (Recall / Accuracy per Class)", fontsize=14, pad=15)
    plt.xlabel("Predicted Class", fontsize=12)
    plt.ylabel("True Class", fontsize=12)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    plt.savefig(norm_path, dpi=300)
    plt.close()

    logger.info(f"Saved confusion matrix heatmaps to: {raw_path.name} & {norm_path.name}")
    return raw_path, norm_path


def analyze_misclassifications(
    cm: np.ndarray,
    classes: List[str],
    top_n: int = 5
) -> List[Dict[str, Any]]:
    """Identifies the top most frequent disease misclassification pairs."""
    misclass_pairs = []
    num_classes = len(classes)

    for i in range(num_classes):
        for j in range(num_classes):
            if i != j and cm[i, j] > 0:
                misclass_pairs.append({
                    "true_class": classes[i],
                    "predicted_class": classes[j],
                    "count": int(cm[i, j]),
                    "pct_of_true_class": round(float(cm[i, j] / max(1, cm[i].sum()) * 100), 2),
                })

    # Sort descending by count
    misclass_pairs.sort(key=lambda x: x["count"], reverse=True)
    return misclass_pairs[:top_n]


def _dataframe_to_markdown_table(df: pd.DataFrame) -> str:
    """Converts a DataFrame to a Markdown table without requiring external tabulate dependency."""
    headers = [str(c) for c in df.columns]
    alignments = []
    for h in headers:
        if "name" in h.lower() or "class" in h.lower() and "id" not in h.lower():
            alignments.append(":---")
        else:
            alignments.append(":---:")

    header_row = "| " + " | ".join(headers) + " |"
    separator_row = "| " + " | ".join(alignments) + " |"

    body_rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            val = row[col]
            if isinstance(val, (float, np.floating)):
                cells.append(f"{val:.4f}")
            else:
                cells.append(str(val))
        body_rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header_row, separator_row] + body_rows)


def generate_markdown_report(
    summary_metrics: Dict[str, Any],
    per_class_df: pd.DataFrame,
    top_confusions: List[Dict[str, Any]],
    output_path: Path
) -> None:
    """Generates an executive-level performance audit report in Markdown."""
    lines = [
        "# Model Evaluation & Performance Audit Scorecard",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Model Architecture:** `{summary_metrics.get('model_name')}`",
        f"- **Checkpoint Path:** `{summary_metrics.get('checkpoint_path')}`",
        f"- **Device:** `{summary_metrics.get('device')}`",
        f"- **Total Test Samples:** `{summary_metrics.get('total_samples')}` across `{summary_metrics.get('num_classes')}` classes",
        "",
        "---",
        "",
        "## 1. Executive Summary & Headline Metrics",
        "",
        "| Metric | Value | Target Benchmark | Status |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Top-1 Accuracy** | `{summary_metrics['top1_accuracy'] * 100:.2f}%` | ≥ 90.00% | {'✅ Pass' if summary_metrics['top1_accuracy'] >= 0.90 else '⚠️ Warning'} |",
    ]

    if "top3_accuracy" in summary_metrics:
        lines.append(f"| **Top-3 Accuracy** | `{summary_metrics['top3_accuracy'] * 100:.2f}%` | ≥ 97.00% | {'✅ Pass' if summary_metrics['top3_accuracy'] >= 0.97 else '⚠️ Warning'} |")
    if "top5_accuracy" in summary_metrics:
        lines.append(f"| **Top-5 Accuracy** | `{summary_metrics['top5_accuracy'] * 100:.2f}%` | ≥ 99.00% | {'✅ Pass' if summary_metrics['top5_accuracy'] >= 0.99 else '⚠️ Warning'} |")

    lines.extend([
        f"| **Test Cross-Entropy Loss** | `{summary_metrics['test_loss']:.4f}` | ≤ 0.3500 | {'✅ Pass' if summary_metrics['test_loss'] <= 0.35 else '⚠️ High'} |",
        f"| **Macro F1-Score** | `{summary_metrics['macro_f1'] * 100:.2f}%` | ≥ 88.00% | {'✅ Pass' if summary_metrics['macro_f1'] >= 0.88 else '⚠️ Attention'} |",
        f"| **Weighted F1-Score** | `{summary_metrics['weighted_f1'] * 100:.2f}%` | ≥ 90.00% | {'✅ Pass' if summary_metrics['weighted_f1'] >= 0.90 else '⚠️ Attention'} |",
    ])

    if summary_metrics.get("roc_auc_ovr_macro") is not None:
        lines.append(f"| **ROC-AUC (OvR Macro)** | `{summary_metrics['roc_auc_ovr_macro']:.4f}` | ≥ 0.9500 | {'✅ Pass' if summary_metrics['roc_auc_ovr_macro'] >= 0.95 else '⚠️ Review'} |")

    if "latency" in summary_metrics:
        lat = summary_metrics["latency"]
        lines.extend([
            "",
            "## 2. Production Latency & Deployment Readiness",
            "",
            f"- **Mean Single-Sample Latency:** `{lat['mean_latency_ms']:.2f} ms`",
            f"- **P50 (Median) Latency:** `{lat['median_p50_latency_ms']:.2f} ms`",
            f"- **P95 Latency:** `{lat['p95_latency_ms']:.2f} ms`",
            f"- **P99 Latency:** `{lat['p99_latency_ms']:.2f} ms`",
            f"- **Inference Throughput:** `{lat['throughput_fps']:.1f} frames/sec (FPS)`",
        ])

    lines.extend([
        "",
        "## 3. High-Priority Misclassification Analysis",
        "",
        "Top error pairs where the model confused the pathology:",
        "",
        "| True Pathology | Misclassified As | Error Count | % of True Class |",
        "| :--- | :--- | :---: | :---: |",
    ])

    if top_confusions:
        for c in top_confusions:
            lines.append(f"| `{c['true_class']}` | `{c['predicted_class']}` | {c['count']} | {c['pct_of_true_class']:.1f}% |")
    else:
        lines.append("| *None* | *None* | 0 | 0.0% (Zero misclassifications detected) |")

    lines.extend([
        "",
        "## 4. Per-Class Diagnostic Performance Breakdown",
        "",
        "Ranked from lowest to highest F1-Score to highlight classes needing data augmentation or targeted sampling:",
        "",
    ])

    # Convert per-class dataframe sorted by f1-score ascending
    sorted_df = per_class_df.sort_values(by="f1-score", ascending=True)
    lines.append(_dataframe_to_markdown_table(sorted_df))

    lines.extend([
        "",
        "---",
        "### Diagnostic Visualizations",
        "- Raw Confusion Matrix: `reports/evaluation/confusion_matrix.png`",
        "- Normalized Confusion Matrix (Recall): `reports/evaluation/confusion_matrix_normalized.png`",
        "- Complete Structured Metrics: `reports/evaluation/test_metrics.json`",
    ])

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Saved executive evaluation scorecard to: {output_path}")


def evaluate_model(
    data_dir: str,
    checkpoint_path: Optional[str] = None,
    batch_size: int = 32,
    model_name: str = "resnet50",
    seed: int = 42,
    output_dir: Optional[str] = None,
    device_name: Optional[str] = None,
    benchmark_latency: bool = True,
) -> Dict[str, Any]:
    """
    Executes a comprehensive, production-grade model audit against the test dataset.

    Parameters
    ----------
    data_dir : str
        Path to processed PlantVillage dataset root.
    checkpoint_path : str, optional
        Path to .pth checkpoint file. Defaults to `models/best_model.pth`.
    batch_size : int
        Inference batch size.
    model_name : str
        Model architecture string ("resnet50" or "efficientnet_b0").
    seed : int
        Seed for deterministic evaluation splits matching training.
    output_dir : str, optional
        Directory where audit reports, tables, and plots are saved.
    device_name : str, optional
        'cuda', 'cpu', or None for auto-detection.
    benchmark_latency : bool
        Whether to run single-image inference latency benchmark.
    """
    set_seed(seed)

    # 1. Device configuration
    if device_name:
        device = torch.device(device_name)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Executing evaluation on device: {device}")
    if device.type == "cuda":
        logger.info(f"GPU Hardware: {torch.cuda.get_device_name(0)}")

    # 2. Path resolution
    data_path = Path(data_dir).resolve()
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_path}")

    ckpt_path = Path(checkpoint_path) if checkpoint_path else _PROJECT_ROOT / "models" / "best_model.pth"
    out_dir = Path(output_dir) if output_dir else _PROJECT_ROOT / "reports" / "evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 3. Load DataLoaders (Held-out Test Split)
    logger.info(f"Loading held-out test split from {data_path} (seed={seed})...")
    _, _, test_loader, classes = create_dataloaders(
        data_dir=str(data_path),
        batch_size=batch_size,
        seed=seed,
    )
    num_classes = len(classes)
    total_test_samples = len(test_loader.dataset)
    logger.info(f"Loaded {total_test_samples} test samples across {num_classes} distinct disease classes.")

    # 4. Initialize Architecture & Load Model Weights
    logger.info(f"Initializing {model_name} architecture for {num_classes} classes...")
    model = get_crop_disease_model(
        num_classes=num_classes,
        model_name=model_name,
        pretrained=False,
        freeze_backbone=False,
    ).to(device)

    ckpt_meta = load_evaluation_checkpoint(ckpt_path, model, device)

    # 5. Evaluation Loop
    model.eval()
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    all_preds: List[int] = []
    all_labels: List[int] = []
    all_probs_list: List[np.ndarray] = []

    logger.info("Executing evaluation loop with torch.inference_mode()...")
    with torch.inference_mode():
        for images, labels in tqdm(test_loader, desc="Evaluating Test Set", unit="batch"):
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            logits = model(images)
            loss = criterion(logits, labels)

            total_loss += loss.item() * images.size(0)
            probs = torch.softmax(logits, dim=1)
            _, preds = torch.max(logits, dim=1)

            all_preds.extend(preds.cpu().numpy().tolist())
            all_labels.extend(labels.cpu().numpy().tolist())
            all_probs_list.append(probs.cpu().numpy())

    # Aggregate evaluation tensors
    y_true = np.array(all_labels)
    y_pred = np.array(all_preds)
    y_probs = np.vstack(all_probs_list)
    avg_loss = total_loss / total_test_samples

    # 6. Comprehensive Metrics Computation
    top1_acc = float(accuracy_score(y_true, y_pred))

    # Top-k Accuracies
    top3_acc: Optional[float] = None
    top5_acc: Optional[float] = None
    if num_classes >= 3:
        top3_acc = float(top_k_accuracy_score(y_true, y_probs, k=3, labels=list(range(num_classes))))
    if num_classes >= 5:
        top5_acc = float(top_k_accuracy_score(y_true, y_probs, k=5, labels=list(range(num_classes))))

    # Precision, Recall, F1
    prec_macro, rec_macro, f1_macro, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    prec_weighted, rec_weighted, f1_weighted, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    roc_macro, roc_weighted = compute_roc_auc_ovr(y_true, y_probs, num_classes)

    # Confidence diagnostics
    max_probs = np.max(y_probs, axis=1)
    correct_mask = (y_true == y_pred)
    avg_conf_correct = float(np.mean(max_probs[correct_mask])) if np.any(correct_mask) else 0.0
    avg_conf_incorrect = float(np.mean(max_probs[~correct_mask])) if np.any(~correct_mask) else 0.0

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=list(range(num_classes)))
    top_confusions = analyze_misclassifications(cm, classes, top_n=5)

    # Per-class metrics dataframe
    p_class, r_class, f_class, s_class = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(num_classes)), zero_division=0
    )
    per_class_df = pd.DataFrame({
        "class_id": list(range(num_classes)),
        "class_name": classes,
        "precision": np.round(p_class, 4),
        "recall": np.round(r_class, 4),
        "f1-score": np.round(f_class, 4),
        "support": s_class,
    })

    # Save per-class CSV
    csv_report_path = out_dir / "classification_report.csv"
    per_class_df.to_csv(csv_report_path, index=False)

    # 7. Plots
    raw_cm_path, norm_cm_path = plot_and_save_confusion_matrices(cm, classes, out_dir)

    # 8. Latency Benchmark
    latency_stats: Optional[Dict[str, float]] = None
    if benchmark_latency:
        latency_stats = benchmark_inference_latency(model, device)

    # 9. Structure Final Audit Summary
    audit_summary: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_name": model_name,
        "checkpoint_path": str(ckpt_path),
        "device": str(device),
        "checkpoint_metadata": ckpt_meta,
        "total_samples": int(total_test_samples),
        "num_classes": int(num_classes),
        "test_loss": round(float(avg_loss), 4),
        "top1_accuracy": round(top1_acc, 4),
        "macro_precision": round(float(prec_macro), 4),
        "macro_recall": round(float(rec_macro), 4),
        "macro_f1": round(float(f1_macro), 4),
        "weighted_precision": round(float(prec_weighted), 4),
        "weighted_recall": round(float(rec_weighted), 4),
        "weighted_f1": round(float(f1_weighted), 4),
        "roc_auc_ovr_macro": round(roc_macro, 4) if roc_macro is not None else None,
        "roc_auc_ovr_weighted": round(roc_weighted, 4) if roc_weighted is not None else None,
        "confidence_analysis": {
            "mean_confidence_correct": round(avg_conf_correct, 4),
            "mean_confidence_incorrect": round(avg_conf_incorrect, 4),
        },
        "top_misclassifications": top_confusions,
    }

    if top3_acc is not None:
        audit_summary["top3_accuracy"] = round(top3_acc, 4)
    if top5_acc is not None:
        audit_summary["top5_accuracy"] = round(top5_acc, 4)
    if latency_stats is not None:
        audit_summary["latency"] = latency_stats

    # Save JSON metrics
    json_path = out_dir / "test_metrics.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    # Generate Markdown Scorecard
    md_report_path = out_dir / "evaluation_summary.md"
    generate_markdown_report(audit_summary, per_class_df, top_confusions, md_report_path)

    # 10. Console Printout
    logger.info("=" * 70)
    logger.info("PERFORMANCE AUDIT RESULTS SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Test Samples Audited : {total_test_samples}")
    logger.info(f"Test Loss            : {avg_loss:.4f}")
    logger.info(f"Top-1 Accuracy       : {top1_acc * 100:.2f}%")
    if top3_acc is not None:
        logger.info(f"Top-3 Accuracy       : {top3_acc * 100:.2f}%")
    if top5_acc is not None:
        logger.info(f"Top-5 Accuracy       : {top5_acc * 100:.2f}%")
    logger.info(f"Macro F1-Score       : {f1_macro * 100:.2f}%")
    logger.info(f"Weighted F1-Score    : {f1_weighted * 100:.2f}%")
    if roc_macro is not None:
        logger.info(f"ROC-AUC (OvR Macro)  : {roc_macro:.4f}")
    if latency_stats:
        logger.info(f"Single-Image Latency : {latency_stats['mean_latency_ms']:.2f} ms ({latency_stats['throughput_fps']:.1f} FPS)")
    logger.info("=" * 70)

    print("\nDetailed Scikit-Learn Classification Report:")
    print(classification_report(y_true, y_pred, target_names=classes, digits=4, zero_division=0))

    logger.info(f"All audit artifacts successfully generated in: {out_dir}")
    return audit_summary


def parse_args():
    parser = argparse.ArgumentParser(description="Rigorous Crop Disease Model Evaluation Audit")
    default_data = _PROJECT_ROOT / "data" / "processed" / "PlantVillage"
    default_ckpt = _PROJECT_ROOT / "models" / "best_model.pth"
    default_out = _PROJECT_ROOT / "reports" / "evaluation"

    parser.add_argument("--data-dir", type=str, default=str(default_data), help="Path to processed dataset")
    parser.add_argument("--checkpoint", type=str, default=str(default_ckpt), help="Path to .pth checkpoint")
    parser.add_argument("--batch-size", type=int, default=32, help="Evaluation batch size")
    parser.add_argument("--model-name", type=str, default="resnet50", choices=["resnet50", "efficientnet_b0"], help="Architecture name")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for test split replication")
    parser.add_argument("--output-dir", type=str, default=str(default_out), help="Output directory for reports")
    parser.add_argument("--device", type=str, default=None, help="Device ('cuda' or 'cpu')")
    parser.add_argument("--skip-latency", action="store_true", help="Skip inference latency benchmarking")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate_model(
        data_dir=args.data_dir,
        checkpoint_path=args.checkpoint,
        batch_size=args.batch_size,
        model_name=args.model_name,
        seed=args.seed,
        output_dir=args.output_dir,
        device_name=args.device,
        benchmark_latency=not args.skip_latency,
    )
