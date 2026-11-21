import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.models import Farm, Plot, FieldObservation, PredictionRecord, TwinScenario, EpistemicType
from app.db.repositories import (
    FarmRepository,
    PlotRepository,
    FieldObservationRepository,
    PredictionRepository,
    TwinScenarioRepository,
)

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()

def test_farm_and_plot_creation(db_session):
    farm_repo = FarmRepository(db_session)
    plot_repo = PlotRepository(db_session)

    farm = farm_repo.create(name="Green Valley", location="California")
    assert farm.id is not None
    assert farm.name == "Green Valley"

    plot = plot_repo.create(farm_id=farm.id, name="Tomato Field A", crop_type="Tomato", area_hectares=2.5)
    assert plot.id is not None
    assert plot.farm_id == farm.id
    assert plot.crop_type == "Tomato"

    plots = plot_repo.list_by_farm(farm.id)
    assert len(plots) == 1
    assert plots[0].name == "Tomato Field A"

def test_epistemic_provenance_separation(db_session):
    farm_repo = FarmRepository(db_session)
    plot_repo = PlotRepository(db_session)
    obs_repo = FieldObservationRepository(db_session)
    pred_repo = PredictionRepository(db_session)
    twin_repo = TwinScenarioRepository(db_session)

    farm = farm_repo.create(name="EcoFarm")
    plot = plot_repo.create(farm_id=farm.id, name="Potato Plot 1", crop_type="Potato")

    # 1. Physical Field Observation (epistemic_type = 'observed' or 'external')
    obs = obs_repo.create(
        plot_id=plot.id,
        source="soil_probe_01",
        data={"soil_moisture": 32.1, "temp_c": 19.5},
        epistemic_type=EpistemicType.OBSERVED,
        notes="Calibrated reading",
    )
    assert obs.epistemic_type == "observed"

    # Verify invalid epistemic_type rejection in FieldObservation
    with pytest.raises(ValueError):
        obs_repo.create(
            plot_id=plot.id,
            source="faulty",
            data={},
            epistemic_type=EpistemicType.SIMULATED,  # Cannot be simulated!
        )

    # 2. Prediction Record (epistemic_type = 'predicted')
    pred = pred_repo.create(
        plot_id=plot.id,
        task="crop_disease_classification",
        model_name="resnet50",
        model_version="1.1.0",
        primary_prediction="Potato___healthy",
        confidence=0.985,
        top_k_predictions=[{"class_name": "Potato___healthy", "confidence": 0.985}],
        inference_time_ms=12.4,
    )
    assert pred.epistemic_type == "predicted"
    assert pred.primary_prediction == "Potato___healthy"
    assert pred.model_version == "1.1.0"

    # 3. Digital Twin Scenario (epistemic_type = 'simulated')
    twin = twin_repo.create(
        plot_id=plot.id,
        scenario_name="Drought Stress Sim 2026",
        simulation_engine="agri_sim_v1",
        parameters={"water_reduction_pct": 30},
        simulation_results={"projected_yield_loss_pct": 14.2},
    )
    assert twin.epistemic_type == "simulated"
    assert twin.parameters["water_reduction_pct"] == 30
