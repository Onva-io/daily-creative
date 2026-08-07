"""Moderation operator principal and dual-path auth (admin JWT or shared token)."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import TokenVerifier, get_token_verifier
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.db.session import get_db_session
from app.models.user import UserStatus
from app.services.users import UserService

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class OperatorPrincipal:
    """Authenticated moderation operator (named admin or shared token)."""

    identity: str
    user_id: uuid.UUID | None = None


async def require_moderation_operator(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    x_moderation_token: Annotated[str | None, Header(alias="X-Moderation-Token")] = None,
) -> OperatorPrincipal:
    """Allow Descope admin Bearer JWT or the shared moderation operator token.

    Independent OR: a valid admin session yields ``user:<uuid>``; otherwise a matching
    ``X-Moderation-Token`` yields ``token:operator``. Invalid Bearer still returns 401.
    Non-admin Bearer falls through to the shared-token check.
    """
    if (
        credentials is not None
        and credentials.scheme.lower() == "bearer"
        and credentials.credentials
    ):
        verifier: TokenVerifier = getattr(
            request.app.state, "token_verifier", None
        ) or get_token_verifier(settings)
        verified = verifier.verify(credentials.credentials)
        admin_role = settings.descope_admin_role
        if admin_role in verified.roles:
            user = await UserService(session).resolve_or_provision(verified)
            if user.status == UserStatus.active:
                return OperatorPrincipal(
                    identity=f"user:{user.id}",
                    user_id=user.id,
                )

    expected = settings.moderation_operator_token
    if expected and x_moderation_token and secrets.compare_digest(x_moderation_token, expected):
        return OperatorPrincipal(identity="token:operator", user_id=None)

    raise AppError(
        code="moderation_forbidden",
        message="Moderation access is not permitted.",
        status_code=403,
    )
