"""Add integration models

Revision ID: 003
Revises: 002
Create Date: 2025-01-18 05:34:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create LinkedIn profiles table
    op.create_table(
        "linkedin_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("linkedin_id", sa.String(length=100), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("profile_url", sa.String(length=500), nullable=False),
        sa.Column("headline", sa.String(length=500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("industry", sa.String(length=255), nullable=True),
        sa.Column("profile_picture_url", sa.String(length=500), nullable=True),
        sa.Column(
            "experience",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "education",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "certifications",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "languages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("auto_sync_enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "sync_frequency", sa.String(length=50), nullable=False, default="weekly"
        ),
        sa.Column("last_synced", sa.DateTime(), nullable=True),
        sa.Column(
            "sync_status", sa.String(length=50), nullable=False, default="active"
        ),
        sa.Column(
            "sync_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("sync_profile_picture", sa.Boolean(), nullable=False, default=True),
        sa.Column("sync_experience", sa.Boolean(), nullable=False, default=True),
        sa.Column("sync_education", sa.Boolean(), nullable=False, default=True),
        sa.Column("sync_skills", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("linkedin_id"),
    )
    op.create_index(
        op.f("ix_linkedin_profiles_linkedin_id"),
        "linkedin_profiles",
        ["linkedin_id"],
        unique=False,
    )

    # Create calendar integrations table
    op.create_table(
        "calendar_integrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("primary_calendar_id", sa.String(length=255), nullable=True),
        sa.Column(
            "timezone", sa.String(length=100), nullable=False, default="Africa/Nairobi"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "auto_schedule_interviews", sa.Boolean(), nullable=False, default=True
        ),
        sa.Column("send_reminders", sa.Boolean(), nullable=False, default=True),
        sa.Column("sync_job_deadlines", sa.Boolean(), nullable=False, default=True),
        sa.Column("last_synced", sa.DateTime(), nullable=True),
        sa.Column(
            "sync_status", sa.String(length=50), nullable=False, default="active"
        ),
        sa.Column(
            "sync_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_calendar_provider",
        "calendar_integrations",
        ["user_id", "provider"],
        unique=False,
    )

    # Create calendar events table
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("calendar_integration_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("external_event_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("is_all_day", sa.Boolean(), nullable=False, default=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("related_job_id", sa.Integer(), nullable=True),
        sa.Column("related_application_id", sa.Integer(), nullable=True),
        sa.Column("meeting_url", sa.String(length=500), nullable=True),
        sa.Column("meeting_platform", sa.String(length=50), nullable=True),
        sa.Column(
            "attendees",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("status", sa.String(length=50), nullable=False, default="scheduled"),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "reminder_times",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["calendar_integration_id"],
            ["calendar_integrations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["related_application_id"],
            ["job_applications.id"],
        ),
        sa.ForeignKeyConstraint(
            ["related_job_id"],
            ["job_post.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create ATS integrations table
    op.create_table(
        "ats_integrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("ats_provider", sa.String(length=50), nullable=False),
        sa.Column("ats_instance_url", sa.String(length=500), nullable=False),
        sa.Column("ats_company_id", sa.String(length=255), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("api_secret", sa.Text(), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("sync_jobs", sa.Boolean(), nullable=False, default=True),
        sa.Column("sync_applications", sa.Boolean(), nullable=False, default=True),
        sa.Column("sync_candidates", sa.Boolean(), nullable=False, default=False),
        sa.Column("webhook_url", sa.String(length=500), nullable=True),
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
        sa.Column(
            "webhook_events",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("last_synced", sa.DateTime(), nullable=True),
        sa.Column(
            "sync_status", sa.String(length=50), nullable=False, default="active"
        ),
        sa.Column(
            "sync_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("jobs_synced_count", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_org_ats_provider",
        "ats_integrations",
        ["organization_id", "ats_provider"],
        unique=False,
    )

    # Create ATS job sync table
    op.create_table(
        "ats_job_syncs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ats_integration_id", sa.Integer(), nullable=False),
        sa.Column("job_post_id", sa.Integer(), nullable=False),
        sa.Column("ats_job_id", sa.String(length=255), nullable=False),
        sa.Column("ats_job_url", sa.String(length=500), nullable=True),
        sa.Column("ats_status", sa.String(length=50), nullable=False),
        sa.Column(
            "first_synced",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "last_synced",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "sync_status", sa.String(length=50), nullable=False, default="active"
        ),
        sa.Column(
            "sync_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "ats_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("hiring_manager", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("job_code", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["ats_integration_id"],
            ["ats_integrations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["job_post_id"],
            ["job_post.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_ats_job_sync",
        "ats_job_syncs",
        ["ats_integration_id", "ats_job_id"],
        unique=True,
    )

    # Create ATS application sync table
    op.create_table(
        "ats_application_syncs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ats_integration_id", sa.Integer(), nullable=False),
        sa.Column("job_application_id", sa.Integer(), nullable=False),
        sa.Column("ats_application_id", sa.String(length=255), nullable=False),
        sa.Column("ats_candidate_id", sa.String(length=255), nullable=True),
        sa.Column("ats_status", sa.String(length=100), nullable=False),
        sa.Column("ats_stage", sa.String(length=100), nullable=True),
        sa.Column("submitted_to_ats", sa.Boolean(), nullable=False, default=False),
        sa.Column("ats_submission_date", sa.DateTime(), nullable=True),
        sa.Column("last_status_update", sa.DateTime(), nullable=True),
        sa.Column(
            "ats_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("recruiter_notes", sa.Text(), nullable=True),
        sa.Column(
            "interview_feedback",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "sync_status", sa.String(length=50), nullable=False, default="active"
        ),
        sa.Column(
            "sync_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["ats_integration_id"],
            ["ats_integrations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["job_application_id"],
            ["job_applications.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_ats_app_sync",
        "ats_application_syncs",
        ["ats_integration_id", "ats_application_id"],
        unique=True,
    )

    # Create integration activity log table
    op.create_table(
        "integration_activity_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("integration_type", sa.String(length=50), nullable=False),
        sa.Column("integration_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("activity_description", sa.Text(), nullable=False),
        sa.Column(
            "activity_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            default=sa.text("CURRENT_TIMESTAMP"),
        ),
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
    op.create_index(
        "idx_integration_activity",
        "integration_activity_logs",
        ["integration_type", "integration_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_integration_activity_logs_created_at"),
        "integration_activity_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(
        op.f("ix_integration_activity_logs_created_at"),
        table_name="integration_activity_logs",
    )
    op.drop_index("idx_integration_activity", table_name="integration_activity_logs")
    op.drop_table("integration_activity_logs")

    op.drop_index("idx_ats_app_sync", table_name="ats_application_syncs")
    op.drop_table("ats_application_syncs")

    op.drop_index("idx_ats_job_sync", table_name="ats_job_syncs")
    op.drop_table("ats_job_syncs")

    op.drop_index("idx_org_ats_provider", table_name="ats_integrations")
    op.drop_table("ats_integrations")

    op.drop_table("calendar_events")

    op.drop_index("idx_user_calendar_provider", table_name="calendar_integrations")
    op.drop_table("calendar_integrations")

    op.drop_index(
        op.f("ix_linkedin_profiles_linkedin_id"), table_name="linkedin_profiles"
    )
    op.drop_table("linkedin_profiles")
