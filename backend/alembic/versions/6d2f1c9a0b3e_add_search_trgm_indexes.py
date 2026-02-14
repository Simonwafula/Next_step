"""Add Postgres search performance indexes (pg_trgm) (T-633).

Revision ID: 6d2f1c9a0b3e
Revises: 4c8c2a0d6a9f
Create Date: 2026-02-14
"""

from alembic import op


revision = "6d2f1c9a0b3e"
down_revision = "4c8c2a0d6a9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # CREATE INDEX CONCURRENTLY cannot run inside a transaction.
    with op.get_context().autocommit_block():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_post_title_raw_trgm
            ON job_post USING gin (title_raw gin_trgm_ops)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_post_description_raw_trgm
            ON job_post USING gin (description_raw gin_trgm_ops)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_post_requirements_raw_trgm
            ON job_post USING gin (requirements_raw gin_trgm_ops)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_title_norm_canonical_title_trgm
            ON title_norm USING gin (canonical_title gin_trgm_ops)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_title_norm_family_trgm
            ON title_norm USING gin (family gin_trgm_ops)
            """
        )

        # FK indexes help joins in /api/search facets and admin dashboard queries.
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_post_title_norm_id
            ON job_post (title_norm_id)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_post_org_id
            ON job_post (org_id)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_post_location_id
            ON job_post (location_id)
            """
        )

        # Supports fast "latest jobs" ordering and broad query probes.
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_post_is_active_first_seen_desc
            ON job_post (is_active, first_seen DESC)
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS idx_job_post_is_active_first_seen_desc"
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_job_post_location_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_job_post_org_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_job_post_title_norm_id")

        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_title_norm_family_trgm")
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS idx_title_norm_canonical_title_trgm"
        )
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS idx_job_post_requirements_raw_trgm"
        )
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS idx_job_post_description_raw_trgm"
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_job_post_title_raw_trgm")
