"""Create user_preferences table.

Revision ID: 0003_user_preferences
Revises: 0002_users
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_user_preferences"
down_revision: str | None = "0002_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

timer_mode = postgresql.ENUM(
    "countdown",
    "no_timer",
    name="timer_mode",
    create_type=False,
)

appearance = postgresql.ENUM(
    "system",
    "light",
    "dark",
    name="appearance",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "countdown",
        "no_timer",
        name="timer_mode",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "system",
        "light",
        "dark",
        name="appearance",
    ).create(bind, checkfirst=True)

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False),
        sa.Column("notification_time_local", sa.Time(), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("remember_timer_option", sa.Boolean(), nullable=False),
        sa.Column("remembered_timer_mode", timer_mode, nullable=True),
        sa.Column("remembered_timer_seconds", sa.Integer(), nullable=True),
        sa.Column("appearance", appearance, nullable=False),
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
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
    postgresql.ENUM(name="appearance").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="timer_mode").drop(op.get_bind(), checkfirst=True)
