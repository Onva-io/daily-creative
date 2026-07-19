"""Integration and contract tests for profile completion and preferences."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from jwt_helpers import StaticTokenVerifier, generate_rsa_keypair, mint_token
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.jwt import set_token_verifier
from app.db.session import Base, get_db_session
from app.main import create_app
from app.models.user import User, UserStatus
from app.models.user_preferences import UserPreferences  # noqa: F401

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dailysketch:dailysketch@localhost:5432/dailysketch",  # pragma: allowlist secret
)

requires_postgres = pytest.mark.skipif(
    os.environ.get("SKIP_POSTGRES_TESTS") == "1",
    reason="SKIP_POSTGRES_TESTS=1",
)


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

    app = create_app()
    app.state.token_verifier = verifier
    app.state.test_private_key = private_key

    async def override_db() -> AsyncGenerator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        http_client.app = app  # type: ignore[attr-defined]
        yield http_client

    app.dependency_overrides.clear()
    set_token_verifier(None)


def _auth_header(
    client: AsyncClient, *, subject: str | None = None, name: str = "Sketchy"
) -> dict[str, str]:
    private_key = client.app.state.test_private_key  # type: ignore[attr-defined]
    token = mint_token(private_key, subject=subject or f"descope|{uuid.uuid4()}", name=name)
    return {"Authorization": f"Bearer {token}"}


@requires_postgres
@pytest.mark.asyncio
async def test_patch_me_completes_profile(client: AsyncClient) -> None:
    headers = _auth_header(client, name="Matt")
    created = await client.get("/api/v1/me", headers=headers)
    assert created.status_code == 200
    assert created.json()["profile_completed"] is False
    assert created.json()["preferences"]["appearance"] == "system"

    response = await client.patch(
        "/api/v1/me",
        headers=headers,
        json={"username": "sketchy_matt", "display_name": "Matt", "bio": "Hello"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "sketchy_matt"
    assert body["display_name"] == "Matt"
    assert body["profile_completed"] is True
    assert body["status"] == "active"
    assert body["preferences"]["timezone"] == "UTC"


@requires_postgres
@pytest.mark.asyncio
async def test_duplicate_username_rejected(client: AsyncClient) -> None:
    first_headers = _auth_header(client, subject=f"descope|{uuid.uuid4()}")
    second_headers = _auth_header(client, subject=f"descope|{uuid.uuid4()}")

    first = await client.patch(
        "/api/v1/me",
        headers=first_headers,
        json={"username": "taken_name", "display_name": "One"},
    )
    assert first.status_code == 200

    duplicate = await client.patch(
        "/api/v1/me",
        headers=second_headers,
        json={"username": "Taken_Name", "display_name": "Two"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "username_taken"


@requires_postgres
@pytest.mark.asyncio
async def test_reserved_and_invalid_username(client: AsyncClient) -> None:
    headers = _auth_header(client)
    reserved = await client.patch(
        "/api/v1/me",
        headers=headers,
        json={"username": "admin", "display_name": "Admin"},
    )
    assert reserved.status_code == 422
    assert reserved.json()["error"]["code"] == "username_reserved"

    invalid = await client.patch(
        "/api/v1/me",
        headers=headers,
        json={"username": "bad-name!", "display_name": "Bad"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "username_invalid"


@requires_postgres
@pytest.mark.asyncio
async def test_preferences_persist(client: AsyncClient) -> None:
    headers = _auth_header(client)
    await client.get("/api/v1/me", headers=headers)

    updated = await client.patch(
        "/api/v1/me/preferences",
        headers=headers,
        json={
            "notifications_enabled": True,
            "notification_time_local": "09:00:00",
            "remember_timer_option": True,
            "remembered_timer_mode": "countdown",
            "remembered_timer_seconds": 300,
            "appearance": "dark",
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["notifications_enabled"] is True
    assert body["notification_time_local"] == "09:00:00"
    assert body["remember_timer_option"] is True
    assert body["remembered_timer_mode"] == "countdown"
    assert body["remembered_timer_seconds"] == 300
    assert body["appearance"] == "dark"

    fetched = await client.get("/api/v1/me/preferences", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == body

    me = await client.get("/api/v1/me", headers=headers)
    assert me.json()["preferences"]["appearance"] == "dark"


@requires_postgres
@pytest.mark.asyncio
async def test_invalid_timer_preference_rejected(client: AsyncClient) -> None:
    headers = _auth_header(client)
    await client.get("/api/v1/me", headers=headers)
    response = await client.patch(
        "/api/v1/me/preferences",
        headers=headers,
        json={
            "remembered_timer_mode": "countdown",
            "remembered_timer_seconds": 90,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_timer_preference"


@requires_postgres
@pytest.mark.asyncio
async def test_public_profile_safe_fields_only(client: AsyncClient) -> None:
    headers = _auth_header(client, name="Matt")
    await client.patch(
        "/api/v1/me",
        headers=headers,
        json={"username": "public_matt", "display_name": "Matt", "bio": "Public bio"},
    )

    response = await client.get("/api/v1/users/Public_Matt")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "public_matt"
    assert body["display_name"] == "Matt"
    assert body["bio"] == "Public bio"
    assert body["avatar_url"] is None
    assert body["submission_count"] == 0
    assert body["current_streak"] == 0
    assert body["is_self"] is False
    assert "preferences" not in body
    assert "descope_subject" not in body
    assert "status" not in body
    assert "email" not in body

    owned = await client.get("/api/v1/users/Public_Matt", headers=headers)
    assert owned.status_code == 200
    assert owned.json()["is_self"] is True


@requires_postgres
@pytest.mark.asyncio
async def test_public_profile_hides_incomplete(client: AsyncClient) -> None:
    headers = _auth_header(client)
    me = await client.get("/api/v1/me", headers=headers)
    assert me.json()["profile_completed"] is False

    # Incomplete users have no public username.
    missing = await client.get("/api/v1/users/nobody_here")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "user_not_found"


@requires_postgres
@pytest.mark.asyncio
async def test_public_profile_hides_suspended(client: AsyncClient, db_engine) -> None:
    private_key = client.app.state.test_private_key  # type: ignore[attr-defined]
    subject = f"descope|{uuid.uuid4()}"
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            descope_subject=subject,
            username="suspended_user",
            username_normalized="suspended_user",
            display_name="Suspended",
            status=UserStatus.suspended,
            profile_completed_at=None,
        )
        # Mark completed timestamp without activating — still suspended.
        from datetime import datetime, timezone

        user.profile_completed_at = datetime.now(timezone.utc)
        session.add(user)
        await session.commit()

    response = await client.get("/api/v1/users/suspended_user")
    assert response.status_code == 404
    # Ensure auth still rejects suspended accounts.
    token = mint_token(private_key, subject=subject)
    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 403
