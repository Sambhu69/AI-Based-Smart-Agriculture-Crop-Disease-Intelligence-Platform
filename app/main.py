import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1.routes import router as v1_router

logger = logging.getLogger("app")


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

    @application.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={"error": "validation_error", "detail": str(exc), "path": request.url.path},
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Full traceback goes to server logs only; never to the client.
        logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": "An unexpected error occurred.",
                "path": request.url.path,
            },
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
