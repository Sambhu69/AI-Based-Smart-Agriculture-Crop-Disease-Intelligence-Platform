import datetime
import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Text,
)
from sqlalchemy.orm import relationship
from app.db.base import Base

class EpistemicType(str, enum.Enum):
    OBSERVED = "observed"
    EXTERNAL = "external"
    SIMULATED = "simulated"
    PREDICTED = "predicted"

class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    location = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    plots = relationship("Plot", back_populates="farm", cascade="all, delete-orphan")

class Plot(Base):
    __tablename__ = "plots"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    crop_type = Column(String(64), nullable=False)
    area_hectares = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    farm = relationship("Farm", back_populates="plots")
    field_observations = relationship("FieldObservation", back_populates="plot", cascade="all, delete-orphan")
    prediction_records = relationship("PredictionRecord", back_populates="plot", cascade="all, delete-orphan")
    twin_scenarios = relationship("TwinScenario", back_populates="plot", cascade="all, delete-orphan")

class FieldObservation(Base):
    """
    Real-world physical field observations (sensor readouts, scout reports).
    epistemic_type must strictly be 'observed' or 'external'.
    """
    __tablename__ = "field_observations"

    id = Column(Integer, primary_key=True, index=True)
    plot_id = Column(Integer, ForeignKey("plots.id"), nullable=False, index=True)
    epistemic_type = Column(String(32), nullable=False, default=EpistemicType.OBSERVED.value)
    source = Column(String(64), nullable=False)  # e.g., 'iot_sensor', 'field_scout', 'weather_station'
    observed_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    data = Column(JSON, nullable=False)  # e.g., {"temperature": 24.5, "soil_moisture": 0.42}
    notes = Column(Text, nullable=True)

    plot = relationship("Plot", back_populates="field_observations")

class PredictionRecord(Base):
    """
    ML/Analytics predictions (crop disease diagnoses, yield forecasts).
    Maintains provenance of model version, architecture, and top predictions.
    """
    __tablename__ = "prediction_records"

    id = Column(Integer, primary_key=True, index=True)
    plot_id = Column(Integer, ForeignKey("plots.id"), nullable=True, index=True)
    epistemic_type = Column(String(32), nullable=False, default=EpistemicType.PREDICTED.value)
    task = Column(String(64), nullable=False)  # e.g. 'crop_disease_classification'
    model_name = Column(String(64), nullable=False)
    model_version = Column(String(32), nullable=False)
    primary_prediction = Column(String(128), nullable=False)
    confidence = Column(Float, nullable=False)
    top_k_predictions = Column(JSON, nullable=True)
    inference_time_ms = Column(Float, nullable=True)
    image_filename = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    plot = relationship("Plot", back_populates="prediction_records")

class TwinScenario(Base):
    """
    Digital Twin simulations and hypothetical what-if runs.
    epistemic_type is strictly 'simulated' to ensure strict physical vs simulated separation.
    """
    __tablename__ = "twin_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    plot_id = Column(Integer, ForeignKey("plots.id"), nullable=False, index=True)
    epistemic_type = Column(String(32), nullable=False, default=EpistemicType.SIMULATED.value)
    scenario_name = Column(String(128), nullable=False)
    simulation_engine = Column(String(64), nullable=False)  # e.g. 'crop_growth_sim_v1'
    parameters = Column(JSON, nullable=False)  # e.g. {"irrigation_delta_pct": -20}
    simulation_results = Column(JSON, nullable=False)  # e.g. {"projected_yield_kg": 4200}
    simulated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    plot = relationship("Plot", back_populates="twin_scenarios")
