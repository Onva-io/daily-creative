"""Unified creative sessions/publications and per-app preferences.

Revision ID: 0004_unified_creative_model
Revises: 0003_admin_mod
Create Date: 2026-09-19

Replaces the per-type ``sketch_*``/``story_*`` session and submission tables
with one ``creative_sessions`` table (plus events) and type-specific JSONB
``content`` on ``creative_publications``. Existing rows are backfilled. Also
moves the daily reminder from account-wide ``user_preferences`` to per-app
``creative_type_preferences``.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_unified_creative_model"
down_revision: str | None = "0003_admin_mod"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- creative_sessions ------------------------------------------------
    creative_session_status = postgresql.ENUM(
        "active",
        "paused",
        "completed",
        "abandoned",
        "expired",
        name="creative_session_status",
        create_type=False,
    )
    creative_session_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "creative_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_id", sa.Uuid(), nullable=False),
        sa.Column(
            "creative_type",
            postgresql.ENUM(name="creative_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "timer_mode",
            postgresql.ENUM(name="timer_mode", create_type=False),
            nullable=False,
        ),
        sa.Column("selected_timer_seconds", sa.Integer(), nullable=True),
        sa.Column("status", creative_session_status, nullable=False),
        sa.Column("stage", sa.Text(), nullable=True),
        sa.Column(
            "stage_timestamps",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["prompt_id"],
            ["daily_prompts.id"],
            name=op.f("fk_creative_sessions_prompt_id_daily_prompts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_creative_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creative_sessions")),
    )
    op.create_index(
        "ix_creative_sessions_user_id_created_at",
        "creative_sessions",
        ["user_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_creative_sessions_prompt_id_created_at",
        "creative_sessions",
        ["prompt_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_creative_sessions_creative_type_status",
        "creative_sessions",
        ["creative_type", "status"],
        unique=False,
    )

    op.create_table(
        "creative_session_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["creative_sessions.id"],
            name=op.f("fk_creative_session_events_session_id_creative_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creative_session_events")),
    )
    op.create_index(
        "ix_creative_session_events_session_id",
        "creative_session_events",
        ["session_id"],
        unique=False,
    )

    # --- backfill sessions -----------------------------------------------
    op.execute(
        """
        INSERT INTO creative_sessions (
            id, user_id, prompt_id, creative_type, timer_mode, selected_timer_seconds,
            status, stage, stage_timestamps, started_at, paused_total_seconds,
            timer_completed_at, finish_requested_at, completed_at, abandoned_at,
            created_at, updated_at
        )
        SELECT
            id, user_id, prompt_id, 'sketch'::creative_type, timer_mode, selected_timer_seconds,
            CASE status::text
                WHEN 'ready_for_photo' THEN 'active'
                WHEN 'uploading' THEN 'active'
                ELSE status::text
            END::creative_session_status,
            CASE status::text
                WHEN 'ready_for_photo' THEN 'ready_for_photo'
                WHEN 'uploading' THEN 'uploading'
                ELSE NULL
            END,
            jsonb_strip_nulls(jsonb_build_object(
                'photo_step_reached_at', photo_step_reached_at,
                'upload_started_at', upload_started_at,
                'upload_completed_at', upload_completed_at
            )),
            started_at, paused_total_seconds, timer_completed_at, finish_requested_at,
            completed_at, abandoned_at, created_at, updated_at
        FROM sketch_sessions
        """
    )
    op.execute(
        """
        INSERT INTO creative_sessions (
            id, user_id, prompt_id, creative_type, timer_mode, selected_timer_seconds,
            status, stage, stage_timestamps, started_at, paused_total_seconds,
            timer_completed_at, finish_requested_at, completed_at, abandoned_at,
            created_at, updated_at
        )
        SELECT
            id, user_id, prompt_id, 'story'::creative_type, timer_mode, selected_timer_seconds,
            CASE status::text WHEN 'writing' THEN 'active' ELSE status::text END
                ::creative_session_status,
            CASE status::text WHEN 'writing' THEN 'writing' ELSE NULL END,
            '{}'::jsonb,
            started_at, paused_total_seconds, timer_completed_at, finish_requested_at,
            completed_at, abandoned_at, created_at, updated_at
        FROM story_sessions
        """
    )
    op.execute(
        """
        INSERT INTO creative_session_events (
            id, session_id, event_type, occurred_at, client_occurred_at, metadata_json, created_at
        )
        SELECT id, sketch_session_id, event_type::text, occurred_at, client_occurred_at,
               metadata_json, created_at
        FROM sketch_session_events
        UNION ALL
        SELECT id, story_session_id, event_type::text, occurred_at, client_occurred_at,
               metadata_json, created_at
        FROM story_session_events
        """
    )

    # --- creative_publications: shared columns + typed content ------------
    op.add_column("creative_publications", sa.Column("caption", sa.Text(), nullable=True))
    op.add_column("creative_publications", sa.Column("upload_id", sa.Uuid(), nullable=True))
    op.add_column(
        "creative_publications",
        sa.Column(
            "content",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE creative_publications AS p
        SET caption = s.caption, upload_id = s.upload_id, content = '{}'::jsonb
        FROM sketch_submissions AS s
        WHERE s.publication_id = p.id
        """
    )
    op.execute(
        """
        UPDATE creative_publications AS p
        SET caption = s.caption, content = jsonb_build_object('body', s.body)
        FROM story_submissions AS s
        WHERE s.publication_id = p.id
        """
    )
    op.create_foreign_key(
        op.f("fk_creative_publications_session_id_creative_sessions"),
        "creative_publications",
        "creative_sessions",
        ["session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        op.f("uq_creative_publications_session_id"),
        "creative_publications",
        ["session_id"],
    )
    op.create_foreign_key(
        op.f("fk_creative_publications_upload_id_uploads"),
        "creative_publications",
        "uploads",
        ["upload_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        op.f("uq_creative_publications_upload_id"),
        "creative_publications",
        ["upload_id"],
    )

    # --- drop per-type tables ---------------------------------------------
    op.drop_table("sketch_submissions")
    op.drop_table("story_submissions")
    op.drop_table("sketch_session_events")
    op.drop_table("story_session_events")
    op.drop_table("sketch_sessions")
    op.drop_table("story_sessions")
    for enum_name in (
        "sketch_session_status",
        "sketch_session_event_type",
        "story_session_status",
        "story_session_event_type",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

    # --- per-app daily reminder -------------------------------------------
    op.add_column(
        "creative_type_preferences",
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "creative_type_preferences",
        sa.Column("notification_time_local", sa.Time(), nullable=True),
    )
    # Reminders were account-wide, so users who had one on get it in every
    # app they can currently install; per-app opt-out is then a settings tap.
    op.execute(
        """
        INSERT INTO creative_type_preferences (
            user_id, creative_type, remember_timer_option,
            remembered_timer_mode, remembered_timer_seconds
        )
        SELECT up.user_id, ct.creative_type, false, NULL, NULL
        FROM user_preferences AS up
        CROSS JOIN (
            SELECT unnest(enum_range(NULL::creative_type)) AS creative_type
        ) AS ct
        WHERE up.notifications_enabled = true
        ON CONFLICT (user_id, creative_type) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE creative_type_preferences AS ctp
        SET notifications_enabled = up.notifications_enabled,
            notification_time_local = up.notification_time_local
        FROM user_preferences AS up
        WHERE up.user_id = ctp.user_id
        """
    )
    op.drop_column("user_preferences", "notification_time_local")
    op.drop_column("user_preferences", "notifications_enabled")


def downgrade() -> None:
    # --- daily reminder back to account-wide ------------------------------
    op.add_column(
        "user_preferences",
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column("notification_time_local", sa.Time(), nullable=True),
    )
    op.execute(
        """
        UPDATE user_preferences AS up
        SET notifications_enabled = src.enabled, notification_time_local = src.time_local
        FROM (
            SELECT user_id,
                   bool_or(notifications_enabled) AS enabled,
                   min(notification_time_local) AS time_local
            FROM creative_type_preferences
            GROUP BY user_id
        ) AS src
        WHERE src.user_id = up.user_id
        """
    )
    op.drop_column("creative_type_preferences", "notification_time_local")
    op.drop_column("creative_type_preferences", "notifications_enabled")

    # --- recreate per-type tables -----------------------------------------
    sketch_status = postgresql.ENUM(
        "active",
        "paused",
        "ready_for_photo",
        "uploading",
        "completed",
        "abandoned",
        "expired",
        name="sketch_session_status",
    )
    story_status = postgresql.ENUM(
        "active",
        "paused",
        "writing",
        "completed",
        "abandoned",
        "expired",
        name="story_session_status",
    )
    sketch_event = postgresql.ENUM(
        "started",
        "paused",
        "resumed",
        "timer_completed",
        "finished_early",
        "photo_step_reached",
        "upload_started",
        "upload_completed",
        "submission_created",
        "abandoned",
        name="sketch_session_event_type",
    )
    story_event = postgresql.ENUM(
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
    )
    bind = op.get_bind()
    for enum_type in (sketch_status, story_status, sketch_event, story_event):
        enum_type.create(bind, checkfirst=True)

    timer_mode = postgresql.ENUM(name="timer_mode", create_type=False)
    shared_session_columns = [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_id", sa.Uuid(), nullable=False),
        sa.Column("timer_mode", timer_mode, nullable=False),
        sa.Column("selected_timer_seconds", sa.Integer(), nullable=True),
    ]
    trailing_session_columns = [
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paused_total_seconds", sa.Integer(), nullable=False),
        sa.Column("timer_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finish_requested_at", sa.DateTime(timezone=True), nullable=True),
    ]
    tail_columns = [
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
    ]
    op.create_table(
        "sketch_sessions",
        *[column.copy() for column in shared_session_columns],
        sa.Column("status", postgresql.ENUM(name="sketch_session_status", create_type=False)),
        *[column.copy() for column in trailing_session_columns],
        sa.Column("photo_step_reached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("upload_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("upload_completed_at", sa.DateTime(timezone=True), nullable=True),
        *[column.copy() for column in tail_columns],
        sa.ForeignKeyConstraint(["prompt_id"], ["daily_prompts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sketch_sessions")),
    )
    op.create_table(
        "story_sessions",
        *[column.copy() for column in shared_session_columns],
        sa.Column("status", postgresql.ENUM(name="story_session_status", create_type=False)),
        *[column.copy() for column in trailing_session_columns],
        *[column.copy() for column in tail_columns],
        sa.ForeignKeyConstraint(["prompt_id"], ["daily_prompts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_story_sessions")),
    )
    op.execute(
        """
        INSERT INTO sketch_sessions (
            id, user_id, prompt_id, timer_mode, selected_timer_seconds, status, started_at,
            paused_total_seconds, timer_completed_at, finish_requested_at,
            photo_step_reached_at, upload_started_at, upload_completed_at,
            completed_at, abandoned_at, created_at, updated_at
        )
        SELECT id, user_id, prompt_id, timer_mode, selected_timer_seconds,
               COALESCE(stage, status::text)::sketch_session_status, started_at,
               paused_total_seconds, timer_completed_at, finish_requested_at,
               (stage_timestamps->>'photo_step_reached_at')::timestamptz,
               (stage_timestamps->>'upload_started_at')::timestamptz,
               (stage_timestamps->>'upload_completed_at')::timestamptz,
               completed_at, abandoned_at, created_at, updated_at
        FROM creative_sessions WHERE creative_type = 'sketch'
        """
    )
    op.execute(
        """
        INSERT INTO story_sessions (
            id, user_id, prompt_id, timer_mode, selected_timer_seconds, status, started_at,
            paused_total_seconds, timer_completed_at, finish_requested_at,
            completed_at, abandoned_at, created_at, updated_at
        )
        SELECT id, user_id, prompt_id, timer_mode, selected_timer_seconds,
               COALESCE(stage, status::text)::story_session_status, started_at,
               paused_total_seconds, timer_completed_at, finish_requested_at,
               completed_at, abandoned_at, created_at, updated_at
        FROM creative_sessions WHERE creative_type = 'story'
        """
    )
    for prefix, event_enum in (
        ("sketch", "sketch_session_event_type"),
        ("story", "story_session_event_type"),
    ):
        op.create_table(
            f"{prefix}_session_events",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column(f"{prefix}_session_id", sa.Uuid(), nullable=False),
            sa.Column("event_type", postgresql.ENUM(name=event_enum, create_type=False)),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("client_occurred_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "metadata_json",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default="{}",
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                [f"{prefix}_session_id"], [f"{prefix}_sessions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{prefix}_session_events")),
        )
        op.execute(
            f"""
            INSERT INTO {prefix}_session_events (
                id, {prefix}_session_id, event_type, occurred_at, client_occurred_at,
                metadata_json, created_at
            )
            SELECT e.id, e.session_id, e.event_type::{event_enum}, e.occurred_at,
                   e.client_occurred_at, e.metadata_json, e.created_at
            FROM creative_session_events AS e
            JOIN creative_sessions AS s ON s.id = e.session_id
            WHERE s.creative_type = '{prefix}'
            """
        )

    op.create_table(
        "sketch_submissions",
        sa.Column("publication_id", sa.Uuid(), nullable=False),
        sa.Column("sketch_session_id", sa.Uuid(), nullable=False),
        sa.Column("upload_id", sa.Uuid(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["publication_id"], ["creative_publications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["sketch_session_id"], ["sketch_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("publication_id", name=op.f("pk_sketch_submissions")),
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
            ["publication_id"], ["creative_publications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["story_session_id"], ["story_sessions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("publication_id", name=op.f("pk_story_submissions")),
        sa.UniqueConstraint("story_session_id"),
    )
    op.execute(
        """
        INSERT INTO sketch_submissions (publication_id, sketch_session_id, upload_id, caption)
        SELECT id, session_id, upload_id, caption
        FROM creative_publications
        WHERE creative_type = 'sketch' AND upload_id IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO story_submissions (publication_id, story_session_id, body, caption)
        SELECT id, session_id, COALESCE(content->>'body', ''), caption
        FROM creative_publications
        WHERE creative_type = 'story'
        """
    )

    op.drop_constraint(
        op.f("uq_creative_publications_upload_id"), "creative_publications", type_="unique"
    )
    op.drop_constraint(
        op.f("fk_creative_publications_upload_id_uploads"),
        "creative_publications",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("uq_creative_publications_session_id"), "creative_publications", type_="unique"
    )
    op.drop_constraint(
        op.f("fk_creative_publications_session_id_creative_sessions"),
        "creative_publications",
        type_="foreignkey",
    )
    op.drop_column("creative_publications", "content")
    op.drop_column("creative_publications", "upload_id")
    op.drop_column("creative_publications", "caption")

    op.drop_table("creative_session_events")
    op.drop_table("creative_sessions")
    op.execute("DROP TYPE IF EXISTS creative_session_status")
