"""Opaque cursor encoding for keyset pagination."""

from __future__ import annotations

import base64
import binascii
import uuid
from datetime import datetime

from app.core.errors import AppError

_CURSOR_SEP = "|"


def encode_cursor(*, published_at: datetime, submission_id: uuid.UUID) -> str:
    """Encode a feed cursor from a published_at timestamp and submission id."""
    if published_at.tzinfo is None:
        raise ValueError("published_at must be timezone-aware")
    payload = f"{published_at.isoformat()}{_CURSOR_SEP}{submission_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode an opaque feed cursor into (published_at, submission_id)."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        published_at_raw, submission_id_raw = raw.split(_CURSOR_SEP, maxsplit=1)
        published_at = datetime.fromisoformat(published_at_raw)
        if published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
        submission_id = uuid.UUID(submission_id_raw)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise AppError(
            code="invalid_cursor",
            message="The feed cursor is invalid.",
            status_code=422,
        ) from exc
    return published_at, submission_id


def encode_reflection_cursor(*, created_at: datetime, reflection_id: uuid.UUID) -> str:
    """Encode a Reflection list cursor from created_at and reflection id."""
    if created_at.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    payload = f"{created_at.isoformat()}{_CURSOR_SEP}{reflection_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_reflection_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode an opaque Reflection cursor into (created_at, reflection_id)."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        created_at_raw, reflection_id_raw = raw.split(_CURSOR_SEP, maxsplit=1)
        created_at = datetime.fromisoformat(created_at_raw)
        if created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        reflection_id = uuid.UUID(reflection_id_raw)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise AppError(
            code="invalid_cursor",
            message="The reflection cursor is invalid.",
            status_code=422,
        ) from exc
    return created_at, reflection_id
