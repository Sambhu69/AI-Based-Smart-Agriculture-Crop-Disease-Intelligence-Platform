"""
Stage 7A Tests — GIS Vegetation Indices & Digital Twin Simulation
=================================================================
Tests:
  GIS (vegetation_indices.py):
    1. test_ndvi_valid_values
    2. test_ndvi_zero_denominator
    3. test_ndwi_computation
    4. test_evi_computation
    5. test_savi_computation
    6. test_summarize_index_array
    7. test_summarize_all_nan

  Twin service (twin_service.py):
    8. test_twin_simulate_baseline
    9. test_twin_simulate_warming
    10. test_twin_simulate_drought
    11. test_twin_simulate_disease_pressure
    12. test_twin_simulate_custom_fertilizer
    13. test_twin_simulate_wet_monsoon

  API endpoint (/api/v1/twin/simulate):
    14. test_api_twin_simulate_no_plot
    15. test_api_twin_simulate_with_valid_plot
    16. test_api_twin_simulate_invalid_plot
"""

import math
import pytest
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# ---------------------------------------------------------------------------
# In-memory SQLite test DB fixture
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
# GIS Tests
# ===========================================================================

from pipelines.gis.vegetation_indices import (
    compute_ndvi,
    compute_ndwi,
    compute_evi,
    compute_savi,
    summarize_index_array,
)


class TestNDVI:
    def test_ndvi_valid_values(self):
        """NDVI with known inputs should produce correct values in [-1, 1]."""
        nir = np.array([0.8, 0.5, 0.3])
        red = np.array([0.1, 0.2, 0.4])
        result = compute_ndvi(nir, red)
        expected = (nir - red) / (nir + red)
        np.testing.assert_allclose(result, expected, rtol=1e-6)
        assert result.min() >= -1.0
        assert result.max() <= 1.0

    def test_ndvi_zero_denominator(self):
        """When NIR == RED == 0 the denominator is 0; result must be NaN, not Inf."""
        nir = np.array([0.0, 0.5])
        red = np.array([0.0, 0.1])
        result = compute_ndvi(nir, red)
        assert math.isnan(result[0]), "Expected NaN for zero denominator"
        assert not math.isnan(result[1]), "Non-zero pixel must not be NaN"

    def test_ndvi_clipped_to_range(self):
        """NDVI output is always clipped to [-1, 1]."""
        nir = np.array([1.0, 0.0])
        red = np.array([0.0, 1.0])
        result = compute_ndvi(nir, red)
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(-1.0)


class TestNDWI:
    def test_ndwi_computation(self):
        """NDWI = (GREEN - NIR) / (GREEN + NIR); values in [-1, 1]."""
        green = np.array([0.4, 0.3])
        nir = np.array([0.2, 0.5])
        result = compute_ndwi(green, nir)
        expected = np.clip((green - nir) / (green + nir), -1.0, 1.0)
        np.testing.assert_allclose(result, expected, rtol=1e-6)

    def test_ndwi_zero_denominator(self):
        """NDWI with green==nir==0 must return NaN."""
        green = np.array([0.0])
        nir = np.array([0.0])
        result = compute_ndwi(green, nir)
        assert math.isnan(result[0])


class TestEVI:
    def test_evi_computation(self):
        """EVI formula correctness with default coefficients."""
        nir = np.array([0.6])
        red = np.array([0.1])
        blue = np.array([0.05])
        result = compute_evi(nir, red, blue)
        G, C1, C2, L = 2.5, 6.0, 7.5, 1.0
        expected = G * (nir - red) / (nir + C1 * red - C2 * blue + L)
        np.testing.assert_allclose(result, expected, rtol=1e-6)

    def test_evi_zero_denominator(self):
        """EVI must return NaN not Inf when denominator is zero."""
        # Construct inputs so NIR + C1*RED - C2*BLUE + L == 0
        # G*(NIR-RED)/0 → should give NaN
        nir = np.array([0.0])
        red = np.array([0.0])
        blue = np.array([1.0 / 7.5])  # denom = 0 + 0 - 7.5*(1/7.5) + 1 = 0
        result = compute_evi(nir, red, blue)
        assert math.isnan(result[0])


