"""Standard error envelope tests."""

from collections.abc import AsyncGenerator

import pytest
from app.core.errors import AppError
from app.main import create_app
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    app = create_app()

    @app.get("/__test__/domain-error")
    async def domain_error() -> None:
        raise AppError(
            code="submission_not_found",
            message="The requested sketch could not be found.",
            status_code=404,
            details={"submission_id": "f7d7c950-2892-4b6c-9300-ef6c5cbcb2d1"},
        )

    @app.get("/__test__/unhandled")
    async def unhandled() -> None:
        raise RuntimeError("boom")

    # raise_app_exceptions=False so handled Exception responses are returned
    # instead of re-raised by the ASGI transport (httpx default).
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_app_error_returns_standard_envelope(client: AsyncClient) -> None:
    expected_request_id = "11111111-2222-3333-4444-555555555555"
    response = await client.get(
        "/__test__/domain-error",
        headers={"X-Request-ID": expected_request_id},
    )
    assert response.status_code == 404
    assert response.headers.get("X-Request-ID") == expected_request_id
    body = response.json()
    assert body == {
        "error": {
            "code": "submission_not_found",
            "message": "The requested sketch could not be found.",
            "details": {"submission_id": "f7d7c950-2892-4b6c-9300-ef6c5cbcb2d1"},
            "request_id": expected_request_id,
        }
    }


@pytest.mark.asyncio
async def test_unhandled_error_returns_safe_envelope(client: AsyncClient) -> None:
    expected_request_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    response = await client.get(
        "/__test__/unhandled",
        headers={"X-Request-ID": expected_request_id},
    )
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert body["error"]["request_id"] == expected_request_id
    assert "boom" not in response.text
    assert "RuntimeError" not in response.text
    assert response.headers.get("X-Request-ID") == expected_request_id


@pytest.mark.asyncio
async def test_http_not_found_uses_error_envelope() -> None:
    app: FastAPI = create_app()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "http_error"
    assert body["error"]["request_id"]
    assert response.headers.get("X-Request-ID") == body["error"]["request_id"]
