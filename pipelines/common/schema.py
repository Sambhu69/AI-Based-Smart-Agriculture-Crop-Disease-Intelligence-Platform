"""
Pipelines Common Schemas & Contracts
====================================
Defines epistemic types and Pydantic validation contracts for standardized
weather, soil, and crop yield records with explicit provenance metadata.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EpistemicType(str, Enum):
    OBSERVED = "observed"
    EXTERNAL = "external"
    PREDICTED = "predicted"
    SIMULATED = "simulated"
    RECOMMENDED = "recommended"


EPISTEMIC_TYPES = tuple(t.value for t in EpistemicType)


class BaseProvenanceRecord(BaseModel):
    """Base schema enforcing explicit provenance and epistemic classification."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    source_id: str = Field(..., description="Unique source identifier (e.g. sensor ID, API endpoint)")
    epistemic_type: EpistemicType = Field(..., description="Epistemic categorization of data")
    collected_at: datetime = Field(..., description="Timestamp when record was acquired or generated")
    lineage_version: str = Field("1.0.0", description="Pipeline lineage / schema revision")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible provenance metadata")


class WeatherRecord(BaseProvenanceRecord):
    """Standardized agroclimatology / weather observation or forecast."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate")
    record_date: date = Field(..., description="Date of daily observation")
    temperature_c: float = Field(..., ge=-60.0, le=60.0, description="Mean 2m air temperature (°C)")
    precipitation_mm: float = Field(..., ge=0.0, le=500.0, description="Corrected precipitation (mm/day)")
    relative_humidity_pct: float = Field(..., ge=0.0, le=100.0, description="Relative humidity at 2m (%)")
    solar_radiation_mj: float = Field(..., ge=0.0, le=45.0, description="All-sky surface shortwave solar downward flux (MJ/m^2/day)")
    wind_speed_ms: float = Field(..., ge=0.0, le=100.0, description="Wind speed at 2m (m/s)")


class SoilRecord(BaseProvenanceRecord):
    """Standardized soil property observation or simulation."""
    plot_id: Optional[str] = Field(None, description="Plot identifier if bound to a field")
    depth_cm: float = Field(..., ge=0.0, le=200.0, description="Sampling or layer depth (cm)")
    ph: float = Field(..., ge=3.0, le=11.0, description="Soil pH level")
    moisture_pct: float = Field(..., ge=0.0, le=100.0, description="Soil volumetric moisture content (%)")
    nitrogen_mg_kg: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Available Nitrogen (mg/kg)")
    phosphorus_mg_kg: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Available Phosphorus (mg/kg)")
    potassium_mg_kg: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Available Potassium (mg/kg)")
    organic_matter_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Soil organic matter (%)")


class CropYieldRecord(BaseProvenanceRecord):
    """Standardized crop yield record (observed ground truth, predicted, or simulated)."""
    plot_id: str = Field(..., description="Plot identifier")
    crop_type: str = Field(..., min_length=1, description="Cultivated crop name")
    harvest_year: int = Field(..., ge=1900, le=2100, description="Harvest calendar year")
    yield_kg_per_ha: float = Field(..., ge=0.0, le=50000.0, description="Yield in kg per hectare")
    area_hectares: float = Field(..., gt=0.0, description="Cultivated land area (ha)")
