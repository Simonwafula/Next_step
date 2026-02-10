"""Add application_url and source_url to job_post (T-620).

Revision ID: 9c1d7c3b6a21
Revises: 2ae4be61eb25
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9c1d7c3b6a21"
down_revision = "2ae4be61eb25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_post", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("job_post", sa.Column("application_url", sa.Text(), nullable=True))

    # Backfill: existing rows treat the old `url` as both discovery + application URL.
    op.execute("UPDATE job_post SET source_url = url WHERE source_url IS NULL")
    op.execute(
        "UPDATE job_post SET application_url = url WHERE application_url IS NULL"
    )


def downgrade() -> None:
    op.drop_column("job_post", "application_url")
    op.drop_column("job_post", "source_url")
