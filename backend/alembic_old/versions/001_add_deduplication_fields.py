"""add deduplication fields to job_post

Revision ID: 001_dedup_fields
Revises:
Create Date: 2026-01-08

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_dedup_fields"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add url_hash column
    op.add_column(
        "job_post", sa.Column("url_hash", sa.String(length=32), nullable=True)
    )
    op.create_index(
        op.f("ix_job_post_url_hash"), "job_post", ["url_hash"], unique=False
    )

    # Add repost_count column
    op.add_column(
        "job_post",
        sa.Column("repost_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add quality_score column
    op.add_column("job_post", sa.Column("quality_score", sa.Float(), nullable=True))

    # Add processed_at column
    op.add_column("job_post", sa.Column("processed_at", sa.DateTime(), nullable=True))


def downgrade():
    # Remove columns in reverse order
    op.drop_column("job_post", "processed_at")
    op.drop_column("job_post", "quality_score")
    op.drop_column("job_post", "repost_count")
    op.drop_index(op.f("ix_job_post_url_hash"), table_name="job_post")
    op.drop_column("job_post", "url_hash")
