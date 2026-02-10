"""Make user_analytics.user_id nullable for public events (T-620).

Revision ID: 0f3a9b7d1b4d
Revises: 9c1d7c3b6a21
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0f3a9b7d1b4d"
down_revision = "9c1d7c3b6a21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "user_analytics", "user_id", existing_type=sa.Integer(), nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "user_analytics", "user_id", existing_type=sa.Integer(), nullable=False
    )
