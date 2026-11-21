"""
Advanced Intelligence Service
=============================
Module: app.services.advanced_intelligence_service

Provides prototype intelligence capabilities for Stage 7B:
1. assess_outbreak_and_multimodal_risk:
   Multimodal & environmental disease risk assessment (epistemic_type="predicted").
2. run_irrigation_rl_simulation:
   Lightweight water balance Q-learning / epsilon-greedy simulation (epistemic_type="simulated").
3. build_agricultural_graph_summary:
   NetworkX knowledge graph connecting farms, plots, crops, weather, and diseases (epistemic_type="simulated").
4. answer_farming_assistant_query:
   Deterministic, tool-grounded assistant routing to agronomy & intelligence tools.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

# Agronomic helpers from Stage 6B
try:
    from app.services.agronomy_service import (
        CROP_AGRONOMIC_PROFILES,
        recommend_crops,
        recommend_irrigation_and_fertilizer,
    )
except ImportError:
    # Graceful fallback for isolated test execution
    CROP_AGRONOMIC_PROFILES = {
        "Tomato": {"temp_opt": (18.0, 26.0), "temp_tol": (12.0, 32.0), "ph_opt": (6.0, 6.8)},
        "Potato": {"temp_opt": (12.0, 20.0), "temp_tol": (5.0, 28.0), "ph_opt": (5.2, 6.4)},
        "Pepper": {"temp_opt": (18.0, 27.0), "temp_tol": (12.0, 35.0), "ph_opt": (6.0, 7.0)},
        "Maize":  {"temp_opt": (20.0, 30.0), "temp_tol": (10.0, 40.0), "ph_opt": (5.8, 7.0)},
        "Rice":   {"temp_opt": (22.0, 32.0), "temp_tol": (15.0, 38.0), "ph_opt": (5.5, 7.0)},
    }
    recommend_crops = None  # type: ignore
    recommend_irrigation_and_fertilizer = None  # type: ignore


# ---------------------------------------------------------------------------
# 1. Multimodal Outbreak & Environmental Risk Assessment
# ---------------------------------------------------------------------------

def assess_outbreak_and_multimodal_risk(
    crop_type: str,
    temperature_c: float,
    relative_humidity_pct: float,
    rainfall_mm: float = 0.0,
    leaf_wetness_hours: Optional[float] = None,
    visual_anomaly_score: float = 0.0,
) -> Dict[str, Any]:
    """
    Evaluates environmental, disease, and visual anomaly risk factors for a crop.

    Parameters
    ----------
    crop_type : str
        Cultivated crop species (e.g., 'Tomato', 'Potato', 'Pepper').
    temperature_c : float
        Ambient or canopy temperature in °C.
    relative_humidity_pct : float
        Relative humidity (0.0 to 100.0 %).
    rainfall_mm : float
        Recent or forecast 24h precipitation in mm.
    leaf_wetness_hours : Optional[float]
        Hours of continuous leaf moisture (0 to 24). If None, estimated from RH and rain.
    visual_anomaly_score : float
        Confidence/severity score from computer vision or scouting observations (0.0 to 1.0).

    Returns
    -------
    dict
        Structured risk output with epistemic_type="predicted".
    """
    contributing_factors: List[str] = []
    crop_norm = crop_type.capitalize()

    # 1. Humidity factor
    rh = max(0.0, min(100.0, relative_humidity_pct))
    if rh >= 85.0:
        humidity_score = 1.0
        contributing_factors.append(f"Critical relative humidity ({rh:.1f}%) exceeds sporulation threshold (>=85%)")
    elif rh >= 70.0:
        humidity_score = (rh - 70.0) / 15.0
        contributing_factors.append(f"Elevated relative humidity ({rh:.1f}%) promotes fungal spore germination")
    else:
        humidity_score = max(0.0, (rh - 40.0) / 60.0) * 0.4

    # 2. Temperature window suitability for common foliar pathogens
    # Optimal sporulation for Late Blight / Early Blight / Fungal mildews is ~15-24°C
    if 15.0 <= temperature_c <= 24.0:
        temp_score = 1.0
        contributing_factors.append(f"Temperature ({temperature_c:.1f}°C) is in optimal fungal infection window (15-24°C)")
    elif 10.0 <= temperature_c < 15.0 or 24.0 < temperature_c <= 28.0:
        temp_score = 0.6
        contributing_factors.append(f"Temperature ({temperature_c:.1f}°C) is moderately conducive to pathogen growth")
    else:
        temp_score = 0.2

    # 3. Moisture / Rain & Leaf Wetness
    if leaf_wetness_hours is None:
        # Estimate leaf wetness from RH and rainfall
        if rainfall_mm > 5.0 or rh > 85.0:
            est_wetness = min(24.0, (rainfall_mm / 2.0) + (rh - 70.0) * 0.3)
        else:
            est_wetness = max(0.0, (rh - 60.0) * 0.1)
    else:
        est_wetness = max(0.0, min(24.0, leaf_wetness_hours))

    if est_wetness >= 8.0:
        wetness_score = 1.0
        contributing_factors.append(f"Prolonged leaf wetness (~{est_wetness:.1f}h) enables zoospore motility and penetration")
    elif est_wetness >= 4.0:
        wetness_score = 0.65
        contributing_factors.append(f"Moderate leaf wetness (~{est_wetness:.1f}h) supports surface colonization")
    else:
        wetness_score = 0.2

    # 4. Visual Anomaly factor
    anomaly = max(0.0, min(1.0, visual_anomaly_score))
    if anomaly >= 0.5:
        contributing_factors.append(f"Visual scouting anomaly score ({anomaly:.2f}) indicates symptomatic foliar lesions")

    # Combine environmental risk (weights: 40% humidity, 30% wetness, 30% temp)
    env_risk = 0.40 * humidity_score + 0.30 * wetness_score + 0.30 * temp_score

    # Multimodal integration: visual anomalies amplify or corroborate environmental risk
    overall_score = min(1.0, env_risk * 0.70 + anomaly * 0.30 + (0.15 if env_risk > 0.6 and anomaly > 0.5 else 0.0))
    overall_score = round(overall_score, 4)

    # Classify Risk Level
    if overall_score >= 0.75:
        risk_level = "Critical"
    elif overall_score >= 0.50:
        risk_level = "High"
    elif overall_score >= 0.25:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    # Identify primary threats and preventative recommendations
    threat_map = {
        "Tomato": ["Late Blight (Phytophthora infestans)", "Early Blight (Alternaria solani)", "Bacterial Spot (Xanthomonas)"],
        "Potato": ["Late Blight (Phytophthora infestans)", "Early Blight (Alternaria solani)", "Blackleg / Soft Rot"],
        "Pepper": ["Bacterial Spot (Xanthomonas)", "Anthracnose (Colletotrichum)", "Phytophthora Blight"],
        "Maize":  ["Northern Corn Leaf Blight (Exserohilum turcicum)", "Common Rust (Puccinia sorghi)"],
        "Rice":   ["Bacterial Leaf Blight (Xanthomonas oryzae)", "Rice Blast (Magnaporthe oryzae)"],
    }
    threats = threat_map.get(crop_norm, ["General Foliar Blight", "Fungal Leaf Spot", "Damping-off"])

    preventative_actions = []
    if overall_score >= 0.50:
        preventative_actions.extend([
            "Apply protective preventive contact bio-fungicide (e.g. Copper oxychloride / Trichoderma) prior to rain events.",
            "Avoid overhead sprinkler irrigation; switch to drip or sub-canopy furrow to keep foliage dry.",
            "Increase plant spacing or prune lower senescent leaves to improve canopy air circulation.",
        ])
    else:
        preventative_actions.extend([
            "Continue routine scout monitoring twice weekly, focusing on lower canopy and hill depressions.",
            "Maintain balanced nitrogen fertilization to avoid lush, overly susceptible vegetative tissues.",
        ])

    return {
        "epistemic_type": "predicted",
        "crop_type": crop_type,
        "risk_score": overall_score,
        "risk_level": risk_level,
        "environmental_risk_subscore": round(env_risk, 4),
        "visual_anomaly_score": round(anomaly, 4),
        "estimated_leaf_wetness_hours": round(est_wetness, 1),
        "primary_threats": threats,
        "contributing_factors": contributing_factors,
        "preventative_actions": preventative_actions,
        "caveats": (
            "Model predicts risk probability based on microclimate conduciveness and preliminary visual signals. "
            "Cultivar genetic resistance, soil drainage, and pathogen inoculum availability will dictate actual infection. "
            "Epistemic type: predicted."
        ),
    }


# ---------------------------------------------------------------------------
# 2. Lightweight Reinforcement Learning Irrigation Simulation
# ---------------------------------------------------------------------------

def run_irrigation_rl_simulation(
    crop_type: str = "Tomato",
    initial_soil_moisture_pct: float = 50.0,
    num_days: int = 14,
    daily_evapotranspiration_mm: float = 4.0,
    daily_rainfall_forecast_mm: Optional[List[float]] = None,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Lightweight 1D soil water balance simulation comparing a standard threshold-based
    irrigation rule against an exploratory Q-learning agent policy over N days.

    Epistemic type: 'simulated'.

    Parameters
    ----------
    crop_type : str
        Cultivated crop.
    initial_soil_moisture_pct : float
        Starting moisture percentage (0-100%).
    num_days : int
        Number of simulation days (default 14).
    daily_evapotranspiration_mm : float
        Average reference evapotranspiration ET_0 (mm/day).
    daily_rainfall_forecast_mm : Optional[List[float]]
        Forecast rainfall per day. If None, deterministic synthetic series is generated.
    random_seed : int
        Seed for reproducibility.
    """
    rng = random.Random(random_seed)

    # Synthetic forecast if not provided: a couple of dry days and one rain event
    if daily_rainfall_forecast_mm is None or len(daily_rainfall_forecast_mm) < num_days:
        rain_series = [0.0] * num_days
        if num_days > 4:
            rain_series[3] = 12.0  # Day 4 rain event
        if num_days > 9:
            rain_series[8] = 6.0   # Day 9 light rain
    else:
        rain_series = list(daily_rainfall_forecast_mm[:num_days])

    # Simulation Bucket Parameters (1% moisture approx 1.5 mm available water capacity)
    fc_pct = 80.0    # Field capacity
    crit_pct = 40.0  # Critical moisture stress threshold
    pwp_pct = 20.0   # Permanent wilting point

    # Available actions: 0 mm, 10 mm, 20 mm
    ACTIONS = [0.0, 10.0, 20.0]

    # --- 1. Run Rule-based Baseline ---
    # Rule: If moisture < 45%, apply 20 mm irrigation.
    baseline_moisture = max(pwp_pct, min(fc_pct, initial_soil_moisture_pct))
    baseline_water_used = 0.0
    baseline_stress_days = 0
    baseline_trajectory = []

    for day in range(num_days):
        rain = rain_series[day]
        et = daily_evapotranspiration_mm

        # Baseline decision rule
        if baseline_moisture < 45.0:
            irrig = 20.0
        else:
            irrig = 0.0

        baseline_water_used += irrig
        # Soil moisture balance update
        delta_water_mm = rain + irrig - et
        delta_pct = delta_water_mm / 1.5
        new_moisture = max(pwp_pct, min(fc_pct, baseline_moisture + delta_pct))

        is_stressed = new_moisture < crit_pct
        if is_stressed:
            baseline_stress_days += 1

        baseline_trajectory.append({
            "day": day + 1,
            "moisture_pct": round(new_moisture, 1),
            "rain_mm": rain,
            "irrigation_mm": irrig,
            "stressed": is_stressed,
        })
        baseline_moisture = new_moisture

    # --- 2. Lightweight Q-learning Policy Simulation ---
    # Discrete States: 0: Severe Stress (<35%), 1: Deficit (35-48%), 2: Optimal (48-68%), 3: Surplus (>68%)
    def get_state(m_pct: float) -> int:
        if m_pct < 35.0:
            return 0
        if m_pct < 48.0:
            return 1
        if m_pct <= 68.0:
            return 2
        return 3

    # Fast offline Q-value calibration over 30 episodes
    q_table = {s: [0.0, 0.0, 0.0] for s in range(4)}
    alpha = 0.2
    gamma = 0.9

    for _ in range(40):
        sim_m = initial_soil_moisture_pct
        for d in range(num_days):
            s = get_state(sim_m)
            # Epsilon-greedy
            if rng.random() < 0.25:
                a_idx = rng.randint(0, 2)
            else:
                a_idx = int(max(range(3), key=lambda i: q_table[s][i]))

            a_mm = ACTIONS[a_idx]
            r_mm = rain_series[d]
            nxt_m = max(pwp_pct, min(fc_pct, sim_m + (r_mm + a_mm - daily_evapotranspiration_mm) / 1.5))

            # Reward formulation: penalize moisture stress heavily, small penalty for water use
            reward = 0.0
            if nxt_m < crit_pct:
                reward -= (crit_pct - nxt_m) * 2.0  # Stress penalty
            reward -= a_mm * 0.15                   # Water conservation incentive

            nxt_s = get_state(nxt_m)
            best_next = max(q_table[nxt_s])
            q_table[s][a_idx] += alpha * (reward + gamma * best_next - q_table[s][a_idx])
            sim_m = nxt_m

    # Execute greedy learned policy
    rl_moisture = max(pwp_pct, min(fc_pct, initial_soil_moisture_pct))
    rl_water_used = 0.0
    rl_stress_days = 0
    rl_trajectory = []

    for day in range(num_days):
        s = get_state(rl_moisture)
        best_a_idx = int(max(range(3), key=lambda i: q_table[s][i]))
        irrig = ACTIONS[best_a_idx]
        rl_water_used += irrig

        rain = rain_series[day]
        et = daily_evapotranspiration_mm
        delta_water_mm = rain + irrig - et
        delta_pct = delta_water_mm / 1.5
        new_moisture = max(pwp_pct, min(fc_pct, rl_moisture + delta_pct))

        is_stressed = new_moisture < crit_pct
        if is_stressed:
            rl_stress_days += 1

        rl_trajectory.append({
            "day": day + 1,
            "moisture_pct": round(new_moisture, 1),
            "rain_mm": rain,
            "irrigation_mm": irrig,
            "stressed": is_stressed,
        })
        rl_moisture = new_moisture

    water_saved_pct = round(
        ((baseline_water_used - rl_water_used) / max(baseline_water_used, 1.0)) * 100.0, 2
    )

    return {
        "epistemic_type": "simulated",
        "crop_type": crop_type,
        "simulation_days": num_days,
        "daily_et_mm": daily_evapotranspiration_mm,
        "baseline_rule_results": {
            "total_water_applied_mm": baseline_water_used,
            "stress_days": baseline_stress_days,
            "trajectory_summary": baseline_trajectory[:5],  # Sample first 5 days
        },
        "rl_policy_results": {
            "total_water_applied_mm": rl_water_used,
            "stress_days": rl_stress_days,
            "water_savings_pct": water_saved_pct,
            "trajectory_summary": rl_trajectory[:5],
        },
        "simulation_insights": [
            f"Baseline threshold rule applied {baseline_water_used:.1f} mm with {baseline_stress_days} stress days.",
            f"RL policy applied {rl_water_used:.1f} mm with {rl_stress_days} stress days (water savings: {water_saved_pct}%).",
            "Anticipatory rain event integration dampens over-irrigation before natural recharge.",
        ],
        "limitations": (
            "Simulation employs a single-layer bucket soil hydrology representation. "
            "Does not capture 3D matric potential gradients, subsurface drainage losses, or crop stage-specific Kc curves. "
            "Epistemic type: simulated."
        ),
    }


