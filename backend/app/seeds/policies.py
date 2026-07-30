"""Seed draft (and optionally publish) initial policy documents.

Usage:
  python -m app.seeds.policies              # draft only
  python -m app.seeds.policies --publish    # draft and force-publish (fresh database)
  python -m app.seeds.policies --bootstrap  # idempotent; run on every deploy
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.settings import get_settings
from app.models.policy import PolicyKind
from app.observability.metrics import send_alert
from app.services.policies import PolicySeedDocument, PolicyService

# Serializes bootstrap across replicas booting at the same time.
_BOOTSTRAP_LOCK_KEY = 815_432_101

TERMS_BODY = """# Terms of Service (Draft — legal review required)

By creating an account or using Daily Creative apps, you agree to these Terms.

## Eligibility
You must be at least 13 years old to use this service. If you are under 18, you confirm a parent or guardian has reviewed these Terms where required by law.

## Acceptable use
You may not upload, publish, or share content that is:
- inappropriate, obscene, or pornographic;
- profane or abusive;
- hateful or discriminatory;
- sexually explicit;
- violently graphic or that threatens violence;
- illegal or that promotes illegal activity;
- harassing, bullying, or stalking;
- related to self-harm or suicide in a promotional way;
- infringing of someone else's intellectual property or privacy rights.

We may remove content, suspend accounts, and cooperate with law enforcement when required.

## User-generated content
You remain responsible for content you post. We may screen content automatically and review reports. We aim to act on reports of objectionable content within 24 hours.

## Changes
We may publish updated Terms. Continued use after you accept a new version constitutes agreement to that version.
"""

PRIVACY_BODY = """# Privacy Policy (Draft — legal review required)

We collect account identifiers, profile information you provide (including date of birth for age gating), creative content you upload, device/app metadata needed to operate the service, and reports you submit.

We use this information to provide the service, enforce our Terms and Community Guidelines, moderate content, and meet legal obligations.

We do not sell personal data. We retain content and account data until you delete your account or as required for safety, legal, and operational purposes.

Contact support using the address published in the app for privacy questions.
"""

GUIDELINES_BODY = """# Community Guidelines (Draft — legal review required)

Daily Creative is a place for constructive daily creativity. Be kind. Celebrate effort over perfection.

## Not allowed
Obscene or pornographic material; hate; harassment; threats; graphic violence; illegal content; spam; impersonation; or anything that sexualizes or endangers minors.

## Reporting and blocking
Use Report to flag content or profiles, and Block to hide another user. Reports are private. Our team aims to review reports within 24 hours and may remove content or suspend accounts.

## Enforcement
Violations may result in content removal, temporary suspension, or permanent account disablement.
"""


SEED_DOCUMENTS: tuple[PolicySeedDocument, ...] = (
    PolicySeedDocument(
        kind=PolicyKind.terms,
        version="1.0.0",
        title="Terms of Service",
        body_markdown=TERMS_BODY,
        minimum_age=13,
        is_significant_change=True,
        change_summary="Initial public terms including acceptable use and age eligibility.",
    ),
    PolicySeedDocument(
        kind=PolicyKind.privacy,
        version="1.0.0",
        title="Privacy Policy",
        body_markdown=PRIVACY_BODY,
        minimum_age=13,
        is_significant_change=True,
        change_summary="Initial privacy policy covering account, content, and age data.",
    ),
    PolicySeedDocument(
        kind=PolicyKind.community_guidelines,
        version="1.0.0",
        title="Community Guidelines",
        body_markdown=GUIDELINES_BODY,
        minimum_age=13,
        is_significant_change=True,
        change_summary="Initial community guidelines and reporting expectations.",
    ),
)


async def seed_policies(*, publish: bool) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        service = PolicyService(session, settings=settings)
        for seed in SEED_DOCUMENTS:
            document = await service.create_draft(
                kind=seed.kind,
                version=seed.version,
                title=seed.title,
                body_markdown=seed.body_markdown,
                minimum_age=seed.minimum_age,
                is_significant_change=seed.is_significant_change,
                change_summary=seed.change_summary,
                operator_identity="seed",
            )
            if publish:
                await service.publish(document.id, operator_identity="seed")
                print(f"Published {seed.kind.value} v{seed.version}")
            else:
                print(f"Drafted {seed.kind.value} v{seed.version} (id={document.id})")
    await engine.dispose()


async def bootstrap_policies() -> bool:
    """Publish the seed policy set in environments that have nothing published yet.

    Returns False when bootstrap could not complete, so callers can surface the
    failure without blocking API startup.
    """
    settings = get_settings()
    if not settings.policy_bootstrap_enabled:
        print("[policies] POLICY_BOOTSTRAP_ENABLED is false; skipping bootstrap.")
        return True

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as lock_connection:
            await lock_connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": _BOOTSTRAP_LOCK_KEY},
            )
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                outcomes = await PolicyService(session, settings=settings).bootstrap(
                    SEED_DOCUMENTS,
                    operator_identity="deploy-bootstrap",
                )
        for outcome in outcomes:
            print(f"[policies] {outcome.kind.value} v{outcome.version}: {outcome.action.value}")
    except Exception as exc:  # noqa: BLE001 - startup must not fail on bootstrap errors
        print(f"[policies] Bootstrap failed: {exc}", file=sys.stderr)
        await send_alert(
            settings,
            title="Policy bootstrap failed",
            detail=(
                "Consent and age gating stay inactive while no policy documents are "
                f"published. Error: {exc}"
            ),
        )
        return False
    finally:
        await engine.dispose()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed policy documents")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish drafts immediately after create/update (fresh database only)",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Idempotently publish seed policies only for kinds with nothing published",
    )
    args = parser.parse_args()
    if args.bootstrap:
        if not asyncio.run(bootstrap_policies()):
            sys.exit(1)
        return
    asyncio.run(seed_policies(publish=args.publish))


if __name__ == "__main__":
    main()
