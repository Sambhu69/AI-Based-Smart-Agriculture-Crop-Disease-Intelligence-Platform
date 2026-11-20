"""
Test Suite for Stage 5 Multi-Domain EDA Pipelines
=================================================
Tests:
- Multi-region NASA POWER ingestion and normalized schema compliance
- Tabular crop yield and soil profile ingestion
- Leakage-safe train/val/test splitting on tabular agricultural datasets
- Multi-domain EDA pipeline execution, figure generation, and metric calculation
"""

import json
from pathlib import Path
import pytest
import pandas as pd

from pipelines.ingest.nasa_power_batch import parse_nasa_power_payload
from pipelines.ingest.tabular_crops import ingest_crop_yield_and_soil, REGIONAL_CROP_YIELD_DATA
from pipelines.eda.run_eda import run_agricultural_eda


def test_nasa_power_batch_parsing():
    mock_payload = {
        "properties": {
            "parameter": {
                "T2M": {"20230101": 18.5, "20230102": 19.0},
                "PRECTOTCORR": {"20230101": 0.0, "20230102": 1.2},
                "RH2M": {"20230101": 70.0, "20230102": 72.0},
                "ALLSKY_SFC_SW_DWN": {"20230101": 14.0, "20230102": 14.5},
                "WS2M": {"20230101": 1.8, "20230102": 2.0},
            }
        }
    }
    records = parse_nasa_power_payload(mock_payload, latitude=27.68, longitude=84.43, region_id="test_reg")
    assert len(records) == 2
    assert records[0].temperature_c == 18.5
    assert records[0].epistemic_type == "external"
    assert records[0].source_id == "NASA_POWER_TEST_REG"


def test_tabular_crop_and_soil_ingestion(tmp_path: Path):
    res = ingest_crop_yield_and_soil(output_dir=tmp_path / "crops")
    assert res["total_yield_records"] == len(REGIONAL_CROP_YIELD_DATA)
    assert res["total_soil_records"] == 3
    assert Path(res["yield_json"]).exists()
    assert Path(res["soil_json"]).exists()
    assert res["split_manifest"]["disjointness"]["is_disjoint"] is True


def test_eda_figures_and_metrics_generation(tmp_path: Path):
    audit_file = tmp_path / "audit.json"
    audit_file.write_text(json.dumps({
        "classes": {
            "Tomato_healthy": {"raw_count": 100, "processed_count": 100, "flagged_outliers": 5, "outlier_pct_of_raw": 5.0},
            "Potato_healthy": {"raw_count": 10, "processed_count": 10, "flagged_outliers": 1, "outlier_pct_of_raw": 10.0},
        }
    }), encoding="utf-8")

    outlier_file = tmp_path / "outliers.csv"
    pd.DataFrame({
        "image_path": ["p1", "p2"],
        "class_name": ["Tomato_healthy", "Potato_healthy"],
        "cosine_distance": [0.1, 0.4],
        "iso_score": [0.05, -0.1],
        "is_outlier": [False, True],
    }).to_csv(outlier_file, index=False)

    figures_dir = tmp_path / "figs"
    stats = run_agricultural_eda(
        audit_json_path=audit_file,
        outlier_csv_path=outlier_file,
        nasa_power_dir=Path("data/external/nasa_power"),
        tabular_crop_dir=Path("data/external/tabular_crops"),
        figures_dir=figures_dir,
    )

    assert stats["imbalance_ratio"] == 10.0
    assert (figures_dir / "01_plantvillage_class_imbalance.png").exists()
    assert (figures_dir / "02_plantvillage_outliers_by_class.png").exists()
    assert (figures_dir / "03_outlier_feature_space.png").exists()
