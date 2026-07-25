"""Daily Creative FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import Response

from app.api.health import router as health_router
from app.api.moderation import router as moderation_router
from app.api.v1 import router as v1_router
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.core.request_limits import RequestSizeLimitMiddleware, RequestTimeoutMiddleware
from app.core.settings import get_settings
from app.observability.metrics import MetricsMiddleware, configure_observability, metrics_response
from app.storage.base import get_storage_adapter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_application: FastAPI) -> AsyncIterator[None]:
    storage = get_storage_adapter()
    try:
        await storage.ensure_bucket()
    except Exception:
        # Readiness will surface storage failures; do not block boot on create.
        logger.exception("Failed to ensure object-storage bucket exists")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    configure_observability(settings)

    application = FastAPI(
        title="Daily Creative API",
        version=settings.release_version,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=_lifespan,
    )

    application.add_middleware(MetricsMiddleware, settings=settings)
    application.add_middleware(RequestTimeoutMiddleware, settings=settings)
    application.add_middleware(RequestSizeLimitMiddleware, settings=settings)
    application.add_middleware(RateLimitMiddleware, settings=settings)
    application.add_middleware(RequestIDMiddleware, settings=settings)

    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(v1_router)
    application.include_router(moderation_router)

    if settings.metrics_enabled:

        @application.get("/metrics", include_in_schema=False)
        async def metrics() -> Response:
            return metrics_response()

    return application


app = create_app()
