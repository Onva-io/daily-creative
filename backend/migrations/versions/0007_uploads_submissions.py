"""Create uploads and submissions tables.

Revision ID: 0007_uploads_submissions
Revises: 0006_idempotency_keys
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007_uploads_submissions"
down_revision: str | None = "0006_idempotency_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

upload_purpose = postgresql.ENUM(
    "submission",
    "avatar",
    name="upload_purpose",
    create_type=False,
)

upload_status = postgresql.ENUM(
    "pending",
    "uploaded",
    "verified",
    "processing",
    "ready",
    "consumed",
    "failed",
    "expired",
    "deleted",
    name="upload_status",
    create_type=False,
)

derivative_status = postgresql.ENUM(
    "pending",
    "ready",
    "failed",
    name="derivative_status",
    create_type=False,
)

submission_visibility = postgresql.ENUM(
    "public",
    name="submission_visibility",
    create_type=False,
)

submission_status = postgresql.ENUM(
    "processing",
    "published",
    "hidden",
    "removed",
    "deleted",
    name="submission_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "submission",
        "avatar",
        name="upload_purpose",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "pending",
        "uploaded",
        "verified",
        "processing",
        "ready",
        "consumed",
        "failed",
        "expired",
        "deleted",
        name="upload_status",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "pending",
        "ready",
        "failed",
        name="derivative_status",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "public",
        name="submission_visibility",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "processing",
        "published",
        "hidden",
        "removed",
        "deleted",
        name="submission_status",
    ).create(bind, checkfirst=True)

    op.create_table(
        "uploads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", upload_purpose, nullable=False),
        sa.Column("status", upload_status, nullable=False),
        sa.Column("storage_bucket", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column("derivative_status", derivative_status, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_uploads_storage_key"),
    )
    op.create_index(
        "ix_uploads_user_id_created_at",
        "uploads",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_uploads_status_expires_at",
        "uploads",
        ["status", "expires_at"],
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_id", sa.Uuid(), nullable=False),
        sa.Column("sketch_session_id", sa.Uuid(), nullable=False),
        sa.Column("upload_id", sa.Uuid(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("visibility", submission_visibility, nullable=False),
        sa.Column("status", submission_status, nullable=False),
        sa.Column("like_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reflection_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_id"], ["daily_prompts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["sketch_session_id"],
            ["sketch_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sketch_session_id", name="uq_submissions_sketch_session_id"),
        sa.UniqueConstraint("upload_id", name="uq_submissions_upload_id"),
    )
    op.create_index(
        "ix_submissions_published_at_id",
        "submissions",
        [sa.text("published_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_submissions_user_id_published_at_id",
        "submissions",
        ["user_id", sa.text("published_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_submissions_prompt_id_published_at_id",
        "submissions",
        ["prompt_id", sa.text("published_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_submissions_published_active",
        "submissions",
        [sa.text("published_at DESC"), sa.text("id DESC")],
        postgresql_where=sa.text("status = 'published' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_submissions_published_active", table_name="submissions")
    op.drop_index("ix_submissions_prompt_id_published_at_id", table_name="submissions")
    op.drop_index("ix_submissions_user_id_published_at_id", table_name="submissions")
    op.drop_index("ix_submissions_published_at_id", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_uploads_status_expires_at", table_name="uploads")
    op.drop_index("ix_uploads_user_id_created_at", table_name="uploads")
    op.drop_table("uploads")

    bind = op.get_bind()
    submission_status.drop(bind, checkfirst=True)
    submission_visibility.drop(bind, checkfirst=True)
    derivative_status.drop(bind, checkfirst=True)
    upload_status.drop(bind, checkfirst=True)
    upload_purpose.drop(bind, checkfirst=True)
