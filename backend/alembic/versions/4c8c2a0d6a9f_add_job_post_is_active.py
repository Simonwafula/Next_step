"""Add job_post.is_active for quarantine/soft-delete (T-625).

Revision ID: 4c8c2a0d6a9f
Revises: 3b2c1d4e5f60
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa


revision = "4c8c2a0d6a9f"
down_revision = "3b2c1d4e5f60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_post",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_index("ix_job_post_is_active", "job_post", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_post_is_active", table_name="job_post")
    op.drop_column("job_post", "is_active")
