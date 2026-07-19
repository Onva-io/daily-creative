"""Create submission_likes, reflections, and activity_events tables.

Revision ID: 0008_likes_reflections_activity
Revises: 0007_uploads_submissions
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008_likes_reflections_activity"
down_revision: str | None = "0007_uploads_submissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

reflection_status = postgresql.ENUM(
    "published",
    "hidden",
    "removed",
    "deleted",
    name="reflection_status",
    create_type=False,
)

activity_event_type = postgresql.ENUM(
    "submission_liked",
    "reflection_added",
    name="activity_event_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "published",
        "hidden",
        "removed",
        "deleted",
        name="reflection_status",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "submission_liked",
        "reflection_added",
        name="activity_event_type",
    ).create(bind, checkfirst=True)

    op.create_table(
        "submission_likes",
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("submission_id", "user_id"),
    )
    op.create_index(
        "ix_submission_likes_user_id_created_at",
        "submission_likes",
        ["user_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "reflections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", reflection_status, nullable=False),
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
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reflections_submission_id_created_at_id",
        "reflections",
        ["submission_id", sa.text("created_at ASC"), sa.text("id ASC")],
    )
    op.create_index(
        "ix_reflections_user_id_created_at",
        "reflections",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_reflections_active",
        "reflections",
        ["submission_id", sa.text("created_at ASC"), sa.text("id ASC")],
        postgresql_where=sa.text("status = 'published' AND deleted_at IS NULL"),
    )

    op.create_table(
        "activity_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", activity_event_type, nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=True),
        sa.Column("reflection_id", sa.Uuid(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reflection_id"], ["reflections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_activity_events_recipient_user_id_created_at",
        "activity_events",
        ["recipient_user_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_activity_events_recipient_user_id_created_at",
        table_name="activity_events",
    )
    op.drop_table("activity_events")
    op.drop_index("ix_reflections_active", table_name="reflections")
    op.drop_index("ix_reflections_user_id_created_at", table_name="reflections")
    op.drop_index("ix_reflections_submission_id_created_at_id", table_name="reflections")
    op.drop_table("reflections")
    op.drop_index("ix_submission_likes_user_id_created_at", table_name="submission_likes")
    op.drop_table("submission_likes")

    bind = op.get_bind()
    activity_event_type.drop(bind, checkfirst=True)
    reflection_status.drop(bind, checkfirst=True)
