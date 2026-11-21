from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.db.repositories import (
    FarmRepository,
    PlotRepository,
    FieldObservationRepository,
    PredictionRepository,
    TwinScenarioRepository,
    list_recent_predictions,
    list_recent_twin_scenarios,
)
from app.schemas.contracts import (
    FarmCreate,
    FarmResponse,
    FarmDetailResponse,
    HistoryItem,
    HistoryResponse,
    MonitoringStatusResponse,
    PlotCreate,
    PlotResponse,
    FieldObservationCreate,
    FieldObservationResponse,
    TwinScenarioCreate,
    TwinScenarioResponse,
    DiseasePredictionResponse,
    CropIrrigationAdvisoryRequest,
    CropIrrigationAdvisoryResponse,
    YieldPredictionRequest,
    YieldPredictionResponse,
    TwinSimulationRequest,
    TwinSimulationResponse,
    IntelligenceAssessmentRequest,
    IntelligenceAssessmentResponse,
)
from app.services.disease_service import disease_service
from app.services.agronomy_service import recommend_crops, recommend_irrigation_and_fertilizer
from app.services.twin_service import simulate_plot_scenario
from app.services.advanced_intelligence_service import (
    assess_outbreak_and_multimodal_risk,
    answer_farming_assistant_query,
)

router = APIRouter()

# --- Health Check ---
@router.get("/health", tags=["System"])
def api_v1_health():
    return {
        "status": "healthy",
        "api_version": "v1",
        "model_loaded": disease_service.model is not None,
        "model_version": disease_service.model_version,
        "model_architecture": disease_service.architecture,
        "num_classes": len(disease_service.class_names),
        "inference_device": str(disease_service.device),
    }

# --- Farms & Plots Endpoints ---
@router.post("/farms", response_model=FarmResponse, status_code=status.HTTP_201_CREATED, tags=["Farms"])
def create_farm(farm_in: FarmCreate, db: Session = Depends(get_db)):
    repo = FarmRepository(db)
    return repo.create(name=farm_in.name, location=farm_in.location)

@router.get("/farms", response_model=List[FarmResponse], tags=["Farms"])
def list_farms(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = FarmRepository(db)
    return repo.list_all(skip=skip, limit=limit)

@router.get("/farms/{farm_id}", response_model=FarmDetailResponse, tags=["Farms"])
def get_farm(farm_id: int, db: Session = Depends(get_db)):
    repo = FarmRepository(db)
    farm = repo.get_by_id(farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm

@router.post("/farms/{farm_id}/plots", response_model=PlotResponse, status_code=status.HTTP_201_CREATED, tags=["Plots"])
def create_plot(farm_id: int, plot_in: PlotCreate, db: Session = Depends(get_db)):
    farm_repo = FarmRepository(db)
    if not farm_repo.get_by_id(farm_id):
        raise HTTPException(status_code=404, detail="Farm not found")
    plot_repo = PlotRepository(db)
    return plot_repo.create(
        farm_id=farm_id,
        name=plot_in.name,
        crop_type=plot_in.crop_type,
        area_hectares=plot_in.area_hectares,
    )

@router.get("/farms/{farm_id}/plots", response_model=List[PlotResponse], tags=["Plots"])
def list_plots(farm_id: int, db: Session = Depends(get_db)):
    farm_repo = FarmRepository(db)
    if not farm_repo.get_by_id(farm_id):
        raise HTTPException(status_code=404, detail="Farm not found")
    plot_repo = PlotRepository(db)
    return plot_repo.list_by_farm(farm_id)

# --- Field Observations (Physical Ground Truth) ---
@router.post("/plots/{plot_id}/observations", response_model=FieldObservationResponse, status_code=status.HTTP_201_CREATED, tags=["Observations"])
def create_observation(plot_id: int, obs_in: FieldObservationCreate, db: Session = Depends(get_db)):
    plot_repo = PlotRepository(db)
    if not plot_repo.get_by_id(plot_id):
        raise HTTPException(status_code=404, detail="Plot not found")
    repo = FieldObservationRepository(db)
    try:
        return repo.create(
            plot_id=plot_id,
            source=obs_in.source,
            data=obs_in.data,
            epistemic_type=obs_in.epistemic_type,
            notes=obs_in.notes,
        )
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))

