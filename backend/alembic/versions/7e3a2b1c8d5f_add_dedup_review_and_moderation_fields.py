"""Add dedup review status and moderation fields.

Revision ID: 7e3a2b1c8d5f
Revises: 6d2f1c9a0b3e
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa


revision = "7e3a2b1c8d5f"
down_revision = "6d2f1c9a0b3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # JobDedupeMap: add review tracking columns
    op.add_column(
        "job_dedupe_map",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "job_dedupe_map",
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "job_dedupe_map",
        sa.Column(
            "reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
    )
    op.create_index("ix_job_dedupe_map_status", "job_dedupe_map", ["status"])

    # CompanyReview: add moderation workflow columns
    op.add_column(
        "company_reviews",
        sa.Column(
            "moderation_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "company_reviews",
        sa.Column("moderated_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "company_reviews",
        sa.Column(
            "moderated_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_company_reviews_moderation_status",
        "company_reviews",
        ["moderation_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_company_reviews_moderation_status", "company_reviews")
    op.drop_column("company_reviews", "moderated_by")
    op.drop_column("company_reviews", "moderated_at")
    op.drop_column("company_reviews", "moderation_status")

    op.drop_index("ix_job_dedupe_map_status", "job_dedupe_map")
    op.drop_column("job_dedupe_map", "reviewed_by")
    op.drop_column("job_dedupe_map", "reviewed_at")
    op.drop_column("job_dedupe_map", "status")
