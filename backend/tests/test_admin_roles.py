"""Admin role dual-path moderation auth."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.jwt import set_token_verifier
from app.core.clock import Clock, get_clock
from app.core.settings import Settings, get_settings
from app.db.session import Base, get_db_session
from app.main import create_app
from app.models.daily_prompt import DailyPrompt  # noqa: F401
from app.models.idempotency_key import IdempotencyKey  # noqa: F401
from app.models.moderation_action import ModerationAction  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.sketch_session import SketchSession  # noqa: F401
from app.models.sketch_session_event import SketchSessionEvent  # noqa: F401
from app.models.creative_publication import CreativePublication  # noqa: F401
from app.models.upload import Upload  # noqa: F401
from app.models.user import User, UserStatus  # noqa: F401
from app.models.user_block import UserBlock  # noqa: F401
from app.models.user_preferences import UserPreferences  # noqa: F401
from app.storage.base import get_storage_adapter
from fake_storage import InMemoryStorageAdapter
from jwt_helpers import StaticTokenVerifier, generate_rsa_keypair, mint_token
from test_uploads_submissions import FixedClock, _complete_profile

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dailycreative:dailycreative@localhost:5432/dailycreative",  # pragma: allowlist secret
)

OPERATOR_TOKEN = "test-operator-token"

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
    clock = FixedClock(datetime(2026, 7, 19, 12, 0, tzinfo=UTC))
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    fake_storage = InMemoryStorageAdapter()
    settings = get_settings().model_copy(update={"moderation_operator_token": OPERATOR_TOKEN})

    app = create_app()
    app.state.token_verifier = verifier
    app.state.test_private_key = private_key

    async def override_db() -> AsyncGenerator[AsyncSession]:
        async with session_factory() as session:
            yield session

    def override_clock() -> Clock:
        return clock

    def override_storage() -> InMemoryStorageAdapter:
        return fake_storage

    def override_settings() -> Settings:
        return settings

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_clock] = override_clock
    app.dependency_overrides[get_storage_adapter] = override_storage
    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        http_client.app = app  # type: ignore[attr-defined]
        http_client.clock = clock  # type: ignore[attr-defined]
        http_client.session_factory = session_factory  # type: ignore[attr-defined]
        http_client.storage = fake_storage  # type: ignore[attr-defined]
        yield http_client

    app.dependency_overrides.clear()
    set_token_verifier(None)


def _auth_headers(
    client: AsyncClient,
    *,
    subject: str | None = None,
    roles: list[str] | None = None,
) -> dict[str, str]:
    private_key = client.app.state.test_private_key  # type: ignore[attr-defined]
    token = mint_token(
        private_key,
        subject=subject or f"descope|{uuid.uuid4()}",
        roles=roles,
    )
    return {"Authorization": f"Bearer {token}"}


def _operator_headers() -> dict[str, str]:
    return {"X-Moderation-Token": OPERATOR_TOKEN}


@requires_postgres
@pytest.mark.asyncio
async def test_admin_jwt_can_list_reports(client: AsyncClient) -> None:
    admin_headers = _auth_headers(client, subject="descope|admin", roles=["admin"])
    admin = await _complete_profile(client, admin_headers, username="mod_admin")

    response = await client.get("/internal/moderation/reports", headers=admin_headers)
    assert response.status_code == 200
    assert "items" in response.json()

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == uuid.UUID(admin["id"])))
        ).scalar_one()
        assert user.status == UserStatus.active


@requires_postgres
@pytest.mark.asyncio
async def test_non_admin_jwt_without_token_forbidden(client: AsyncClient) -> None:
    headers = _auth_headers(client, subject="descope|member", roles=[])
    await _complete_profile(client, headers, username="mod_member")

    response = await client.get("/internal/moderation/reports", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "moderation_forbidden"


@requires_postgres
@pytest.mark.asyncio
async def test_non_admin_jwt_with_operator_token_allowed(client: AsyncClient) -> None:
    headers = {
        **_auth_headers(client, subject="descope|member2", roles=[]),
        **_operator_headers(),
    }
    await _complete_profile(
        client,
        _auth_headers(client, subject="descope|member2", roles=[]),
        username="mod_member2",
    )

    response = await client.get("/internal/moderation/reports", headers=headers)
    assert response.status_code == 200


@requires_postgres
@pytest.mark.asyncio
async def test_shared_token_still_works(client: AsyncClient) -> None:
    response = await client.get("/internal/moderation/reports", headers=_operator_headers())
    assert response.status_code == 200


@requires_postgres
@pytest.mark.asyncio
async def test_admin_action_audits_user_identity(client: AsyncClient) -> None:
    from test_moderation_phase11 import _publish

    admin_headers = _auth_headers(client, subject="descope|admin_audit", roles=["admin"])
    author_headers = _auth_headers(client, subject="descope|author_audit")
    admin = await _complete_profile(client, admin_headers, username="admin_audit")
    await _complete_profile(client, author_headers, username="author_audit")
    submission = await _publish(client, author_headers)

    hide = await client.post(
        f"/internal/moderation/submissions/{submission['id']}/hide",
        headers=admin_headers,
        json={"reason": "admin hide"},
    )
    assert hide.status_code == 200

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        actions = (await session.execute(select(ModerationAction))).scalars().all()
        assert any(action.operator_identity == f"user:{admin['id']}" for action in actions)


@requires_postgres
@pytest.mark.asyncio
async def test_suspended_admin_forbidden(client: AsyncClient) -> None:
    admin_headers = _auth_headers(client, subject="descope|suspended_admin", roles=["admin"])
    admin = await _complete_profile(client, admin_headers, username="susp_admin")

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == uuid.UUID(admin["id"])))
        ).scalar_one()
        user.status = UserStatus.suspended
        await session.commit()

    response = await client.get("/internal/moderation/reports", headers=admin_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_suspended"
