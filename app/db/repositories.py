from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import Farm, Plot, FieldObservation, PredictionRecord, TwinScenario, EpistemicType

class FarmRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, location: Optional[str] = None) -> Farm:
        farm = Farm(name=name, location=location)
        self.db.add(farm)
        self.db.commit()
        self.db.refresh(farm)
        return farm

    def get_by_id(self, farm_id: int) -> Optional[Farm]:
        return self.db.query(Farm).filter(Farm.id == farm_id).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Farm]:
        return self.db.query(Farm).offset(skip).limit(limit).all()

class PlotRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, farm_id: int, name: str, crop_type: str, area_hectares: Optional[float] = None) -> Plot:
        plot = Plot(farm_id=farm_id, name=name, crop_type=crop_type, area_hectares=area_hectares)
        self.db.add(plot)
        self.db.commit()
        self.db.refresh(plot)
        return plot

    def get_by_id(self, plot_id: int) -> Optional[Plot]:
        return self.db.query(Plot).filter(Plot.id == plot_id).first()

    def list_by_farm(self, farm_id: int) -> List[Plot]:
        return self.db.query(Plot).filter(Plot.farm_id == farm_id).all()

class FieldObservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        plot_id: int,
        source: str,
        data: dict,
        epistemic_type: EpistemicType = EpistemicType.OBSERVED,
        notes: Optional[str] = None,
    ) -> FieldObservation:
        if epistemic_type not in (EpistemicType.OBSERVED, EpistemicType.EXTERNAL):
            raise ValueError(f"FieldObservation epistemic_type must be 'observed' or 'external', got '{epistemic_type}'")
        obs = FieldObservation(
            plot_id=plot_id,
            source=source,
            data=data,
            epistemic_type=epistemic_type.value if isinstance(epistemic_type, EpistemicType) else epistemic_type,
            notes=notes,
        )
        self.db.add(obs)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def list_by_plot(self, plot_id: int) -> List[FieldObservation]:
        return self.db.query(FieldObservation).filter(FieldObservation.plot_id == plot_id).all()

class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        task: str,
        model_name: str,
        model_version: str,
        primary_prediction: str,
        confidence: float,
        plot_id: Optional[int] = None,
        top_k_predictions: Optional[list] = None,
        inference_time_ms: Optional[float] = None,
        image_filename: Optional[str] = None,
    ) -> PredictionRecord:
        record = PredictionRecord(
            plot_id=plot_id,
            task=task,
            model_name=model_name,
            model_version=model_version,
            primary_prediction=primary_prediction,
            confidence=confidence,
            top_k_predictions=top_k_predictions,
            inference_time_ms=inference_time_ms,
            image_filename=image_filename,
            epistemic_type=EpistemicType.PREDICTED.value,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_all(self, limit: int = 100) -> List[PredictionRecord]:
        return self.db.query(PredictionRecord).order_by(PredictionRecord.created_at.desc()).limit(limit).all()

class TwinScenarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        plot_id: int,
        scenario_name: str,
        simulation_engine: str,
        parameters: dict,
        simulation_results: dict,
    ) -> TwinScenario:
        scenario = TwinScenario(
            plot_id=plot_id,
            scenario_name=scenario_name,
            simulation_engine=simulation_engine,
            parameters=parameters,
            simulation_results=simulation_results,
            epistemic_type=EpistemicType.SIMULATED.value,
        )
        self.db.add(scenario)
        self.db.commit()
        self.db.refresh(scenario)
        return scenario

    def list_by_plot(self, plot_id: int) -> List[TwinScenario]:
        return self.db.query(TwinScenario).filter(TwinScenario.plot_id == plot_id).all()


def list_recent_predictions(db: Session, limit: int = 50, module_name: Optional[str] = None) -> List[PredictionRecord]:
    """Most recent prediction records, optionally filtered by task (module name)."""
    query = db.query(PredictionRecord)
    if module_name:
        query = query.filter(PredictionRecord.task == module_name)
    return query.order_by(PredictionRecord.created_at.desc(), PredictionRecord.id.desc()).limit(limit).all()


def list_recent_twin_scenarios(db: Session, limit: int = 50, module_name: Optional[str] = None) -> List[TwinScenario]:
    """Most recent twin scenarios, optionally filtered by simulation engine (module name)."""
    query = db.query(TwinScenario)
    if module_name:
        query = query.filter(TwinScenario.simulation_engine == module_name)
    return query.order_by(TwinScenario.simulated_at.desc(), TwinScenario.id.desc()).limit(limit).all()
