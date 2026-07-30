"""Add versioned policy documents, acceptances, age, and moderation review.

Revision ID: 0002_policy_safety
Revises: 0001_baseline
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_policy_safety"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# create_type=False keeps CREATE TABLE from re-emitting CREATE TYPE; the types are
# created once up front in upgrade() instead.
policy_kind = postgresql.ENUM(
    "terms",
    "privacy",
    "community_guidelines",
    name="policy_kind",
    create_type=False,
)
policy_status = postgresql.ENUM(
    "draft",
    "published",
    "superseded",
    name="policy_status",
    create_type=False,
)
moderation_review_status = postgresql.ENUM(
    "open",
    "resolved",
    "dismissed",
    name="moderation_review_status",
    create_type=False,
)
report_target_type = postgresql.ENUM(
    "submission",
    "reflection",
    "profile",
    name="report_target_type",
    create_type=False,
)


def upgrade() -> None:
    policy_kind.create(op.get_bind(), checkfirst=True)
    policy_status.create(op.get_bind(), checkfirst=True)
    moderation_review_status.create(op.get_bind(), checkfirst=True)

    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))

    # Extend moderation_action_type enum with automated / policy actions.
    op.execute("ALTER TYPE moderation_action_type ADD VALUE IF NOT EXISTS 'auto_block_content'")
    op.execute("ALTER TYPE moderation_action_type ADD VALUE IF NOT EXISTS 'auto_queue_review'")
    op.execute("ALTER TYPE moderation_action_type ADD VALUE IF NOT EXISTS 'publish_policy'")

    op.create_table(
        "policy_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", policy_kind, nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("minimum_age", sa.Integer(), nullable=False),
        sa.Column("status", policy_status, nullable=False),
        sa.Column("is_significant_change", sa.Boolean(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_documents")),
        sa.UniqueConstraint("kind", "version", name="uq_policy_documents_kind_version"),
    )
    op.create_index(
        "ix_policy_documents_kind_status",
        "policy_documents",
        ["kind", "status"],
        unique=False,
    )

    op.create_table(
        "policy_acceptances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("policy_document_id", sa.Uuid(), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("app_version", sa.String(length=64), nullable=True),
        sa.Column("platform", sa.String(length=32), nullable=True),
        sa.Column("locale", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["policy_document_id"],
            ["policy_documents.id"],
            name=op.f("fk_policy_acceptances_policy_document_id_policy_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_policy_acceptances_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_acceptances")),
        sa.UniqueConstraint(
            "user_id",
            "policy_document_id",
            name="uq_policy_acceptances_user_document",
        ),
    )
    op.create_index(
        "ix_policy_acceptances_user_id",
        "policy_acceptances",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "moderation_review_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_type", report_target_type, nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("status", moderation_review_status, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("categories", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_response", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_moderation_review_items_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_moderation_review_items")),
    )
    op.create_index(
        "ix_moderation_review_items_status_created",
        "moderation_review_items",
        ["status", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_moderation_review_items_status_created", table_name="moderation_review_items")
    op.drop_table("moderation_review_items")
    op.drop_index("ix_policy_acceptances_user_id", table_name="policy_acceptances")
    op.drop_table("policy_acceptances")
    op.drop_index("ix_policy_documents_kind_status", table_name="policy_documents")
    op.drop_table("policy_documents")
    op.drop_column("users", "date_of_birth")
    moderation_review_status.drop(op.get_bind(), checkfirst=True)
    policy_status.drop(op.get_bind(), checkfirst=True)
    policy_kind.drop(op.get_bind(), checkfirst=True)
