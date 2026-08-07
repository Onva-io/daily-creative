"""Extend moderation action enum and admin approval workflows.

Revision ID: 0003_admin_mod
Revises: 0002_policy_safety
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_admin_mod"
down_revision: str | None = "0002_policy_safety"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE moderation_action_type ADD VALUE IF NOT EXISTS 'approve_review_item'")
    op.execute("ALTER TYPE moderation_action_type ADD VALUE IF NOT EXISTS 'reject_review_item'")
    op.execute(
        "ALTER TYPE moderation_action_type ADD VALUE IF NOT EXISTS 'approve_reported_content'"
    )
    op.execute("ALTER TYPE moderation_action_type ADD VALUE IF NOT EXISTS 'redact_caption'")


def downgrade() -> None:
    # PostgreSQL cannot drop individual enum values safely; leave values in place.
    pass
