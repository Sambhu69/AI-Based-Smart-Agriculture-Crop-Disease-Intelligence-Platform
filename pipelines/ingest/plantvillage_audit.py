"""
PlantVillage Dataset Audit Utility
==================================
Performs a strictly read-only audit across raw, processed, and outlier datasets,
analyzing per-class sample distributions, outlier fractions, and dataset shifts.
Saves structured audit results to reports/data_quality/plantvillage_audit.json.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pipelines.lineage import LineageRecord

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".JPG", ".JPEG", ".PNG"}


def count_images_per_class(root_dir: Path) -> Dict[str, int]:
    """Counts valid images in each class subfolder of a given dataset directory."""
    if not root_dir.exists() or not root_dir.is_dir():
        return {}

    counts: Dict[str, int] = {}
    for class_dir in sorted(root_dir.iterdir()):
        if class_dir.is_dir():
            img_count = sum(1 for f in class_dir.iterdir() if f.is_file() and f.suffix in IMAGE_EXTENSIONS)
            counts[class_dir.name] = img_count
    return counts


def parse_outlier_report(report_path: Path) -> Dict[str, Any]:
    """Extracts outlier metrics per class from outlier_report.csv."""
    if not report_path.exists() or not report_path.is_file():
        return {"total_outliers": 0, "per_class_outliers": {}, "available": False}

    per_class_outliers: Dict[str, int] = {}
    total_outliers = 0

    with open(report_path, mode="r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            is_outlier_val = str(row.get("is_outlier", "")).strip().lower()
            if is_outlier_val in ("true", "1", "yes"):
                total_outliers += 1
                cls = row.get("class_name", "unknown")
                per_class_outliers[cls] = per_class_outliers.get(cls, 0) + 1

    return {
        "total_outliers": total_outliers,
        "per_class_outliers": per_class_outliers,
        "available": True,
    }


def audit_plantvillage(
    raw_dir: Path = Path("data/raw/PlantVillage"),
    processed_dir: Path = Path("data/processed/PlantVillage"),
    outlier_report_path: Path = Path("suspicious_outliers/outlier_report.csv"),
    output_report_path: Path = Path("reports/data_quality/plantvillage_audit.json"),
) -> Dict[str, Any]:
    """
    Executes a comprehensive, non-destructive audit of the PlantVillage dataset
    comparing raw vs processed states and outlier incidence.
    """
    lineage = LineageRecord(
        pipeline_name="PlantVillageAudit",
        stage_name="DatasetIntegrityCheck",
        parameters={
            "raw_dir": str(raw_dir),
            "processed_dir": str(processed_dir),
            "outlier_report_path": str(outlier_report_path),
        },
    )

    if raw_dir.exists():
        lineage.add_input(raw_dir, "Raw PlantVillage dataset root")
    if processed_dir.exists():
        lineage.add_input(processed_dir, "Processed PlantVillage dataset root")
    if outlier_report_path.exists():
        lineage.add_input(outlier_report_path, "Outlier detection report CSV")

    raw_counts = count_images_per_class(raw_dir)
    proc_counts = count_images_per_class(processed_dir)
    outlier_data = parse_outlier_report(outlier_report_path)

    all_classes = sorted(set(raw_counts.keys()) | set(proc_counts.keys()))
    class_summaries = {}
    total_raw = sum(raw_counts.values())
    total_proc = sum(proc_counts.values())

    for cls in all_classes:
        r_cnt = raw_counts.get(cls, 0)
        p_cnt = proc_counts.get(cls, 0)
        o_cnt = outlier_data.get("per_class_outliers", {}).get(cls, 0)
        class_summaries[cls] = {
            "raw_count": r_cnt,
            "processed_count": p_cnt,
            "delta_removed": r_cnt - p_cnt,
            "flagged_outliers": o_cnt,
            "outlier_pct_of_raw": round((o_cnt / r_cnt * 100), 2) if r_cnt > 0 else 0.0,
        }

    audit_summary = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_classes": len(all_classes),
        "total_raw_samples": total_raw,
        "total_processed_samples": total_proc,
        "total_removed_samples": total_raw - total_proc,
        "total_flagged_outliers": outlier_data.get("total_outliers", 0),
        "outlier_report_present": outlier_data.get("available", False),
        "classes": class_summaries,
    }

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    lineage.add_output(output_report_path, "PlantVillage Audit Report JSON")
    lineage.finish(
        status="success",
        metadata={"total_raw": total_raw, "total_processed": total_proc},
    )

    lineage_path = output_report_path.parent / "plantvillage_audit_lineage.json"
    lineage.save(lineage_path)

    return audit_summary


if __name__ == "__main__":
    summary = audit_plantvillage()
    print(f"PlantVillage Audit Completed: {summary['total_classes']} classes, {summary['total_processed_samples']} processed samples.")
