"""Policy acceptance, age gate, and content moderation tests."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml
from httpx import ASGITransport, AsyncClient
from jsonschema import validate
from jwt_helpers import StaticTokenVerifier, generate_rsa_keypair, mint_token
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.jwt import set_token_verifier
from app.db.session import Base, get_db_session
from app.main import create_app
from app.models.policy import PolicyKind
from app.moderation.base import HeuristicModerationAdapter, ModerationTier
from app.seeds.policies import SEED_DOCUMENTS
from app.services.policies import (
    PolicyBootstrapAction,
    PolicyBootstrapOutcome,
    PolicySeedDocument,
    PolicyService,
    age_on,
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dailycreative:dailycreative@localhost:5432/dailycreative",  # pragma: allowlist secret
)

requires_postgres = pytest.mark.skipif(
    os.environ.get("SKIP_POSTGRES_TESTS") == "1",
    reason="SKIP_POSTGRES_TESTS=1",
)

OPENAPI = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "api" / "openapi" / "openapi.yaml").read_text()
)


def _schema(name: str) -> dict:
    """Return a component schema with local $refs inlined for standalone validation."""

    def expand(node: object) -> object:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                return expand(OPENAPI["components"]["schemas"][ref.rsplit("/", 1)[-1]])
            return {key: expand(value) for key, value in node.items()}
        if isinstance(node, list):
            return [expand(item) for item in node]
        return node

    expanded = expand(OPENAPI["components"]["schemas"][name])
    assert isinstance(expanded, dict)
    return expanded


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
    app.state.session_factory = session_factory

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


async def _publish_policies(session: AsyncSession) -> None:
    service = PolicyService(session)
    for kind, version, title in [
        (PolicyKind.terms, "1.0.0", "Terms"),
        (PolicyKind.privacy, "1.0.0", "Privacy"),
        (PolicyKind.community_guidelines, "1.0.0", "Guidelines"),
    ]:
        doc = await service.create_draft(
            kind=kind,
            version=version,
            title=title,
            body_markdown=f"# {title}\n\nBe kind. No porn. No hate.",
            minimum_age=13,
            is_significant_change=True,
            change_summary=f"Initial {title}",
            operator_identity="test",
        )
        await service.publish(doc.id, operator_identity="test")


@requires_postgres
@pytest.mark.asyncio
async def test_current_policies_and_accept_flow(client: AsyncClient) -> None:
    session_factory = client.app.state.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        await _publish_policies(session)

    response = await client.get("/api/v1/policies/current")
    assert response.status_code == 200
    body = response.json()
    validate(instance=body, schema=_schema("CurrentPoliciesResponse"))
    assert len(body["documents"]) == 3

    private_key = client.app.state.test_private_key  # type: ignore[attr-defined]
    token = mint_token(private_key, subject=f"descope|{uuid.uuid4()}")
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/me", params={"creative_type": "sketch"}, headers=headers)
    assert me.status_code == 200
    validate(instance=me.json(), schema=_schema("CurrentUser"))
    assert me.json()["consent"]["consent_required"] is True
    assert me.json()["date_of_birth_set"] is False

    blocked = await client.patch(
        "/api/v1/me/preferences",
        params={"creative_type": "sketch"},
        headers=headers,
        json={"timezone": "UTC"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "consent_required"

    underage = await client.post(
        "/api/v1/me/date-of-birth",
        params={"creative_type": "sketch"},
        headers=headers,
        json={"date_of_birth": (date.today() - timedelta(days=365 * 10)).isoformat()},
    )
    assert underage.status_code == 403
    assert underage.json()["error"]["code"] == "under_minimum_age"

    dob = await client.post(
        "/api/v1/me/date-of-birth",
        params={"creative_type": "sketch"},
        headers=headers,
        json={"date_of_birth": "2000-01-15"},
    )
    assert dob.status_code == 200
    assert dob.json()["date_of_birth_set"] is True

    docs = body["documents"]
    accept = await client.post(
        "/api/v1/me/policies/accept",
        headers=headers,
        json={
            "documents": [{"kind": d["kind"], "version": d["version"]} for d in docs],
            "platform": "ios",
            "app_version": "0.1.0",
        },
    )
    assert accept.status_code == 200
    validate(instance=accept.json(), schema=_schema("AcceptPoliciesResponse"))

    again = await client.post(
        "/api/v1/me/policies/accept",
        headers=headers,
        json={"documents": [{"kind": docs[0]["kind"], "version": docs[0]["version"]}]},
    )
    assert again.status_code == 200

    me2 = await client.get("/api/v1/me", params={"creative_type": "sketch"}, headers=headers)
    assert me2.json()["consent"]["consent_required"] is False

    allowed = await client.patch(
        "/api/v1/me/preferences",
        params={"creative_type": "sketch"},
        headers=headers,
        json={"timezone": "America/New_York"},
    )
    assert allowed.status_code == 200


@requires_postgres
@pytest.mark.asyncio
async def test_stale_policy_version_conflict(client: AsyncClient) -> None:
    session_factory = client.app.state.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        await _publish_policies(session)
        service = PolicyService(session)
        doc = await service.create_draft(
            kind=PolicyKind.terms,
            version="2.0.0",
            title="Terms",
            body_markdown="# Terms v2",
            minimum_age=13,
            operator_identity="test",
        )
        await service.publish(doc.id, operator_identity="test")

    private_key = client.app.state.test_private_key  # type: ignore[attr-defined]
    token = mint_token(private_key, subject=f"descope|{uuid.uuid4()}")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/v1/me/date-of-birth",
        params={"creative_type": "sketch"},
        headers=headers,
        json={"date_of_birth": "1990-05-01"},
    )
    stale = await client.post(
        "/api/v1/me/policies/accept",
        headers=headers,
        json={"documents": [{"kind": "terms", "version": "1.0.0"}]},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "policy_version_stale"


async def _bootstrap(
    session: AsyncSession,
    documents: tuple[PolicySeedDocument, ...] = SEED_DOCUMENTS,
) -> list[PolicyBootstrapOutcome]:
    return await PolicyService(session).bootstrap(documents, operator_identity="test-bootstrap")


@requires_postgres
@pytest.mark.asyncio
async def test_bootstrap_publishes_seed_policies_on_empty_environment(client: AsyncClient) -> None:
    session_factory = client.app.state.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        outcomes = await _bootstrap(session)

    assert {outcome.action for outcome in outcomes} == {PolicyBootstrapAction.published}

    response = await client.get("/api/v1/policies/current")
    assert response.status_code == 200
    assert len(response.json()["documents"]) == 3

    private_key = client.app.state.test_private_key  # type: ignore[attr-defined]
    token = mint_token(private_key, subject=f"descope|{uuid.uuid4()}")
    me = await client.get(
        "/api/v1/me",
        params={"creative_type": "sketch"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    # An environment that skipped bootstrap reported consent_required false, which let
    # first-time users through without ever seeing the consent gate.
    assert me.json()["consent"]["consent_required"] is True
    assert me.json()["consent"]["age_required"] is True


@requires_postgres
@pytest.mark.asyncio
async def test_bootstrap_is_idempotent_across_restarts(client: AsyncClient) -> None:
    session_factory = client.app.state.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        await _bootstrap(session)
    async with session_factory() as session:
        outcomes = await _bootstrap(session)

    assert {outcome.action for outcome in outcomes} == {PolicyBootstrapAction.unchanged}
    response = await client.get("/api/v1/policies/current")
    assert len(response.json()["documents"]) == 3


@requires_postgres
@pytest.mark.asyncio
async def test_bootstrap_drafts_new_versions_without_publishing_them(client: AsyncClient) -> None:
    session_factory = client.app.state.session_factory  # type: ignore[attr-defined]
    async with session_factory() as session:
        await _bootstrap(session)

    bumped = tuple(
        replace(document, version="2.0.0") if document.kind == PolicyKind.terms else document
        for document in SEED_DOCUMENTS
    )
    async with session_factory() as session:
        outcomes = await _bootstrap(session, bumped)

    actions = {outcome.kind: outcome.action for outcome in outcomes}
    assert actions[PolicyKind.terms] == PolicyBootstrapAction.drafted
    assert actions[PolicyKind.privacy] == PolicyBootstrapAction.unchanged

    response = await client.get("/api/v1/policies/current")
    published_terms = [
        document for document in response.json()["documents"] if document["kind"] == "terms"
    ]
    assert [document["version"] for document in published_terms] == ["1.0.0"]


def test_age_on_helper() -> None:
    assert age_on(date(2026, 7, 30), date_of_birth=date(2013, 7, 30)) == 13
    assert age_on(date(2026, 7, 29), date_of_birth=date(2013, 7, 30)) == 12


@pytest.mark.asyncio
async def test_heuristic_moderation_tiers() -> None:
    adapter = HeuristicModerationAdapter()
    blocked = await adapter.screen_text(text="this contains childporn material", context="test")
    assert blocked.tier == ModerationTier.block
    queued = await adapter.screen_text(text="what the fuck", context="test")
    assert queued.tier == ModerationTier.queue
    allowed = await adapter.screen_text(text="a lovely sketch of a tree", context="test")
    assert allowed.tier == ModerationTier.allow
