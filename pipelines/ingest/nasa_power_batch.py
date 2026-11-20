"""
NASA POWER Agroclimatology Batch Acquisition Utility
====================================================
Fetches daily agroclimatology data (2015–2024/2025) across primary agricultural
pilot zones in Nepal:
- Bharatpur / Chitwan (Terai agricultural bowl): Lat 27.68, Lon 84.43
- Pokhara Valley (Mid-hills agro-zone): Lat 28.21, Lon 83.98
- Kathmandu Valley (Horticulture/Vegetable basin): Lat 27.70, Lon 85.32

Saves raw responses, normalized WeatherRecord objects, and execution lineage.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from pipelines.common.schema import EpistemicType, WeatherRecord
from pipelines.lineage import LineageRecord
from pipelines.validate.quality import validate_weather_records

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("nasa_power")

NASA_POWER_API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

PILOT_REGIONS = {
    "chitwan_terai": {
        "name": "Chitwan (Terai Agricultural Basin)",
        "latitude": 27.68,
        "longitude": 84.43,
    },
    "pokhara_valley": {
        "name": "Pokhara (Mid-Hills Agro-Ecology)",
        "latitude": 28.21,
        "longitude": 83.98,
    },
    "kathmandu_valley": {
        "name": "Kathmandu (Peri-Urban Vegetable Basin)",
        "latitude": 27.70,
        "longitude": 85.32,
    },
}


def parse_nasa_power_payload(
    payload: Dict[str, Any],
    latitude: float,
    longitude: float,
    region_id: str,
) -> List[WeatherRecord]:
    """Parses raw NASA POWER JSON into validated WeatherRecord models."""
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
        try:
            rec_date = datetime.strptime(d_str, "%Y%m%d").date()
        except ValueError:
            continue

        t_val = float(t2m_dict.get(d_str, -999.0))
        p_val = float(precip_dict.get(d_str, -999.0))
        rh_val = float(rh2m_dict.get(d_str, -999.0))
        solar_val = float(solar_dict.get(d_str, -999.0))
        ws_val = float(ws2m_dict.get(d_str, -999.0))

        # Filter out NASA POWER fill values (-999, -99)
        if t_val < -100 or p_val < 0 or rh_val < 0 or solar_val < 0 or ws_val < 0:
            continue

        rec = WeatherRecord(
            source_id=f"NASA_POWER_{region_id.upper()}",
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
            metadata={"region_id": region_id, "original_date_key": d_str},
        )
        records.append(rec)

    return records


def fetch_multi_region_weather(
    regions: Optional[Dict[str, Dict[str, Any]]] = None,
    start_date: str = "20150101",
    end_date: str = "20241231",
    output_dir: Path = Path("data/external/nasa_power"),
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Fetches daily agroclimatology data across targeted agricultural pilot points.
    Saves raw JSON and standardized WeatherRecord datasets with lineage.
    """
    target_regions = regions or PILOT_REGIONS
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
        "regions": {},
        "total_records": 0,
    }

    lineage = LineageRecord(
        pipeline_name="NASAPowerMultiRegionIngest",
        stage_name="BatchAgroclimatologyAcquisition",
        parameters={"regions": list(target_regions.keys()), "start_date": start_date, "end_date": end_date},
    )

    for region_id, info in target_regions.items():
        lat = info["latitude"]
        lon = info["longitude"]
        logger.info(f"Fetching NASA POWER data for {info['name']} ({lat}, {lon})...")

        raw_path = output_dir / f"nasa_power_raw_{region_id}_{start_date}_{end_date}.json"
        norm_path = output_dir / f"nasa_power_normalized_{region_id}_{start_date}_{end_date}.json"

        # Idempotent fetch: check if raw response is already cached locally
        if raw_path.exists():
            logger.info(f"Loading cached response from {raw_path}")
            with open(raw_path, "r", encoding="utf-8") as f:
                raw_json = json.load(f)
        else:
            params = {
                "parameters": "T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,WS2M",
                "community": "AG",
                "longitude": lon,
                "latitude": lat,
                "start": start_date,
                "end": end_date,
                "format": "JSON",
            }
            resp = requests.get(NASA_POWER_API_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            raw_json = resp.json()
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_json, f)
            logger.info(f"Saved raw response to {raw_path}")

        records = parse_nasa_power_payload(raw_json, latitude=lat, longitude=lon, region_id=region_id)
        with open(norm_path, "w", encoding="utf-8") as f:
            json.dump([r.model_dump(mode="json") for r in records], f)

        # Validate quality
        val_report = validate_weather_records(records)

        summary["regions"][region_id] = {
            "name": info["name"],
            "records_count": len(records),
            "valid_records": val_report.valid_records,
            "errors": len(val_report.errors),
            "raw_path": str(raw_path),
            "normalized_path": str(norm_path),
        }
        summary["total_records"] += len(records)
        lineage.add_output(norm_path, f"Normalized WeatherRecords for {region_id}")

    lineage_path = output_dir / "nasa_power_batch_lineage.json"
    lineage.finish(status="success", metadata=summary)
    lineage.save(lineage_path)
    summary["lineage_path"] = str(lineage_path)

    return summary


if __name__ == "__main__":
    res = fetch_multi_region_weather()
    print(f"Batch fetch complete. Ingested {res['total_records']} weather records.")
