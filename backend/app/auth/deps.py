"""Authenticated-user FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.guest_age import missing_guest_age_error, verify_guest_age_token
from app.auth.jwt import TokenVerifier, get_token_verifier
from app.core.clock import Clock, get_clock
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.services.policies import PolicyService
from app.services.users import UserService

_bearer = HTTPBearer(auto_error=False)


async def _resolve_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    session: AsyncSession,
    settings: Settings,
    *,
    allow_pending_deletion: bool = False,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AppError(
            code="unauthenticated",
            message="Authentication is required.",
            status_code=401,
            details={"reason": "missing_token"},
        )

    verifier: TokenVerifier = getattr(
        request.app.state, "token_verifier", None
    ) or get_token_verifier(settings)
    verified = verifier.verify(credentials.credentials)
    return await UserService(session).resolve_or_provision(
        verified,
        allow_pending_deletion=allow_pending_deletion,
    )


async def get_current_user_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User:
    """Authenticate and provision the user without requiring policy consent."""
    return await _resolve_user(request, credentials, session, settings)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    clock: Clock = Depends(get_clock),
) -> User:
    """Authenticate and require current policy consent + age declaration."""
    user = await _resolve_user(request, credentials, session, settings)
    await PolicyService(session, clock=clock, settings=settings).require_consent(user)
    return user


async def get_current_user_allowing_pending_deletion(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User:
    """Like get_current_user_identity, but permits pending_deletion for DELETE /me."""
    return await _resolve_user(
        request,
        credentials,
        session,
        settings,
        allow_pending_deletion=True,
    )


async def _optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    session: AsyncSession,
    settings: Settings,
) -> User | None:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        return None
    verifier: TokenVerifier = getattr(
        request.app.state, "token_verifier", None
    ) or get_token_verifier(settings)
    try:
        verified = verifier.verify(credentials.credentials)
        return await UserService(session).resolve_or_provision(verified)
    except AppError:
        return None


async def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User | None:
    """Return the authenticated user when a bearer token is present, else None.

    Invalid, expired, or unverifiable tokens fall back to anonymous.
    Community reads should use ``require_community_access`` instead so guests
    must present a server-issued age token.
    """
    return await _optional_user(request, credentials, session, settings)


async def require_community_access(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    x_guest_age_token: Annotated[str | None, Header(alias="X-Guest-Age-Token")] = None,
) -> User | None:
    """Allow community GETs for an authenticated user or a valid guest age token.

    The Daily Prompt and policy documents stay ungated. Invalid bearer tokens
    fall back to the guest-token path so a stale session still works after
    the guest declaration.
    """
    viewer = await _optional_user(request, credentials, session, settings)
    if viewer is not None:
        return viewer
    if x_guest_age_token:
        verify_guest_age_token(x_guest_age_token, settings)
        return None
    raise missing_guest_age_error()
