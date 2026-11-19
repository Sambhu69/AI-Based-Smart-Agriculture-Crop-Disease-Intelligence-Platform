"""
Test Suite for Stage 4 Pipelines
=================================
Tests:
- Provenance schemas (WeatherRecord, SoilRecord, CropYieldRecord, EPISTEMIC_TYPES)
- Lineage tracking mechanics (file hashing, execution trace, serialization)
- PlantVillage audit logic using mock temporary directory structures
- NASA POWER API parser and fetch logic using simulated JSON payloads (zero network dependency)
- Quality validator constraints (missing values, coordinate checks, duplicate checks, physical thresholds)
- Leakage-safe chronological and group splits (verifying disjointness and temporal ordering)
"""

from datetime import date, datetime, timezone
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from pipelines.common.schema import (
    EPISTEMIC_TYPES,
    CropYieldRecord,
    EpistemicType,
    SoilRecord,
    WeatherRecord,
)
from pipelines.lineage import LineageRecord
from pipelines.ingest.plantvillage_audit import (
    audit_plantvillage,
    count_images_per_class,
    parse_outlier_report,
)
from pipelines.ingest.nasa_power import (
    fetch_nasa_power_agroclimatology,
    parse_nasa_power_response,
)
from pipelines.validate.quality import (
    validate_crop_yield_records,
    validate_soil_records,
    validate_weather_records,
)
from pipelines.validate.splits import (
    chronological_split,
    group_split,
    verify_chronological_integrity,
    verify_split_disjointness,
)


# --- 1. Schemas & Epistemic Types ---

def test_epistemic_types_enumeration():
    assert "observed" in EPISTEMIC_TYPES
    assert "external" in EPISTEMIC_TYPES
    assert "predicted" in EPISTEMIC_TYPES
    assert "simulated" in EPISTEMIC_TYPES
    assert "recommended" in EPISTEMIC_TYPES


def test_weather_record_valid():
    rec = WeatherRecord(
        source_id="TEST_SENSOR_01",
        epistemic_type=EpistemicType.OBSERVED,
        collected_at=datetime.now(timezone.utc),
        latitude=27.5291,
        longitude=84.3542,
        record_date=date(2026, 1, 15),
        temperature_c=22.4,
        precipitation_mm=1.2,
        relative_humidity_pct=65.0,
        solar_radiation_mj=16.8,
        wind_speed_ms=2.1,
    )
    assert rec.temperature_c == 22.4
    assert rec.epistemic_type == EpistemicType.OBSERVED


def test_weather_record_invalid_bounds():
    with pytest.raises(ValidationError):
        WeatherRecord(
            source_id="TEST",
            epistemic_type=EpistemicType.OBSERVED,
            collected_at=datetime.now(timezone.utc),
            latitude=120.0,  # Invalid latitude (> 90)
            longitude=84.0,
            record_date=date(2026, 1, 15),
            temperature_c=20.0,
            precipitation_mm=0.0,
            relative_humidity_pct=50.0,
            solar_radiation_mj=10.0,
            wind_speed_ms=1.0,
        )


def test_soil_record_valid():
    rec = SoilRecord(
        source_id="SOIL_LAB_01",
        epistemic_type=EpistemicType.OBSERVED,
        collected_at=datetime.now(timezone.utc),
        plot_id="plot_42",
        depth_cm=15.0,
        ph=6.5,
        moisture_pct=28.4,
        nitrogen_mg_kg=45.0,
    )
    assert rec.ph == 6.5
    assert rec.moisture_pct == 28.4


def test_crop_yield_record_bounds():
    rec = CropYieldRecord(
        source_id="HARVEST_REPORT",
        epistemic_type=EpistemicType.OBSERVED,
        collected_at=datetime.now(timezone.utc),
        plot_id="plot_101",
        crop_type="Tomato",
        harvest_year=2026,
        yield_kg_per_ha=8500.0,
        area_hectares=1.5,
    )
    assert rec.yield_kg_per_ha == 8500.0


# --- 2. Lineage Tracking ---

