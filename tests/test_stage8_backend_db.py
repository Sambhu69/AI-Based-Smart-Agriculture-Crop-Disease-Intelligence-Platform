"""
Stage 8 Tests - Backend & Database Integration
Covers: farm/plot retrieval, farm-scoped observations with provenance separation,
/api/v1/history, 404/422/500 handling, and Alembic migration on a temporary SQLite DB.
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db

    @application.get("/_test/value-error")
    def _raise_value_error():
        raise ValueError("bad value supplied")

    @application.get("/_test/boom")
    def _raise_runtime():
        raise RuntimeError("secret internal detail /etc/passwd")

    with TestClient(application, raise_server_exceptions=False) as c:
        yield c


def _make_farm_and_plot(client, farm_name="F1", plot_name="P1", crop="Tomato"):
    farm = client.post("/api/v1/farms", json={"name": farm_name, "location": "Chitwan"}).json()
    plot = client.post(
        f"/api/v1/farms/{farm['id']}/plots",
        json={"name": plot_name, "crop_type": crop, "area_hectares": 1.5},
    ).json()
    return farm["id"], plot["id"]


# --- Farm / plot retrieval ---------------------------------------------------

def test_list_and_get_farm_with_plots(client):
    farm_id, plot_id = _make_farm_and_plot(client)

    listing = client.get("/api/v1/farms")
    assert listing.status_code == 200
    assert [f["id"] for f in listing.json()] == [farm_id]

    detail = client.get(f"/api/v1/farms/{farm_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == farm_id
    assert len(body["plots"]) == 1
    assert body["plots"][0]["id"] == plot_id
    assert body["plots"][0]["crop_type"] == "Tomato"


def test_get_farm_not_found(client):
    resp = client.get("/api/v1/farms/9999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Farm not found"


# --- Observations ------------------------------------------------------------

def test_observation_create_and_list_with_provenance(client):
    farm_id, plot_id = _make_farm_and_plot(client)
    url = f"/api/v1/farms/{farm_id}/plots/{plot_id}/observations"

    r1 = client.post(url, json={"source": "field_scout", "epistemic_type": "observed", "data": {"ph": 6.4}})
    r2 = client.post(url, json={"source": "nasa_power", "epistemic_type": "external", "data": {"rain_mm": 3.2}})
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["epistemic_type"] == "observed"
    assert r2.json()["epistemic_type"] == "external"

    listing = client.get(url)
    assert listing.status_code == 200
    types = sorted(o["epistemic_type"] for o in listing.json())
    assert types == ["external", "observed"]
    assert all(o["plot_id"] == plot_id for o in listing.json())


@pytest.mark.parametrize("bad_type", ["simulated", "predicted", "recommended", "nonsense"])
def test_observation_rejects_non_observed_types(client, bad_type):
    farm_id, plot_id = _make_farm_and_plot(client)
    resp = client.post(
        f"/api/v1/farms/{farm_id}/plots/{plot_id}/observations",
        json={"source": "x", "epistemic_type": bad_type, "data": {"a": 1}},
    )
    assert resp.status_code == 422
    # nothing persisted
    assert client.get(f"/api/v1/farms/{farm_id}/plots/{plot_id}/observations").json() == []


def test_observation_ownership_and_existence_404(client):
    farm_a, plot_a = _make_farm_and_plot(client, "A", "PA")
    farm_b, plot_b = _make_farm_and_plot(client, "B", "PB")
    payload = {"source": "s", "epistemic_type": "observed", "data": {"k": 1}}

    # plot belongs to a different farm
    assert client.post(f"/api/v1/farms/{farm_a}/plots/{plot_b}/observations", json=payload).status_code == 404
    assert client.get(f"/api/v1/farms/{farm_a}/plots/{plot_b}/observations").status_code == 404
    # missing farm / missing plot
    assert client.post(f"/api/v1/farms/9999/plots/{plot_a}/observations", json=payload).status_code == 404
    assert client.get(f"/api/v1/farms/{farm_a}/plots/9999/observations").status_code == 404


# --- History -----------------------------------------------------------------

def test_history_returns_predictions_and_twin_with_epistemic_types(client):
    farm_id, plot_id = _make_farm_and_plot(client)

    assert client.post("/api/v1/predict/yield", json={
        "crop_type": "Tomato", "area_hectares": 2.0, "plot_id": plot_id,
    }).status_code == 200
    assert client.post("/api/v1/twin/simulate", json={
        "crop_type": "Tomato", "baseline_yield_kg_ha": 20000.0,
        "scenario": "warming_2c", "plot_id": plot_id,
    }).status_code == 200

    resp = client.get("/api/v1/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    by_type = {i["record_type"]: i for i in body["items"]}
    assert by_type["prediction"]["epistemic_type"] == "predicted"
    assert by_type["prediction"]["module_name"] == "crop_yield_prediction"
    assert by_type["prediction"]["model_version"] == "1.0.0"
    assert by_type["twin_scenario"]["epistemic_type"] == "simulated"
    assert by_type["twin_scenario"]["module_name"] == "twin_service_v1"
    assert all(i["timestamp"] for i in body["items"])

    # timestamps are newest-first
    stamps = [i["timestamp"] for i in body["items"]]
    assert stamps == sorted(stamps, reverse=True)


def test_history_filter_by_module_and_limit(client):
    farm_id, plot_id = _make_farm_and_plot(client)
    for _ in range(3):
        client.post("/api/v1/predict/yield", json={"crop_type": "Potato", "area_hectares": 1.0, "plot_id": plot_id})
    client.post("/api/v1/twin/simulate", json={
        "crop_type": "Potato", "baseline_yield_kg_ha": 15000.0, "plot_id": plot_id,
    })

    only_pred = client.get("/api/v1/history", params={"module_name": "crop_yield_prediction"}).json()
    assert only_pred["count"] == 3
    assert {i["record_type"] for i in only_pred["items"]} == {"prediction"}

    only_twin = client.get("/api/v1/history", params={"module_name": "twin_service_v1"}).json()
    assert only_twin["count"] == 1
    assert only_twin["items"][0]["epistemic_type"] == "simulated"

    limited = client.get("/api/v1/history", params={"limit": 2}).json()
    assert limited["count"] == 2

    assert client.get("/api/v1/history", params={"module_name": "does_not_exist"}).json()["count"] == 0


def test_history_invalid_limit_422(client):
    assert client.get("/api/v1/history", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/history", params={"limit": 1000}).status_code == 422


# --- Exception handling ------------------------------------------------------

def test_value_error_returns_structured_422(client):
    resp = client.get("/_test/value-error")
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "validation_error"
    assert "bad value supplied" in body["detail"]


def test_unhandled_exception_returns_500_without_leaking(client):
    resp = client.get("/_test/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "internal_server_error"
    assert "secret internal detail" not in resp.text
    assert "Traceback" not in resp.text
    assert "RuntimeError" not in resp.text


# --- Alembic on a temporary SQLite DB ---------------------------------------

def _alembic(args, db_path):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )


def test_alembic_single_head_and_upgrade_on_temp_db(tmp_path):
    db_path = tmp_path / "migration_check.db"

    heads = _alembic(["heads"], db_path)
    assert heads.returncode == 0, heads.stderr
    assert heads.stdout.count("(head)") == 1

    up = _alembic(["upgrade", "head"], db_path)
    assert up.returncode == 0, up.stderr

    con = sqlite3.connect(db_path)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        version = con.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    finally:
        con.close()
    assert {"farms", "plots", "field_observations", "prediction_records", "twin_scenarios"} <= tables
    assert version in heads.stdout
