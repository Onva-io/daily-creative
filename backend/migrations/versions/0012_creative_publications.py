"""Migrate submissions to creative_publications with typed detail tables.

Revision ID: 0012_creative_publications
Revises: 0011_story_sessions_creative_type
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012_creative_publications"
down_revision: str | None = "0011_story_sessions_creative_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

creative_type = sa.Enum("sketch", "story", name="creative_type", create_type=False)
submission_visibility = sa.Enum("public", name="submission_visibility", create_type=False)
submission_status = sa.Enum(
    "processing",
    "published",
    "hidden",
    "removed",
    "deleted",
    name="submission_status",
    create_type=False,
)


def upgrade() -> None:
    # -- creative_publications anchor table --
    op.create_table(
        "creative_publications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_id", sa.Uuid(), nullable=False),
        sa.Column("creative_type", creative_type, nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("visibility", submission_visibility, nullable=False),
        sa.Column("status", submission_status, nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("reflection_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_creative_publications_creative_type",
        "creative_publications",
        ["creative_type"],
    )
    op.create_index(
        "ix_creative_publications_user_id_published_at",
        "creative_publications",
        ["user_id", sa.text("published_at DESC")],
    )

    # -- typed detail tables --
    op.create_table(
        "sketch_submissions",
        sa.Column("publication_id", sa.Uuid(), nullable=False),
        sa.Column("sketch_session_id", sa.Uuid(), nullable=False),
        sa.Column("upload_id", sa.Uuid(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["creative_publications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sketch_session_id"],
            ["sketch_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("publication_id"),
        sa.UniqueConstraint("sketch_session_id"),
        sa.UniqueConstraint("upload_id"),
    )

    op.create_table(
        "story_submissions",
        sa.Column("publication_id", sa.Uuid(), nullable=False),
        sa.Column("story_session_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["creative_publications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["story_session_id"],
            ["story_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("publication_id"),
        sa.UniqueConstraint("story_session_id"),
    )

    # -- migrate existing submissions data --
    op.execute(
        """
        INSERT INTO creative_publications (
            id, user_id, prompt_id, creative_type, session_id,
            visibility, status, like_count, reflection_count,
            published_at, created_at, updated_at, deleted_at
        )
        SELECT
            id,
            user_id,
            prompt_id,
            creative_type,
            COALESCE(sketch_session_id, story_session_id),
            visibility,
            status,
            like_count,
            reflection_count,
            published_at,
            created_at,
            updated_at,
            deleted_at
        FROM submissions
        """
    )

    op.execute(
        """
        INSERT INTO sketch_submissions (publication_id, sketch_session_id, upload_id, caption)
        SELECT id, sketch_session_id, upload_id, caption
        FROM submissions
        WHERE creative_type = 'sketch'
        """
    )

    op.execute(
        """
        INSERT INTO story_submissions (publication_id, story_session_id, body, caption)
        SELECT id, story_session_id, body, caption
        FROM submissions
        WHERE creative_type = 'story'
        """
    )

    # -- publication_likes (replaces submission_likes) --
    op.create_table(
        "publication_likes",
        sa.Column("publication_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["creative_publications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("publication_id", "user_id"),
    )

    op.execute(
        """
        INSERT INTO publication_likes (publication_id, user_id, created_at)
        SELECT submission_id, user_id, created_at
        FROM submission_likes
        """
    )
    op.drop_table("submission_likes")

    # -- reflections: repoint FK to creative_publications --
    op.drop_constraint("reflections_submission_id_fkey", "reflections", type_="foreignkey")
    op.create_foreign_key(
        "reflections_publication_id_fkey",
        "reflections",
        "creative_publications",
        ["submission_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # -- activity_events: repoint FK to creative_publications --
    op.drop_constraint("activity_events_submission_id_fkey", "activity_events", type_="foreignkey")
    op.create_foreign_key(
        "activity_events_publication_id_fkey",
        "activity_events",
        "creative_publications",
        ["submission_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- drop legacy submissions table --
    op.drop_index("ix_submissions_creative_type", table_name="submissions")
    op.drop_constraint("ck_submissions_session_xor", "submissions", type_="check")
    op.drop_constraint("fk_submissions_story_session_id", "submissions", type_="foreignkey")
    op.drop_table("submissions")

    # -- move timer prefs from user_preferences to creative_type_preferences --
    op.execute(
        """
        INSERT INTO creative_type_preferences (
            user_id,
            creative_type,
            remember_timer_option,
            remembered_timer_mode,
            remembered_timer_seconds
        )
        SELECT
            user_id,
            'sketch',
            remember_timer_option,
            remembered_timer_mode,
            remembered_timer_seconds
        FROM user_preferences
        WHERE remember_timer_option = true
           OR remembered_timer_mode IS NOT NULL
           OR remembered_timer_seconds IS NOT NULL
        ON CONFLICT (user_id, creative_type) DO NOTHING
        """
    )
    op.drop_column("user_preferences", "remember_timer_option")
    op.drop_column("user_preferences", "remembered_timer_mode")
    op.drop_column("user_preferences", "remembered_timer_seconds")


def downgrade() -> None:
    raise NotImplementedError("0012_creative_publications downgrade is not supported")
