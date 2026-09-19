"""Add the ``photo`` creative type.

Revision ID: 0005_photo_creative_type
Revises: 0004_unified_creative_model
Create Date: 2026-09-19

Daily Photo reuses the unified session/publication tables; the only schema
change is a new ``creative_type`` enum value. Photo-specific data (the
author-confirmed location and its sharing flag) lives in the JSONB
``creative_publications.content`` column like every other type.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_photo_creative_type"
down_revision: str | None = "0004_unified_creative_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PREVIOUS_VALUES = ("sketch", "story")
NEW_VALUE = "photo"

# Every column typed as ``creative_type``.
ENUM_COLUMNS = (
    ("creative_sessions", "creative_type"),
    ("creative_publications", "creative_type"),
    ("creative_type_preferences", "creative_type"),
)


def upgrade() -> None:
    # PostgreSQL >= 12 allows ADD VALUE inside a transaction as long as the
    # new value is not used in the same transaction, which this migration
    # does not do.
    op.execute(f"ALTER TYPE creative_type ADD VALUE IF NOT EXISTS '{NEW_VALUE}'")


def downgrade() -> None:
    # PostgreSQL cannot drop an enum value, so remove the rows that use it
    # and rebuild the type without it.
    op.execute("DELETE FROM creative_publications WHERE creative_type = 'photo'::creative_type")
    op.execute("DELETE FROM creative_sessions WHERE creative_type = 'photo'::creative_type")
    op.execute("DELETE FROM creative_type_preferences WHERE creative_type = 'photo'::creative_type")

    values = ", ".join(f"'{value}'" for value in PREVIOUS_VALUES)
    op.execute("ALTER TYPE creative_type RENAME TO creative_type_old")
    op.execute(f"CREATE TYPE creative_type AS ENUM ({values})")
    for table, column in ENUM_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE creative_type "
            f"USING {column}::text::creative_type"
        )
    op.execute("DROP TYPE creative_type_old")
