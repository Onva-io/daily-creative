"""Baseline schema — empty until Phase 1+ domain migrations.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-18
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No tables yet — establishes Alembic version tracking."""
    pass


def downgrade() -> None:
    pass
