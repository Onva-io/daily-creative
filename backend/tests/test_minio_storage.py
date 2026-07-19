"""Optional MinIO-backed storage adapter smoke test.

Skipped unless STORAGE_TEST=1 so default CI/local suites stay green
without requiring live object storage for the primary test path.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.settings import Settings
from app.storage.minio import MinioStorageAdapter

requires_storage = pytest.mark.skipif(
    os.environ.get("STORAGE_TEST") != "1",
    reason="Set STORAGE_TEST=1 to run MinIO adapter tests",
)


@requires_storage
@pytest.mark.asyncio
async def test_minio_put_head_download_delete_roundtrip() -> None:
    settings = Settings()
    adapter = MinioStorageAdapter(settings)
    key = f"tests/{uuid4()}/original"
    body = b"phase7-minio-smoke"
    content_type = "image/jpeg"

    await adapter.put_object(key=key, body=body, content_type=content_type)
    meta = await adapter.verify_object(key=key)
    assert meta.key == key
    assert meta.byte_size == len(body)
    assert meta.content_type == content_type

    downloaded = await adapter.download_object(key=key)
    assert downloaded == body

    expires_at = datetime.now(UTC) + timedelta(minutes=5)
    read_url = await adapter.read_url(key=key, expires_at=expires_at)
    assert read_url.startswith("http")

    await adapter.delete_object(key=key)
    with pytest.raises(Exception) as exc_info:
        await adapter.verify_object(key=key)
    assert getattr(exc_info.value, "code", None) == "object_missing"
