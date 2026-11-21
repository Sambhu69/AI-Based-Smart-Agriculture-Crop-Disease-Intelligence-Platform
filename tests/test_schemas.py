import pytest
from pydantic import ValidationError
from app.schemas.contracts import (
    FarmCreate,
    PlotCreate,
    FieldObservationCreate,
    TwinScenarioCreate,
)

def test_farm_schema_validation():
    valid = FarmCreate(name="Sunrise Acres", location="Iowa")
    assert valid.name == "Sunrise Acres"

    with pytest.raises(ValidationError):
        FarmCreate(name="")

def test_plot_schema_validation():
    valid = PlotCreate(name="North Field", crop_type="Pepper", area_hectares=10.5)
    assert valid.area_hectares == 10.5

    with pytest.raises(ValidationError):
        PlotCreate(name="Invalid Area", crop_type="Pepper", area_hectares=-5.0)

def test_field_observation_epistemic_validation():
    # Valid types
    obs1 = FieldObservationCreate(source="sensor", epistemic_type="observed", data={"ph": 6.5})
    assert obs1.epistemic_type == "observed"

    obs2 = FieldObservationCreate(source="weather_gov", epistemic_type="external", data={"rainfall_mm": 12.0})
    assert obs2.epistemic_type == "external"

    # Invalid epistemic type should fail validation
    with pytest.raises(ValidationError):
        FieldObservationCreate(source="simulation", epistemic_type="simulated", data={})

def test_twin_scenario_schema_validation():
    twin = TwinScenarioCreate(
        scenario_name="Excess Rainfall Scenario",
        simulation_engine="hydro_v2",
        parameters={"rainfall_increase_pct": 50},
        simulation_results={"flood_risk": "high"},
    )
    assert twin.scenario_name == "Excess Rainfall Scenario"
