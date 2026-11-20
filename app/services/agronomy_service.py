"""
Core Agronomy & Advisory Service
=================================
Module: app.services.agronomy_service

Provides:
1. recommend_crops: Evaluates agronomic suitability of candidate crops
   (Tomato, Potato, Pepper, Maize, Rice) against soil pH, temperature, and moisture.
2. recommend_irrigation_and_fertilizer: Prescriptive irrigation need and nutrient guidance
   with explicit assumptions, limitations, and epistemic_type="recommended".
"""

from typing import Any, Dict, List, Optional


# Agronomic optimal and absolute tolerance ranges
CROP_AGRONOMIC_PROFILES = {
    "Tomato": {
        "ph_opt": (6.0, 6.8),
        "ph_tol": (5.5, 7.5),
        "temp_opt": (18.0, 26.0),
        "temp_tol": (12.0, 32.0),
        "moisture_opt": (60.0, 80.0),  # % field capacity / volumetric proxy
        "moisture_tol": (40.0, 90.0),
        "cycle_days": 110,
        "notes": "Prefers well-drained loamy soil, sensitive to frost and prolonged waterlogging.",
    },
    "Potato": {
        "ph_opt": (5.2, 6.4),
        "ph_tol": (4.8, 7.0),
        "temp_opt": (15.0, 21.0),
        "temp_tol": (8.0, 28.0),
        "moisture_opt": (65.0, 85.0),
        "moisture_tol": (45.0, 95.0),
        "cycle_days": 90,
        "notes": "Cool-season tuber crop; tuber initiation severely inhibited above 27°C; high late blight risk if humidity > 85%.",
    },
    "Pepper": {
        "ph_opt": (6.0, 6.8),
        "ph_tol": (5.5, 7.2),
        "temp_opt": (20.0, 28.0),
        "temp_tol": (14.0, 34.0),
        "moisture_opt": (55.0, 75.0),
        "moisture_tol": (40.0, 85.0),
        "cycle_days": 120,
        "notes": "Warm-season crop; sensitive to cold snaps and root rot in heavy clay.",
    },
    "Maize": {
        "ph_opt": (5.8, 7.0),
        "ph_tol": (5.0, 7.8),
        "temp_opt": (20.0, 30.0),
        "temp_tol": (10.0, 36.0),
        "moisture_opt": (50.0, 75.0),
        "moisture_tol": (35.0, 90.0),
        "cycle_days": 105,
        "notes": "Moderate drought tolerance; requires high nitrogen during vegetative and tasseling stages.",
    },
    "Rice": {
        "ph_opt": (5.5, 6.8),
        "ph_tol": (4.5, 8.0),
        "temp_opt": (22.0, 32.0),
        "temp_tol": (16.0, 38.0),
        "moisture_opt": (80.0, 100.0),
        "moisture_tol": (60.0, 100.0),
        "cycle_days": 130,
        "notes": "Requires high moisture or flooded paddy conditions; heavy alluvium / clay soils preferred.",
    },
}


def _calculate_trait_score(val: float, opt_range: tuple, tol_range: tuple) -> float:
    """Computes a continuous suitability score [0.0, 1.0] for a single trait."""
    if opt_range[0] <= val <= opt_range[1]:
        return 1.0
    elif tol_range[0] <= val <= tol_range[1]:
        # Linear degradation outside optimal range
        if val < opt_range[0]:
            return max(0.1, (val - tol_range[0]) / (opt_range[0] - tol_range[0]))
        else:
            return max(0.1, (tol_range[1] - val) / (tol_range[1] - opt_range[1]))
    else:
        return 0.05


