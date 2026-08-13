"""Metrics scrape auth and route-label cardinality."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core import settings as settings_module
from app.main import create_app
from app.observability.metrics import _route_key


def test_metrics_route_key_collapses_unmatched_paths() -> None:
    assert _route_key({"method": "GET", "path": "/api/v1/users/alice"}) == "GET user"
    assert _route_key({"method": "GET", "path": "/nope/secret-uuid"}) == "GET unmatched"


@pytest.mark.asyncio
async def test_metrics_open_locally_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METRICS_ENABLED", "true")
    monkeypatch.delenv("METRICS_SCRAPE_TOKEN", raising=False)
    settings_module.get_settings.cache_clear()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
    settings_module.get_settings.cache_clear()
    assert response.status_code == 200
    assert "dailycreative_http_requests_total" in response.text


@pytest.mark.asyncio
async def test_metrics_requires_scrape_token_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_ENABLED", "true")
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", "scrape-secret-token")
    settings_module.get_settings.cache_clear()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.get("/metrics")
        allowed = await client.get(
            "/metrics",
            headers={"X-Metrics-Token": "scrape-secret-token"},
        )
    settings_module.get_settings.cache_clear()
    assert denied.status_code == 401
    assert allowed.status_code == 200
