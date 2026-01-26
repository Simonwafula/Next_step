"""Add advanced features: recommendations, reviews, assessments, alerts

Revision ID: 002_add_advanced_features
Revises: 001_add_user_auth
Create Date: 2025-08-17 23:25:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002_add_advanced_features"
down_revision = "001_add_user_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_job_recommendations table
    op.create_table(
        "user_job_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_post_id", sa.Integer(), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("skill_match_score", sa.Float(), nullable=False),
        sa.Column("location_match_score", sa.Float(), nullable=False),
        sa.Column("salary_match_score", sa.Float(), nullable=False),
        sa.Column("experience_match_score", sa.Float(), nullable=False),
        sa.Column("match_explanation", sa.Text(), nullable=True),
        sa.Column(
            "missing_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=[],
        ),
        sa.Column(
            "matching_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=[],
        ),
        sa.Column(
            "recommended_at", sa.DateTime(), nullable=False, default=sa.func.now()
        ),
        sa.Column(
            "algorithm_version", sa.String(length=50), nullable=False, default="v1.0"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("viewed", sa.Boolean(), nullable=False, default=False),
        sa.Column("clicked", sa.Boolean(), nullable=False, default=False),
        sa.Column("dismissed", sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(
            ["job_post_id"],
            ["job_post.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_job_recommendation",
        "user_job_recommendations",
        ["user_id", "job_post_id"],
        unique=True,
    )
    op.create_index(
        "ix_user_job_recommendations_recommended_at",
        "user_job_recommendations",
        ["recommended_at"],
    )

    # Create company_reviews table
    op.create_table(
        "company_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("overall_rating", sa.Float(), nullable=False),
        sa.Column("work_life_balance", sa.Float(), nullable=True),
        sa.Column("compensation", sa.Float(), nullable=True),
        sa.Column("career_growth", sa.Float(), nullable=True),
        sa.Column("management", sa.Float(), nullable=True),
        sa.Column("culture", sa.Float(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("pros", sa.Text(), nullable=True),
        sa.Column("cons", sa.Text(), nullable=True),
        sa.Column("advice_to_management", sa.Text(), nullable=True),
        sa.Column("job_title", sa.String(length=255), nullable=True),
        sa.Column("employment_status", sa.String(length=50), nullable=True),
        sa.Column("employment_duration", sa.String(length=100), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column("is_approved", sa.Boolean(), nullable=False, default=False),
        sa.Column("moderation_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create skill_assessments table
    op.create_table(
        "skill_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("percentile", sa.Float(), nullable=True),
        sa.Column("assessment_type", sa.String(length=50), nullable=False),
        sa.Column("questions_total", sa.Integer(), nullable=False),
        sa.Column("questions_correct", sa.Integer(), nullable=False),
        sa.Column("time_taken_minutes", sa.Integer(), nullable=True),
        sa.Column("is_certified", sa.Boolean(), nullable=False, default=False),
        sa.Column("certificate_url", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("taken_at", sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skill.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_skill_assessment", "skill_assessments", ["user_id", "skill_id"]
    )

    # Create job_alerts table
    op.create_table(
        "job_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default={},
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("frequency", sa.String(length=50), nullable=False, default="daily"),
        sa.Column(
            "delivery_methods",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=[],
        ),
        sa.Column("jobs_found_total", sa.Integer(), nullable=False, default=0),
        sa.Column("last_triggered", sa.DateTime(), nullable=True),
        sa.Column("last_jobs_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create interview_preparations table
    op.create_table(
        "interview_preparations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_application_id", sa.Integer(), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("role_title", sa.String(length=255), nullable=False),
        sa.Column("interview_type", sa.String(length=50), nullable=False),
        sa.Column("scheduled_date", sa.DateTime(), nullable=True),
        sa.Column(
            "questions_practiced",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=[],
        ),
        sa.Column("research_notes", sa.Text(), nullable=True),
        sa.Column("preparation_score", sa.Float(), nullable=True),
        sa.Column(
            "suggested_questions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=[],
        ),
        sa.Column(
            "company_insights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default={},
        ),
        sa.Column(
            "role_specific_tips",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=[],
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["job_application_id"],
            ["job_applications.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create user_analytics table
    op.create_table(
        "user_analytics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column(
            "event_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default={},
        ),
        sa.Column("page_url", sa.String(length=500), nullable=True),
        sa.Column("referrer", sa.String(length=500), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_analytics_timestamp", "user_analytics", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_user_analytics_timestamp", table_name="user_analytics")
    op.drop_table("user_analytics")
    op.drop_table("interview_preparations")
    op.drop_table("job_alerts")
    op.drop_index("idx_user_skill_assessment", table_name="skill_assessments")
    op.drop_table("skill_assessments")
    op.drop_table("company_reviews")
    op.drop_index(
        "ix_user_job_recommendations_recommended_at",
        table_name="user_job_recommendations",
    )
    op.drop_index("idx_user_job_recommendation", table_name="user_job_recommendations")
    op.drop_table("user_job_recommendations")
