"""Daily Sketch FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Daily Sketch API",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )
    application.include_router(health_router)
    return application


app = create_app()
