"""Upload API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.upload import Upload


class UploadPurposeSchema(str, Enum):
    submission = "submission"
    avatar = "avatar"


class UploadStatusSchema(str, Enum):
    pending = "pending"
    uploaded = "uploaded"
    verified = "verified"
    processing = "processing"
    ready = "ready"
    consumed = "consumed"
    failed = "failed"
    expired = "expired"
    deleted = "deleted"


class CreateUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: UploadPurposeSchema
    content_type: str = Field(min_length=1, max_length=128)
    byte_size: int = Field(ge=1)


class SignedUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    method: str
    headers: dict[str, str]
    expires_at: datetime
    max_bytes: int
    content_type: str


class UploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    purpose: UploadPurposeSchema
    status: UploadStatusSchema
    content_type: str
    byte_size: int | None
    width: int | None
    height: int | None
    created_at: datetime
    uploaded_at: datetime | None
    verified_at: datetime | None
    consumed_at: datetime | None
    expires_at: datetime
    signed_upload: SignedUploadResponse | None = None

    @classmethod
    def from_orm(
        cls,
        upload: Upload,
        *,
        signed_upload: SignedUploadResponse | None = None,
    ) -> UploadResponse:
        return cls(
            id=upload.id,
            purpose=UploadPurposeSchema(upload.purpose.value),
            status=UploadStatusSchema(upload.status.value),
            content_type=upload.content_type,
            byte_size=upload.byte_size,
            width=upload.width,
            height=upload.height,
            created_at=upload.created_at,
            uploaded_at=upload.uploaded_at,
            verified_at=upload.verified_at,
            consumed_at=upload.consumed_at,
            expires_at=upload.expires_at,
            signed_upload=signed_upload,
        )
