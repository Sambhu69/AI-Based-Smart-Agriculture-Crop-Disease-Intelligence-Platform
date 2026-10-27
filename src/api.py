"""
FastAPI Crop Disease Intelligence Inference API
===============================================
Module: src.api

Provides high-throughput RESTful endpoints for real-time crop disease
classification. Loads model weights once at startup, handles image
preprocessing identically to the training pipeline, and returns structured
disease diagnostics with softmax confidence scores and Top-k alternatives.

Endpoints:
  GET  /health        - Operational health check with model metadata
  GET  /classes       - List all supported disease/healthy class names
  POST /predict       - Upload a leaf image; receive ranked disease predictions
  GET  /              - Redirect to interactive API docs

Run from the project root with:
  python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
Or directly:
  python src/api.py
"""

import io
import sys
import time
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from torchvision import transforms

# -- Dynamic module resolution -------------------------------------------------
# Supports running both as `python src/api.py` and `python -m uvicorn src.api:app`
_SRC_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SRC_DIR.parent
for _path in (_SRC_DIR, _PROJECT_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

try:
    from model import get_crop_disease_model
except ImportError:
    from src.model import get_crop_disease_model  # type: ignore[no-redef]

# -- Logging -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api")

# -- Project-level path constants ----------------------------------------------
MODEL_PATH = _PROJECT_ROOT / "models" / "best_model.pth"
DATA_PATH = _PROJECT_ROOT / "data" / "processed" / "PlantVillage"

# -- Runtime limits ------------------------------------------------------------
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB hard ceiling
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
}

# -- Inference pre-processing transform ---------------------------------------
# Must match `val_transforms` in dataset.py exactly (224x224 + ImageNet stats)
INFERENCE_TRANSFORMS = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


# -- Application state (populated once at startup) ----------------------------
class _AppState:
    """Holds singleton model + metadata loaded during lifespan startup."""
    model: Optional[torch.nn.Module] = None
    class_names: List[str] = []
    device: torch.device = torch.device("cpu")
    checkpoint_meta: Dict = {}


_state = _AppState()


# ==============================================================================
# Pydantic Response Schemas
# ==============================================================================

class ClassPrediction(BaseModel):
    """Single disease/healthy classification candidate."""
    rank: int = Field(..., description="1-based rank (1 = top prediction)")
    class_name: str = Field(..., description="Disease or healthy class label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Softmax probability (0-1)")
    confidence_pct: str = Field(..., description="Human-readable percentage string")


class HealthResponse(BaseModel):
    status: str = Field(..., description="'healthy' | 'degraded'")
    model_loaded: bool
    device: str
    num_classes: int
    model_path: str
    checkpoint_epoch: Optional[int] = None
    best_val_loss: Optional[float] = None


class ClassesResponse(BaseModel):
    num_classes: int
    classes: List[str]


class PredictionResponse(BaseModel):
    filename: str
    primary_prediction: ClassPrediction
    top_k_predictions: List[ClassPrediction]
    inference_device: str
    inference_time_ms: float = Field(..., description="Wall-clock inference time in milliseconds")


# ==============================================================================
# Internal helpers
# ==============================================================================

def _discover_class_names() -> List[str]:
    """
    Discovers class names from the dataset folder structure (alphabetically sorted),
    matching the ordering produced by torchvision.datasets.ImageFolder.
    Falls back gracefully if DATA_PATH is unavailable.
    """
    if not DATA_PATH.exists():
        logger.warning(
            f"Dataset directory not found at {DATA_PATH}. "
            "Class names cannot be auto-discovered from disk."
        )
        return []
    classes = sorted([d.name for d in DATA_PATH.iterdir() if d.is_dir()])
    if not classes:
        raise ValueError(f"No class sub-folders found inside {DATA_PATH}.")
    return classes


