"""
Digital Twin Scenario Simulator
================================
Module: app.services.twin_service

Provides simulate_plot_scenario() which applies named or custom
agronomic adjustment scenarios to a baseline yield and returns
a full simulation summary with epistemic_type="simulated".

Named scenarios
---------------
  "baseline"       : No change — returns inputs unchanged.
  "warming_2c"     : Global +2 °C temperature increase.
  "monsoon_drought": Severe rainfall reduction (×0.4), soil moisture −20 %.
  "wet_monsoon"    : High rainfall (×1.8), soil moisture +15 %.
  "custom"         : User-supplied adjustments dict (no preset overrides).

Adjustment keys (all optional, additive/multiplicative)
---------------------------------------------------------
  temperature_delta_c  : float  — temperature change (°C) added to crop optimum evaluation.
  rainfall_multiplier  : float  — multiplies baseline effective rainfall (1.0 = no change).
  irrigation_mm        : float  — supplemental irrigation (mm); moderate positive boost.
  fertilizer_kg_ha     : float  — fertilizer applied (kg/ha); logarithmic-capped positive effect.
  disease_pressure     : float  — 0.0 (no disease) to 1.0 (total crop loss).

Epistemic type: "simulated" — outputs are model projections, not measured values.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Import crop profiles for temperature tolerance lookup
# ---------------------------------------------------------------------------
try:
    from app.services.agronomy_service import CROP_AGRONOMIC_PROFILES
except ImportError:
    # Fallback minimal profiles if import fails (e.g., unit testing isolation)
    CROP_AGRONOMIC_PROFILES = {
        "Tomato":  {"temp_opt": (18.0, 26.0), "temp_tol": (12.0, 32.0)},
        "Potato":  {"temp_opt": (12.0, 20.0), "temp_tol": (5.0, 28.0)},
        "Pepper":  {"temp_opt": (18.0, 27.0), "temp_tol": (12.0, 35.0)},
        "Maize":   {"temp_opt": (20.0, 30.0), "temp_tol": (10.0, 40.0)},
        "Rice":    {"temp_opt": (22.0, 32.0), "temp_tol": (15.0, 38.0)},
    }

# ---------------------------------------------------------------------------
# Named scenario presets — each key overwrites the matching adjustment
# ---------------------------------------------------------------------------
_SCENARIO_PRESETS: Dict[str, Dict[str, Any]] = {
    "baseline": {},
    "warming_2c": {
        "temperature_delta_c": 2.0,
    },
    "monsoon_drought": {
        "rainfall_multiplier": 0.4,
        # Encode moisture change via a custom key the simulator reads
        "_moisture_delta_pct": -20.0,
    },
    "wet_monsoon": {
        "rainfall_multiplier": 1.8,
        "_moisture_delta_pct": 15.0,
    },
    "custom": {},  # entirely user-driven
}

_SUPPORTED_SCENARIOS = list(_SCENARIO_PRESETS.keys())


def _temperature_yield_factor(crop_type: str, temperature_delta_c: float) -> tuple[float, str]:
    """
    Compute multiplicative yield factor due to temperature shift.

    Returns (factor, driver_description).
    Factor < 1.0 → penalty; factor == 1.0 → no change.
    """
    profile = CROP_AGRONOMIC_PROFILES.get(crop_type, {})
    temp_opt = profile.get("temp_opt", (20.0, 28.0))
    temp_tol = profile.get("temp_tol", (10.0, 38.0))

    # Representative ambient temperature (mid of optimal range + delta)
    mid_opt = (temp_opt[0] + temp_opt[1]) / 2.0
    effective_temp = mid_opt + temperature_delta_c

    tol_low, tol_high = temp_tol
    opt_low, opt_high = temp_opt

    if opt_low <= effective_temp <= opt_high:
        factor = 1.0
        desc = f"Temperature {effective_temp:.1f}°C within optimal range — no yield penalty"
    elif tol_low <= effective_temp < opt_low:
        # Mild cold stress — linear penalty up to 20 %
        stress = (opt_low - effective_temp) / (opt_low - tol_low)
        factor = max(0.80, 1.0 - 0.20 * stress)
        desc = f"Mild cold stress at {effective_temp:.1f}°C — yield factor {factor:.2f}"
    elif opt_high < effective_temp <= tol_high:
        # Mild heat stress — linear penalty up to 25 %
        stress = (effective_temp - opt_high) / (tol_high - opt_high)
        factor = max(0.75, 1.0 - 0.25 * stress)
        desc = f"Mild heat stress at {effective_temp:.1f}°C — yield factor {factor:.2f}"
    else:
        # Outside tolerance — severe penalty up to 70 %
        factor = 0.30
        desc = f"Severe thermal stress at {effective_temp:.1f}°C (outside tolerance) — yield factor {factor:.2f}"

    return factor, desc


def _rainfall_yield_factor(rainfall_multiplier: float, moisture_delta_pct: float) -> tuple[float, str]:
    """
    Compute multiplicative yield factor from rainfall and moisture adjustments.

    - multiplier < 0.5 → drought stress
    - multiplier > 1.5 → possible waterlogging
    - moisture_delta_pct < −15 → compounding drought
    - moisture_delta_pct > +20 → compounding excess
    """
    # Baseline at multiplier = 1.0 → factor 1.0
    if rainfall_multiplier < 0.3:
        rain_factor = 0.45
        rain_desc = f"Severe drought (rainfall ×{rainfall_multiplier:.1f}) — heavy yield loss"
    elif rainfall_multiplier < 0.6:
        rain_factor = 0.70 + 0.30 * (rainfall_multiplier - 0.3) / 0.3
        rain_desc = f"Drought stress (rainfall ×{rainfall_multiplier:.1f}) — yield factor {rain_factor:.2f}"
    elif rainfall_multiplier <= 1.3:
        rain_factor = 1.0
        rain_desc = f"Rainfall ×{rainfall_multiplier:.1f} within normal range — no rainfall penalty"
    elif rainfall_multiplier <= 1.7:
        # Moderate excess — slight positive for most crops
        rain_factor = 1.03
        rain_desc = f"Above-normal rainfall ×{rainfall_multiplier:.1f} — slight yield boost"
    else:
        # Excessive → waterlogging risk → moderate penalty
        rain_factor = 0.88
        rain_desc = f"Excess rainfall ×{rainfall_multiplier:.1f} — waterlogging risk, yield factor {rain_factor:.2f}"

    # Moisture modifier
    if moisture_delta_pct < -15.0:
        moist_factor = 0.85
    elif moisture_delta_pct > 20.0:
        moist_factor = 0.92
    else:
        moist_factor = 1.0

    combined = rain_factor * moist_factor
    return combined, rain_desc


def _irrigation_yield_factor(irrigation_mm: float, rainfall_multiplier: float) -> tuple[float, str]:
    """
    Supplemental irrigation provides a moderate positive boost when rainfall is deficient.
    Minimal effect when rainfall is already adequate.
    """
    if irrigation_mm <= 0.0:
        return 1.0, "No supplemental irrigation applied"

    deficit_regime = rainfall_multiplier < 0.75
    # Cap benefit at 10 % for drought, 4 % otherwise
    max_boost = 0.10 if deficit_regime else 0.04
    # Logarithmic saturation: 50 mm gives ~half the max benefit
    boost = max_boost * math.log1p(irrigation_mm) / math.log1p(50.0)
    boost = min(boost, max_boost)
    factor = 1.0 + boost
    desc = f"Supplemental irrigation {irrigation_mm:.0f} mm — yield factor {factor:.3f}"
    return factor, desc


def _fertilizer_yield_factor(fertilizer_kg_ha: float) -> tuple[float, str]:
    """
    Fertilizer application gives a logarithmic-capped positive effect.
    Zero fertilizer → no change. Saturates around 200 kg/ha (max +12 %).
    """
    if fertilizer_kg_ha <= 0.0:
        return 1.0, "No additional fertilizer applied"

    max_boost = 0.12
    boost = max_boost * math.log1p(fertilizer_kg_ha) / math.log1p(200.0)
    boost = min(boost, max_boost)
    factor = 1.0 + boost
    desc = f"Fertilizer {fertilizer_kg_ha:.0f} kg/ha — yield factor {factor:.3f}"
    return factor, desc


def _disease_yield_factor(disease_pressure: float) -> tuple[float, str]:
    """
    Linear negative effect: 0.0 = no loss, 1.0 = total crop loss.
    """
    disease_pressure = max(0.0, min(1.0, disease_pressure))
    factor = 1.0 - disease_pressure
    if disease_pressure == 0.0:
        desc = "No disease pressure — no yield impact"
    elif disease_pressure < 0.3:
        desc = f"Low disease pressure ({disease_pressure:.0%}) — minor yield reduction"
    elif disease_pressure < 0.7:
        desc = f"Moderate disease pressure ({disease_pressure:.0%}) — significant yield reduction"
    else:
        desc = f"High disease pressure ({disease_pressure:.0%}) — severe yield loss"
    return factor, desc


def simulate_plot_scenario(
    plot_id: Optional[int],
    crop_type: str,
    baseline_yield_kg_ha: float,
    scenario: str = "baseline",
    adjustments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Simulate the effect of a named or custom scenario on crop yield.

    Parameters
    ----------
    plot_id            : Optional plot ID for provenance (can be None).
    crop_type          : Crop species (e.g., "Tomato", "Potato").
    baseline_yield_kg_ha: Reference yield in kg/ha before scenario effects.
    scenario           : Named scenario or "custom".
    adjustments        : Dict of adjustment keys (overrides presets for "custom").

    Returns
    -------
    dict with keys:
        epistemic_type        : "simulated"
        crop_type             : str
        scenario              : str
        baseline_yield_kg_ha  : float
        simulated_yield_kg_ha : float
        yield_change_pct      : float
        key_drivers           : List[str]
        assumptions           : List[str]
        limitations           : str
    """
    if adjustments is None:
        adjustments = {}

    # Merge preset → user adjustments (user values override preset)
    preset = _SCENARIO_PRESETS.get(scenario, {})
    merged = {**preset, **adjustments}

    # Extract adjustment values
    temp_delta = float(merged.get("temperature_delta_c", 0.0))
    rain_mult = float(merged.get("rainfall_multiplier", 1.0))
    irrigation = float(merged.get("irrigation_mm", 0.0))
    fertilizer = float(merged.get("fertilizer_kg_ha", 0.0))
    disease = float(merged.get("disease_pressure", 0.0))
    moisture_delta = float(merged.get("_moisture_delta_pct", 0.0))

    # Clamp inputs
    rain_mult = max(0.0, rain_mult)
    irrigation = max(0.0, irrigation)
    fertilizer = max(0.0, fertilizer)
    disease = max(0.0, min(1.0, disease))

    # --- Compute individual factors ---
    temp_factor, temp_driver = _temperature_yield_factor(crop_type, temp_delta)
    rain_factor, rain_driver = _rainfall_yield_factor(rain_mult, moisture_delta)
    irrig_factor, irrig_driver = _irrigation_yield_factor(irrigation, rain_mult)
    fert_factor, fert_driver = _fertilizer_yield_factor(fertilizer)
    disease_factor, disease_driver = _disease_yield_factor(disease)

    # --- Combined multiplicative model ---
    combined_factor = temp_factor * rain_factor * irrig_factor * fert_factor * disease_factor
    simulated_yield = max(0.0, round(baseline_yield_kg_ha * combined_factor, 2))
    yield_change_pct = round((simulated_yield - baseline_yield_kg_ha) / baseline_yield_kg_ha * 100.0, 2)

    # --- Key drivers (only non-neutral factors) ---
    key_drivers: List[str] = []
    for driver in [temp_driver, rain_driver, irrig_driver, fert_driver, disease_driver]:
        if driver and "no yield" not in driver.lower() and "no additional" not in driver.lower() and "no disease" not in driver.lower() and "no supplemental" not in driver.lower():
            key_drivers.append(driver)
    if not key_drivers:
        key_drivers = ["No significant adjustments applied — baseline conditions maintained"]

    return {
        "epistemic_type": "simulated",
        "crop_type": crop_type,
        "scenario": scenario if scenario in _SUPPORTED_SCENARIOS else "custom",
        "baseline_yield_kg_ha": float(baseline_yield_kg_ha),
        "simulated_yield_kg_ha": simulated_yield,
        "yield_change_pct": yield_change_pct,
        "combined_yield_factor": round(combined_factor, 4),
        "factor_breakdown": {
            "temperature": round(temp_factor, 4),
            "rainfall_moisture": round(rain_factor, 4),
            "irrigation": round(irrig_factor, 4),
            "fertilizer": round(fert_factor, 4),
            "disease": round(disease_factor, 4),
        },
        "key_drivers": key_drivers,
        "assumptions": [
            "Yield factors are multiplicative and independent — real interactions may differ.",
            "Temperature factor uses mid-range of crop optimal temperature; actual ambient may vary.",
            "Irrigation benefit assumes deficient baseline; soil type not modelled.",
            "Fertilizer response assumes no nutrient toxicity or salinity constraints.",
            "Disease pressure modelled as linear reduction; actual losses depend on pathogen, timing, and intervention.",
            f"Crop profile used: {crop_type} from CROP_AGRONOMIC_PROFILES.",
        ],
        "limitations": (
            "This is a simplified multiplicative scenario model. It does not account for "
            "phenological stage, soil type, slope/drainage, pest–disease interactions, market price, "
            "or multi-year soil health effects. Use only for directional planning and sensitivity analysis. "
            "Epistemic type: simulated — outputs are NOT measured or observed field values."
        ),
    }