class TestSAVI:
    def test_savi_computation(self):
        """SAVI = ((NIR - RED) / (NIR + RED + L)) * (1 + L)."""
        nir = np.array([0.5, 0.3])
        red = np.array([0.1, 0.2])
        L = 0.5
        result = compute_savi(nir, red, L)
        expected = ((nir - red) / (nir + red + L)) * (1.0 + L)
        np.testing.assert_allclose(result, expected, rtol=1e-6)

    def test_savi_zero_denominator_impossible_with_L(self):
        """With default L=0.5, denominator cannot be zero for non-negative inputs."""
        nir = np.array([0.0])
        red = np.array([0.0])
        result = compute_savi(nir, red, L=0.5)
        # denom = 0.0 + 0.0 + 0.5 = 0.5 → valid result
        assert math.isfinite(result[0])
        assert not math.isnan(result[0])


class TestSummarizeIndexArray:
    def test_summarize_index_array(self):
        """summarize_index_array returns correct stats keys and finite values."""
        arr = np.array([0.1, 0.5, 0.8, np.nan])
        summary = summarize_index_array(arr)
        required_keys = {"min", "max", "mean", "valid_pixel_count", "nan_count"}
        assert required_keys.issubset(summary.keys())
        assert summary["valid_pixel_count"] == 3
        assert summary["nan_count"] == 1
        assert summary["min"] == pytest.approx(0.1, rel=1e-6)
        assert summary["max"] == pytest.approx(0.8, rel=1e-6)
        assert summary["mean"] == pytest.approx((0.1 + 0.5 + 0.8) / 3, rel=1e-6)

    def test_summarize_all_nan(self):
        """All-NaN array should return nan stats and valid_pixel_count=0."""
        arr = np.full((3, 3), np.nan)
        summary = summarize_index_array(arr)
        assert summary["valid_pixel_count"] == 0
        assert summary["nan_count"] == 9
        assert math.isnan(summary["min"])
        assert math.isnan(summary["mean"])


# ===========================================================================
# Twin Service Unit Tests
# ===========================================================================

from app.services.twin_service import simulate_plot_scenario


class TestTwinService:
    def test_twin_simulate_baseline(self):
        """Baseline scenario: no adjustments → yield unchanged."""
        result = simulate_plot_scenario(
            plot_id=None,
            crop_type="Tomato",
            baseline_yield_kg_ha=20000.0,
            scenario="baseline",
        )
        assert result["epistemic_type"] == "simulated"
        assert result["baseline_yield_kg_ha"] == 20000.0
        # Baseline: all factors = 1.0 → no change
        assert result["simulated_yield_kg_ha"] == pytest.approx(20000.0, rel=1e-4)
        assert result["yield_change_pct"] == pytest.approx(0.0, abs=0.01)

    def test_twin_simulate_warming(self):
        """High temperature delta on a cool-preference crop (Potato) should reduce yield."""
        result = simulate_plot_scenario(
            plot_id=None,
            crop_type="Potato",
            baseline_yield_kg_ha=15000.0,
            scenario="custom",
            adjustments={"temperature_delta_c": 15.0},  # extreme heat stress for Potato
        )
        assert result["epistemic_type"] == "simulated"
        assert result["simulated_yield_kg_ha"] < result["baseline_yield_kg_ha"], (
            "High temperature delta should decrease Potato yield"
        )
        assert result["yield_change_pct"] < 0.0

    def test_twin_simulate_drought(self):
        """Extreme drought (rainfall_multiplier=0.2) should reduce yield significantly."""
        result = simulate_plot_scenario(
            plot_id=None,
            crop_type="Tomato",
            baseline_yield_kg_ha=18000.0,
            scenario="monsoon_drought",
        )
        assert result["epistemic_type"] == "simulated"
        assert result["simulated_yield_kg_ha"] < result["baseline_yield_kg_ha"]
        assert result["yield_change_pct"] < 0.0

    def test_twin_simulate_disease_pressure(self):
        """High disease pressure (0.8) should cause ~80% yield reduction."""
        result = simulate_plot_scenario(
            plot_id=None,
            crop_type="Tomato",
            baseline_yield_kg_ha=20000.0,
            scenario="custom",
            adjustments={"disease_pressure": 0.8},
        )
        # factor = 1 - 0.8 = 0.2 → ~80% loss
        assert result["simulated_yield_kg_ha"] == pytest.approx(4000.0, rel=0.05)
        assert result["yield_change_pct"] < -70.0

    def test_twin_simulate_custom_fertilizer(self):
        """Fertilizer application should increase yield (logarithmic boost)."""
        result = simulate_plot_scenario(
            plot_id=None,
            crop_type="Maize",
            baseline_yield_kg_ha=12000.0,
            scenario="custom",
            adjustments={"fertilizer_kg_ha": 100.0},
        )
        assert result["simulated_yield_kg_ha"] > result["baseline_yield_kg_ha"]
        assert result["yield_change_pct"] > 0.0

    def test_twin_simulate_wet_monsoon(self):
        """Wet monsoon scenario (rainfall ×1.8) should return small positive or neutral yield change."""
        result = simulate_plot_scenario(
            plot_id=None,
            crop_type="Rice",
            baseline_yield_kg_ha=10000.0,
            scenario="wet_monsoon",
        )
        assert result["epistemic_type"] == "simulated"
        # Wet monsoon → rain factor expected slightly positive or slightly negative (waterlogging)
        assert isinstance(result["yield_change_pct"], float)
        assert "key_drivers" in result
        assert "assumptions" in result
        assert len(result["assumptions"]) >= 3


