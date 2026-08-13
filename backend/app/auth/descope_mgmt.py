"""Descope management-API helpers (account deletion and similar operator work)."""

from __future__ import annotations

import logging
from collections.abc import Callable

from descope import AuthException, DescopeClient

logger = logging.getLogger(__name__)

DescopeUserDeleter = Callable[[str, str, str], None]


def delete_descope_user(*, project_id: str, management_key: str, subject: str) -> None:
    """Permanently delete the Descope user identified by JWT subject.

    Raises AuthException (or other SDK errors) on failure so callers can log
    without treating a missing key as success.
    """
    client = DescopeClient(project_id=project_id, management_key=management_key)
    client.mgmt.user.delete_by_user_id(subject)


def is_descope_not_found(exc: BaseException) -> bool:
    """True when the IdP already has no such user (idempotent finalize)."""
    if not isinstance(exc, AuthException):
        return False
    message = f"{exc.error_message or ''} {exc.status_code}".lower()
    return "not found" in message or "404" in message
