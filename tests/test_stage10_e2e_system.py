"""
Stage 10 End-to-End Integration & System Tests
==============================================
Covers:
1. Full multi-domain E2E lifecycle:
   Farm -> Plot -> Field Observations (observed/external) -> Yield Prediction (predicted)
   -> Crop/Irrigation Advisory (recommended) -> Digital Twin Simulation (simulated)
   -> Multimodal Intelligence Assessment (predicted) -> Unified History Audit (/api/v1/history).
2. Error & boundary verification:
   - 404 on unknown farm/plot or mismatched farm-plot ownership
   - 422 on invalid observation epistemic_type, invalid history limit, invalid yield area
   - Clean JSON 500 without traceback or internal detail leakage (raise_server_exceptions=False)
3. Runtime / latency sanity check on /api/v1/health and /api/v1/history.
"""

import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db


@pytest.fixture()
def e2e_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db

    @application.get("/_e2e/internal-crash")
    def _crash_endpoint():
        raise RuntimeError("SENSITIVE_DB_CREDENTIAL_XYZ_999")

    with TestClient(application, raise_server_exceptions=False) as client:
        yield client


def test_full_end_to_end_agricultural_lifecycle(e2e_client):
    """
    Exercises the complete platform workflow from physical farm registration through
    observations, ML predictions, agronomic recommendations, digital twin simulation,
    and unified provenance history auditing.
    """
    # 1. Register Farm
    farm_resp = e2e_client.post(
        "/api/v1/farms",
        json={"name": "Chitwan E2E Research Station", "location": "Chitwan, Nepal"},
    )
    assert farm_resp.status_code == 201, farm_resp.text
    farm_id = farm_resp.json()["id"]

    # 2. Create Plot under Farm
    plot_resp = e2e_client.post(
        f"/api/v1/farms/{farm_id}/plots",
        json={"name": "Plot Alpha Tomato", "crop_type": "Tomato", "area_hectares": 2.5},
    )
    assert plot_resp.status_code == 201, plot_resp.text
    plot_id = plot_resp.json()["id"]

    # Verify farm detail includes created plot
    farm_detail = e2e_client.get(f"/api/v1/farms/{farm_id}")
    assert farm_detail.status_code == 200
    assert len(farm_detail.json()["plots"]) == 1
    assert farm_detail.json()["plots"][0]["id"] == plot_id

    # 3. Record Observed and External Field Observations
    obs_url = f"/api/v1/farms/{farm_id}/plots/{plot_id}/observations"
    obs_1 = e2e_client.post(
        obs_url,
        json={
            "source": "iot_soil_probe",
            "epistemic_type": "observed",
            "data": {"soil_ph": 6.4, "soil_moisture_pct": 58.0, "temperature_c": 23.0},
            "notes": "Morning probe reading",
        },
    )
    obs_2 = e2e_client.post(
        obs_url,
        json={
            "source": "nasa_power_agro",
            "epistemic_type": "external",
            "data": {"precipitation_mm": 4.2, "relative_humidity_pct": 84.0},
            "notes": "Daily agroclimatology pull",
        },
    )
    assert obs_1.status_code == 201 and obs_1.json()["epistemic_type"] == "observed"
    assert obs_2.status_code == 201 and obs_2.json()["epistemic_type"] == "external"

    obs_list = e2e_client.get(obs_url)
    assert obs_list.status_code == 200
    assert {o["epistemic_type"] for o in obs_list.json()} == {"observed", "external"}

    # 4. Run Tabular Yield Prediction (predicted)
    yield_resp = e2e_client.post(
        "/api/v1/predict/yield",
        json={
            "crop_type": "Tomato",
            "harvest_year": 2025,
            "area_hectares": 2.5,
            "ph": 6.4,
            "moisture_pct": 58.0,
            "plot_id": plot_id,
        },
    )
    assert yield_resp.status_code == 200, yield_resp.text
    yield_data = yield_resp.json()
    assert yield_data["epistemic_type"] == "predicted"
    assert yield_data["predicted_yield_kg_per_ha"] > 0
    assert yield_data["record_id"] is not None

    # 5. Run Crop & Irrigation Recommendation (recommended)
    rec_resp = e2e_client.post(
        "/api/v1/recommend/crop-irrigation",
        json={
            "crop_type": "Tomato",
            "soil_ph": 6.4,
            "temperature_c": 23.0,
            "soil_moisture_pct": 58.0,
            "precipitation_mm": 4.2,
            "plot_id": plot_id,
        },
    )
    assert rec_resp.status_code == 200, rec_resp.text
    rec_data = rec_resp.json()
    assert rec_data["epistemic_type"] == "recommended"
    assert len(rec_data["crop_suitability_ranking"]) == 5
    assert rec_data["record_id"] is not None

    # 6. Run Digital Twin Scenario Simulation (simulated)
    twin_resp = e2e_client.post(
        "/api/v1/twin/simulate",
        json={
            "crop_type": "Tomato",
            "baseline_yield_kg_ha": yield_data["predicted_yield_kg_per_ha"],
            "scenario": "monsoon_drought",
            "plot_id": plot_id,
        },
    )
    assert twin_resp.status_code == 200, twin_resp.text
    twin_data = twin_resp.json()
    assert twin_data["epistemic_type"] == "simulated"
    assert twin_data["simulated_yield_kg_ha"] < twin_data["baseline_yield_kg_ha"]
    assert twin_data["record_id"] is not None

    # 7. Run Multimodal Intelligence Assessment (predicted)
    intel_resp = e2e_client.post(
        "/api/v1/intelligence/assess",
        json={
            "crop_type": "Tomato",
            "temperature_c": 21.0,
            "relative_humidity_pct": 88.0,
            "rainfall_mm": 6.0,
            "visual_anomaly_score": 0.2,
            "query": "Check late blight outbreak risk",
            "plot_id": plot_id,
        },
    )
    assert intel_resp.status_code == 200, intel_resp.text
    intel_data = intel_resp.json()
    assert intel_data["epistemic_type"] == "predicted"
    assert intel_data["assistant_response"]["intent_detected"] == "disease_risk_assessment"
    assert intel_data["record_id"] is not None

    # 8. Verify Unified Provenance Audit History (/api/v1/history)
    hist_resp = e2e_client.get("/api/v1/history", params={"limit": 20})
    assert hist_resp.status_code == 200, hist_resp.text
    hist_data = hist_resp.json()
    # 3 prediction_records (yield, advisory, intelligence) + 1 twin_scenario = 4 items
    assert hist_data["count"] == 4
    modules = {item["module_name"] for item in hist_data["items"]}
    assert modules == {
        "crop_yield_prediction",
        "crop_and_irrigation_advisory",
        "disease_outbreak_risk_assessment",
        "twin_service_v1",
    }
    epistemic_by_type = {item["record_type"]: item["epistemic_type"] for item in hist_data["items"]}
    assert epistemic_by_type["prediction"] == "predicted"
    assert epistemic_by_type["twin_scenario"] == "simulated"
    assert all(item["plot_id"] == plot_id for item in hist_data["items"])


