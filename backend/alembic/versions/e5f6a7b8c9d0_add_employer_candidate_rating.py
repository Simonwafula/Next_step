"""Add employer_candidate_rating table (T-DS-961).

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_candidate_rating",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "employer_account_id",
            sa.Integer(),
            sa.ForeignKey("employer_account.id"),
            nullable=False,
        ),
        sa.Column(
            "rated_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "candidate_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "job_post_id", sa.Integer(), sa.ForeignKey("job_post.id"), nullable=False
        ),
        sa.Column("sentiment", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(60), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("stage_at_rating", sa.String(30), nullable=True),
        sa.Column("rated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_ecr_employer_account_id",
        "employer_candidate_rating",
        ["employer_account_id"],
    )
    op.create_index(
        "ix_ecr_rated_by_user_id",
        "employer_candidate_rating",
        ["rated_by_user_id"],
    )
    op.create_index(
        "ix_ecr_candidate_user_id",
        "employer_candidate_rating",
        ["candidate_user_id"],
    )
    op.create_index(
        "ix_ecr_job_post_id", "employer_candidate_rating", ["job_post_id"]
    )
    op.create_index(
        "ix_ecr_sentiment", "employer_candidate_rating", ["sentiment"]
    )
    op.create_index(
        "ix_ecr_rated_at", "employer_candidate_rating", ["rated_at"]
    )
    op.create_index(
        "idx_ecr_employer_candidate_job",
        "employer_candidate_rating",
        ["employer_account_id", "candidate_user_id", "job_post_id"],
    )


def downgrade() -> None:
    op.drop_table("employer_candidate_rating")
