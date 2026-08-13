"""Unit tests for account-deletion anonymization and Descope teardown."""

from __future__ import annotations

import uuid

from app.auth.descope_mgmt import is_descope_not_found
from app.core.clock import SystemClock
from app.core.settings import Settings
from app.models.user import User, UserStatus
from app.services.account_deletion import DELETED_DISPLAY_NAME, AccountDeletionService
from descope import AuthException


def _settings(**kwargs: str) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        DESCOPE_PROJECT_ID="P123",
        DESCOPE_MANAGEMENT_KEY="mgmt-key",  # pragma: allowlist secret
        **kwargs,  # type: ignore[arg-type]
    )


def test_anonymize_user_clears_identifying_fields() -> None:
    user = User(
        id=uuid.uuid4(),
        descope_subject="descope|abc",
        username="ada",
        username_normalized="ada",
        display_name="Ada Lovelace",
        bio="notes",
        status=UserStatus.pending_deletion,
    )
    service = AccountDeletionService(
        session=None,  # type: ignore[arg-type]
        clock=SystemClock(),
        settings=_settings(),
    )
    service._anonymize_user(user)
    assert user.username is None
    assert user.username_normalized is None
    assert user.display_name == DELETED_DISPLAY_NAME
    assert user.bio is None
    assert user.date_of_birth is None
    assert user.avatar_upload_id is None
    assert user.descope_subject == f"deleted:{user.id}"


def test_descope_deletion_invokes_management_api() -> None:
    seen: list[tuple[str, str, str]] = []

    def deleter(project_id: str, management_key: str, subject: str) -> None:
        seen.append((project_id, management_key, subject))

    settings = _settings()
    service = AccountDeletionService(
        session=None,  # type: ignore[arg-type]
        clock=SystemClock(),
        settings=settings,
        descope_deleter=deleter,
    )
    user = User(id=uuid.uuid4(), descope_subject="U2abc", display_name="Ada")
    service._coordinate_descope_deletion(user)
    assert seen == [("P123", "mgmt-key", "U2abc")]


def test_descope_deletion_skips_when_already_tombstoned() -> None:
    seen: list[str] = []
    settings = _settings()
    service = AccountDeletionService(
        session=None,  # type: ignore[arg-type]
        clock=SystemClock(),
        settings=settings,
        descope_deleter=lambda *_args: seen.append("called"),
    )
    user = User(id=uuid.uuid4(), descope_subject="deleted:already", display_name="Ada")
    service._coordinate_descope_deletion(user)
    assert seen == []


def test_descope_not_found_is_idempotent() -> None:
    assert is_descope_not_found(AuthException(404, "not found", "user not found"))
    assert not is_descope_not_found(AuthException(500, "server error", "boom"))
    assert not is_descope_not_found(RuntimeError("nope"))
