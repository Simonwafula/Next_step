"""Set server default for skill.aliases (T-622).

Revision ID: 3b2c1d4e5f60
Revises: 0f3a9b7d1b4d
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "3b2c1d4e5f60"
down_revision = "0f3a9b7d1b4d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill any legacy NULLs defensively, then set a server default so raw
    # SQL inserts (e.g., ON CONFLICT upserts) don't violate NOT NULL.
    op.execute("UPDATE skill SET aliases = '{}'::jsonb WHERE aliases IS NULL")
    op.alter_column(
        "skill",
        "aliases",
        existing_type=postgresql.JSONB(),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )


def downgrade() -> None:
    op.alter_column(
        "skill",
        "aliases",
        existing_type=postgresql.JSONB(),
        nullable=False,
        server_default=None,
    )