# --- Digital Twin Scenarios (Simulation) ---
@router.post("/plots/{plot_id}/twin-scenarios", response_model=TwinScenarioResponse, status_code=status.HTTP_201_CREATED, tags=["Digital Twin"])
def create_twin_scenario(plot_id: int, scenario_in: TwinScenarioCreate, db: Session = Depends(get_db)):
    plot_repo = PlotRepository(db)
    if not plot_repo.get_by_id(plot_id):
        raise HTTPException(status_code=404, detail="Plot not found")
    repo = TwinScenarioRepository(db)
    return repo.create(
        plot_id=plot_id,
        scenario_name=scenario_in.scenario_name,
        simulation_engine=scenario_in.simulation_engine,
        parameters=scenario_in.parameters,
        simulation_results=scenario_in.simulation_results,
    )

# --- Crop Disease Prediction ---
@router.post("/predict/disease", response_model=DiseasePredictionResponse, tags=["Inference"])
async def predict_crop_disease(
    file: UploadFile = File(...),
    plot_id: Optional[int] = Query(None, description="Optional Plot ID for tracking history"),
    top_k: int = Query(3, ge=1, le=15),
    db: Session = Depends(get_db),
):
    # Validate content type
    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/bmp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content-type '{file.content_type}'. Must be one of {allowed_types}",
        )

    # Read and validate payload size
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum upload limit of {settings.MAX_UPLOAD_BYTES} bytes",
        )

    # Execute inference
    try:
        result = disease_service.predict(content, top_k=top_k)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Inference error: {exc}")

    # Persist prediction record in DB provenance log
    pred_repo = PredictionRepository(db)
    record = pred_repo.create(
        plot_id=plot_id,
        task="crop_disease_classification",
        model_name=result["model_architecture"],
        model_version=result["model_version"],
        primary_prediction=result["primary_prediction"]["class_name"],
        confidence=result["primary_prediction"]["confidence"],
        top_k_predictions=result["top_k_predictions"],
        inference_time_ms=result["inference_time_ms"],
        image_filename=file.filename,
    )

    return DiseasePredictionResponse(
        filename=file.filename or "unknown.jpg",
        primary_prediction=result["primary_prediction"],
        top_k_predictions=result["top_k_predictions"],
        model_version=result["model_version"],
        model_architecture=result["model_architecture"],
        epistemic_type="predicted",
        inference_device=result["inference_device"],
        inference_time_ms=result["inference_time_ms"],
        record_id=record.id,
    )

# --- Agronomy & Crop-Irrigation Advisory ---
@router.post("/recommend/crop-irrigation", response_model=CropIrrigationAdvisoryResponse, tags=["Agronomy Advisory"])
def recommend_crop_and_irrigation(
    req: CropIrrigationAdvisoryRequest,
    db: Session = Depends(get_db),
):
    """
    Evaluates crop suitability ranking and produces prescriptive irrigation
    and fertilizer recommendations with explicit epistemic_type="recommended".
    """
    suitability_res = recommend_crops(
        soil_ph=req.soil_ph,
        temperature_c=req.temperature_c,
        soil_moisture_pct=req.soil_moisture_pct,
    )

    irrigation_res = recommend_irrigation_and_fertilizer(
        crop_type=req.crop_type,
        soil_moisture_pct=req.soil_moisture_pct,
        temperature_c=req.temperature_c,
        precipitation_mm=req.precipitation_mm,
        soil_ph=req.soil_ph,
    )

    record_id = None
    if req.plot_id is not None:
        pred_repo = PredictionRepository(db)
        record = pred_repo.create(
            plot_id=req.plot_id,
            task="crop_and_irrigation_advisory",
            model_name="agronomy_rule_engine_v1",
            model_version="1.0.0",
            primary_prediction=suitability_res["ranked_crops"][0]["crop_type"],
            confidence=suitability_res["ranked_crops"][0]["suitability_score"],
            top_k_predictions=[
                {"crop": c["crop_type"], "score": c["suitability_score"]}
                for c in suitability_res["ranked_crops"][:3]
            ],
        )
        record_id = record.id

    return CropIrrigationAdvisoryResponse(
        epistemic_type="recommended",
        crop_type=req.crop_type,
        crop_suitability_ranking=suitability_res["ranked_crops"],
        irrigation_recommendation=irrigation_res["irrigation_recommendation"],
        fertilizer_recommendation=irrigation_res["fertilizer_recommendation"],
        assumptions=suitability_res["assumptions"] + irrigation_res["assumptions"],
        limitations=f"{suitability_res['limitations']} {irrigation_res['limitations']}",
        record_id=record_id,
    )

