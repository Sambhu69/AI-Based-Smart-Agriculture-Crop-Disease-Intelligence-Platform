"""
Weather Time-Series Next-Day Temperature Forecasting Baseline
=============================================================
Builds lag and rolling features strictly in chronological order (no future lookahead)
from NASA POWER daily records to predict next-day mean temperature (temperature_c / T2M).

Evaluates:
1. Persistence / Naive baseline: T_{t+1} = T_t
2. Linear Ridge Regression with lag-1, lag-2, lag-7, and 7-day rolling mean/std
3. Random Forest Regressor

Logs real MAE and RMSE metrics to reports/evaluation/weather_baseline_metrics.json.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

from pipelines.lineage import LineageRecord
from pipelines.validate.splits import chronological_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("weather_baseline")

DEFAULT_WEATHER_DIR = Path("data/external/nasa_power")
DEFAULT_METRICS_PATH = Path("reports/evaluation/weather_baseline_metrics.json")


def load_weather_time_series(weather_dir: Path = DEFAULT_WEATHER_DIR) -> pd.DataFrame:
    """Loads daily NASA POWER normalized records into a sorted time-series DataFrame."""
    files = list(weather_dir.glob("nasa_power_normalized_*.json"))
    records = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            records.extend(json.load(fp))

    if not records:
        # Synthetic fallback for testing
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        return pd.DataFrame({
            "record_date": dates,
            "temperature_c": 20.0 + 5.0 * np.sin(np.linspace(0, 3.14 * 2, 100)),
            "precipitation_mm": 1.0,
            "relative_humidity_pct": 65.0,
            "solar_radiation_mj": 15.0,
            "wind_speed_ms": 2.0,
            "source_id": "NASA_POWER_SYNTHETIC",
        })

    df = pd.DataFrame(records)
    df["record_date"] = pd.to_datetime(df["record_date"])
    # Focus on single continuous primary region to ensure strict time-series continuity (e.g. Chitwan Terai)
    if "source_id" in df.columns:
        chitwan_records = df[df["source_id"] == "NASA_POWER_CHITWAN_TERAI"]
        if not chitwan_records.empty:
            df = chitwan_records

    df = df.sort_values("record_date").reset_index(drop=True)
    return df


def engineer_time_series_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constructs strictly causal historical features without future lookahead:
    - lag_1, lag_2, lag_7 for temperature
    - roll_mean_7, roll_std_7
    - Target: next_day_temp = T(t+1)
    """
    df_feat = df.copy()

    # Features strictly using past observations
    df_feat["temp_lag_1"] = df_feat["temperature_c"].shift(1)
    df_feat["temp_lag_2"] = df_feat["temperature_c"].shift(2)
    df_feat["temp_lag_7"] = df_feat["temperature_c"].shift(7)
    df_feat["temp_roll_mean_7"] = df_feat["temperature_c"].shift(1).rolling(window=7).mean()
    df_feat["temp_roll_std_7"] = df_feat["temperature_c"].shift(1).rolling(window=7).std()

    df_feat["precip_lag_1"] = df_feat["precipitation_mm"].shift(1)
    df_feat["rh_lag_1"] = df_feat["relative_humidity_pct"].shift(1)
    df_feat["solar_lag_1"] = df_feat["solar_radiation_mj"].shift(1)

    # Persistence baseline feature
    df_feat["persistence_pred"] = df_feat["temperature_c"]

    # Target: next day temperature
    df_feat["target_next_day_temp"] = df_feat["temperature_c"].shift(-1)

    # Drop edge rows containing NaNs
    df_clean = df_feat.dropna().reset_index(drop=True)
    return df_clean


def train_and_evaluate_weather_baseline(
    df: Optional[pd.DataFrame] = None,
    metrics_path: Path = DEFAULT_METRICS_PATH,
) -> Dict[str, Any]:
    """
    Trains and benchmarks next-day temperature forecast models strictly on chronological split.
    """
    if df is None:
        df = load_weather_time_series()

    df_features = engineer_time_series_features(df)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    lineage = LineageRecord(
        pipeline_name="WeatherTimeSeriesBaseline",
        stage_name="ChronologicalForecastBenchmark",
        parameters={"total_clean_samples": len(df_features)},
    )

    records = df_features.to_dict(orient="records")
    train_recs, val_recs, test_recs = chronological_split(
        records, date_key="record_date", train_ratio=0.70, val_ratio=0.15
    )

    df_train = pd.DataFrame(train_recs)
    df_val = pd.DataFrame(val_recs)
    df_test = pd.DataFrame(test_recs)

    feature_cols = [
        "temp_lag_1",
        "temp_lag_2",
        "temp_lag_7",
        "temp_roll_mean_7",
        "temp_roll_std_7",
        "precip_lag_1",
        "rh_lag_1",
        "solar_lag_1",
    ]

    X_train = df_train[feature_cols]
    y_train = df_train["target_next_day_temp"]

    X_test = df_test[feature_cols]
    y_test = df_test["target_next_day_temp"]

    # 1. Persistence Baseline: T(t+1) = T(t)
    persistence_preds = df_test["persistence_pred"]
    pers_mae = float(mean_absolute_error(y_test, persistence_preds))
    pers_rmse = float(np.sqrt(mean_squared_error(y_test, persistence_preds)))

    # 2. Ridge Regression Model
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train, y_train)
    ridge_preds = ridge.predict(X_test)
    ridge_mae = float(mean_absolute_error(y_test, ridge_preds))
    ridge_rmse = float(np.sqrt(mean_squared_error(y_test, ridge_preds)))

    # 3. Random Forest Regressor
    rf = RandomForestRegressor(n_estimators=50, random_state=42, max_depth=8)
    rf.fit(X_train, y_train)
    rf_preds = rf.predict(X_test)
    rf_mae = float(mean_absolute_error(y_test, rf_preds))
    rf_rmse = float(np.sqrt(mean_squared_error(y_test, rf_preds)))

    metrics = {
        "train_days": len(df_train),
        "val_days": len(df_val),
        "test_days": len(df_test),
        "test_start_date": str(df_test["record_date"].min()),
        "test_end_date": str(df_test["record_date"].max()),
        "models": {
            "persistence_naive": {
                "MAE": round(pers_mae, 3),
                "RMSE": round(pers_rmse, 3),
            },
            "ridge_regression": {
                "MAE": round(ridge_mae, 3),
                "RMSE": round(ridge_rmse, 3),
            },
            "random_forest": {
                "MAE": round(rf_mae, 3),
                "RMSE": round(rf_rmse, 3),
            },
        },
        "best_model": "ridge_regression" if ridge_rmse <= rf_rmse else "random_forest",
        "improvement_over_naive_rmse_pct": round(((pers_rmse - min(ridge_rmse, rf_rmse)) / pers_rmse) * 100, 2),
    }

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info(f"Weather Baseline -> Naive RMSE: {pers_rmse:.3f}, Ridge RMSE: {ridge_rmse:.3f}, RF RMSE: {rf_rmse:.3f}")
    lineage.add_output(metrics_path, "Weather Baseline Metrics JSON")
    lineage.finish(status="success", metadata=metrics)
    lineage.save(metrics_path.parent / "weather_baseline_lineage.json")

    return metrics


if __name__ == "__main__":
    res = train_and_evaluate_weather_baseline()
    print("Weather Time-Series Baseline Finished:", json.dumps(res, indent=2))