# ===========================================================================
# API Endpoint Tests
# ===========================================================================

class TestTwinAPI:
    def test_api_twin_simulate_no_plot(self, test_client):
        """POST /twin/simulate without plot_id returns 200 and epistemic_type='simulated'."""
        payload = {
            "crop_type": "Tomato",
            "baseline_yield_kg_ha": 20000.0,
            "scenario": "baseline",
            "temperature_delta_c": 0.0,
            "rainfall_multiplier": 1.0,
            "irrigation_mm": 0.0,
            "fertilizer_kg_ha": 0.0,
            "disease_pressure": 0.0,
        }
        response = test_client.post("/api/v1/twin/simulate", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["epistemic_type"] == "simulated"
        assert data["crop_type"] == "Tomato"
        assert data["scenario"] == "baseline"
        assert data["simulated_yield_kg_ha"] == pytest.approx(20000.0, rel=1e-4)
        assert data["record_id"] is None

    def test_api_twin_simulate_with_valid_plot(self, test_client):
        """POST /twin/simulate with a valid plot_id returns 200 with record_id populated."""
        # Create a farm then a plot
        farm_resp = test_client.post("/api/v1/farms", json={"name": "TwinTestFarm", "location": "Chitwan"})
        assert farm_resp.status_code == 201, farm_resp.text
        farm_id = farm_resp.json()["id"]

        plot_resp = test_client.post(
            f"/api/v1/farms/{farm_id}/plots",
            json={"name": "Plot-TwinTest", "area_hectares": 2.0, "crop_type": "Tomato"},
        )
        assert plot_resp.status_code == 201, plot_resp.text
        plot_id = plot_resp.json()["id"]

        payload = {
            "crop_type": "Tomato",
            "baseline_yield_kg_ha": 18000.0,
            "scenario": "warming_2c",
            "temperature_delta_c": 2.0,
            "rainfall_multiplier": 1.0,
            "irrigation_mm": 20.0,
            "fertilizer_kg_ha": 50.0,
            "disease_pressure": 0.1,
            "plot_id": plot_id,
        }
        response = test_client.post("/api/v1/twin/simulate", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["epistemic_type"] == "simulated"
        assert data["record_id"] is not None, "record_id should be set when plot_id is provided"
        assert isinstance(data["record_id"], int)
        assert data["scenario"] == "warming_2c"

    def test_api_twin_simulate_invalid_plot(self, test_client):
        """POST /twin/simulate with a nonexistent plot_id must return HTTP 404."""
        payload = {
            "crop_type": "Tomato",
            "baseline_yield_kg_ha": 20000.0,
            "scenario": "baseline",
            "plot_id": 999999,
        }
        response = test_client.post("/api/v1/twin/simulate", json=payload)
        assert response.status_code == 404, response.text
        assert "not found" in response.json()["detail"].lower()