# --- Tabular Crop Yield Prediction ---
@router.post("/predict/yield", response_model=YieldPredictionResponse, tags=["Yield Prediction"])
def predict_crop_yield_endpoint(
    req: YieldPredictionRequest,
    db: Session = Depends(get_db),
):
    """
    Predicts expected crop yield (kg/ha and total kg) using the trained Ridge
    yield baseline with epistemic_type="predicted".
    Gracefully falls back to baseline agronomic heuristics if artifact is missing.
    """
    model_bundle = Path("models/stage6/yield_baseline.joblib")
    features_dict = {
        "crop_type": req.crop_type,
        "harvest_year": req.harvest_year,
        "area_hectares": req.area_hectares,
        "ph": req.ph or 6.2,
        "moisture_pct": req.moisture_pct or 28.0,
        "nitrogen_mg_kg": req.nitrogen_mg_kg or 40.0,
        "organic_matter_pct": req.organic_matter_pct or 2.5,
    }

    model_name = "ridge_regression_baseline"
    if model_bundle.exists():
        from pipelines.models.yield_baseline import predict_yield
        try:
            pred_kg_ha = predict_yield(features_dict, model_bundle_path=model_bundle)
        except Exception:
            # Fallback baseline
            base_yields = {"Tomato": 21000.0, "Potato": 16000.0, "Pepper": 9500.0}
            pred_kg_ha = base_yields.get(req.crop_type, 15000.0)
            model_name = "agronomic_heuristic_fallback"
    else:
        base_yields = {"Tomato": 21000.0, "Potato": 16000.0, "Pepper": 9500.0}
        pred_kg_ha = base_yields.get(req.crop_type, 15000.0)
        model_name = "agronomic_heuristic_fallback"

    total_kg = round(pred_kg_ha * req.area_hectares, 2)

    record_id = None
    if req.plot_id is not None:
        pred_repo = PredictionRepository(db)
        record = pred_repo.create(
            plot_id=req.plot_id,
            task="crop_yield_prediction",
            model_name=model_name,
            model_version="1.0.0",
            primary_prediction=f"{pred_kg_ha} kg/ha",
            confidence=0.90,
            top_k_predictions=[{"crop": req.crop_type, "yield_kg_per_ha": pred_kg_ha}],
        )
        record_id = record.id

    return YieldPredictionResponse(
        crop_type=req.crop_type,
        predicted_yield_kg_per_ha=pred_kg_ha,
        total_projected_yield_kg=total_kg,
        area_hectares=req.area_hectares,
        harvest_year=req.harvest_year,
        model_name=model_name,
        epistemic_type="predicted",
        record_id=record_id,
    )


# ---------------------------------------------------------------------------
# --- Digital Twin Simulation Endpoint ---
# ---------------------------------------------------------------------------

