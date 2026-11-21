"""
Stage 11 Tests — MLOps, Containerization Hygiene & Drift Monitoring
===================================================================
Covers:
1. pipelines.monitoring.drift_monitor:
   - compute_feature_drift (normal, watch, drift_alert, empty batch)
   - compute_confidence_drift (normal, watch, drift_alert, empty list)
   - evaluate_monitoring_status combined escalation
2. API endpoint GET /api/v1/monitoring/status (empty DB vs low-confidence drift alert)
3. .dockerignore, Dockerfile, and docker-compose.yml presence & secret hygiene
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db
from app.db.repositories import PredictionRepository
from pipelines.monitoring.drift_monitor import (
    compute_feature_drift,
    compute_confidence_drift,
    evaluate_monitoring_status,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. Drift Monitor Unit Tests
# ---------------------------------------------------------------------------

def test_feature_drift_normal_watch_and_alert():
    ref = {"temperature_c": (22.0, 2.0), "soil_ph": (6.4, 0.3)}

    # Normal: close to reference means
    normal_res = compute_feature_drift(
        ref,
        {"temperature_c": [21.5, 22.2, 22.8], "soil_ph": [6.3, 6.4, 6.5]},
    )
    assert normal_res["status"] == "normal"
    assert normal_res["features"]["temperature_c"]["status"] == "normal"

    # Watch: ~1.8 std shift on temperature
    watch_res = compute_feature_drift(
        ref,
        {"temperature_c": [25.6, 25.6, 25.6], "soil_ph": [6.4, 6.4]},
    )
    assert watch_res["status"] == "watch"
    assert watch_res["features"]["temperature_c"]["status"] == "watch"

    # Alert: >= 2.5 std shift on temperature
    alert_res = compute_feature_drift(
        ref,
        {"temperature_c": [29.0, 30.0, 29.5], "soil_ph": [6.4, 6.4]},
    )
    assert alert_res["status"] == "drift_alert"
    assert alert_res["features"]["temperature_c"]["status"] == "drift_alert"


def test_confidence_drift_statuses():
    # Empty
    empty_res = compute_confidence_drift([])
    assert empty_res["status"] == "normal"
    assert empty_res["sample_count"] == 0
    assert empty_res["mean_confidence"] is None

    # Normal (>= 0.85 baseline)
    norm_res = compute_confidence_drift([0.92, 0.89, 0.95], ref_mean_conf=0.85)
    assert norm_res["status"] == "normal"
    assert norm_res["sample_count"] == 3

    # Watch (drop >= 0.08, < 0.15 -> e.g. 0.75)
    watch_res = compute_confidence_drift([0.74, 0.76, 0.75], ref_mean_conf=0.85)
    assert watch_res["status"] == "watch"

    # Alert (drop >= 0.15 -> e.g. 0.60)
    alert_res = compute_confidence_drift([0.58, 0.62, 0.60], ref_mean_conf=0.85)
    assert alert_res["status"] == "drift_alert"


def test_evaluate_monitoring_status_combined():
    res = evaluate_monitoring_status(
        reference_stats={"soil_ph": (6.4, 0.2)},
        current_batch={"soil_ph": [6.4, 6.5, 6.3]},
        confidences=[0.55, 0.60],
        ref_mean_conf=0.85,
    )
    # Confidence dropped sharply -> escalates overall status to drift_alert
    assert res["status"] == "drift_alert"
    assert res["feature_drift"]["status"] == "normal"
    assert res["confidence_drift"]["status"] == "drift_alert"


# ---------------------------------------------------------------------------
# 2. API Endpoint Tests: GET /api/v1/monitoring/status
# ---------------------------------------------------------------------------

@pytest.fixture()
def monitor_client():
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

    with TestClient(application) as client:
        yield client, TestingSession


def test_api_monitoring_status_empty_and_alert(monitor_client):
    client, SessionLocal = monitor_client

    # Empty DB -> normal with sample_count=0
    resp_empty = client.get("/api/v1/monitoring/status")
    assert resp_empty.status_code == 200
    data_empty = resp_empty.json()
    assert data_empty["status"] == "normal"
    assert data_empty["sample_count"] == 0
    assert data_empty["mean_confidence"] is None

    # Insert low-confidence predictions -> drift_alert
    db = SessionLocal()
    try:
        repo = PredictionRepository(db)
        for conf in (0.52, 0.58, 0.55):
            repo.create(
                task="crop_disease_classification",
                model_name="resnet50",
                model_version="1.1.0",
                primary_prediction="Tomato_Early_blight",
                confidence=conf,
            )
    finally:
        db.close()

    resp_alert = client.get("/api/v1/monitoring/status")
    assert resp_alert.status_code == 200
    data_alert = resp_alert.json()
    assert data_alert["status"] == "drift_alert"
    assert data_alert["sample_count"] == 3
    assert data_alert["mean_confidence"] == pytest.approx(0.55, abs=0.01)


# ---------------------------------------------------------------------------
# 3. Docker & MLOps Configuration Hygiene Tests
# ---------------------------------------------------------------------------

def test_docker_files_present_and_hygienic():
    dockerignore = PROJECT_ROOT / ".dockerignore"
    dockerfile = PROJECT_ROOT / "Dockerfile"
    compose = PROJECT_ROOT / "docker-compose.yml"

    assert dockerignore.exists(), ".dockerignore must exist"
    assert dockerfile.exists(), "Dockerfile must exist"
    assert compose.exists(), "docker-compose.yml must exist"

    di_text = dockerignore.read_text(encoding="utf-8")
    for pattern in (".env", "venv/", "data/", "models/*.pth", "frontend/node_modules/"):
        assert pattern in di_text, f".dockerignore missing {pattern}"

    df_text = dockerfile.read_text(encoding="utf-8")
    assert "uvicorn" in df_text and "app.main:app" in df_text
    assert "DATABASE_URL" in df_text
    assert "8000" in df_text

    dc_text = compose.read_text(encoding="utf-8")
    assert "DATABASE_URL" in dc_text
    assert "AIza" not in dc_text and "ghp_" not in dc_text
