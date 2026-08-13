"""Guest age-capability token unit and API tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.guest_age import (
    GUEST_AGE_ALGORITHM,
    mint_guest_age_token,
    verify_guest_age_token,
)
from app.auth.jwt import set_token_verifier
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.db.session import Base, get_db_session
from app.main import create_app
from jwt_helpers import StaticTokenVerifier, generate_rsa_keypair, mint_token

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dailycreative:dailycreative@localhost:5432/dailycreative",  # pragma: allowlist secret
)

requires_postgres = pytest.mark.skipif(
    os.environ.get("SKIP_POSTGRES_TESTS") == "1",
    reason="SKIP_POSTGRES_TESTS=1",
)


def _settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_guest_age_token_round_trip() -> None:
    settings = _settings()
    token, expires_at = mint_guest_age_token(settings, minimum_age=13)
    claims = verify_guest_age_token(token, settings)
    assert claims["typ"] == "guest_age"
    assert claims["min_age"] == 13
    assert expires_at > datetime.now(UTC)


def test_guest_age_token_rejects_wrong_secret() -> None:
    settings = _settings()
    token, _ = mint_guest_age_token(settings, minimum_age=13)
    other = Settings(
        _env_file=None,  # type: ignore[call-arg]
        GUEST_AGE_TOKEN_SECRET="a-different-guest-age-secret-value-32",  # pragma: allowlist secret
    )
    with pytest.raises(AppError) as exc_info:
        verify_guest_age_token(token, other)
    assert exc_info.value.code == "age_declaration_required"
    assert exc_info.value.details["reason"] == "invalid_token"


def test_guest_age_token_rejects_expired() -> None:
    settings = _settings()
    past = datetime.now(UTC) - timedelta(days=2)
    token = jwt.encode(
        {
            "sub": "guest",
            "typ": "guest_age",
            "min_age": 13,
            "iat": int(past.timestamp()),
            "exp": int((past + timedelta(hours=1)).timestamp()),
        },
        settings.guest_age_token_secret,
        algorithm=GUEST_AGE_ALGORITHM,
    )
    with pytest.raises(AppError) as exc_info:
        verify_guest_age_token(token, settings)
    assert exc_info.value.details["reason"] == "token_expired"


def test_staging_requires_unique_guest_age_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("DESCOPE_PROJECT_ID", "P123")
    monkeypatch.setenv("MODERATION_OPERATOR_TOKEN", "staging-token")
    monkeypatch.setenv("STORAGE_ACCESS_KEY", "remote-key")
    monkeypatch.setenv("STORAGE_SECRET_KEY", "remote-secret")
    monkeypatch.setenv("STORAGE_USE_SSL", "true")
    monkeypatch.setenv("STORAGE_ENDPOINT", "https://storage.example.com")
    monkeypatch.setenv("DB_SSL_REQUIRE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@db.example.com:5432/dailycreative",  # pragma: allowlist secret
    )
    monkeypatch.setenv("MODERATION_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")  # pragma: allowlist secret
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.fixture
async def db_engine():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"PostgreSQL unavailable: {exc}")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient]:
    private_key, _ = generate_rsa_keypair()
    verifier = StaticTokenVerifier(private_key)
    set_token_verifier(verifier)
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    settings = _settings()

    app = create_app()
    app.state.token_verifier = verifier
    app.state.test_private_key = private_key

    async def override_db() -> AsyncGenerator[AsyncSession]:
        async with session_factory() as session:
            yield session

    def override_settings() -> Settings:
        return settings

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        http_client.app = app  # type: ignore[attr-defined]
        yield http_client

    app.dependency_overrides.clear()
    set_token_verifier(None)


@requires_postgres
@pytest.mark.asyncio
async def test_prompt_stays_ungated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prompts/today")
    assert response.status_code in {200, 404}


@requires_postgres
@pytest.mark.asyncio
async def test_feed_requires_guest_age_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/feed/recent", params={"creative_type": "sketch"})
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "age_declaration_required"


@requires_postgres
@pytest.mark.asyncio
async def test_guest_declaration_issues_token_and_unlocks_feed(client: AsyncClient) -> None:
    declared = await client.post(
        "/api/v1/guest/age-declaration",
        json={"date_of_birth": "1990-01-15"},
    )
    assert declared.status_code == 200, declared.text
    payload = declared.json()
    assert payload["guest_age_token"]
    assert payload["minimum_age"] == 13

    feed = await client.get(
        "/api/v1/feed/recent",
        params={"creative_type": "sketch"},
        headers={"X-Guest-Age-Token": payload["guest_age_token"]},
    )
    assert feed.status_code == 200
    assert feed.json()["items"] == []


@requires_postgres
@pytest.mark.asyncio
async def test_guest_declaration_rejects_underage(client: AsyncClient) -> None:
    yesterday = datetime.now(UTC).date()
    declared = await client.post(
        "/api/v1/guest/age-declaration",
        json={"date_of_birth": yesterday.isoformat()},
    )
    assert declared.status_code == 403
    assert declared.json()["error"]["code"] == "under_minimum_age"


@requires_postgres
@pytest.mark.asyncio
async def test_authenticated_feed_skips_guest_token(client: AsyncClient) -> None:
    private_key = client.app.state.test_private_key  # type: ignore[attr-defined]
    token = mint_token(private_key, subject="descope|guest-age-auth")
    response = await client.get(
        "/api/v1/feed/recent",
        params={"creative_type": "sketch"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
