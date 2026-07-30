"""Versioned policy documents and per-user acceptance records."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PolicyKind(str, enum.Enum):
    """Kinds of versioned legal / community documents."""

    terms = "terms"
    privacy = "privacy"
    community_guidelines = "community_guidelines"


class PolicyStatus(str, enum.Enum):
    """Publication lifecycle for a policy document version."""

    draft = "draft"
    published = "published"
    superseded = "superseded"


class PolicyDocument(Base):
    """Immutable published policy document version (drafts are mutable until published)."""

    __tablename__ = "policy_documents"
    __table_args__ = (
        UniqueConstraint("kind", "version", name="uq_policy_documents_kind_version"),
        Index("ix_policy_documents_kind_status", "kind", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[PolicyKind] = mapped_column(
        Enum(PolicyKind, name="policy_kind", native_enum=True),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    minimum_age: Mapped[int] = mapped_column(Integer, nullable=False, default=13)
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus, name="policy_status", native_enum=True),
        nullable=False,
        default=PolicyStatus.draft,
    )
    is_significant_change: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PolicyAcceptance(Base):
    """Append-only record that a user accepted a specific policy document version."""

    __tablename__ = "policy_acceptances"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "policy_document_id",
            name="uq_policy_acceptances_user_document",
        ),
        Index("ix_policy_acceptances_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("policy_documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    app_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(32), nullable=True)
