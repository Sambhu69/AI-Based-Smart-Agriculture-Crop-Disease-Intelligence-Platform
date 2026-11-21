"""
Lightweight Model & Feature Drift Monitor
=========================================
Module: pipelines.monitoring.drift_monitor

Provides reproducible, zero-bloat numerical drift & prediction confidence checks:
1. compute_feature_drift:
   Compares current batch feature means/stds against reference baseline (mean, std)
   using standardized z-shift thresholds -> 'normal' | 'watch' | 'drift_alert'.
2. compute_confidence_drift:
   Evaluates recent model confidence scores against a reference baseline mean.
3. evaluate_monitoring_status:
   Aggregates feature and confidence checks into a structured status report.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np


_SEVERITY_ORDER = {"normal": 0, "watch": 1, "drift_alert": 2}


def _max_status(a: str, b: str) -> str:
    return a if _SEVERITY_ORDER.get(a, 0) >= _SEVERITY_ORDER.get(b, 0) else b


def compute_feature_drift(
    reference_stats: Dict[str, Tuple[float, float]],
    current_batch: Dict[str, List[float]],
    z_watch: float = 1.5,
    z_alert: float = 2.5,
) -> Dict[str, Any]:
    """
    Compare current batch feature distributions against reference (mean, std) pairs.

    Parameters
    ----------
    reference_stats : dict[str, tuple[float, float]]
        Mapping of feature_name -> (reference_mean, reference_std).
    current_batch : dict[str, list[float]]
        Mapping of feature_name -> list of observed numeric values.
    z_watch : float
        Standardized mean-shift threshold for 'watch' status.
    z_alert : float
        Standardized mean-shift threshold for 'drift_alert' status.
    """
    feature_results: Dict[str, Dict[str, Any]] = {}
    overall = "normal"

    for feat, (ref_mean, ref_std) in reference_stats.items():
        vals = current_batch.get(feat, [])
        if not vals:
            feature_results[feat] = {
                "status": "normal",
                "sample_count": 0,
                "note": "No samples provided for feature in current batch.",
            }
            continue

        arr = np.asarray(vals, dtype=np.float64)
        curr_mean = float(np.mean(arr))
        curr_std = float(np.std(arr))
        denom = max(float(ref_std), 1e-6)
        z_shift = abs(curr_mean - float(ref_mean)) / denom

        if z_shift >= z_alert:
            feat_status = "drift_alert"
        elif z_shift >= z_watch:
            feat_status = "watch"
        else:
            feat_status = "normal"

        overall = _max_status(overall, feat_status)
        feature_results[feat] = {
            "status": feat_status,
            "sample_count": int(arr.size),
            "reference_mean": round(float(ref_mean), 4),
            "reference_std": round(float(ref_std), 4),
            "current_mean": round(curr_mean, 4),
            "current_std": round(curr_std, 4),
            "z_shift": round(z_shift, 4),
        }

    return {
        "status": overall,
        "features": feature_results,
    }


def compute_confidence_drift(
    confidences: List[float],
    ref_mean_conf: float = 0.85,
    watch_drop: float = 0.08,
    alert_drop: float = 0.15,
) -> Dict[str, Any]:
    """
    Evaluate model prediction confidence distribution against a reference baseline.
    """
    if not confidences:
        return {
            "status": "normal",
            "sample_count": 0,
            "mean_confidence": None,
            "min_confidence": None,
            "reference_baseline_confidence": ref_mean_conf,
            "drop_from_baseline": 0.0,
            "note": "No prediction confidence samples available yet.",
        }

    arr = np.asarray(confidences, dtype=np.float64)
    mean_c = float(np.mean(arr))
    min_c = float(np.min(arr))
    drop = float(ref_mean_conf) - mean_c

    if drop >= alert_drop:
        status = "drift_alert"
        note = f"Mean confidence ({mean_c:.3f}) dropped by {drop:.3f} below baseline ({ref_mean_conf:.2f})."
    elif drop >= watch_drop:
        status = "watch"
        note = f"Mean confidence ({mean_c:.3f}) is moderately below baseline ({ref_mean_conf:.2f})."
    else:
        status = "normal"
        note = f"Mean confidence ({mean_c:.3f}) is within expected operating range."

    return {
        "status": status,
        "sample_count": int(arr.size),
        "mean_confidence": round(mean_c, 4),
        "min_confidence": round(min_c, 4),
        "reference_baseline_confidence": ref_mean_conf,
        "drop_from_baseline": round(drop, 4),
        "note": note,
    }


def evaluate_monitoring_status(
    reference_stats: Optional[Dict[str, Tuple[float, float]]] = None,
    current_batch: Optional[Dict[str, List[float]]] = None,
    confidences: Optional[List[float]] = None,
    ref_mean_conf: float = 0.85,
) -> Dict[str, Any]:
    """
    Produce a combined monitoring summary across tabular feature drift and
    prediction confidence checks.
    """
    feat_report = (
        compute_feature_drift(reference_stats, current_batch or {})
        if reference_stats
        else {"status": "normal", "features": {}}
    )
    conf_report = compute_confidence_drift(
        confidences or [],
        ref_mean_conf=ref_mean_conf,
    )

    overall_status = _max_status(feat_report["status"], conf_report["status"])

    return {
        "status": overall_status,
        "feature_drift": feat_report,
        "confidence_drift": conf_report,
        "limitations": (
            "Lightweight z-shift and mean-confidence monitor. Does not replace full KS/PSI "
            "distributional testing or labeled ground-truth accuracy auditing."
        ),
    }
