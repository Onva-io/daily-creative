"""Upload ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    Uuid,
    desc,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UploadPurpose(str, enum.Enum):
    """Intended use of an Upload."""

    submission = "submission"
    avatar = "avatar"


class UploadStatus(str, enum.Enum):
    """Upload lifecycle status."""

    pending = "pending"
    uploaded = "uploaded"
    verified = "verified"
    processing = "processing"
    ready = "ready"
    consumed = "consumed"
    failed = "failed"
    expired = "expired"
    deleted = "deleted"


class DerivativeStatus(str, enum.Enum):
    """Derivative generation status."""

    pending = "pending"
    ready = "ready"
    failed = "failed"


class Upload(Base):
    """Pending or consumed direct-upload slot and media metadata."""

    __tablename__ = "uploads"
    __table_args__ = (
        Index("ix_uploads_user_id_created_at", "user_id", desc("created_at")),
        Index("ix_uploads_status_expires_at", "status", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    purpose: Mapped[UploadPurpose] = mapped_column(
        Enum(UploadPurpose, name="upload_purpose", native_enum=True),
        nullable=False,
    )
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, name="upload_status", native_enum=True),
        nullable=False,
        default=UploadStatus.pending,
    )
    storage_bucket: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(Text, nullable=True)
    derivative_status: Mapped[DerivativeStatus | None] = mapped_column(
        Enum(DerivativeStatus, name="derivative_status", native_enum=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
