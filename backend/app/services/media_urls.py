"""Signed media URL helpers for display derivatives and avatars."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.models.upload import Upload
from app.storage.base import StorageAdapter


async def signed_display_url(
    *,
    storage: StorageAdapter,
    original_key: str,
    expires_at: datetime,
) -> str:
    """Return a signed read URL for the display derivative of an original key."""
    display_key = storage.derivative_key(original_key=original_key, kind="display")
    return await storage.read_url(key=display_key, expires_at=expires_at)


async def signed_thumbnail_url(
    *,
    storage: StorageAdapter,
    original_key: str,
    expires_at: datetime,
) -> str:
    """Return a signed read URL for the thumbnail derivative of an original key."""
    thumbnail_key = storage.derivative_key(original_key=original_key, kind="thumbnail")
    return await storage.read_url(key=thumbnail_key, expires_at=expires_at)


async def resolve_avatar_url(
    *,
    storage: StorageAdapter,
    upload: Upload | None,
    expires_at: datetime,
) -> str | None:
    """Return a signed avatar display URL, or None when no upload is available."""
    if upload is None:
        return None
    return await signed_display_url(
        storage=storage,
        original_key=upload.storage_key,
        expires_at=expires_at,
    )


async def resolve_avatar_urls(
    *,
    storage: StorageAdapter,
    uploads_by_id: dict[uuid.UUID, Upload],
    avatar_upload_ids: list[uuid.UUID | None],
    expires_at: datetime,
) -> dict[uuid.UUID, str | None]:
    """Batch-resolve avatar display URLs keyed by avatar upload id.

    Missing upload ids map to None.
    """
    unique_ids = {upload_id for upload_id in avatar_upload_ids if upload_id is not None}
    resolved: dict[uuid.UUID, str | None] = {}
    for upload_id in unique_ids:
        upload = uploads_by_id.get(upload_id)
        resolved[upload_id] = await resolve_avatar_url(
            storage=storage,
            upload=upload,
            expires_at=expires_at,
        )
    return resolved
