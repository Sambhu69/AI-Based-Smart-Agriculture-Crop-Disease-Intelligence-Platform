"""
Test Suite for Stage 6B Agronomy Service & API Endpoints
=========================================================
Tests:
1. recommend_crops: Suitability scoring, ranking order, reasons, and epistemic tagging.
2. recommend_irrigation_and_fertilizer: Urgency levels, drainage warnings, fertilizer notes, and caveats.
3. FastAPI endpoint POST /api/v1/recommend/crop-irrigation (validation, epistemic_type="recommended", DB persistence).
4. FastAPI endpoint POST /api/v1/predict/yield (validation, projection calculation, fallback tolerance, epistemic_type="predicted").
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.services.agronomy_service import recommend_crops, recommend_irrigation_and_fertilizer


# SQLite in-memory test DB fixture for Thread-safe FastAPI test client
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# --- 1. Agronomy Service Unit Tests ---

def test_recommend_crops_ranking():
    # Warm, slightly acidic, moderate moisture condition -> High for Tomato/Pepper
    res = recommend_crops(soil_ph=6.5, temperature_c=24.0, soil_moisture_pct=65.0)

    assert res["epistemic_type"] == "recommended"
    assert "ranked_crops" in res
    assert len(res["ranked_crops"]) == 5
    # The top ranked crop should have a high score
    top_crop = res["ranked_crops"][0]
    assert top_crop["suitability_score"] > 0.7
    assert len(top_crop["reasons"]) > 0
    assert "limitations" in res
    assert "assumptions" in res


def test_recommend_crops_extreme_condition():
    # Low temperature, acidic -> Potato should rank higher than warm-season Rice
    res = recommend_crops(soil_ph=5.5, temperature_c=16.0, soil_moisture_pct=70.0)
    crop_order = [c["crop_type"] for c in res["ranked_crops"]]
    assert crop_order.index("Potato") < crop_order.index("Rice")


def test_recommend_irrigation_urgent():
    # Low moisture, dry day
    res = recommend_irrigation_and_fertilizer(
        crop_type="Tomato",
        soil_moisture_pct=25.0,
        temperature_c=28.0,
        precipitation_mm=0.0,
        soil_ph=6.2,
    )
    assert res["epistemic_type"] == "recommended"
    assert res["irrigation_recommendation"]["urgency"] in ("High", "Moderate")
    assert res["irrigation_recommendation"]["estimated_water_liters_per_m2"] > 0.0


def test_recommend_irrigation_drainage_warning():
    # Saturated soil + heavy rain
    res = recommend_irrigation_and_fertilizer(
        crop_type="Potato",
        soil_moisture_pct=85.0,
        temperature_c=22.0,
        precipitation_mm=40.0,
        soil_ph=5.0,
    )
    assert res["irrigation_recommendation"]["urgency"] == "None"
    assert "drainage" in res["irrigation_recommendation"]["action"].lower()
    # Acidic soil check
    assert res["fertilizer_recommendation"]["soil_ph_status"] == "Acidic"
    assert any("limestone" in note.lower() for note in res["fertilizer_recommendation"]["guidance_notes"])


# --- 2. FastAPI Endpoint Integration Tests ---

def test_api_recommend_crop_irrigation_endpoint():
    payload = {
        "crop_type": "Tomato",
        "soil_ph": 6.4,
        "temperature_c": 23.5,
        "soil_moisture_pct": 68.0,
        "precipitation_mm": 5.0,
    }
    resp = client.post("/api/v1/recommend/crop-irrigation", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["epistemic_type"] == "recommended"
    assert data["crop_type"] == "Tomato"
    assert len(data["crop_suitability_ranking"]) > 0
    assert "irrigation_recommendation" in data
    assert "fertilizer_recommendation" in data
    assert len(data["assumptions"]) > 0


def test_api_recommend_crop_irrigation_with_plot_tracking():
    # Setup Farm and Plot in test DB
    f_resp = client.post("/api/v1/farms", json={"name": "Advisory Test Farm"})
    farm_id = f_resp.json()["id"]
    p_resp = client.post(f"/api/v1/farms/{farm_id}/plots", json={"name": "Plot Beta", "crop_type": "Pepper"})
    plot_id = p_resp.json()["id"]

    payload = {
        "crop_type": "Pepper",
        "soil_ph": 6.2,
        "temperature_c": 25.0,
        "soil_moisture_pct": 60.0,
        "plot_id": plot_id,
    }
    resp = client.post("/api/v1/recommend/crop-irrigation", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["record_id"] is not None


def test_api_predict_yield_endpoint():
    payload = {
        "crop_type": "Tomato",
        "harvest_year": 2025,
        "area_hectares": 2.5,
        "ph": 6.4,
        "moisture_pct": 28.0,
    }
    resp = client.post("/api/v1/predict/yield", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["epistemic_type"] == "predicted"
    assert data["crop_type"] == "Tomato"
    assert data["predicted_yield_kg_per_ha"] > 0.0
    assert data["total_projected_yield_kg"] == round(data["predicted_yield_kg_per_ha"] * 2.5, 2)
    assert "model_name" in data


def test_api_predict_yield_validation_failure():
    # Negative area should trigger HTTP 422
    payload = {
        "crop_type": "Tomato",
        "harvest_year": 2025,
        "area_hectares": -1.5,
    }
    resp = client.post("/api/v1/predict/yield", json=payload)
    assert resp.status_code == 422
