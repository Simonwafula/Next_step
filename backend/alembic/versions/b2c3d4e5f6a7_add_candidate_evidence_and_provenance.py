"""Add candidate_evidence and verification_provenance tables (T-DS-931/933).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    JSONB = sa.JSON  # type: ignore[misc,assignment]

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- candidate_evidence (T-DS-931) ---
    op.create_table(
        "candidate_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("evidence_type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("skills_demonstrated", JSONB(), nullable=False, server_default="[]"),
        sa.Column("start_date", sa.String(20), nullable=True),
        sa.Column("end_date", sa.String(20), nullable=True),
        sa.Column(
            "source",
            sa.String(60),
            nullable=False,
            server_default="self_reported",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_candidate_evidence_user_id", "candidate_evidence", ["user_id"])
    op.create_index(
        "ix_candidate_evidence_evidence_type", "candidate_evidence", ["evidence_type"]
    )
    op.create_index(
        "idx_candidate_evidence_user_type",
        "candidate_evidence",
        ["user_id", "evidence_type"],
    )

    # --- verification_provenance (T-DS-933) ---
    op.create_table(
        "verification_provenance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "evidence_id",
            sa.Integer(),
            sa.ForeignKey("candidate_evidence.id"),
            nullable=False,
        ),
        sa.Column("evidence_source", sa.String(60), nullable=False),
        sa.Column("assessment_version", sa.String(60), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("expiry_date", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_verification_provenance_evidence_id",
        "verification_provenance",
        ["evidence_id"],
    )
    op.create_index(
        "ix_verification_provenance_source",
        "verification_provenance",
        ["evidence_source"],
    )


def downgrade() -> None:
    op.drop_table("verification_provenance")
    op.drop_table("candidate_evidence")
