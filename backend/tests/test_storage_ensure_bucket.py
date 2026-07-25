"""Unit tests for MinIO bucket ensure + public endpoint normalization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.core.settings import Settings
from app.storage.minio import MinioStorageAdapter


def _client_error(*, code: str, http_status: int = 404) -> ClientError:
    return ClientError(
        {
            "Error": {"Code": code, "Message": "missing"},
            "ResponseMetadata": {"HTTPStatusCode": http_status},
        },
        "HeadBucket",
    )


def test_resolved_storage_public_endpoint_strips_default_https_port() -> None:
    settings = Settings(
        STORAGE_ENDPOINT="http://minio:9000",
        STORAGE_PUBLIC_ENDPOINT="https://bucket.example.com:443",
    )
    assert settings.resolved_storage_public_endpoint == "https://bucket.example.com"


@pytest.mark.asyncio
async def test_ensure_bucket_creates_when_missing() -> None:
    settings = Settings(STORAGE_BUCKET="test-media")
    adapter = MinioStorageAdapter(settings)
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = _client_error(code="404")
    adapter._client = mock_client

    await adapter.ensure_bucket()

    mock_client.create_bucket.assert_called_once_with(Bucket="test-media")


@pytest.mark.asyncio
async def test_ensure_bucket_noop_when_present() -> None:
    settings = Settings(STORAGE_BUCKET="test-media")
    adapter = MinioStorageAdapter(settings)
    mock_client = MagicMock()
    adapter._client = mock_client

    await adapter.ensure_bucket()

    mock_client.head_bucket.assert_called_once_with(Bucket="test-media")
    mock_client.create_bucket.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_bucket_ignores_already_exists_race() -> None:
    settings = Settings(STORAGE_BUCKET="test-media")
    adapter = MinioStorageAdapter(settings)
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = _client_error(code="NoSuchBucket")
    mock_client.create_bucket.side_effect = _client_error(
        code="BucketAlreadyOwnedByYou",
        http_status=409,
    )
    adapter._client = mock_client

    await adapter.ensure_bucket()


@pytest.mark.asyncio
async def test_create_signed_upload_uses_normalized_public_endpoint() -> None:
    settings = Settings(
        STORAGE_ENDPOINT="http://minio:9000",
        STORAGE_PUBLIC_ENDPOINT="https://bucket.example.com:443",
        STORAGE_ACCESS_KEY="key",
        STORAGE_SECRET_KEY="secret",  # pragma: allowlist secret
    )
    with patch.object(MinioStorageAdapter, "_build_client") as build:
        public_client = MagicMock()
        public_client.generate_presigned_url.return_value = (
            "https://bucket.example.com/test-media/key?X-Amz-Signature=abc"
        )
        build.side_effect = [MagicMock(), public_client]
        adapter = MinioStorageAdapter(settings)

    from datetime import UTC, datetime, timedelta

    signed = await adapter.create_signed_upload(
        key="users/x/original",
        content_type="image/jpeg",
        max_bytes=1000,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    assert "bucket.example.com:443" not in signed.url
    # First client is internal endpoint; second is public without :443
    assert build.call_args_list[1].args[0] == "https://bucket.example.com"
