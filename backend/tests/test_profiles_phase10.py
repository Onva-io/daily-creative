"""Phase 10 public profile, streak, submissions, and avatar tests."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from httpx import ASGITransport, AsyncClient
from jsonschema import Draft202012Validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.jwt import set_token_verifier
from app.core.clock import Clock, get_clock
from app.core.settings import Settings, get_settings
from app.db.session import Base, get_db_session
from app.main import create_app
from app.models.daily_prompt import DailyPrompt  # noqa: F401
from app.models.idempotency_key import IdempotencyKey  # noqa: F401
from app.models.sketch_session import SketchSession  # noqa: F401
from app.models.sketch_session_event import SketchSessionEvent  # noqa: F401
from app.models.creative_publication import CreativePublication  # noqa: F401
from app.models.upload import Upload, UploadPurpose, UploadStatus  # noqa: F401
from app.models.user import User, UserStatus
from app.models.user_preferences import UserPreferences  # noqa: F401
from app.repositories.prompts import PromptRepository
from app.storage.base import get_storage_adapter
from fake_storage import InMemoryStorageAdapter
from jwt_helpers import StaticTokenVerifier, generate_rsa_keypair, mint_token
from test_uploads_submissions import (
    FixedClock,
    _complete_profile,
    _create_ready_session,
    _create_ready_upload,
    _put_upload_bytes,
    _sketch_submission_json,
    make_jpeg,
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dailycreative:dailycreative@localhost:5432/dailycreative",  # pragma: allowlist secret
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "api" / "openapi" / "openapi.yaml"

requires_postgres = pytest.mark.skipif(
    os.environ.get("SKIP_POSTGRES_TESTS") == "1",
    reason="SKIP_POSTGRES_TESTS=1",
)


@pytest.fixture(scope="module")
def openapi_spec() -> dict[str, Any]:
    with OPENAPI_PATH.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    assert isinstance(loaded, dict)
    return loaded


def assert_matches_schema(
    instance: object,
    schema_name: str,
    openapi_spec: dict[str, Any],
) -> None:
    schema = openapi_spec["components"]["schemas"][schema_name]

    def expand(node: object) -> object:
        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                ref = node["$ref"]
                if ref.startswith("#/components/schemas/"):
                    name = ref.rsplit("/", 1)[-1]
                    return expand(openapi_spec["components"]["schemas"][name])
            return {key: expand(value) for key, value in node.items()}
        if isinstance(node, list):
            return [expand(item) for item in node]
        return node

    expanded = expand(schema)
    assert isinstance(expanded, dict)
    Draft202012Validator(expanded).validate(instance)


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
    settings = get_settings()

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
        http_client.settings = settings  # type: ignore[attr-defined]
        yield http_client

    app.dependency_overrides.clear()
    set_token_verifier(None)


def _auth_headers(client: AsyncClient, *, subject: str | None = None) -> dict[str, str]:
    private_key = client.app.state.test_private_key  # type: ignore[attr-defined]
    token = mint_token(private_key, subject=subject or f"descope|{uuid.uuid4()}")
    return {"Authorization": f"Bearer {token}"}


async def _seed_prompt_on(client: AsyncClient, prompt_date: date) -> DailyPrompt:
    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        return await PromptRepository(session).upsert_published(
            prompt_date=prompt_date,
            word_1="Chocolate",
            word_2="Coffee",
            word_3="Banana",
            published_at=datetime.combine(prompt_date, datetime.min.time(), tzinfo=UTC),
        )


async def _publish_for_date(
    client: AsyncClient,
    headers: dict[str, str],
    prompt_date: date,
    *,
    caption: str | None = "Sketch",
) -> dict[str, Any]:
    prompt = await _seed_prompt_on(client, prompt_date)
    session_id = await _create_ready_session(client, headers, prompt.id)
    upload = await _create_ready_upload(client, headers)
    created = await client.post(
        "/api/v1/submissions",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json=_sketch_submission_json(session_id, upload["id"], caption=caption),
    )
    assert created.status_code == 201, created.text
    return created.json()


async def _create_ready_avatar_upload(
    client: AsyncClient,
    headers: dict[str, str],
) -> dict[str, Any]:
    data = make_jpeg(width=120, height=120)
    created = await client.post(
        "/api/v1/uploads",
        headers=headers,
        json={
            "purpose": "avatar",
            "content_type": "image/jpeg",
            "byte_size": len(data),
        },
    )
    assert created.status_code == 201, created.text
    upload = created.json()
    await _put_upload_bytes(client, headers, upload["id"], data)
    completed = await client.post(
        f"/api/v1/uploads/{upload['id']}/complete",
        headers=headers,
    )
    assert completed.status_code == 200
    return completed.json()


@requires_postgres
@pytest.mark.asyncio
async def test_public_profile_includes_count_streak_and_is_self(
    client: AsyncClient,
    openapi_spec: dict[str, Any],
) -> None:
    headers = _auth_headers(client)
    profile = await _complete_profile(client, headers, username="streak_user")
    today = client.clock.today()  # type: ignore[attr-defined]
    await _publish_for_date(client, headers, today, caption="Today")
    await _publish_for_date(client, headers, today - timedelta(days=1), caption="Yesterday")
    # Second submission same day should not increase the streak.
    await _publish_for_date(client, headers, today, caption="Today again")

    guest = await client.get("/api/v1/users/streak_user", params={"creative_type": "sketch"})
    assert guest.status_code == 200
    body = guest.json()
    assert_matches_schema(body, "PublicUser", openapi_spec)
    assert body["submission_count"] == 3
    assert body["current_streak"] == 2
    assert body["is_self"] is False
    assert body["avatar_url"] is None
    assert "preferences" not in body
    assert "descope_subject" not in body

    owned = await client.get(
        "/api/v1/users/streak_user", headers=headers, params={"creative_type": "sketch"}
    )
    assert owned.status_code == 200
    assert owned.json()["is_self"] is True
    assert owned.json()["id"] == profile["id"]


@requires_postgres
@pytest.mark.asyncio
async def test_delete_final_submission_changes_streak(client: AsyncClient) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers, username="delete_streak")
    today = client.clock.today()  # type: ignore[attr-defined]
    first = await _publish_for_date(client, headers, today)
    await _publish_for_date(client, headers, today - timedelta(days=1))

    before = await client.get("/api/v1/users/delete_streak", params={"creative_type": "sketch"})
    assert before.json()["current_streak"] == 2
    assert before.json()["submission_count"] == 2

    deleted = await client.delete(
        f"/api/v1/submissions/{first['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204

    after = await client.get("/api/v1/users/delete_streak", params={"creative_type": "sketch"})
    assert after.json()["submission_count"] == 1
    assert after.json()["current_streak"] == 1


@requires_postgres
@pytest.mark.asyncio
async def test_user_submissions_pagination_and_contract(
    client: AsyncClient,
    openapi_spec: dict[str, Any],
) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers, username="gallery_user")
    today = client.clock.today()  # type: ignore[attr-defined]
    for offset in range(3):
        await _publish_for_date(
            client,
            headers,
            today - timedelta(days=offset),
            caption=f"Sketch {offset}",
        )

    first_page = await client.get(
        "/api/v1/users/gallery_user/submissions",
        params={"limit": 2, "creative_type": "sketch"},
    )
    assert first_page.status_code == 200
    body = first_page.json()
    assert_matches_schema(body, "RecentFeed", openapi_spec)
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None
    assert_matches_schema(body["items"][0], "FeedItem", openapi_spec)

    second_page = await client.get(
        "/api/v1/users/gallery_user/submissions",
        params={"limit": 2, "cursor": body["next_cursor"], "creative_type": "sketch"},
    )
    assert second_page.status_code == 200
    second = second_page.json()
    assert len(second["items"]) == 1
    assert second["next_cursor"] is None
    first_ids = {item["id"] for item in body["items"]}
    second_ids = {item["id"] for item in second["items"]}
    assert first_ids.isdisjoint(second_ids)


@requires_postgres
@pytest.mark.asyncio
async def test_user_submissions_404_when_profile_not_public(
    client: AsyncClient,
    db_engine,
) -> None:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            descope_subject=f"descope|{uuid.uuid4()}",
            username="ghost_user",
            username_normalized="ghost_user",
            display_name="Ghost",
            status=UserStatus.suspended,
            profile_completed_at=datetime.now(UTC),
        )
        session.add(user)
        await session.commit()

    response = await client.get(
        "/api/v1/users/ghost_user/submissions", params={"creative_type": "sketch"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"

    profile = await client.get("/api/v1/users/ghost_user", params={"creative_type": "sketch"})
    assert profile.status_code == 404


@requires_postgres
@pytest.mark.asyncio
async def test_avatar_upload_flow_and_idempotent_repatch(
    client: AsyncClient,
    openapi_spec: dict[str, Any],
) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers, username="avatar_user")
    avatar = await _create_ready_avatar_upload(client, headers)

    patched = await client.patch(
        "/api/v1/me",
        headers=headers,
        params={"creative_type": "sketch"},
        json={"avatar_upload_id": avatar["id"]},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert_matches_schema(body, "CurrentUser", openapi_spec)
    assert body["avatar_url"]
    assert body["avatar_url"].startswith("http")

    me = await client.get("/api/v1/me", headers=headers, params={"creative_type": "sketch"})
    assert me.json()["avatar_url"] == body["avatar_url"]

    public = await client.get(
        "/api/v1/users/avatar_user", headers=headers, params={"creative_type": "sketch"}
    )
    assert public.status_code == 200
    assert public.json()["avatar_url"]

    # Idempotent retry with the same consumed avatar succeeds.
    again = await client.patch(
        "/api/v1/me",
        headers=headers,
        params={"creative_type": "sketch"},
        json={"avatar_upload_id": avatar["id"]},
    )
    assert again.status_code == 200
    assert again.json()["avatar_url"]

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        result = await session.execute(select(Upload).where(Upload.id == uuid.UUID(avatar["id"])))
        upload = result.scalar_one()
        assert upload.purpose == UploadPurpose.avatar
        assert upload.status == UploadStatus.consumed


@requires_postgres
@pytest.mark.asyncio
async def test_avatar_rejects_wrong_purpose_and_foreign_upload(client: AsyncClient) -> None:
    owner_headers = _auth_headers(client)
    await _complete_profile(client, owner_headers, username="owner_user")
    submission_upload = await _create_ready_upload(client, owner_headers)

    wrong_purpose = await client.patch(
        "/api/v1/me",
        headers=owner_headers,
        params={"creative_type": "sketch"},
        json={"avatar_upload_id": submission_upload["id"]},
    )
    assert wrong_purpose.status_code == 422
    assert wrong_purpose.json()["error"]["code"] == "avatar_upload_invalid"

    other_headers = _auth_headers(client)
    await _complete_profile(client, other_headers, username="other_user")
    foreign = await _create_ready_avatar_upload(client, owner_headers)
    stolen = await client.patch(
        "/api/v1/me",
        headers=other_headers,
        params={"creative_type": "sketch"},
        json={"avatar_upload_id": foreign["id"]},
    )
    assert stolen.status_code == 404
    assert stolen.json()["error"]["code"] == "upload_not_found"


@requires_postgres
@pytest.mark.asyncio
async def test_current_user_contract_includes_avatar_url(
    client: AsyncClient,
    openapi_spec: dict[str, Any],
) -> None:
    headers = _auth_headers(client)
    response = await client.get("/api/v1/me", headers=headers, params={"creative_type": "sketch"})
    assert response.status_code == 200
    assert_matches_schema(response.json(), "CurrentUser", openapi_spec)
    assert response.json()["avatar_url"] is None
