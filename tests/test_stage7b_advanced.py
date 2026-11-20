"""
Stage 7B Tests — Advanced Intelligence Prototypes & Assistant Routing
=====================================================================
Tests:
  1. test_assess_outbreak_conducive_conditions (High/Critical risk for Tomato under high humidity & optimal temp)
  2. test_assess_outbreak_dry_conditions (Low risk under low humidity)
  3. test_assess_outbreak_multimodal_visual_anomaly (Visual anomaly elevates score)
  4. test_irrigation_rl_simulation_structure (14-day water balance simulation with savings)
  5. test_agricultural_graph_summary (NetworkX graph nodes, edges, centrality, insights)
  6. test_assistant_query_disease_routing (Query with 'blight' routes to disease assessment)
  7. test_assistant_query_irrigation_rl_routing (Query with 'irrigation rl' routes to RL simulation)
  8. test_assistant_query_crop_suitability (Query with 'crop recommendation' routes to agronomy service)
  9. test_assistant_query_graph_topology (Query with 'network topology' routes to graph summary)
  10. test_assistant_query_fallback (General query returns overview guidance)
  11. test_api_intelligence_assess_no_plot (POST without plot_id returns 200)
  12. test_api_intelligence_assess_with_valid_plot (POST with valid plot_id persists record)
  13. test_api_intelligence_assess_invalid_plot (POST with nonexistent plot_id returns 404)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db

from app.services.advanced_intelligence_service import (
    assess_outbreak_and_multimodal_risk,
    run_irrigation_rl_simulation,
    build_agricultural_graph_summary,
    answer_farming_assistant_query,
)


# ---------------------------------------------------------------------------
# Test SQLite In-Memory Database Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_client():
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

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ===========================================================================
# Unit Tests: Advanced Intelligence Service
# ===========================================================================

class TestAdvancedIntelligenceService:
    def test_assess_outbreak_conducive_conditions(self):
        """High humidity (90%), optimal fungal temp (20°C), and rain yields high/critical risk."""
        res = assess_outbreak_and_multimodal_risk(
            crop_type="Tomato",
            temperature_c=20.0,
            relative_humidity_pct=90.0,
            rainfall_mm=10.0,
        )
        assert res["epistemic_type"] == "predicted"
        assert res["risk_level"] in ["High", "Critical"]
        assert res["risk_score"] >= 0.50
        assert "Late Blight (Phytophthora infestans)" in res["primary_threats"]
        assert len(res["contributing_factors"]) >= 2
        assert len(res["preventative_actions"]) >= 1

    def test_assess_outbreak_dry_conditions(self):
        """Low humidity (35%) and warm temp yields low risk."""
        res = assess_outbreak_and_multimodal_risk(
            crop_type="Potato",
            temperature_c=25.0,
            relative_humidity_pct=35.0,
            rainfall_mm=0.0,
        )
        assert res["epistemic_type"] == "predicted"
        assert res["risk_level"] == "Low"
        assert res["risk_score"] < 0.35

    def test_assess_outbreak_multimodal_visual_anomaly(self):
        """Visual anomaly scouting score increases overall risk score."""
        baseline = assess_outbreak_and_multimodal_risk(
            crop_type="Pepper",
            temperature_c=22.0,
            relative_humidity_pct=72.0,
            visual_anomaly_score=0.0,
        )
        with_anomaly = assess_outbreak_and_multimodal_risk(
            crop_type="Pepper",
            temperature_c=22.0,
            relative_humidity_pct=72.0,
            visual_anomaly_score=0.85,
        )
        assert with_anomaly["risk_score"] > baseline["risk_score"]
        assert any("visual scouting anomaly" in f.lower() for f in with_anomaly["contributing_factors"])

    def test_irrigation_rl_simulation_structure(self):
        """RL irrigation simulation runs 14 days and returns comparative metrics."""
        res = run_irrigation_rl_simulation(
            crop_type="Tomato",
            initial_soil_moisture_pct=45.0,
            num_days=14,
            daily_evapotranspiration_mm=4.0,
            random_seed=42,
        )
        assert res["epistemic_type"] == "simulated"
        assert res["simulation_days"] == 14
        assert "baseline_rule_results" in res
        assert "rl_policy_results" in res
        assert "water_savings_pct" in res["rl_policy_results"]
        assert len(res["simulation_insights"]) >= 2
        assert "limitations" in res

    def test_agricultural_graph_summary(self):
        """Constructs and summarizes agricultural knowledge graph using NetworkX."""
        res = build_agricultural_graph_summary()
        assert res["epistemic_type"] == "simulated"
        assert res["node_count"] > 10
        assert res["edge_count"] > 10
        assert res["connected_components"] >= 1
        assert "farm" in res["node_type_counts"]
        assert "crop" in res["node_type_counts"]
        assert "pathogen" in res["node_type_counts"]
        assert len(res["top_central_nodes"]) > 0
        assert len(res["structural_insights"]) >= 2

    def test_assistant_query_disease_routing(self):
        """Query containing 'blight' routes to disease outbreak assessment."""
        res = answer_farming_assistant_query(
            query="Is there any risk of late blight outbreak in my tomato field?",
            context={"crop_type": "Tomato", "relative_humidity_pct": 88.0, "temperature_c": 19.0},
        )
        assert res["intent_detected"] == "disease_risk_assessment"
        assert "assess_outbreak_and_multimodal_risk" in res["tools_invoked"]
        assert res["epistemic_type"] == "predicted"
        assert "Tomato" in res["guidance"]

    def test_assistant_query_irrigation_rl_routing(self):
        """Query mentioning 'irrigation rl simulation' routes to RL simulation."""
        res = answer_farming_assistant_query(
            query="Run an irrigation RL simulation for water savings",
            context={"crop_type": "Tomato", "soil_moisture_pct": 46.0},
        )
        assert res["intent_detected"] == "irrigation_rl_simulation"
        assert "run_irrigation_rl_simulation" in res["tools_invoked"]
        assert res["epistemic_type"] == "simulated"

    def test_assistant_query_crop_suitability(self):
        """Query mentioning 'crop suitability' routes to agronomy service."""
        res = answer_farming_assistant_query(
            query="Which crop is recommended for pH 6.4 and temperature 22C?",
            context={"soil_ph": 6.4, "temperature_c": 22.0},
        )
        assert res["intent_detected"] == "crop_suitability_recommendation"
        assert "recommend_crops" in res["tools_invoked"]
        assert res["epistemic_type"] == "recommended"

    def test_assistant_query_graph_topology(self):
        """Query mentioning 'network topology' routes to graph summary."""
        res = answer_farming_assistant_query(
            query="Show me the agricultural graph network topology and disease bridges",
        )
        assert res["intent_detected"] == "agricultural_graph_topology"
        assert "build_agricultural_graph_summary" in res["tools_invoked"]
        assert res["epistemic_type"] == "simulated"

    def test_assistant_query_fallback(self):
        """General inquiry returns structured capability overview."""
        res = answer_farming_assistant_query(query="Hello assistant, what can you do?")
        assert res["intent_detected"] == "general_inquiry"
        assert "Smart Agriculture Platform Assistant" in res["guidance"]


# ===========================================================================
# API Tests: POST /api/v1/intelligence/assess
# ===========================================================================

class TestIntelligenceAPI:
    def test_api_intelligence_assess_no_plot(self, test_client):
        """POST /api/v1/intelligence/assess without plot_id returns 200 with risk assessment."""
        payload = {
            "crop_type": "Tomato",
            "temperature_c": 21.0,
            "relative_humidity_pct": 88.0,
            "rainfall_mm": 6.0,
            "query": "Check disease risk for tomato foliage",
        }
        response = test_client.post("/api/v1/intelligence/assess", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["epistemic_type"] == "predicted"
        assert data["crop_type"] == "Tomato"
        assert "risk_assessment" in data
        assert data["risk_assessment"]["risk_score"] > 0.0
        assert data["assistant_response"] is not None
        assert data["assistant_response"]["intent_detected"] == "disease_risk_assessment"
        assert data["record_id"] is None

    def test_api_intelligence_assess_with_valid_plot(self, test_client):
        """POST /api/v1/intelligence/assess with valid plot_id creates a prediction record."""
        # Create Farm and Plot
        farm_resp = test_client.post("/api/v1/farms", json={"name": "IntelTestFarm", "location": "Pokhara"})
        assert farm_resp.status_code == 201
        farm_id = farm_resp.json()["id"]

        plot_resp = test_client.post(
            f"/api/v1/farms/{farm_id}/plots",
            json={"name": "IntelPlot-1", "crop_type": "Potato", "area_hectares": 1.5},
        )
        assert plot_resp.status_code == 201
        plot_id = plot_resp.json()["id"]

        payload = {
            "crop_type": "Potato",
            "temperature_c": 18.0,
            "relative_humidity_pct": 92.0,
            "rainfall_mm": 12.0,
            "visual_anomaly_score": 0.4,
            "plot_id": plot_id,
        }
        response = test_client.post("/api/v1/intelligence/assess", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["record_id"] is not None
        assert isinstance(data["record_id"], int)
        assert data["risk_assessment"]["risk_level"] in ["High", "Critical"]

    def test_api_intelligence_assess_invalid_plot(self, test_client):
        """POST /api/v1/intelligence/assess with nonexistent plot_id returns 404."""
        payload = {
            "crop_type": "Tomato",
            "temperature_c": 22.0,
            "relative_humidity_pct": 70.0,
            "plot_id": 999999,
        }
        response = test_client.post("/api/v1/intelligence/assess", json=payload)
        assert response.status_code == 404, response.text
        assert "not found" in response.json()["detail"].lower()
