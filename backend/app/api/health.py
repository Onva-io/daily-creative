"""Health check routes."""

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.settings import get_settings
from app.db.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict[str, str]:
    """Liveness probe — process can respond."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(response: Response) -> dict[str, object]:
    """Readiness probe — required config and database connectivity."""
    settings = get_settings()
    checks: dict[str, str] = {}

    if not settings.database_url:
        checks["database"] = "missing_config"
    else:
        try:
            async with SessionLocal() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:  # readiness must not raise for probe endpoints
            checks["database"] = "unavailable"

    if not settings.storage_bucket:
        checks["storage_config"] = "missing_config"
    else:
        checks["storage_config"] = "ok"

    healthy = all(value == "ok" for value in checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {"status": "ok" if healthy else "unavailable", "checks": checks}
