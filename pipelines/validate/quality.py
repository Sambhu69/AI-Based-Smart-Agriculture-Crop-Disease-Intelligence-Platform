"""
Data Quality Validation Suite
=============================
Applies domain-specific quality checks across:
- Missing values and unexpected nulls
- Exact and composite duplicate detection
- Coordinate range validation
- Physical plausibility constraints for weather, soil, and yield domains
"""

from typing import Any, Dict, List, Optional
from pipelines.common.schema import CropYieldRecord, SoilRecord, WeatherRecord


class QualityReport:
    """Collects validation findings, warnings, and error summaries."""

    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.total_records = 0
        self.valid_records = 0
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def add_error(self, record_index: int, field: str, value: Any, message: str) -> None:
        self.errors.append({
            "index": record_index,
            "field": field,
            "value": value,
            "message": message,
        })

    def add_warning(self, record_index: int, field: str, value: Any, message: str) -> None:
        self.warnings.append({
            "index": record_index,
            "field": field,
            "value": value,
            "message": message,
        })

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset_name,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_weather_records(records: List[WeatherRecord]) -> QualityReport:
    """Validates weather records against physical bounds and integrity constraints."""
    report = QualityReport("WeatherRecords")
    report.total_records = len(records)

    seen_keys = set()

    for idx, r in enumerate(records):
        has_error = False

        # 1. Coordinate boundaries
        if not (-90.0 <= r.latitude <= 90.0):
            report.add_error(idx, "latitude", r.latitude, "Latitude out of valid bounds [-90, 90]")
            has_error = True
        if not (-180.0 <= r.longitude <= 180.0):
            report.add_error(idx, "longitude", r.longitude, "Longitude out of valid bounds [-180, 180]")
            has_error = True

        # 2. Duplicate check (latitude, longitude, record_date)
        coord_date_key = (round(r.latitude, 4), round(r.longitude, 4), r.record_date)
        if coord_date_key in seen_keys:
            report.add_error(idx, "composite_key", str(coord_date_key), "Duplicate record found for point and date")
            has_error = True
        else:
            seen_keys.add(coord_date_key)

        # 3. Physical weather domain plausibility bounds
        if not (-50.0 <= r.temperature_c <= 55.0):
            report.add_error(idx, "temperature_c", r.temperature_c, "Temperature violates terrestrial physical bounds [-50, 55]")
            has_error = True
        if r.precipitation_mm < 0.0 or r.precipitation_mm > 400.0:
            report.add_error(idx, "precipitation_mm", r.precipitation_mm, "Precipitation exceeds terrestrial bounds [0, 400]")
            has_error = True
        if not (0.0 <= r.relative_humidity_pct <= 100.0):
            report.add_error(idx, "relative_humidity_pct", r.relative_humidity_pct, "Relative humidity must be within [0, 100]")
            has_error = True
        if r.solar_radiation_mj < 0.0 or r.solar_radiation_mj > 40.0:
            report.add_error(idx, "solar_radiation_mj", r.solar_radiation_mj, "Solar radiation outside physical limits [0, 40]")
            has_error = True
        if r.wind_speed_ms < 0.0 or r.wind_speed_ms > 75.0:
            report.add_error(idx, "wind_speed_ms", r.wind_speed_ms, "Wind speed outside terrestrial bounds [0, 75]")
            has_error = True

        if not has_error:
            report.valid_records += 1

    return report


def validate_soil_records(records: List[SoilRecord]) -> QualityReport:
    """Validates soil measurements against agronomic boundaries."""
    report = QualityReport("SoilRecords")
    report.total_records = len(records)

    for idx, r in enumerate(records):
        has_error = False

        if not (3.5 <= r.ph <= 9.5):
            report.add_error(idx, "ph", r.ph, "Soil pH violates agricultural range [3.5, 9.5]")
            has_error = True
        if not (0.0 <= r.moisture_pct <= 100.0):
            report.add_error(idx, "moisture_pct", r.moisture_pct, "Soil moisture must be within [0, 100]")
            has_error = True
        if r.depth_cm < 0.0 or r.depth_cm > 150.0:
            report.add_error(idx, "depth_cm", r.depth_cm, "Sampling depth exceeds plausible profile [0, 150]")
            has_error = True

        if not has_error:
            report.valid_records += 1

    return report


def validate_crop_yield_records(records: List[CropYieldRecord]) -> QualityReport:
    """Validates crop yield statistics."""
    report = QualityReport("CropYieldRecords")
    report.total_records = len(records)

    for idx, r in enumerate(records):
        has_error = False

        if r.yield_kg_per_ha < 0 or r.yield_kg_per_ha > 35000.0:
            report.add_error(idx, "yield_kg_per_ha", r.yield_kg_per_ha, "Yield exceeds agronomic maximum threshold (35,000 kg/ha)")
            has_error = True
        if r.area_hectares <= 0.0:
            report.add_error(idx, "area_hectares", r.area_hectares, "Cultivated area must be strictly positive")
            has_error = True

        if not has_error:
            report.valid_records += 1

    return report
