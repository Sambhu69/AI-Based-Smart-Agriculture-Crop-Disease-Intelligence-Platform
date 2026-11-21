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
)
from app.schemas.contracts import (
    FarmCreate,
    FarmResponse,
    PlotCreate,
    PlotResponse,
    FieldObservationCreate,
    FieldObservationResponse,
    TwinScenarioCreate,
    TwinScenarioResponse,
    DiseasePredictionResponse,
)
from app.services.disease_service import disease_service

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

@router.get("/farms/{farm_id}", response_model=FarmResponse, tags=["Farms"])
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
