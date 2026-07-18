"""Object-storage adapter interface.

Phase 1 defines the contract only. Signed upload/read implementations arrive
in Phase 7. The default adapter raises if invoked so missing wiring is obvious.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SignedUpload:
    """Details required for a direct client upload."""

    upload_id: UUID
    url: str
    method: str
    headers: dict[str, str]
    expires_at: datetime
    max_bytes: int
    content_type: str


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    """Verified object metadata from storage."""

    key: str
    content_type: str
    byte_size: int
    etag: str | None = None


class StorageAdapter(Protocol):
    """S3-compatible storage operations used by upload and media flows."""

    async def create_signed_upload(
        self,
        *,
        key: str,
        content_type: str,
        max_bytes: int,
        expires_at: datetime,
    ) -> SignedUpload:
        """Create a short-lived signed upload URL for exactly one object key."""
        ...

    async def verify_object(self, *, key: str) -> ObjectMetadata:
        """Confirm the object exists and return its metadata."""
        ...

    async def read_url(self, *, key: str, expires_at: datetime) -> str:
        """Return a short-lived signed read URL for an object."""
        ...

    async def delete_object(self, *, key: str) -> None:
        """Delete a single object."""
        ...

    def derivative_key(self, *, original_key: str, kind: str) -> str:
        """Derive a stable object key for a display or thumbnail derivative."""
        ...


class NotConfiguredStorageAdapter:
    """Stub adapter used until Phase 7 wiring. Raises if called."""

    async def create_signed_upload(
        self,
        *,
        key: str,
        content_type: str,
        max_bytes: int,
        expires_at: datetime,
    ) -> SignedUpload:
        raise NotImplementedError("Storage adapter is not configured in Phase 1.")

    async def verify_object(self, *, key: str) -> ObjectMetadata:
        raise NotImplementedError("Storage adapter is not configured in Phase 1.")

    async def read_url(self, *, key: str, expires_at: datetime) -> str:
        raise NotImplementedError("Storage adapter is not configured in Phase 1.")

    async def delete_object(self, *, key: str) -> None:
        raise NotImplementedError("Storage adapter is not configured in Phase 1.")

    def derivative_key(self, *, original_key: str, kind: str) -> str:
        raise NotImplementedError("Storage adapter is not configured in Phase 1.")


def get_storage_adapter() -> StorageAdapter:
    """FastAPI dependency returning the Phase 1 stub adapter."""
    return NotConfiguredStorageAdapter()
