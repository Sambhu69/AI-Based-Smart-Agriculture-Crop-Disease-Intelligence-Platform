from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class EpistemicTypeEnum(str):
    OBSERVED = "observed"
    EXTERNAL = "external"
    SIMULATED = "simulated"
    PREDICTED = "predicted"
    RECOMMENDED = "recommended"

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

# Agronomy & Advisory Contracts (Step 6B)
class CropSuitabilityItem(BaseModel):
    crop_type: str
    suitability: str
    suitability_score: float
    reasons: List[str]
    crop_notes: str

class IrrigationRecommendationItem(BaseModel):
    urgency: str
    action: str
    estimated_water_liters_per_m2: float

class FertilizerRecommendationItem(BaseModel):
    soil_ph_status: str
    guidance_notes: List[str]

class CropIrrigationAdvisoryRequest(BaseModel):
    crop_type: str = Field("Tomato", description="Target cultivated crop")
    soil_ph: float = Field(..., ge=3.0, le=10.0, description="Measured soil pH")
    temperature_c: float = Field(..., ge=-10.0, le=55.0, description="Ambient or forecast temperature (°C)")
    soil_moisture_pct: float = Field(..., ge=0.0, le=100.0, description="Soil moisture level (%)")
    precipitation_mm: float = Field(0.0, ge=0.0, description="Recent or forecast precipitation (mm)")
    plot_id: Optional[int] = Field(None, description="Optional Plot ID for provenance tracking")

class CropIrrigationAdvisoryResponse(BaseModel):
    epistemic_type: str = "recommended"
    crop_type: str
    crop_suitability_ranking: List[CropSuitabilityItem]
    irrigation_recommendation: IrrigationRecommendationItem
    fertilizer_recommendation: FertilizerRecommendationItem
    assumptions: List[str]
    limitations: str
    record_id: Optional[int] = None

# Tabular Yield Prediction Contracts (Step 6B)
class YieldPredictionRequest(BaseModel):
    crop_type: str = Field(..., description="Crop type (e.g., Tomato, Potato, Pepper)")
    harvest_year: int = Field(2025, ge=1900, le=2100, description="Target harvest calendar year")
    area_hectares: float = Field(..., gt=0.0, description="Cultivated land area (ha)")
    ph: Optional[float] = Field(6.2, ge=3.0, le=10.0, description="Soil pH")
    moisture_pct: Optional[float] = Field(28.0, ge=0.0, le=100.0, description="Soil moisture (%)")
    nitrogen_mg_kg: Optional[float] = Field(40.0, ge=0.0, description="Available Nitrogen (mg/kg)")
    organic_matter_pct: Optional[float] = Field(2.5, ge=0.0, le=100.0, description="Soil organic matter (%)")
    plot_id: Optional[int] = Field(None, description="Optional Plot ID for tracking")

class YieldPredictionResponse(BaseModel):
    crop_type: str
    predicted_yield_kg_per_ha: float
    total_projected_yield_kg: float
    area_hectares: float
    harvest_year: int
    model_name: str
    epistemic_type: str = "predicted"
    record_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Digital Twin Simulation Contracts (Step 7A)
# ---------------------------------------------------------------------------

class TwinSimulationRequest(BaseModel):
    crop_type: str = Field("Tomato", description="Crop species to simulate")
    baseline_yield_kg_ha: float = Field(..., gt=0, description="Reference yield before scenario (kg/ha)")
    scenario: str = Field(
        "baseline",
        description="Named scenario: 'baseline', 'warming_2c', 'monsoon_drought', 'wet_monsoon', or 'custom'",
    )
    temperature_delta_c: float = Field(0.0, description="Temperature change added to crop optimum evaluation (°C)")
    rainfall_multiplier: float = Field(1.0, ge=0.0, description="Multiplier applied to effective rainfall (1.0 = no change)")
    irrigation_mm: float = Field(0.0, ge=0.0, description="Supplemental irrigation (mm)")
    fertilizer_kg_ha: float = Field(0.0, ge=0.0, description="Additional fertilizer applied (kg/ha)")
    disease_pressure: float = Field(0.0, ge=0.0, le=1.0, description="Disease pressure (0.0 = none, 1.0 = total loss)")
    plot_id: Optional[int] = Field(None, description="Optional Plot ID; triggers persistence and 404 on invalid ID")


class TwinSimulationResponse(BaseModel):
    epistemic_type: str = "simulated"
    crop_type: str
    scenario: str
    baseline_yield_kg_ha: float
    simulated_yield_kg_ha: float
    yield_change_pct: float
    combined_yield_factor: Optional[float] = None
    factor_breakdown: Optional[Dict[str, Any]] = None
    key_drivers: List[str]
    assumptions: List[str]
    limitations: str
    record_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Advanced Intelligence Contracts (Step 7B)
# ---------------------------------------------------------------------------

class IntelligenceAssessmentRequest(BaseModel):
    crop_type: str = Field("Tomato", description="Target cultivated crop")
    temperature_c: float = Field(22.0, ge=-10.0, le=55.0, description="Ambient or canopy temperature (°C)")
    relative_humidity_pct: float = Field(85.0, ge=0.0, le=100.0, description="Relative humidity (%)")
    rainfall_mm: float = Field(5.0, ge=0.0, description="Recent or forecast precipitation (mm)")
    visual_anomaly_score: float = Field(0.0, ge=0.0, le=1.0, description="Visual anomaly or scouting score (0.0-1.0)")
    query: Optional[str] = Field(None, description="Optional natural language query for assistant guidance")
    plot_id: Optional[int] = Field(None, description="Optional Plot ID for tracking")


class IntelligenceAssessmentResponse(BaseModel):
    epistemic_type: str = "predicted"
    crop_type: str
    risk_assessment: Dict[str, Any]
    assistant_response: Optional[Dict[str, Any]] = None
    limitations: str
    record_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Stage 8: Backend & Database Integration Contracts
# ---------------------------------------------------------------------------

class FarmDetailResponse(FarmResponse):
    """Farm details including its plots."""
    plots: List[PlotResponse] = []


class HistoryItem(BaseModel):
    record_type: str  # "prediction" | "twin_scenario"
    id: int
    plot_id: Optional[int] = None
    epistemic_type: str
    module_name: str  # prediction task or simulation engine
    model_version: Optional[str] = None
    timestamp: datetime
    summary: str


class HistoryResponse(BaseModel):
    count: int
    limit: int
    module_name: Optional[str] = None
    items: List[HistoryItem]


# ---------------------------------------------------------------------------
# Stage 11: MLOps & Drift Monitoring Contracts
# ---------------------------------------------------------------------------

class MonitoringStatusResponse(BaseModel):
    status: str  # "normal" | "watch" | "drift_alert"
    epistemic_type: str = "observed"
    sample_count: int
    mean_confidence: Optional[float] = None
    min_confidence: Optional[float] = None
    reference_baseline_confidence: float
    drop_from_baseline: float
    note: str
    limitations: str
