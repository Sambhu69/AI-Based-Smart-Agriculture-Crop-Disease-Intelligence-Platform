from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.routes import router as v1_router

def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.MODEL_VERSION,
        description="Smart Agriculture Platform - Modular Monolith Backend with Provenance-aware Disease Inference",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(v1_router, prefix="/api/v1")

    @application.get("/", include_in_schema=False)
    def root():
        return {
            "platform": settings.APP_NAME,
            "version": settings.MODEL_VERSION,
            "docs": "/docs",
            "v1_health": "/api/v1/health",
        }

    return application

app = create_app()
