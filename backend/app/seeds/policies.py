"""Seed draft (and optionally publish) initial policy documents.

Usage:
  python -m app.seeds.policies
  python -m app.seeds.policies --publish
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.settings import get_settings
from app.models.policy import PolicyKind
from app.services.policies import PolicyService

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


async def seed_policies(*, publish: bool) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        service = PolicyService(session, settings=settings)
        drafts = [
            (
                PolicyKind.terms,
                "1.0.0",
                "Terms of Service",
                TERMS_BODY,
                13,
                "Initial public terms including acceptable use and age eligibility.",
            ),
            (
                PolicyKind.privacy,
                "1.0.0",
                "Privacy Policy",
                PRIVACY_BODY,
                13,
                "Initial privacy policy covering account, content, and age data.",
            ),
            (
                PolicyKind.community_guidelines,
                "1.0.0",
                "Community Guidelines",
                GUIDELINES_BODY,
                13,
                "Initial community guidelines and reporting expectations.",
            ),
        ]
        for kind, version, title, body, minimum_age, summary in drafts:
            document = await service.create_draft(
                kind=kind,
                version=version,
                title=title,
                body_markdown=body,
                minimum_age=minimum_age,
                is_significant_change=True,
                change_summary=summary,
                operator_identity="seed",
            )
            if publish:
                await service.publish(document.id, operator_identity="seed")
                print(f"Published {kind.value} v{version}")
            else:
                print(f"Drafted {kind.value} v{version} (id={document.id})")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed policy documents")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish drafts immediately after create/update",
    )
    args = parser.parse_args()
    asyncio.run(seed_policies(publish=args.publish))


if __name__ == "__main__":
    main()
