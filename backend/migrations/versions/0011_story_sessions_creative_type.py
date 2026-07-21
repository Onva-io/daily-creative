"""Add story sessions, creative type, and multi-type submission support.

Revision ID: 0011_story_sessions_creative_type
Revises: 0010_blocks_reports
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011_story_sessions_creative_type"
down_revision: str | None = "0010_blocks_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

creative_type = postgresql.ENUM(
    "sketch",
    "story",
    name="creative_type",
    create_type=False,
)

story_session_status = postgresql.ENUM(
    "active",
    "paused",
    "writing",
    "completed",
    "abandoned",
    "expired",
    name="story_session_status",
    create_type=False,
)

story_session_event_type = postgresql.ENUM(
    "started",
    "paused",
    "resumed",
    "timer_completed",
    "finished_early",
    "writing_started",
    "draft_saved",
    "submission_created",
    "abandoned",
    name="story_session_event_type",
    create_type=False,
)

timer_mode = postgresql.ENUM(
    "countdown",
    "no_timer",
    name="timer_mode",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # Create new enum types.
    postgresql.ENUM(
        "sketch",
        "story",
        name="creative_type",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "active",
        "paused",
        "writing",
        "completed",
        "abandoned",
        "expired",
        name="story_session_status",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "started",
        "paused",
        "resumed",
        "timer_completed",
        "finished_early",
        "writing_started",
        "draft_saved",
        "submission_created",
        "abandoned",
        name="story_session_event_type",
    ).create(bind, checkfirst=True)

    # -- story_sessions table --
    op.create_table(
        "story_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_id", sa.Uuid(), nullable=False),
        sa.Column("timer_mode", timer_mode, nullable=False),
        sa.Column("selected_timer_seconds", sa.Integer(), nullable=True),
        sa.Column("status", story_session_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paused_total_seconds", sa.Integer(), nullable=False),
        sa.Column("timer_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finish_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_id"], ["daily_prompts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_story_sessions_user_id_created_at",
        "story_sessions",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_story_sessions_prompt_id_created_at",
        "story_sessions",
        ["prompt_id", sa.text("created_at DESC")],
    )

    # -- story_session_events table --
    op.create_table(
        "story_session_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("story_session_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", story_session_event_type, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["story_session_id"],
            ["story_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_story_session_events_story_session_id",
        "story_session_events",
        ["story_session_id"],
    )

    # -- Extend submissions table --
    # Add creative_type column with server default for backfill.
    op.add_column(
        "submissions",
        sa.Column(
            "creative_type",
            creative_type,
            server_default=sa.text("'sketch'"),
            nullable=False,
        ),
    )
    # Backfill existing rows.
    op.execute("UPDATE submissions SET creative_type = 'sketch' WHERE creative_type IS NULL")
    # Remove server default after backfill.
    op.alter_column("submissions", "creative_type", server_default=None)

    # Drop unique constraints before making columns nullable.
    op.drop_constraint("uq_submissions_sketch_session_id", "submissions", type_="unique")
    op.drop_constraint("uq_submissions_upload_id", "submissions", type_="unique")

    # Make sketch_session_id nullable.
    op.alter_column(
        "submissions",
        "sketch_session_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # Make upload_id nullable.
    op.alter_column(
        "submissions",
        "upload_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # Add story_session_id column.
    op.add_column(
        "submissions",
        sa.Column("story_session_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_submissions_story_session_id",
        "submissions",
        "story_sessions",
        ["story_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Add body column.
    op.add_column(
        "submissions",
        sa.Column("body", sa.Text(), nullable=True),
    )

    # Add check constraint: exactly one session FK must be non-null.
    op.create_check_constraint(
        "ck_submissions_session_xor",
        "submissions",
        sa.text(
            "(sketch_session_id IS NOT NULL AND story_session_id IS NULL) OR "
            "(sketch_session_id IS NULL AND story_session_id IS NOT NULL)"
        ),
    )

    # Add index on creative_type for filtered queries.
    op.create_index(
        "ix_submissions_creative_type",
        "submissions",
        ["creative_type"],
    )

    # -- creative_type_preferences table --
    op.create_table(
        "creative_type_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("creative_type", creative_type, nullable=False),
        sa.Column(
            "remember_timer_option", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("remembered_timer_mode", timer_mode, nullable=True),
        sa.Column("remembered_timer_seconds", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "creative_type"),
    )


def downgrade() -> None:
    op.drop_table("creative_type_preferences")
    op.drop_index("ix_submissions_creative_type", table_name="submissions")
    op.drop_constraint("ck_submissions_session_xor", "submissions", type_="check")
    op.drop_column("submissions", "body")
    op.drop_constraint("fk_submissions_story_session_id", "submissions", type_="foreignkey")
    op.drop_column("submissions", "story_session_id")
    op.drop_column("submissions", "creative_type")
    op.alter_column(
        "submissions",
        "upload_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_unique_constraint("uq_submissions_upload_id", "submissions", ["upload_id"])
    op.alter_column(
        "submissions",
        "sketch_session_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_submissions_sketch_session_id", "submissions", ["sketch_session_id"]
    )
    op.drop_index("ix_story_session_events_story_session_id", table_name="story_session_events")
    op.drop_table("story_session_events")
    op.drop_index("ix_story_sessions_prompt_id_created_at", table_name="story_sessions")
    op.drop_index("ix_story_sessions_user_id_created_at", table_name="story_sessions")
    op.drop_table("story_sessions")
    postgresql.ENUM(name="story_session_event_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="story_session_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="creative_type").drop(op.get_bind(), checkfirst=True)
