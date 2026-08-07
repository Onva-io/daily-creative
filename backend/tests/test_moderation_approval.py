"""Approval workflows: review queue, reported content, caption redaction."""

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
from app.models.creative_publication import CreativePublication, PublicationStatus  # noqa: F401
from app.models.daily_prompt import DailyPrompt  # noqa: F401
from app.models.idempotency_key import IdempotencyKey  # noqa: F401
from app.models.moderation_action import ModerationAction, ModerationActionType
from app.models.moderation_review import ModerationReviewItem, ModerationReviewStatus
from app.models.report import Report, ReportStatus, ReportTargetType  # noqa: F401
from app.models.sketch_session import SketchSession  # noqa: F401
from app.models.sketch_session_event import SketchSessionEvent  # noqa: F401
from app.models.sketch_submission import SketchSubmission
from app.models.upload import Upload  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_block import UserBlock  # noqa: F401
from app.models.user_preferences import UserPreferences  # noqa: F401
from app.repositories.moderation_reviews import ModerationReviewRepository
from app.storage.base import get_storage_adapter
from fake_storage import InMemoryStorageAdapter
from jwt_helpers import StaticTokenVerifier, generate_rsa_keypair, mint_token
from test_moderation_phase11 import _publish
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


def _auth_headers(client: AsyncClient, *, subject: str | None = None) -> dict[str, str]:
    private_key = client.app.state.test_private_key  # type: ignore[attr-defined]
    token = mint_token(private_key, subject=subject or f"descope|{uuid.uuid4()}")
    return {"Authorization": f"Bearer {token}"}


def _operator_headers() -> dict[str, str]:
    return {"X-Moderation-Token": OPERATOR_TOKEN}


async def _enqueue_review(
    client: AsyncClient,
    *,
    target_type: ReportTargetType,
    target_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> ModerationReviewItem:
    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        item = await ModerationReviewRepository(session).enqueue(
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            confidence=0.7,
            categories="profanity_or_sensitive",
            provider="heuristic",
        )
        return item


@requires_postgres
@pytest.mark.asyncio
async def test_approve_review_item_keeps_content_published(client: AsyncClient) -> None:
    author_headers = _auth_headers(client, subject="descope|approve_author")
    author = await _complete_profile(client, author_headers, username="approve_author")
    submission = await _publish(client, author_headers)
    item = await _enqueue_review(
        client,
        target_type=ReportTargetType.submission,
        target_id=uuid.UUID(submission["id"]),
        user_id=uuid.UUID(author["id"]),
    )

    listed = await client.get("/internal/moderation/review-queue", headers=_operator_headers())
    assert listed.status_code == 200
    assert any(row["id"] == str(item.id) for row in listed.json()["items"])
    preview = next(row for row in listed.json()["items"] if row["id"] == str(item.id))["preview"]
    assert preview.get("caption") == "moderate me"

    approved = await client.post(
        f"/internal/moderation/review-queue/{item.id}/approve",
        headers=_operator_headers(),
        json={"reason": "false positive"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "resolved"

    public = await client.get(f"/api/v1/submissions/{submission['id']}")
    assert public.status_code == 200

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        refreshed = await session.get(ModerationReviewItem, item.id)
        assert refreshed is not None
        assert refreshed.status == ModerationReviewStatus.resolved
        actions = (await session.execute(select(ModerationAction))).scalars().all()
        assert any(a.action == ModerationActionType.approve_review_item for a in actions)


@requires_postgres
@pytest.mark.asyncio
async def test_reject_review_item_hides_content(client: AsyncClient) -> None:
    author_headers = _auth_headers(client, subject="descope|reject_author")
    author = await _complete_profile(client, author_headers, username="reject_author")
    submission = await _publish(client, author_headers)
    item = await _enqueue_review(
        client,
        target_type=ReportTargetType.submission,
        target_id=uuid.UUID(submission["id"]),
        user_id=uuid.UUID(author["id"]),
    )

    rejected = await client.post(
        f"/internal/moderation/review-queue/{item.id}/reject",
        headers=_operator_headers(),
        json={"reason": "clear violation"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "dismissed"

    public = await client.get(f"/api/v1/submissions/{submission['id']}")
    assert public.status_code == 404

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        pub = await session.get(CreativePublication, uuid.UUID(submission["id"]))
        assert pub is not None
        assert pub.status == PublicationStatus.hidden


@requires_postgres
@pytest.mark.asyncio
async def test_approve_reported_content_restores_and_dismisses(client: AsyncClient) -> None:
    author_headers = _auth_headers(client, subject="descope|rpt_author")
    reporter_headers = _auth_headers(client, subject="descope|rpt_reporter")
    await _complete_profile(client, author_headers, username="rpt_author")
    await _complete_profile(client, reporter_headers, username="rpt_reporter")
    submission = await _publish(client, author_headers)

    report = await client.post(
        "/api/v1/reports",
        headers=reporter_headers,
        json={
            "target_type": "submission",
            "target_id": submission["id"],
            "reason": "inappropriate",
        },
    )
    assert report.status_code == 201
    report_id = report.json()["id"]

    hide = await client.post(
        f"/internal/moderation/submissions/{submission['id']}/hide",
        headers=_operator_headers(),
        json={"reason": "pending review", "report_id": report_id},
    )
    assert hide.status_code == 200

    approved = await client.post(
        f"/internal/moderation/reports/{report_id}/approve",
        headers=_operator_headers(),
        json={"reason": "not a violation"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "dismissed"

    public = await client.get(f"/api/v1/submissions/{submission['id']}")
    assert public.status_code == 200

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        row = await session.get(Report, uuid.UUID(report_id))
        assert row is not None
        assert row.status == ReportStatus.dismissed
        assert row.reviewed_by_user_id is None  # token path
        actions = (await session.execute(select(ModerationAction))).scalars().all()
        assert any(a.action == ModerationActionType.approve_reported_content for a in actions)


@requires_postgres
@pytest.mark.asyncio
async def test_redact_caption_clears_caption(client: AsyncClient) -> None:
    author_headers = _auth_headers(client, subject="descope|caption_author")
    await _complete_profile(client, author_headers, username="caption_author")
    submission = await _publish(client, author_headers)

    redacted = await client.post(
        f"/internal/moderation/submissions/{submission['id']}/redact-caption",
        headers=_operator_headers(),
        json={"reason": "caption only"},
    )
    assert redacted.status_code == 200
    assert redacted.json()["caption"] is None

    public = await client.get(f"/api/v1/submissions/{submission['id']}")
    assert public.status_code == 200
    assert public.json()["caption"] is None

    session_factory = client.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        sketch = await session.get(SketchSubmission, uuid.UUID(submission["id"]))
        assert sketch is not None
        assert sketch.caption is None
        actions = (await session.execute(select(ModerationAction))).scalars().all()
        assert any(a.action == ModerationActionType.redact_caption for a in actions)