@router.post(
    "/twin/simulate",
    response_model=TwinSimulationResponse,
    tags=["Digital Twin"],
    summary="Run a Digital Twin scenario simulation for a crop plot",
    description=(
        "Applies named or custom agronomic adjustment scenarios (temperature, rainfall, "
        "irrigation, fertilizer, disease pressure) to a baseline yield and returns a "
        "structured simulation result with epistemic_type='simulated'. "
        "If plot_id is provided, the result is persisted and 404 is returned for invalid plot IDs."
    ),
)
def simulate_twin_scenario(
    req: TwinSimulationRequest,
    db: Session = Depends(get_db),
):
    # --- Optional: validate plot exists before expensive simulation ---
    record_id = None
    if req.plot_id is not None:
        plot_repo = PlotRepository(db)
        plot = plot_repo.get_by_id(req.plot_id)
        if plot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plot with id={req.plot_id} not found.",
            )

    # --- Run simulation ---
    adjustments = {
        "temperature_delta_c": req.temperature_delta_c,
        "rainfall_multiplier": req.rainfall_multiplier,
        "irrigation_mm": req.irrigation_mm,
        "fertilizer_kg_ha": req.fertilizer_kg_ha,
        "disease_pressure": req.disease_pressure,
    }
    result = simulate_plot_scenario(
        plot_id=req.plot_id,
        crop_type=req.crop_type,
        baseline_yield_kg_ha=req.baseline_yield_kg_ha,
        scenario=req.scenario,
        adjustments=adjustments,
    )

    # --- Persist to twin_scenarios table if plot_id provided ---
    if req.plot_id is not None:
        twin_repo = TwinScenarioRepository(db)
        parameters = {
            "temperature_delta_c": req.temperature_delta_c,
            "rainfall_multiplier": req.rainfall_multiplier,
            "irrigation_mm": req.irrigation_mm,
            "fertilizer_kg_ha": req.fertilizer_kg_ha,
            "disease_pressure": req.disease_pressure,
            "crop_type": req.crop_type,
            "baseline_yield_kg_ha": req.baseline_yield_kg_ha,
        }
        simulation_results = {
            "simulated_yield_kg_ha": result["simulated_yield_kg_ha"],
            "yield_change_pct": result["yield_change_pct"],
            "combined_yield_factor": result.get("combined_yield_factor"),
            "factor_breakdown": result.get("factor_breakdown"),
            "key_drivers": result["key_drivers"],
        }
        record = twin_repo.create(
            plot_id=req.plot_id,
            scenario_name=req.scenario,
            simulation_engine="twin_service_v1",
            parameters=parameters,
            simulation_results=simulation_results,
        )
        record_id = record.id

    return TwinSimulationResponse(
        epistemic_type=result["epistemic_type"],
        crop_type=result["crop_type"],
        scenario=result["scenario"],
        baseline_yield_kg_ha=result["baseline_yield_kg_ha"],
        simulated_yield_kg_ha=result["simulated_yield_kg_ha"],
        yield_change_pct=result["yield_change_pct"],
        combined_yield_factor=result.get("combined_yield_factor"),
        factor_breakdown=result.get("factor_breakdown"),
        key_drivers=result["key_drivers"],
        assumptions=result["assumptions"],
        limitations=result["limitations"],
        record_id=record_id,
    )


# ---------------------------------------------------------------------------
# --- Advanced Intelligence & Risk Assessment Endpoint ---
# ---------------------------------------------------------------------------

@router.post(
    "/intelligence/assess",
    response_model=IntelligenceAssessmentResponse,
    tags=["Intelligence"],
    summary="Assess multimodal disease outbreak risk and get tool-grounded assistant guidance",
    description=(
        "Evaluates microclimate and visual anomaly indicators to quantify pathogen outbreak risk. "
        "Optionally routes natural language queries to platform tools deterministically. "
        "Returns epistemic_type='predicted' with explicit caveats. Persists if plot_id provided."
    ),
)
def assess_intelligence_risk(
    req: IntelligenceAssessmentRequest,
    db: Session = Depends(get_db),
):
    record_id = None
    if req.plot_id is not None:
        plot_repo = PlotRepository(db)
        plot = plot_repo.get_by_id(req.plot_id)
        if plot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plot with id={req.plot_id} not found.",
            )

    # 1. Assess outbreak risk
    risk_res = assess_outbreak_and_multimodal_risk(
        crop_type=req.crop_type,
        temperature_c=req.temperature_c,
        relative_humidity_pct=req.relative_humidity_pct,
        rainfall_mm=req.rainfall_mm,
        visual_anomaly_score=req.visual_anomaly_score,
    )

    # 2. Optional tool-grounded assistant routing
    assistant_res = None
    if req.query:
        ctx = {
            "crop_type": req.crop_type,
            "temperature_c": req.temperature_c,
            "relative_humidity_pct": req.relative_humidity_pct,
            "rainfall_mm": req.rainfall_mm,
            "visual_anomaly_score": req.visual_anomaly_score,
        }
        assistant_res = answer_farming_assistant_query(query=req.query, context=ctx)

    # 3. Provenance tracking via prediction repo
    if req.plot_id is not None:
        pred_repo = PredictionRepository(db)
        record = pred_repo.create(
            plot_id=req.plot_id,
            task="disease_outbreak_risk_assessment",
            model_name="environmental_outbreak_evaluator",
            model_version="1.0.0",
            primary_prediction=f"{risk_res['risk_level']} (score: {risk_res['risk_score']})",
            confidence=round(float(risk_res["risk_score"]), 2),
            top_k_predictions=[{"threat": t} for t in risk_res["primary_threats"][:3]],
        )
        record_id = record.id

    return IntelligenceAssessmentResponse(
        epistemic_type="predicted",
        crop_type=req.crop_type,
        risk_assessment=risk_res,
        assistant_response=assistant_res,
        limitations=risk_res["caveats"],
        record_id=record_id,
    )