def test_e2e_error_and_boundary_guards(e2e_client):
    """Verifies 404, 422, and non-leaking 500 error boundaries."""
    # 404 on unknown farm / plot
    assert e2e_client.get("/api/v1/farms/99999").status_code == 404
    assert e2e_client.post(
        "/api/v1/twin/simulate",
        json={"crop_type": "Tomato", "baseline_yield_kg_ha": 18000.0, "plot_id": 99999},
    ).status_code == 404

    # Setup farm & plot for 422 checks
    f = e2e_client.post("/api/v1/farms", json={"name": "Boundary Farm"}).json()
    p = e2e_client.post(
        f"/api/v1/farms/{f['id']}/plots",
        json={"name": "Plot B", "crop_type": "Potato"},
    ).json()

    # 422 on invalid observation epistemic_type
    bad_obs = e2e_client.post(
        f"/api/v1/farms/{f['id']}/plots/{p['id']}/observations",
        json={"source": "sim", "epistemic_type": "simulated", "data": {"ph": 6.0}},
    )
    assert bad_obs.status_code == 422

    # 422 on invalid history limit & negative yield area
    assert e2e_client.get("/api/v1/history", params={"limit": 0}).status_code == 422
    assert e2e_client.post(
        "/api/v1/predict/yield",
        json={"crop_type": "Potato", "area_hectares": -2.0},
    ).status_code == 422

    # Clean JSON 500 without leaking internal exception string or traceback
    crash = e2e_client.get("/_e2e/internal-crash")
    assert crash.status_code == 500
    body = crash.json()
    assert body["error"] == "internal_server_error"
    assert "SENSITIVE_DB_CREDENTIAL_XYZ_999" not in crash.text
    assert "Traceback" not in crash.text


def test_e2e_health_and_history_latency_sanity(e2e_client):
    """Quick runtime latency sanity check on /api/v1/health and /api/v1/history."""
    t0 = time.perf_counter()
    h_resp = e2e_client.get("/api/v1/health")
    health_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    hist_resp = e2e_client.get("/api/v1/history", params={"limit": 20})
    history_ms = (time.perf_counter() - t1) * 1000.0

    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "healthy"
    assert hist_resp.status_code == 200
    assert health_ms < 2000.0, f"/api/v1/health too slow: {health_ms:.1f} ms"
    assert history_ms < 2000.0, f"/api/v1/history too slow: {history_ms:.1f} ms"