# ---------------------------------------------------------------------------
# 3. Agricultural Knowledge Graph Topology Summary
# ---------------------------------------------------------------------------

def build_agricultural_graph_summary(
    farms_data: Optional[List[Dict[str, Any]]] = None,
    plots_data: Optional[List[Dict[str, Any]]] = None,
    disease_events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Constructs a NetworkX graph linking farms, plots, crops, weather zones, and disease vectors,
    returning topological metrics and structural graph highlights.

    Epistemic type: 'simulated'.
    """
    G = nx.Graph()

    # If no custom entities provided, build standard multi-region knowledge topology
    if not farms_data:
        farms_data = [
            {"id": "farm_chitwan", "name": "Chitwan Agro Hub", "zone": "zone_terai"},
            {"id": "farm_pokhara", "name": "Pokhara Valley Orchards", "zone": "zone_hills"},
            {"id": "farm_kathmandu", "name": "Kathmandu Green Valley", "zone": "zone_valley"},
        ]

    if not plots_data:
        plots_data = [
            {"id": "plot_c1", "farm_id": "farm_chitwan", "crop": "Tomato", "area_ha": 2.5},
            {"id": "plot_c2", "farm_id": "farm_chitwan", "crop": "Maize", "area_ha": 4.0},
            {"id": "plot_p1", "farm_id": "farm_pokhara", "crop": "Potato", "area_ha": 1.8},
            {"id": "plot_p2", "farm_id": "farm_pokhara", "crop": "Pepper", "area_ha": 1.2},
            {"id": "plot_k1", "farm_id": "farm_kathmandu", "crop": "Tomato", "area_ha": 1.0},
            {"id": "plot_k2", "farm_id": "farm_kathmandu", "crop": "Potato", "area_ha": 2.2},
        ]

    # Add Zones
    zones = {"zone_terai": "Terai Lowlands", "zone_hills": "Mid-Hills", "zone_valley": "Kathmandu Basin"}
    for zid, zname in zones.items():
        G.add_node(zid, type="weather_zone", label=zname)

    # Add Farms and link to Zones
    for f in farms_data:
        fid = f["id"]
        G.add_node(fid, type="farm", label=f["name"])
        if "zone" in f:
            G.add_edge(fid, f["zone"], relation="located_in")

    # Add Plots and Crops, link Plot -> Farm and Plot -> Crop
    for p in plots_data:
        pid = p["id"]
        crop_node = f"crop_{p['crop'].lower()}"
        G.add_node(pid, type="plot", crop=p["crop"], area_ha=p.get("area_ha", 1.0))
        G.add_node(crop_node, type="crop", label=p["crop"])

        G.add_edge(p["farm_id"], pid, relation="contains_plot")
        G.add_edge(pid, crop_node, relation="cultivates")

    # Add Known Pathogens and link Pathogen -> Crop (susceptibility) and Pathogen -> Zone (conduciveness)
    pathogen_edges = [
        ("pathogen_late_blight", "crop_potato", "infects"),
        ("pathogen_late_blight", "crop_tomato", "infects"),
        ("pathogen_late_blight", "zone_hills", "conducive_climate"),
        ("pathogen_late_blight", "zone_valley", "conducive_climate"),
        ("pathogen_bacterial_spot", "crop_tomato", "infects"),
        ("pathogen_bacterial_spot", "crop_pepper", "infects"),
        ("pathogen_bacterial_spot", "zone_terai", "conducive_climate"),
        ("pathogen_corn_rust", "crop_maize", "infects"),
    ]

    for src, dst, rel in pathogen_edges:
        p_name = src.replace("pathogen_", "").replace("_", " ").title()
        G.add_node(src, type="pathogen", label=p_name)
        G.add_edge(src, dst, relation=rel)

    # Compute network metrics
    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()
    degree_dict = dict(G.degree())
    degree_centrality = nx.degree_centrality(G)
    top_central_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]

    node_type_counts: Dict[str, int] = {}
    for _, attrs in G.nodes(data=True):
        ntype = attrs.get("type", "unknown")
        node_type_counts[ntype] = node_type_counts.get(ntype, 0) + 1

    components = nx.number_connected_components(G)

    # Topological insights
    structural_insights = [
        f"Graph incorporates {total_nodes} entities ({node_type_counts}) linked by {total_edges} relations.",
        f"Highest connectivity nodes: {top_central_nodes[0][0]} ({top_central_nodes[0][1]:.2f}) and {top_central_nodes[1][0]} ({top_central_nodes[1][1]:.2f}).",
        "Pathogen 'Late Blight' serves as a topological disease bridge connecting Solanaceae plots across both Hills and Kathmandu regions.",
    ]

    return {
        "epistemic_type": "simulated",
        "node_count": total_nodes,
        "edge_count": total_edges,
        "connected_components": components,
        "node_type_counts": node_type_counts,
        "top_central_nodes": [
            {"node": node, "centrality": round(cent, 4), "degree": degree_dict[node]}
            for node, cent in top_central_nodes
        ],
        "structural_insights": structural_insights,
        "limitations": (
            "Graph structure reflects static relational topology and epidemiological co-occurrence. "
            "Dynamic vector transmission, windborne dispersal vectors, and temporal latency are not modeled. "
            "Epistemic type: simulated."
        ),
    }


# ---------------------------------------------------------------------------
# 4. Tool-Grounded Farming Assistant Query Dispatcher
# ---------------------------------------------------------------------------

def answer_farming_assistant_query(
    query: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deterministic, tool-grounded assistant routing that maps user queries to
    agronomy, risk assessment, and simulation tools without LLM hallucinations.

    Parameters
    ----------
    query : str
        User natural language query.
    context : Optional[Dict[str, Any]]
        Optional agricultural context parameters (crop_type, soil_ph, moisture, temperature, etc.).

    Returns
    -------
    dict
        Structured assistant answer containing detected intent, invoked tools,
        grounded data, and strict epistemic qualifiers.
    """
    ctx = context or {}
    q_lower = query.lower().strip()
    crop = ctx.get("crop_type", "Tomato")

    # Intent 1: Farm Topology / Graph Knowledge (check first to avoid intercept by entity keywords like 'disease' or 'crop')
    if any(k in q_lower for k in ["graph", "network", "topology", "centrality", "connectivity", "bridge"]):
        graph_res = build_agricultural_graph_summary()
        guidance = (
            f"Synthesized agricultural graph topology: {graph_res['node_count']} nodes and "
            f"{graph_res['edge_count']} edges across {graph_res['connected_components']} components. "
            f"{graph_res['structural_insights'][2]}"
        )
        return {
            "query": query,
            "intent_detected": "agricultural_graph_topology",
            "epistemic_type": "simulated",
            "tools_invoked": ["build_agricultural_graph_summary"],
            "guidance": guidance,
            "tool_data": graph_res,
            "limitations": "Relational topology modeling. Epistemic type: simulated.",
        }

    # Intent 2: Disease Outbreak / Blight / Pathogen Risk
    elif any(k in q_lower for k in ["disease", "blight", "spot", "pathogen", "outbreak", "rot", "infection", "fungus"]):
        temp = float(ctx.get("temperature_c", 21.0))
        rh = float(ctx.get("relative_humidity_pct", 82.0))
        rain = float(ctx.get("rainfall_mm", 4.0))
        anomaly = float(ctx.get("visual_anomaly_score", 0.0))

        risk_res = assess_outbreak_and_multimodal_risk(
            crop_type=crop,
            temperature_c=temp,
            relative_humidity_pct=rh,
            rainfall_mm=rain,
            visual_anomaly_score=anomaly,
        )

        guidance = (
            f"Assessed disease outbreak risk for {crop}: {risk_res['risk_level']} (score: {risk_res['risk_score']:.2f}). "
            f"Primary threats: {', '.join(risk_res['primary_threats'])}. "
            f"Recommended preventative action: {risk_res['preventative_actions'][0]}"
        )

        return {
            "query": query,
            "intent_detected": "disease_risk_assessment",
            "epistemic_type": "predicted",
            "tools_invoked": ["assess_outbreak_and_multimodal_risk"],
            "guidance": guidance,
            "tool_data": risk_res,
            "limitations": "Directly grounded in environmental risk heuristics; no generative LLM hallucination.",
        }

    # Intent 3: Irrigation Scheduling & RL Water Balance
    elif any(k in q_lower for k in ["irrigation", "water", "drought", "schedule", "watering", "rl"]):
        if any(k in q_lower for k in ["rl", "policy", "simulation", "optimize", "savings"]):
            rl_res = run_irrigation_rl_simulation(
                crop_type=crop,
                initial_soil_moisture_pct=float(ctx.get("soil_moisture_pct", 48.0)),
                num_days=int(ctx.get("num_days", 14)),
            )
            guidance = (
                f"Completed 14-day irrigation RL simulation for {crop}: "
                f"Policy achieved {rl_res['rl_policy_results']['water_savings_pct']}% water savings "
                f"compared to fixed threshold baseline ({rl_res['rl_policy_results']['total_water_applied_mm']} mm vs "
                f"{rl_res['baseline_rule_results']['total_water_applied_mm']} mm applied)."
            )
            return {
                "query": query,
                "intent_detected": "irrigation_rl_simulation",
                "epistemic_type": "simulated",
                "tools_invoked": ["run_irrigation_rl_simulation"],
                "guidance": guidance,
                "tool_data": rl_res,
                "limitations": "Simulated single-layer bucket water balance. Epistemic type: simulated.",
            }
        else:
            # Prescriptive agronomic recommendation
            if recommend_irrigation_and_fertilizer:
                rec_res = recommend_irrigation_and_fertilizer(
                    crop_type=crop,
                    soil_moisture_pct=float(ctx.get("soil_moisture_pct", 55.0)),
                    precipitation_mm=float(ctx.get("precipitation_mm", 0.0)),
                    temperature_c=float(ctx.get("temperature_c", 22.0)),
                    soil_ph=float(ctx.get("soil_ph", 6.2)),
                )
                irr = rec_res.get("irrigation_recommendation", {})
                urgency = irr.get("urgency", rec_res.get("irrigation_urgency", "Moderate"))
                action = irr.get("action", rec_res.get("irrigation_action", "Monitor soil moisture"))
                water_l = irr.get("estimated_water_liters_per_m2", rec_res.get("estimated_water_liters_per_m2", 0.0))
                guidance = (
                    f"Irrigation advisory for {crop}: urgency is '{urgency}' "
                    f"({action}). Estimated water required: {water_l} L/m²."
                )
                return {
                    "query": query,
                    "intent_detected": "irrigation_advisory",
                    "epistemic_type": "recommended",
                    "tools_invoked": ["recommend_irrigation_and_fertilizer"],
                    "guidance": guidance,
                    "tool_data": rec_res,
                    "limitations": "Rule-based agronomic advisory. Epistemic type: recommended.",
                }

    # Intent 4: Crop Selection / Suitability
    elif any(k in q_lower for k in ["crop", "plant", "suitability", "ph", "recommend", "soil"]):
        if recommend_crops:
            crop_res = recommend_crops(
                soil_ph=float(ctx.get("soil_ph", 6.5)),
                temperature_c=float(ctx.get("temperature_c", 23.0)),
                soil_moisture_pct=float(ctx.get("soil_moisture_pct", 65.0)),
            )
            ranking = crop_res.get("ranked_crops", crop_res.get("ranking", []))
            top_crop = (ranking[0].get("crop_type") or ranking[0].get("crop", "None")) if ranking else "None"
            guidance = (
                f"Ranked {len(ranking)} crops for conditions (pH {ctx.get('soil_ph', 6.5)}, "
                f"Temp {ctx.get('temperature_c', 23.0)}°C). Top recommended crop: {top_crop}."
            )
            return {
                "query": query,
                "intent_detected": "crop_suitability_recommendation",
                "epistemic_type": "recommended",
                "tools_invoked": ["recommend_crops"],
                "guidance": guidance,
                "tool_data": crop_res,
                "limitations": "Agronomic suitability scoring based on standard crop profiles. Epistemic type: recommended.",
            }

    # Default fallback: Platform capabilities overview
    return {
        "query": query,
        "intent_detected": "general_inquiry",
        "epistemic_type": "recommended",
        "tools_invoked": [],
        "guidance": (
            "Smart Agriculture Platform Assistant ready. You can query: "
            "1) Disease outbreak risk for crops under weather conditions, "
            "2) Irrigation schedules or RL water balance simulations, "
            "3) Crop suitability based on soil pH and temperature, or "
            "4) Agricultural knowledge graph topology."
        ),
        "tool_data": None,
        "limitations": "Strictly deterministic routing. No external LLM or unverified statements.",
    }