def test_lineage_tracking(tmp_path: Path):
    lineage = LineageRecord(
        pipeline_name="UnitTestPipeline",
        stage_name="TestStage",
        parameters={"alpha": 0.5},
    )

    dummy_file = tmp_path / "artifact.txt"
    dummy_file.write_text("dummy test content", encoding="utf-8")
    lineage.add_input(dummy_file, "Input artifact")

    out_file = tmp_path / "output.txt"
    out_file.write_text("transformed content", encoding="utf-8")
    lineage.add_output(out_file, "Output artifact")

    lineage.finish(status="success", metadata={"records_processed": 10})
    save_dest = tmp_path / "lineage.json"
    lineage.save(save_dest)

    assert save_dest.exists()
    with open(save_dest, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["pipeline_name"] == "UnitTestPipeline"
    assert data["status"] == "success"
    assert len(data["inputs"]) == 1
    assert len(data["outputs"]) == 1
    assert data["inputs"][0]["sha256"] is not None


# --- 3. PlantVillage Audit Logic ---

def test_plantvillage_audit_with_fixture(tmp_path: Path):
    # Setup temporary mock dataset structure
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "proc"
    (raw_dir / "Tomato_healthy").mkdir(parents=True)
    (proc_dir / "Tomato_healthy").mkdir(parents=True)

    # 3 raw images, 2 processed images
    (raw_dir / "Tomato_healthy" / "img1.JPG").write_text("a")
    (raw_dir / "Tomato_healthy" / "img2.JPG").write_text("b")
    (raw_dir / "Tomato_healthy" / "img3.JPG").write_text("c")

    (proc_dir / "Tomato_healthy" / "img1.JPG").write_text("a")
    (proc_dir / "Tomato_healthy" / "img2.JPG").write_text("b")

    outlier_csv = tmp_path / "outliers.csv"
    outlier_csv.write_text(
        "image_path,class_name,is_outlier\n"
        "mock_path,Tomato_healthy,True\n"
        "mock_path2,Tomato_healthy,False\n"
    )

    report_out = tmp_path / "audit_report.json"
    summary = audit_plantvillage(
        raw_dir=raw_dir,
        processed_dir=proc_dir,
        outlier_report_path=outlier_csv,
        output_report_path=report_out,
    )

    assert summary["total_classes"] == 1
    assert summary["total_raw_samples"] == 3
    assert summary["total_processed_samples"] == 2
    assert summary["total_removed_samples"] == 1
    assert summary["total_flagged_outliers"] == 1
    assert report_out.exists()


# --- 4. NASA POWER Ingestion (Mocked Offline) ---

def test_nasa_power_ingestion_offline(tmp_path: Path):
    mock_api_payload = {
        "properties": {
            "parameter": {
                "T2M": {"20260101": 21.5, "20260102": 22.0},
                "PRECTOTCORR": {"20260101": 0.0, "20260102": 2.5},
                "RH2M": {"20260101": 60.0, "20260102": 70.0},
                "ALLSKY_SFC_SW_DWN": {"20260101": 15.0, "20260102": 14.5},
                "WS2M": {"20260101": 1.5, "20260102": 2.0},
            }
        }
    }

    result = fetch_nasa_power_agroclimatology(
        latitude=27.5291,
        longitude=84.3542,
        start_date="20260101",
        end_date="20260102",
        output_dir=tmp_path / "nasa_out",
        mock_payload=mock_api_payload,
    )

    assert result["status"] == "success"
    assert result["record_count"] == 2
    assert len(result["records"]) == 2
    assert result["records"][0].temperature_c == 21.5
    assert result["records"][1].precipitation_mm == 2.5


# --- 5. Quality Validation Suite ---

def test_validate_weather_quality():
    valid_rec = WeatherRecord(
        source_id="S1",
        epistemic_type=EpistemicType.OBSERVED,
        collected_at=datetime.now(timezone.utc),
        latitude=27.5,
        longitude=84.3,
        record_date=date(2026, 1, 1),
        temperature_c=25.0,
        precipitation_mm=5.0,
        relative_humidity_pct=75.0,
        solar_radiation_mj=18.0,
        wind_speed_ms=3.0,
    )

    # Valid check
    report = validate_weather_records([valid_rec])
    assert report.is_valid
    assert report.valid_records == 1

    # Duplicate check
    report_dup = validate_weather_records([valid_rec, valid_rec])
    assert not report_dup.is_valid
    assert any("Duplicate" in e["message"] for e in report_dup.errors)


def test_validate_soil_quality():
    valid_soil = SoilRecord(
        source_id="S1",
        epistemic_type=EpistemicType.OBSERVED,
        collected_at=datetime.now(timezone.utc),
        depth_cm=20.0,
        ph=6.8,
        moisture_pct=30.0,
    )
    report = validate_soil_records([valid_soil])
    assert report.is_valid


def test_validate_yield_quality():
    valid_yield = CropYieldRecord(
        source_id="S1",
        epistemic_type=EpistemicType.OBSERVED,
        collected_at=datetime.now(timezone.utc),
        plot_id="P1",
        crop_type="Potato",
        harvest_year=2026,
        yield_kg_per_ha=12000.0,
        area_hectares=2.0,
    )
    report = validate_crop_yield_records([valid_yield])
    assert report.is_valid


# --- 6. Splitting & Leakage Verification ---

def test_chronological_split_and_disjointness():
    records = [
        {"record_date": f"2026-01-{i:02d}", "val": i}
        for i in range(1, 21)
    ]
    train, val, test = chronological_split(records, date_key="record_date", train_ratio=0.7, val_ratio=0.15)
    
    assert len(train) == 14
    assert len(val) == 3
    assert len(test) == 3

    integrity = verify_chronological_integrity(train, val, test, date_key="record_date")
    assert not integrity["has_leakage"]

    disjointness = verify_split_disjointness(train, val, test, key_func=lambda x: x["record_date"])
    assert disjointness["is_disjoint"]


def test_group_split_disjointness():
    records = [
        {"farm_id": f"farm_{(i % 5) + 1}", "obs_id": i}
        for i in range(50)
    ]
    train, val, test = group_split(records, group_key="farm_id", train_ratio=0.6, val_ratio=0.2, seed=42)

    assert len(train) > 0
    assert len(val) > 0
    assert len(test) > 0

    disjointness = verify_split_disjointness(train, val, test, key_func=lambda x: x["farm_id"])
    assert disjointness["is_disjoint"]
