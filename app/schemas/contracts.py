from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class EpistemicTypeEnum(str):
    OBSERVED = "observed"
    EXTERNAL = "external"
    SIMULATED = "simulated"
    PREDICTED = "predicted"

# Farm Contracts
class FarmCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    location: Optional[str] = Field(None, max_length=256)

class FarmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: Optional[str]
    created_at: datetime
    updated_at: datetime

# Plot Contracts
class PlotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    crop_type: str = Field(..., min_length=1, max_length=64)
    area_hectares: Optional[float] = Field(None, ge=0.0)

class PlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    name: str
    crop_type: str
    area_hectares: Optional[float]
    created_at: datetime

# Field Observation Contracts
class FieldObservationCreate(BaseModel):
    source: str = Field(..., min_length=1, max_length=64)
    epistemic_type: str = Field("observed", pattern="^(observed|external)$")
    data: Dict[str, Any]
    notes: Optional[str] = None

class FieldObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plot_id: int
    epistemic_type: str
    source: str
    observed_at: datetime
    data: Dict[str, Any]
    notes: Optional[str]

# Twin Scenario Contracts
class TwinScenarioCreate(BaseModel):
    scenario_name: str = Field(..., min_length=1, max_length=128)
    simulation_engine: str = Field(..., min_length=1, max_length=64)
    parameters: Dict[str, Any]
    simulation_results: Dict[str, Any]

class TwinScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plot_id: int
    epistemic_type: str
    scenario_name: str
    simulation_engine: str
    parameters: Dict[str, Any]
    simulation_results: Dict[str, Any]
    simulated_at: datetime

# Crop Disease Inference Contracts
class DiseasePredictionItem(BaseModel):
    rank: int = Field(..., ge=1)
    class_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_pct: str

class DiseasePredictionResponse(BaseModel):
    filename: str
    primary_prediction: DiseasePredictionItem
    top_k_predictions: List[DiseasePredictionItem]
    model_version: str
    model_architecture: str
    epistemic_type: str = "predicted"
    inference_device: str
    inference_time_ms: float
    record_id: Optional[int] = None