# ---------------------------------------------------------------------------
# --- Farm-Scoped Observations & Unified History ---
# ---------------------------------------------------------------------------

def _require_plot_in_farm(db: Session, farm_id: int, plot_id: int):
    if not FarmRepository(db).get_by_id(farm_id):
        raise HTTPException(status_code=404, detail="Farm not found")
    plot = PlotRepository(db).get_by_id(plot_id)
    if not plot or plot.farm_id != farm_id:
        raise HTTPException(status_code=404, detail="Plot not found in this farm")
    return plot


@router.post(
    "/farms/{farm_id}/plots/{plot_id}/observations",
    response_model=FieldObservationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Observations"],
)
def create_farm_plot_observation(
    farm_id: int,
    plot_id: int,
    obs_in: FieldObservationCreate,
    db: Session = Depends(get_db),
):
    _require_plot_in_farm(db, farm_id, plot_id)
    try:
        return FieldObservationRepository(db).create(
            plot_id=plot_id,
            source=obs_in.source,
            data=obs_in.data,
            epistemic_type=obs_in.epistemic_type,
            notes=obs_in.notes,
        )
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))


@router.get(
    "/farms/{farm_id}/plots/{plot_id}/observations",
    response_model=List[FieldObservationResponse],
    tags=["Observations"],
)
def list_farm_plot_observations(farm_id: int, plot_id: int, db: Session = Depends(get_db)):
    _require_plot_in_farm(db, farm_id, plot_id)
    return FieldObservationRepository(db).list_by_plot(plot_id)


@router.get("/history", response_model=HistoryResponse, tags=["History"])
def get_history(
    limit: int = Query(20, ge=1, le=200),
    module_name: Optional[str] = Query(
        None,
        description="Filter by prediction task (e.g. 'crop_yield_prediction') or twin simulation engine (e.g. 'twin_service_v1')",
    ),
    db: Session = Depends(get_db),
):
    """Recent prediction_records (predicted) and twin_scenarios (simulated), newest first."""
    items: List[HistoryItem] = []
    for p in list_recent_predictions(db, limit=limit, module_name=module_name):
        items.append(HistoryItem(
            record_type="prediction",
            id=p.id,
            plot_id=p.plot_id,
            epistemic_type=p.epistemic_type,
            module_name=p.task,
            model_version=p.model_version,
            timestamp=p.created_at,
            summary=f"{p.model_name}: {p.primary_prediction} (confidence {p.confidence:.2f})",
        ))
    for t in list_recent_twin_scenarios(db, limit=limit, module_name=module_name):
        items.append(HistoryItem(
            record_type="twin_scenario",
            id=t.id,
            plot_id=t.plot_id,
            epistemic_type=t.epistemic_type,
            module_name=t.simulation_engine,
            model_version=None,
            timestamp=t.simulated_at,
            summary=f"Scenario '{t.scenario_name}'",
        ))
    items.sort(key=lambda i: i.timestamp, reverse=True)
    items = items[:limit]
    return HistoryResponse(count=len(items), limit=limit, module_name=module_name, items=items)


# ---------------------------------------------------------------------------
# --- MLOps Drift & Confidence Monitoring Endpoint ---
# ---------------------------------------------------------------------------

@router.get("/monitoring/status", response_model=MonitoringStatusResponse, tags=["Monitoring"])
def get_monitoring_status(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Evaluates recent persisted prediction confidences against a reference baseline
    using pipelines.monitoring.drift_monitor without fabricating any metrics.
    """
    from pipelines.monitoring.drift_monitor import compute_confidence_drift

    recent = list_recent_predictions(db, limit=limit)
    confidences = [float(r.confidence) for r in recent if r.confidence is not None]
    report = compute_confidence_drift(confidences, ref_mean_conf=0.85)

    return MonitoringStatusResponse(
        status=report["status"],
        epistemic_type="observed",
        sample_count=report["sample_count"],
        mean_confidence=report["mean_confidence"],
        min_confidence=report["min_confidence"],
        reference_baseline_confidence=report["reference_baseline_confidence"],
        drop_from_baseline=report["drop_from_baseline"],
        note=report["note"],
        limitations=(
            "Evaluates persisted prediction confidence scores only. Does not measure ground-truth "
            "accuracy without labeled field outcomes."
        ),
    )
