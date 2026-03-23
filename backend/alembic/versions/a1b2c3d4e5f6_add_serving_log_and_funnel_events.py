"""Add search_serving_log and application_funnel_events tables (T-DS-911/912/913).

Revision ID: a1b2c3d4e5f6
Revises: 9c1d7c3b6a21
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    JSONB = sa.JSON  # type: ignore[misc,assignment]

revision = "a1b2c3d4e5f6"
down_revision = "9c1d7c3b6a21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- search_serving_log ---
    op.create_table(
        "search_serving_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("query", sa.String(500), nullable=False, server_default=""),
        sa.Column("filters", JSONB(), nullable=False, server_default="{}"),
        sa.Column("result_job_ids", JSONB(), nullable=False, server_default="[]"),
        sa.Column("result_scores", JSONB(), nullable=False, server_default="[]"),
        sa.Column("result_features", JSONB(), nullable=False, server_default="{}"),
        sa.Column("mode", sa.String(50), nullable=False, server_default="standard"),
        sa.Column(
            "served_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_search_serving_log_user_id", "search_serving_log", ["user_id"])
    op.create_index(
        "ix_search_serving_log_served_at", "search_serving_log", ["served_at"]
    )

    # --- application_funnel_events ---
    op.create_table(
        "application_funnel_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey("job_applications.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "job_post_id",
            sa.Integer(),
            sa.ForeignKey("job_post.id"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(50), nullable=False, server_default="system"),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("meta", JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "event_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_funnel_event_application_id",
        "application_funnel_events",
        ["application_id"],
    )
    op.create_index("ix_funnel_event_user_id", "application_funnel_events", ["user_id"])
    op.create_index(
        "ix_funnel_event_job_post_id", "application_funnel_events", ["job_post_id"]
    )
    op.create_index("ix_funnel_event_stage", "application_funnel_events", ["stage"])
    op.create_index(
        "ix_funnel_event_event_at", "application_funnel_events", ["event_at"]
    )
    op.create_index(
        "idx_funnel_event_app_stage",
        "application_funnel_events",
        ["application_id", "stage"],
    )


def downgrade() -> None:
    op.drop_table("application_funnel_events")
    op.drop_table("search_serving_log")