def _load_model() -> Tuple[torch.nn.Module, List[str], Dict]:
    """
    Initialises the model architecture, loads the best checkpoint, sets
    eval mode, and returns (model, class_names, checkpoint_metadata).

    Supports both raw state-dicts and the structured checkpoint dict saved
    by train.py: {'epoch', 'model_state_dict', 'optimizer_state_dict', 'best_val_loss'}.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Inference device: {device}")
    if device.type == "cuda":
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")

    class_names = _discover_class_names()
    if not class_names:
        raise RuntimeError("Unable to determine class names. Aborting model load.")

    num_classes = len(class_names)
    logger.info(f"Initialising ResNet-50 for {num_classes} classes...")
    model = get_crop_disease_model(
        num_classes=num_classes,
        model_name="resnet50",
        pretrained=False,
        freeze_backbone=False,
    ).to(device)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Checkpoint not found at {MODEL_PATH}. "
            "Run training first (python -m src.train)."
        )

    logger.info(f"Loading weights from {MODEL_PATH} ...")
    checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=False)

    meta: Dict = {}
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
        meta["epoch"] = checkpoint.get("epoch")
        meta["best_val_loss"] = checkpoint.get("best_val_loss")
        best_val = f"{meta['best_val_loss']:.6f}" if meta['best_val_loss'] is not None else "N/A"
        logger.info(
            f"Checkpoint restored - epoch {meta['epoch']}, best val loss {best_val}"
        )
    elif isinstance(checkpoint, dict):
        # Raw state_dict with no wrapper keys
        model.load_state_dict(checkpoint)
        logger.info("Raw state_dict loaded.")
    else:
        raise TypeError(
            f"Unexpected checkpoint format: {type(checkpoint)}. "
            "Expected a dict or a raw state_dict."
        )

    model.eval()
    model._inference_device = device  # type: ignore[attr-defined]
    return model, class_names, meta


def _preprocess_image(raw_bytes: bytes) -> torch.Tensor:
    """
    Decodes raw image bytes -> RGB PIL Image -> normalised tensor [1, 3, 224, 224].
    Raises HTTPException with a user-facing message on any decode error.
    """
    try:
        image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
            detail="The uploaded file could not be decoded as an image. "
                   "Please upload a valid JPEG, PNG, WebP, or BMP file.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
            detail=f"Image decode error: {exc}",
        )
    return INFERENCE_TRANSFORMS(image).unsqueeze(0)  # [1, 3, 224, 224]


# ==============================================================================
# FastAPI lifespan
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs model loading once at server startup, storing the live model
    and metadata in module-level `_state`. On shutdown, clears GPU memory.
    """
    logger.info("=== Starting up Crop Disease Inference API ===")
    try:
        _state.model, _state.class_names, _state.checkpoint_meta = _load_model()
        _state.device = getattr(_state.model, "_inference_device", torch.device("cpu"))
        logger.info(
            f"Model ready - {len(_state.class_names)} classes on {_state.device}"
        )
    except Exception as exc:
        logger.critical(f"FATAL: Model failed to load on startup: {exc}", exc_info=True)
        # Allow server to start but report 'degraded' status via /health
    yield
    # Shutdown cleanup
    logger.info("Shutting down API - releasing model resources...")
    if _state.model is not None:
        del _state.model
        _state.model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    logger.info("=== API shutdown complete ===")


# ==============================================================================
# FastAPI application
# ==============================================================================

