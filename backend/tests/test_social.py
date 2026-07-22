"""Likes and Reflections integration, contract, and acceptance tests."""

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
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.db.session import Base, get_db_session
from app.main import create_app
from app.models.activity_event import ActivityEvent, ActivityEventType  # noqa: F401
from app.models.daily_prompt import DailyPrompt  # noqa: F401
from app.models.idempotency_key import IdempotencyKey  # noqa: F401
from app.models.reflection import Reflection  # noqa: F401
from app.models.sketch_session import SketchSession  # noqa: F401
from app.models.sketch_session_event import SketchSessionEvent  # noqa: F401
from app.models.creative_publication import CreativePublication  # noqa: F401
from app.models.publication_like import PublicationLike  # noqa: F401
from app.models.upload import Upload  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_preferences import UserPreferences  # noqa: F401
from app.services.social import normalise_reflection_body
from app.storage.base import get_storage_adapter
from fake_storage import InMemoryStorageAdapter
from jwt_helpers import StaticTokenVerifier, generate_rsa_keypair, mint_token
from test_uploads_submissions import (
    _complete_profile,
    _create_ready_session,
    _create_ready_upload,
    _seed_prompt,
    _sketch_submission_json,
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


class FixedClock:
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant

    def today(self) -> date:
        return self._instant.date()

    def advance(self, **kwargs: Any) -> None:
        self._instant = self._instant + timedelta(**kwargs)


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
    clock = FixedClock(datetime(2026, 7, 18, 20, 0, tzinfo=UTC))
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


async def _publish_submission(
    client: AsyncClient,
    *,
    subject: str | None = None,
    username: str | None = None,
    caption: str | None = "A quiet sketch.",
) -> dict[str, Any]:
    headers = _auth_headers(client, subject=subject)
    await _complete_profile(client, headers, username=username)
    prompt = await _seed_prompt(client)
    session_id = await _create_ready_session(client, headers, prompt.id)
    upload = await _create_ready_upload(client, headers)
    created = await client.post(
        "/api/v1/submissions",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json=_sketch_submission_json(session_id, upload["id"], caption=caption),
    )
    assert created.status_code == 201, created.text
    return {"submission": created.json(), "headers": headers}


def test_normalise_reflection_body_trims_and_rejects_empty() -> None:
    assert normalise_reflection_body("  hello  ", 500) == "hello"
    with pytest.raises(AppError) as empty_exc:
        normalise_reflection_body("   ", 500)
    assert empty_exc.value.code == "validation_error"
    with pytest.raises(AppError) as long_exc:
        normalise_reflection_body("x" * 501, 500)
    assert long_exc.value.code == "validation_error"


@requires_postgres
@pytest.mark.asyncio
async def test_like_is_idempotent_and_unlike_is_safe(
    client: AsyncClient,
    openapi_spec: dict[str, Any],
) -> None:
    owner = await _publish_submission(client, username="owner_like")
    submission_id = owner["submission"]["id"]
    liker_headers = _auth_headers(client)
    await _complete_profile(client, liker_headers, username="liker_one")

    first = await client.put(
        f"/api/v1/submissions/{submission_id}/like",
        headers=liker_headers,
    )
    assert first.status_code == 200, first.text
    assert_matches_schema(first.json(), "LikeState", openapi_spec)
    assert first.json() == {"liked": True, "like_count": 1}

    duplicate = await client.put(
        f"/api/v1/submissions/{submission_id}/like",
        headers=liker_headers,
    )
    assert duplicate.status_code == 200
    assert duplicate.json() == {"liked": True, "like_count": 1}

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        likes = (
            (
                await session.execute(
                    select(PublicationLike).where(
                        PublicationLike.publication_id == uuid.UUID(submission_id)
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(likes) == 1
        events = (
            (
                await session.execute(
                    select(ActivityEvent).where(
                        ActivityEvent.event_type == ActivityEventType.submission_liked,
                        ActivityEvent.submission_id == uuid.UUID(submission_id),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(events) == 1

    unlike = await client.delete(
        f"/api/v1/submissions/{submission_id}/like",
        headers=liker_headers,
    )
    assert unlike.status_code == 200
    assert unlike.json() == {"liked": False, "like_count": 0}

    unlike_again = await client.delete(
        f"/api/v1/submissions/{submission_id}/like",
        headers=liker_headers,
    )
    assert unlike_again.status_code == 200
    assert unlike_again.json() == {"liked": False, "like_count": 0}


@requires_postgres
@pytest.mark.asyncio
async def test_self_like_skips_activity_event(client: AsyncClient) -> None:
    owned = await _publish_submission(client, username="self_liker")
    submission_id = owned["submission"]["id"]
    headers = owned["headers"]

    liked = await client.put(
        f"/api/v1/submissions/{submission_id}/like",
        headers=headers,
    )
    assert liked.status_code == 200
    assert liked.json()["like_count"] == 1

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        events = (
            (
                await session.execute(
                    select(ActivityEvent).where(
                        ActivityEvent.submission_id == uuid.UUID(submission_id)
                    )
                )
            )
            .scalars()
            .all()
        )
        assert events == []


@requires_postgres
@pytest.mark.asyncio
async def test_viewer_has_liked_on_detail_and_feed(client: AsyncClient) -> None:
    owned = await _publish_submission(client, username="feed_owner")
    submission_id = owned["submission"]["id"]
    liker_headers = _auth_headers(client)
    await _complete_profile(client, liker_headers, username="feed_liker")

    await client.put(
        f"/api/v1/submissions/{submission_id}/like",
        headers=liker_headers,
    )

    detail = await client.get(
        f"/api/v1/submissions/{submission_id}",
        headers=liker_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["viewer_has_liked"] is True
    assert detail.json()["like_count"] == 1

    guest_detail = await client.get(f"/api/v1/submissions/{submission_id}")
    assert guest_detail.status_code == 200
    assert guest_detail.json()["viewer_has_liked"] is False

    feed = await client.get(
        "/api/v1/feed/recent", headers=liker_headers, params={"creative_type": "sketch"}
    )
    assert feed.status_code == 200
    item = next(i for i in feed.json()["items"] if i["id"] == submission_id)
    assert item["viewer_has_liked"] is True

    guest_feed = await client.get("/api/v1/feed/recent", params={"creative_type": "sketch"})
    guest_item = next(i for i in guest_feed.json()["items"] if i["id"] == submission_id)
    assert guest_item["viewer_has_liked"] is False


@requires_postgres
@pytest.mark.asyncio
async def test_whitespace_reflection_rejected_and_valid_creates(
    client: AsyncClient,
    openapi_spec: dict[str, Any],
) -> None:
    owned = await _publish_submission(client, username="reflect_owner")
    submission_id = owned["submission"]["id"]
    commenter = _auth_headers(client)
    await _complete_profile(client, commenter, username="commenter")

    blank = await client.post(
        f"/api/v1/submissions/{submission_id}/reflections",
        headers={**commenter, "Idempotency-Key": str(uuid.uuid4())},
        json={"body": "   "},
    )
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "validation_error"

    created = await client.post(
        f"/api/v1/submissions/{submission_id}/reflections",
        headers={**commenter, "Idempotency-Key": str(uuid.uuid4())},
        json={"body": "  Soft lines, nice work.  "},
    )
    assert created.status_code == 201, created.text
    assert_matches_schema(created.json(), "Reflection", openapi_spec)
    assert created.json()["body"] == "Soft lines, nice work."
    assert created.json()["is_author"] is True

    listed = await client.get(f"/api/v1/submissions/{submission_id}/reflections")
    assert listed.status_code == 200
    assert_matches_schema(listed.json(), "ReflectionList", openapi_spec)
    assert len(listed.json()["items"]) == 1
    assert listed.json()["items"][0]["body"] == "Soft lines, nice work."

    detail = await client.get(f"/api/v1/submissions/{submission_id}")
    assert detail.json()["reflection_count"] == 1

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        events = (
            (
                await session.execute(
                    select(ActivityEvent).where(
                        ActivityEvent.event_type == ActivityEventType.reflection_added,
                        ActivityEvent.submission_id == uuid.UUID(submission_id),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(events) == 1


@requires_postgres
@pytest.mark.asyncio
async def test_author_only_delete_and_double_delete_safe(client: AsyncClient) -> None:
    owned = await _publish_submission(client, username="delete_owner")
    submission_id = owned["submission"]["id"]
    author = _auth_headers(client)
    await _complete_profile(client, author, username="reflection_author")
    other = _auth_headers(client)
    await _complete_profile(client, other, username="other_person")

    created = await client.post(
        f"/api/v1/submissions/{submission_id}/reflections",
        headers={**author, "Idempotency-Key": str(uuid.uuid4())},
        json={"body": "Keep going"},
    )
    reflection_id = created.json()["id"]

    forbidden = await client.delete(
        f"/api/v1/reflections/{reflection_id}",
        headers=other,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "reflection_forbidden"

    deleted = await client.delete(
        f"/api/v1/reflections/{reflection_id}",
        headers=author,
    )
    assert deleted.status_code == 204

    listed = await client.get(f"/api/v1/submissions/{submission_id}/reflections")
    assert listed.json()["items"] == []

    detail = await client.get(f"/api/v1/submissions/{submission_id}")
    assert detail.json()["reflection_count"] == 0

    again = await client.delete(
        f"/api/v1/reflections/{reflection_id}",
        headers=author,
    )
    assert again.status_code == 404
    assert again.json()["error"]["code"] == "reflection_not_found"

    detail_again = await client.get(f"/api/v1/submissions/{submission_id}")
    assert detail_again.json()["reflection_count"] == 0


@requires_postgres
@pytest.mark.asyncio
async def test_self_reflection_skips_activity_event(client: AsyncClient) -> None:
    owned = await _publish_submission(client, username="self_reflect")
    submission_id = owned["submission"]["id"]
    headers = owned["headers"]

    created = await client.post(
        f"/api/v1/submissions/{submission_id}/reflections",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json={"body": "Notes to self"},
    )
    assert created.status_code == 201

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        events = (
            (
                await session.execute(
                    select(ActivityEvent).where(
                        ActivityEvent.submission_id == uuid.UUID(submission_id)
                    )
                )
            )
            .scalars()
            .all()
        )
        assert events == []


@requires_postgres
@pytest.mark.asyncio
async def test_guest_can_list_reflections_authenticated_required_to_write(
    client: AsyncClient,
) -> None:
    owned = await _publish_submission(client, username="guest_list")
    submission_id = owned["submission"]["id"]

    guest_list = await client.get(f"/api/v1/submissions/{submission_id}/reflections")
    assert guest_list.status_code == 200
    assert guest_list.json()["items"] == []

    guest_like = await client.put(f"/api/v1/submissions/{submission_id}/like")
    assert guest_like.status_code == 401

    guest_post = await client.post(
        f"/api/v1/submissions/{submission_id}/reflections",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={"body": "Nice"},
    )
    assert guest_post.status_code == 401
