import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from PIL import Image

# SQLite in-memory test DB with StaticPool and check_same_thread=False
# This prevents sqlite3.ProgrammingError across FastAPI background/dispatch threads
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

def test_v1_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api_version"] == "v1"
    assert data["model_loaded"] is True
    assert data["num_classes"] == 15

def test_farms_and_plots_endpoints():
    # 1. Create Farm
    resp = client.post("/api/v1/farms", json={"name": "Highland Orchard", "location": "Colorado"})
    assert resp.status_code == 201
    farm = resp.json()
    farm_id = farm["id"]
    assert farm["name"] == "Highland Orchard"

    # 2. Get Farm
    resp = client.get(f"/api/v1/farms/{farm_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == farm_id

    # 3. Create Plot under Farm
    resp = client.post(
        f"/api/v1/farms/{farm_id}/plots",
        json={"name": "Pepper Patch 1", "crop_type": "Pepper", "area_hectares": 1.2},
    )
    assert resp.status_code == 201
    plot = resp.json()
    assert plot["name"] == "Pepper Patch 1"
    assert plot["farm_id"] == farm_id

    # 4. List Plots
    resp = client.get(f"/api/v1/farms/{farm_id}/plots")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

def test_field_observation_and_twin_endpoints():
    # Setup farm & plot
    f_resp = client.post("/api/v1/farms", json={"name": "Prairie Research Farm"})
    farm_id = f_resp.json()["id"]
    p_resp = client.post(f"/api/v1/farms/{farm_id}/plots", json={"name": "Test Plot", "crop_type": "Potato"})
    plot_id = p_resp.json()["id"]

    # Add Observation
    obs_resp = client.post(
        f"/api/v1/plots/{plot_id}/observations",
        json={"source": "drone_spectral", "epistemic_type": "observed", "data": {"ndvi": 0.78}},
    )
    assert obs_resp.status_code == 201
    assert obs_resp.json()["epistemic_type"] == "observed"

    # Reject Invalid Epistemic Type in Observation
    bad_obs = client.post(
        f"/api/v1/plots/{plot_id}/observations",
        json={"source": "sim", "epistemic_type": "simulated", "data": {"ndvi": 0.5}},
    )
    assert bad_obs.status_code == 422

    # Add Twin Scenario
    twin_resp = client.post(
        f"/api/v1/plots/{plot_id}/twin-scenarios",
        json={
            "scenario_name": "Heatwave +3C",
            "simulation_engine": "agri_sim_v1",
            "parameters": {"temp_delta": 3},
            "simulation_results": {"yield_impact": -8.5},
        },
    )
    assert twin_resp.status_code == 201
    assert twin_resp.json()["epistemic_type"] == "simulated"

def test_predict_disease_endpoint():
    sample_dir = Path("data/processed/PlantVillage/Tomato_healthy")
    if not sample_dir.exists():
        pytest.skip("Processed dataset not available")

    sample_img_path = next(sample_dir.glob("*.JPG"))
    with open(sample_img_path, "rb") as f:
        img_bytes = f.read()

    response = client.post(
        "/api/v1/predict/disease?top_k=3",
        files={"file": (sample_img_path.name, img_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["primary_prediction"]["class_name"] == "Tomato_healthy"
    assert data["primary_prediction"]["confidence"] > 0.8
    assert data["epistemic_type"] == "predicted"
    assert data["record_id"] is not None