app = FastAPI(
    title="Smart Agriculture - Crop Disease Intelligence API",
    description=(
        "Real-time crop disease classification service powered by PyTorch & ResNet-50. "
        "Upload a photograph of a crop leaf and receive ranked disease diagnoses with "
        "softmax confidence scores and top-k alternatives.\n\n"
        "Supported crops: Pepper, Potato, Tomato\n"
        "Model: ResNet-50 fine-tuned on PlantVillage (98.98% test accuracy)\n"
    ),
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Timing middleware: injects X-Request-Time-Ms into every response
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    response.headers["X-Request-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


# ==============================================================================
# Endpoints
# ==============================================================================

@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect bare root requests to the Swagger UI."""
    return RedirectResponse(url="/docs")


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="API health check",
)
async def health_check():
    """
    Returns the current operational status of the inference API, including
    whether the model loaded successfully, which device is active, and
    checkpoint provenance metadata.
    """
    is_ready = _state.model is not None and bool(_state.class_names)
    meta = _state.checkpoint_meta
    return HealthResponse(
        status="healthy" if is_ready else "degraded",
        model_loaded=is_ready,
        device=str(_state.device),
        num_classes=len(_state.class_names),
        model_path=str(MODEL_PATH),
        checkpoint_epoch=meta.get("epoch"),
        best_val_loss=round(meta["best_val_loss"], 6)
        if meta.get("best_val_loss") is not None
        else None,
    )


@app.get(
    "/classes",
    response_model=ClassesResponse,
    tags=["Model Info"],
    summary="List all supported disease classes",
)
async def list_classes():
    """
    Returns the ordered list of all disease / healthy categories that
    the model can predict.
    """
    if not _state.class_names:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Class labels are unavailable - model may have failed to load.",
        )
    return ClassesResponse(
        num_classes=len(_state.class_names),
        classes=_state.class_names,
    )


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["Inference"],
    summary="Classify a crop leaf image",
    responses={
        200: {"description": "Successful disease classification"},
        400: {"description": "Invalid file type or oversized upload"},
        422: {"description": "Image could not be decoded"},
        503: {"description": "Model not ready"},
    },
)
async def predict_crop_disease(
    file: UploadFile = File(
        ...,
        description="JPEG / PNG / WebP / BMP photograph of a single crop leaf. Max 10 MB.",
    ),
    top_k: int = Query(
        default=3,
        ge=1,
        le=10,
        description="Number of top-ranked predictions to return (1-10).",
    ),
):
    """
    Accepts an uploaded crop leaf image and returns:
    - primary_prediction: top-1 disease or healthy classification
    - top_k_predictions: ranked list of up to top_k candidates
    - inference_time_ms: pure model forward-pass time in milliseconds
    """
    # Guard: model must be loaded
    if _state.model is None or not _state.class_names:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inference engine not ready. The model failed to load at startup.",
        )

    # Validate MIME type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type: '{file.content_type}'. "
                f"Accepted types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}."
            ),
        )

    # Read & validate file size
    if hasattr(file, "file") and hasattr(file.file, "read"):
        raw_bytes = file.file.read()
    else:
        raw_bytes = await file.read()
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Uploaded file is {len(raw_bytes) / 1_048_576:.1f} MB, "
                f"which exceeds the {MAX_UPLOAD_BYTES // 1_048_576} MB limit."
            ),
        )
    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Image decoding & preprocessing
    input_tensor = _preprocess_image(raw_bytes)
    input_tensor = input_tensor.to(_state.device, non_blocking=True)

    # Forward pass
    try:
        t_start = time.perf_counter()
        with torch.inference_mode():
            logits = _state.model(input_tensor)          # [1, num_classes]
            probabilities = F.softmax(logits, dim=1)[0]  # [num_classes]
        if _state.device.type == "cuda":
            torch.cuda.synchronize()
        inference_ms = (time.perf_counter() - t_start) * 1000.0
    except Exception as exc:
        logger.error(f"Forward pass failed for '{file.filename}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model inference failed: {exc}",
        )

    # Top-k extraction
    effective_k = min(top_k, len(_state.class_names))
    top_probs, top_indices = torch.topk(probabilities, k=effective_k)

    predictions: List[ClassPrediction] = [
        ClassPrediction(
            rank=rank,
            class_name=_state.class_names[idx.item()],
            confidence=round(float(prob.item()), 6),
            confidence_pct=f"{float(prob.item()) * 100:.2f}%",
        )
        for rank, (prob, idx) in enumerate(zip(top_probs, top_indices), start=1)
    ]

    logger.info(
        f"Predicted '{predictions[0].class_name}' ({predictions[0].confidence_pct}) "
        f"for '{file.filename}' in {inference_ms:.1f} ms"
    )

    return PredictionResponse(
        filename=file.filename or "unknown",
        primary_prediction=predictions[0],
        top_k_predictions=predictions,
        inference_device=str(_state.device),
        inference_time_ms=round(inference_ms, 2),
    )


# ==============================================================================
# Global exception handler
# ==============================================================================

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred. Please try again."},
    )


# Development entry point
if __name__ == "__main__":
    import uvicorn
    # If run as `python src/api.py`, current module is `api` or `src.api`
    uvicorn.run(
        "src.api:app" if str(_PROJECT_ROOT) in sys.path else "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
