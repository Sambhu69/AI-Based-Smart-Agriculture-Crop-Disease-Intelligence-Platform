"""
NASA POWER Agroclimatology Data Ingestion
=========================================
Fetches bounded daily agroclimatology data from NASA POWER API:
- T2M: Temperature at 2 Meters (°C)
- PRECTOTCORR: Corrected Total Precipitation (mm/day)
- RH2M: Relative Humidity at 2 Meters (%)
- ALLSKY_SFC_SW_DWN: All Sky Surface Shortwave Downward Irradiance (MJ/m^2/day)
- WS2M: Wind Speed at 2 Meters (m/s)

Saves raw payload and normalized WeatherRecord entries with lineage metadata.
"""

from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from pipelines.common.schema import EpistemicType, WeatherRecord
from pipelines.lineage import LineageRecord

# Default reference coordinate: Chitwan Valley, Nepal (agricultural pilot point)
DEFAULT_NEPAL_LATITUDE = 27.5291
DEFAULT_NEPAL_LONGITUDE = 84.3542

NASA_POWER_API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


def parse_nasa_power_response(
    payload: Dict[str, Any],
    latitude: float,
    longitude: float,
    source_id: str = "NASA_POWER_API",
) -> List[WeatherRecord]:
    """Parses raw NASA POWER response JSON into validated WeatherRecord instances."""
    properties = payload.get("properties", {})
    parameter_data = properties.get("parameter", {})

    t2m_dict = parameter_data.get("T2M", {})
    precip_dict = parameter_data.get("PRECTOTCORR", {})
    rh2m_dict = parameter_data.get("RH2M", {})
    solar_dict = parameter_data.get("ALLSKY_SFC_SW_DWN", {})
    ws2m_dict = parameter_data.get("WS2M", {})

    dates = sorted(t2m_dict.keys())
    records: List[WeatherRecord] = []
    collected_now = datetime.now(timezone.utc)

    for d_str in dates:
        # Date format in NASA POWER response is YYYYMMDD
        rec_date = datetime.strptime(d_str, "%Y%m%d").date()

        t_val = float(t2m_dict.get(d_str, -999.0))
        p_val = float(precip_dict.get(d_str, -999.0))
        rh_val = float(rh2m_dict.get(d_str, -999.0))
        solar_val = float(solar_dict.get(d_str, -999.0))
        ws_val = float(ws2m_dict.get(d_str, -999.0))

        # Handle fill values (-999 or -99)
        if t_val < -100 or p_val < 0 or rh_val < 0 or solar_val < 0 or ws_val < 0:
            # Skip invalid or fill records
            continue

        rec = WeatherRecord(
            source_id=source_id,
            epistemic_type=EpistemicType.EXTERNAL,
            collected_at=collected_now,
            lineage_version="1.0.0",
            latitude=latitude,
            longitude=longitude,
            record_date=rec_date,
            temperature_c=round(t_val, 2),
            precipitation_mm=round(p_val, 2),
            relative_humidity_pct=round(min(rh_val, 100.0), 2),
            solar_radiation_mj=round(solar_val, 2),
            wind_speed_ms=round(ws_val, 2),
            metadata={"community": "AG", "original_date_key": d_str},
        )
        records.append(rec)

    return records


def fetch_nasa_power_agroclimatology(
    latitude: float = DEFAULT_NEPAL_LATITUDE,
    longitude: float = DEFAULT_NEPAL_LONGITUDE,
    start_date: str = "20260101",
    end_date: str = "20260115",
    output_dir: Path = Path("data/external/nasa_power"),
    mock_payload: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """
    Fetches daily agroclimatology data for a bounded geographical coordinate and date window.
    Supports injecting a mock_payload for offline unit testing without network dependencies.
    """
    lineage = LineageRecord(
        pipeline_name="NASAPowerIngestion",
        stage_name="DailyAgroclimatologyFetch",
        parameters={
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "mock": mock_payload is not None,
        },
    )

    if mock_payload is not None:
        raw_json = mock_payload
    else:
        params = {
            "parameters": "T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,WS2M",
            "community": "AG",
            "longitude": longitude,
            "latitude": latitude,
            "start": start_date,
            "end": end_date,
            "format": "JSON",
        }
        resp = requests.get(NASA_POWER_API_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        raw_json = resp.json()

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"nasa_power_raw_{latitude:.4f}_{longitude:.4f}_{start_date}_{end_date}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_json, f, indent=2)
    lineage.add_output(raw_path, "Raw NASA POWER API Response")

    # Normalize into standard schema
    records = parse_nasa_power_response(raw_json, latitude=latitude, longitude=longitude)
    norm_path = output_dir / f"nasa_power_normalized_{latitude:.4f}_{longitude:.4f}_{start_date}_{end_date}.json"
    with open(norm_path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump(mode="json") for r in records], f, indent=2)
    lineage.add_output(norm_path, "Normalized WeatherRecord Dataset")

    lineage_path = output_dir / f"lineage_{latitude:.4f}_{longitude:.4f}_{start_date}_{end_date}.json"
    lineage.finish(status="success", metadata={"total_records": len(records)})
    lineage.save(lineage_path)

    return {
        "status": "success",
        "record_count": len(records),
        "raw_path": str(raw_path),
        "normalized_path": str(norm_path),
        "lineage_path": str(lineage_path),
        "records": records,
    }