def recommend_crops(
    soil_ph: float,
    temperature_c: float,
    soil_moisture_pct: float,
    candidate_crops: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Ranks candidate crops based on agronomic suitability scores against
    soil pH, temperature, and moisture conditions.
    """
    targets = candidate_crops or list(CROP_AGRONOMIC_PROFILES.keys())
    ranked_entries = []

    for crop in targets:
        profile = CROP_AGRONOMIC_PROFILES.get(crop)
        if not profile:
            continue

        ph_score = _calculate_trait_score(soil_ph, profile["ph_opt"], profile["ph_tol"])
        temp_score = _calculate_trait_score(temperature_c, profile["temp_opt"], profile["temp_tol"])
        moist_score = _calculate_trait_score(soil_moisture_pct, profile["moisture_opt"], profile["moisture_tol"])

        # Weighted composite suitability: temperature (40%), moisture (35%), pH (25%)
        composite_score = round(0.40 * temp_score + 0.35 * moist_score + 0.25 * ph_score, 3)

        reasons = []
        if ph_score >= 0.9:
            reasons.append(f"Soil pH ({soil_ph:.1f}) is within optimal range ({profile['ph_opt'][0]}-{profile['ph_opt'][1]}).")
        elif ph_score < 0.5:
            reasons.append(f"Soil pH ({soil_ph:.1f}) deviates from preference ({profile['ph_opt'][0]}-{profile['ph_opt'][1]}).")

        if temp_score >= 0.9:
            reasons.append(f"Temperature ({temperature_c:.1f}°C) matches thermal preference ({profile['temp_opt'][0]}-{profile['temp_opt'][1]}°C).")
        elif temp_score < 0.5:
            reasons.append(f"Temperature ({temperature_c:.1f}°C) is suboptimal for {crop}.")

        if moist_score >= 0.9:
            reasons.append(f"Moisture ({soil_moisture_pct:.1f}%) aligns with water demand.")
        elif moist_score < 0.5:
            reasons.append(f"Moisture ({soil_moisture_pct:.1f}%) is outside ideal range.")

        suitability = "High" if composite_score >= 0.75 else ("Moderate" if composite_score >= 0.50 else "Low")

        ranked_entries.append({
            "crop_type": crop,
            "suitability": suitability,
            "suitability_score": composite_score,
            "reasons": reasons,
            "crop_notes": profile["notes"],
        })

    # Sort descending by composite suitability score
    ranked_entries.sort(key=lambda x: x["suitability_score"], reverse=True)

    return {
        "epistemic_type": "recommended",
        "input_parameters": {
            "soil_ph": soil_ph,
            "temperature_c": temperature_c,
            "soil_moisture_pct": soil_moisture_pct,
        },
        "ranked_crops": ranked_entries,
        "assumptions": [
            "Assumes macro-nutrients (N, P, K) are managed within standard regional baselines.",
            "Suitability scores reflect static abiotic factors and do not account for localized pest outbreaks.",
        ],
        "limitations": "Advisories are decision-support heuristics; verify with physical on-site soil and drainage testing.",
    }


def recommend_irrigation_and_fertilizer(
    crop_type: str,
    soil_moisture_pct: float,
    temperature_c: float,
    precipitation_mm: float,
    soil_ph: float,
) -> Dict[str, Any]:
    """
    Computes actionable prescriptive guidance for irrigation and fertilizer adjustments
    with explicit agronomic logic, assumptions, and limitations.
    """
    profile = CROP_AGRONOMIC_PROFILES.get(crop_type, CROP_AGRONOMIC_PROFILES["Tomato"])

    # 1. Irrigation Need Logic
    moist_opt_min, moist_opt_max = profile["moisture_opt"]
    effective_water = soil_moisture_pct + (precipitation_mm * 1.5)  # proxy for rainfall infiltration

    if effective_water < moist_opt_min * 0.7:
        irrigation_urgency = "High"
        irrigation_action = "Immediate irrigation recommended. Soil moisture is severely below crop transpiration needs."
        water_amount_liters_m2 = round(max(5.0, (moist_opt_min - effective_water) * 0.4), 1)
    elif effective_water < moist_opt_min:
        irrigation_urgency = "Moderate"
        irrigation_action = "Scheduled light irrigation recommended within 24–48 hours."
        water_amount_liters_m2 = round((moist_opt_min - effective_water) * 0.25, 1)
    elif effective_water > moist_opt_max * 1.2:
        irrigation_urgency = "None"
        irrigation_action = "Over-saturated conditions. Suspend irrigation and verify field drainage to avoid root rot."
        water_amount_liters_m2 = 0.0
    else:
        irrigation_urgency = "Low"
        irrigation_action = "Soil moisture is currently optimal. Maintain normal monitoring schedule."
        water_amount_liters_m2 = 0.0

    # 2. Fertilizer & Soil Amendment Logic
    fertilizer_guidance = []
    if soil_ph < 5.8:
        fertilizer_guidance.append("Acidic soil: Consider applying agricultural limestone (CaCO3) or dolomite to raise pH and improve phosphorus availability.")
    elif soil_ph > 7.5:
        fertilizer_guidance.append("Alkaline soil: Apply elemental sulfur or acidifying nitrogen fertilizer (e.g., ammonium sulfate) to lower pH.")
    else:
        fertilizer_guidance.append("Soil pH is in a balanced agronomic range; standard basal NPK applications are appropriate.")

    if crop_type in ("Tomato", "Pepper"):
        fertilizer_guidance.append(f"Ensure balanced Potassium (K) and Calcium (Ca) nutrition to avoid blossom end rot under variable moisture.")
    elif crop_type == "Potato":
        fertilizer_guidance.append("Ensure adequate Phosphorus and Potassium; avoid excessive late-season Nitrogen which delays tuber bulking.")
    elif crop_type == "Maize":
        fertilizer_guidance.append("Side-dress Nitrogen during knee-high to tasseling stages for maximum canopy development.")

    return {
        "epistemic_type": "recommended",
        "crop_type": crop_type,
        "irrigation_recommendation": {
            "urgency": irrigation_urgency,
            "action": irrigation_action,
            "estimated_water_liters_per_m2": water_amount_liters_m2,
        },
        "fertilizer_recommendation": {
            "soil_ph_status": "Acidic" if soil_ph < 5.8 else ("Alkaline" if soil_ph > 7.5 else "Optimal"),
            "guidance_notes": fertilizer_guidance,
        },
        "assumptions": [
            "Assumes well-maintained surface or drip irrigation infrastructure.",
            "Water infiltration rates vary based on soil texture (sand/loam/clay).",
        ],
        "limitations": "Dosage recommendations are advisory; calibrated chemical soil testing is required before high-volume nutrient application.",
    }
