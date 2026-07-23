"""JWT verification for Descope-issued session tokens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from descope import AuthException, DescopeClient

from app.core.errors import AppError
from app.core.settings import Settings


@dataclass(frozen=True, slots=True)
class VerifiedToken:
    """Claims extracted from a verified Descope JWT."""

    subject: str
    claims: dict[str, Any]

    @property
    def display_name(self) -> str | None:
        name = self.claims.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
        return None


class TokenVerifier(Protocol):
    """Protocol for JWT verification (real Descope SDK or test double)."""

    def verify(self, token: str) -> VerifiedToken: ...


class DescopeTokenVerifier:
    """Verify Descope session JWTs via the official Python SDK."""

    def __init__(self, settings: Settings, client: DescopeClient | None = None) -> None:
        self._settings = settings
        self._client = client or DescopeClient(project_id=settings.descope_project_id)

    def verify(self, token: str) -> VerifiedToken:
        try:
            jwt_response = self._client.validate_session(
                session_token=token,
                audience=self._settings.resolved_descope_audience,
            )
        except AuthException as exc:
            reason = "token_expired" if _is_expired_auth_exception(exc) else "invalid_token"
            raise AppError(
                code="unauthenticated",
                message="Authentication is required.",
                status_code=401,
                details={"reason": reason},
            ) from exc

        subject = jwt_response.get("userId") or jwt_response.get("sub")
        if not isinstance(subject, str) or not subject:
            raise AppError(
                code="unauthenticated",
                message="Authentication is required.",
                status_code=401,
                details={"reason": "missing_subject"},
            )
        return VerifiedToken(subject=subject, claims=jwt_response)


def _is_expired_auth_exception(exc: AuthException) -> bool:
    message = (exc.error_message or "").lower()
    return "expired" in message


_verifier: TokenVerifier | None = None


def get_token_verifier(settings: Settings) -> TokenVerifier:
    global _verifier
    if _verifier is None:
        if settings.descope_project_id == "replace-me" or settings.descope_project_id.startswith(
            "replace-me"
        ):
            from app.auth.local_dev import LocalDevTokenVerifier

            _verifier = LocalDevTokenVerifier()
        else:
            _verifier = DescopeTokenVerifier(settings)
    return _verifier


def set_token_verifier(verifier: TokenVerifier | None) -> None:
    """Override the process-wide verifier (tests)."""
    global _verifier
    _verifier = verifier
