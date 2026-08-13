"""HMAC-signed guest age-capability tokens.

Guests declare a date of birth once. The server checks it against the published
minimum age and returns an opaque token. Community GETs accept that token or a
Descope session; the Daily Prompt stays ungated. Date of birth is not stored
for guests and is not embedded in the token.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.errors import AppError
from app.core.settings import Settings

GUEST_AGE_TOKEN_TYP = "guest_age"
GUEST_AGE_ALGORITHM = "HS256"
GUEST_AGE_HEADER = "X-Guest-Age-Token"

_MISSING = AppError(
    code="age_declaration_required",
    message="Confirm your age to browse community content.",
    status_code=403,
    details={"reason": "missing_guest_age_token"},
)


def mint_guest_age_token(
    settings: Settings,
    *,
    minimum_age: int,
    now: datetime | None = None,
) -> tuple[str, datetime]:
    instant = now or datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    expires_at = instant + timedelta(seconds=settings.guest_age_token_ttl_seconds)
    claims: dict[str, Any] = {
        "sub": "guest",
        "typ": GUEST_AGE_TOKEN_TYP,
        "min_age": minimum_age,
        "iat": int(instant.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(claims, settings.guest_age_token_secret, algorithm=GUEST_AGE_ALGORITHM)
    return token, expires_at


def verify_guest_age_token(token: str, settings: Settings) -> dict[str, Any]:
    stripped = token.strip()
    if not stripped:
        raise AppError(
            code="age_declaration_required",
            message="Confirm your age to browse community content.",
            status_code=403,
            details={"reason": "missing_guest_age_token"},
        )
    try:
        claims = jwt.decode(
            stripped,
            settings.guest_age_token_secret,
            algorithms=[GUEST_AGE_ALGORITHM],
            options={"require": ["exp", "iat", "typ"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            code="age_declaration_required",
            message="Confirm your age to browse community content.",
            status_code=403,
            details={"reason": "token_expired"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(
            code="age_declaration_required",
            message="Confirm your age to browse community content.",
            status_code=403,
            details={"reason": "invalid_token"},
        ) from exc

    if claims.get("typ") != GUEST_AGE_TOKEN_TYP:
        raise AppError(
            code="age_declaration_required",
            message="Confirm your age to browse community content.",
            status_code=403,
            details={"reason": "invalid_token"},
        )
    return claims


def missing_guest_age_error() -> AppError:
    return AppError(
        code=_MISSING.code,
        message=_MISSING.message,
        status_code=_MISSING.status_code,
        details=dict(_MISSING.details),
    )
