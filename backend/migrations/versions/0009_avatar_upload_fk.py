"""Add foreign key and index for users.avatar_upload_id.

Revision ID: 0009_avatar_upload_fk
Revises: 0008_likes_reflections_activity
Create Date: 2026-07-19
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_avatar_upload_fk"
down_revision: str | None = "0008_likes_reflections_activity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_users_avatar_upload_id",
        "users",
        "uploads",
        ["avatar_upload_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_users_avatar_upload_id",
        "users",
        ["avatar_upload_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_users_avatar_upload_id", table_name="users")
    op.drop_constraint("fk_users_avatar_upload_id", "users", type_="foreignkey")
