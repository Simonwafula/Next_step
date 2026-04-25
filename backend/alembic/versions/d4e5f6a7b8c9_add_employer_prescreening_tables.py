"""Add employer_account, employer_user, candidate_shortlist, candidate_shortlist_entry (T-DS-951/953).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    JSONB = sa.JSON  # type: ignore[misc,assignment]

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- employer_account (T-DS-951) ---
    op.create_table(
        "employer_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False, unique=True),
        sa.Column("plan", sa.String(30), nullable=False, server_default="free"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_employer_account_org_id", "employer_account", ["org_id"], unique=True)
    op.create_index("ix_employer_account_plan", "employer_account", ["plan"])

    # --- employer_user (T-DS-951) ---
    op.create_table(
        "employer_user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "employer_account_id",
            sa.Integer(),
            sa.ForeignKey("employer_account.id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="recruiter"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_employer_user_employer_account_id", "employer_user", ["employer_account_id"]
    )
    op.create_index("ix_employer_user_user_id", "employer_user", ["user_id"])
    op.create_index(
        "idx_employer_user_account_user",
        "employer_user",
        ["employer_account_id", "user_id"],
        unique=True,
    )

    # --- candidate_shortlist (T-DS-953) ---
    op.create_table(
        "candidate_shortlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "employer_account_id",
            sa.Integer(),
            sa.ForeignKey("employer_account.id"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("job_post_id", sa.Integer(), sa.ForeignKey("job_post.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default="Shortlist"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("intelligence_sidecar", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_candidate_shortlist_employer_account_id",
        "candidate_shortlist",
        ["employer_account_id"],
    )
    op.create_index(
        "ix_candidate_shortlist_job_post_id", "candidate_shortlist", ["job_post_id"]
    )
    op.create_index(
        "ix_candidate_shortlist_status", "candidate_shortlist", ["status"]
    )
    op.create_index(
        "idx_shortlist_employer_job",
        "candidate_shortlist",
        ["employer_account_id", "job_post_id"],
    )

    # --- candidate_shortlist_entry (T-DS-953) ---
    op.create_table(
        "candidate_shortlist_entry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "shortlist_id",
            sa.Integer(),
            sa.ForeignKey("candidate_shortlist.id"),
            nullable=False,
        ),
        sa.Column(
            "candidate_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("score_breakdown", JSONB(), nullable=False, server_default="{}"),
        sa.Column("explanation", JSONB(), nullable=False, server_default="{}"),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_shortlist_entry_shortlist_id", "candidate_shortlist_entry", ["shortlist_id"]
    )
    op.create_index(
        "ix_shortlist_entry_candidate_user_id",
        "candidate_shortlist_entry",
        ["candidate_user_id"],
    )
    op.create_index(
        "idx_shortlist_entry_shortlist_candidate",
        "candidate_shortlist_entry",
        ["shortlist_id", "candidate_user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("candidate_shortlist_entry")
    op.drop_table("candidate_shortlist")
    op.drop_table("employer_user")
    op.drop_table("employer_account")
