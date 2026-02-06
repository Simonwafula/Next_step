from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Boolean, Index
import os

if os.getenv("DATABASE_URL", "").startswith("sqlite"):
    from sqlalchemy import JSON as JSONB
else:
    try:
        from sqlalchemy.dialects.postgresql import JSONB
    except Exception:
        from sqlalchemy import JSON as JSONB
from datetime import datetime
from .models import Base


# LinkedIn Integration Models
class LinkedInProfile(Base):
    __tablename__ = "linkedin_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    # LinkedIn OAuth tokens
    linkedin_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Profile data
    profile_url: Mapped[str] = mapped_column(String(500))
    headline: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Experience and education (stored as JSON)
    experience: Mapped[list] = mapped_column(JSONB, default=list)
    education: Mapped[list] = mapped_column(JSONB, default=list)
    skills: Mapped[list] = mapped_column(JSONB, default=list)
    certifications: Mapped[list] = mapped_column(JSONB, default=list)
    languages: Mapped[list] = mapped_column(JSONB, default=list)

    # Sync settings
    auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_frequency: Mapped[str] = mapped_column(
        String(50), default="weekly"
    )  # daily, weekly, monthly
    last_synced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active, error, disabled
    sync_errors: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Privacy settings
    sync_profile_picture: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_experience: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_education: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_skills: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Calendar Integration Models
class CalendarIntegration(Base):
    __tablename__ = "calendar_integrations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Calendar provider
    provider: Mapped[str] = mapped_column(String(50))  # google, outlook, exchange
    provider_user_id: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))

    # OAuth tokens
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Calendar settings
    primary_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), default="Africa/Nairobi")

    # Integration settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_schedule_interviews: Mapped[bool] = mapped_column(Boolean, default=True)
    send_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_job_deadlines: Mapped[bool] = mapped_column(Boolean, default=True)

    # Sync status
    last_synced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_status: Mapped[str] = mapped_column(String(50), default="active")
    sync_errors: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("idx_user_calendar_provider", "user_id", "provider"),)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    calendar_integration_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_integrations.id")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Event details
    external_event_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Timing
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    timezone: Mapped[str] = mapped_column(String(100))
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)

    # Event type and context
    event_type: Mapped[str] = mapped_column(
        String(50)
    )  # interview, deadline, reminder, meeting
    related_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_post.id"), nullable=True
    )
    related_application_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_applications.id"), nullable=True
    )

    # Meeting details (for interviews)
    meeting_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meeting_platform: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # zoom, teams, meet
    attendees: Mapped[list] = mapped_column(JSONB, default=list)

    # Status and reminders
    status: Mapped[str] = mapped_column(
        String(50), default="scheduled"
    )  # scheduled, completed, cancelled
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_times: Mapped[list] = mapped_column(
        JSONB, default=list
    )  # minutes before event

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ATS Integration Models
class ATSIntegration(Base):
    __tablename__ = "ats_integrations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"))

    # ATS provider details
    ats_provider: Mapped[str] = mapped_column(
        String(50)
    )  # greenhouse, lever, workday, bamboohr, etc.
    ats_instance_url: Mapped[str] = mapped_column(String(500))
    ats_company_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # API credentials
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Integration settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_jobs: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_applications: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_candidates: Mapped[bool] = mapped_column(Boolean, default=False)

    # Webhook settings
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_events: Mapped[list] = mapped_column(JSONB, default=list)

    # Sync status
    last_synced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_status: Mapped[str] = mapped_column(String(50), default="active")
    sync_errors: Mapped[dict] = mapped_column(JSONB, default=dict)
    jobs_synced_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("idx_org_ats_provider", "organization_id", "ats_provider"),)


class ATSJobSync(Base):
    __tablename__ = "ats_job_syncs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ats_integration_id: Mapped[int] = mapped_column(ForeignKey("ats_integrations.id"))
    job_post_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))

    # ATS job details
    ats_job_id: Mapped[str] = mapped_column(String(255))
    ats_job_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ats_status: Mapped[str] = mapped_column(String(50))  # open, closed, draft, archived

    # Sync metadata
    first_synced: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_synced: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_status: Mapped[str] = mapped_column(String(50), default="active")
    sync_errors: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Job posting metadata from ATS
    ats_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    hiring_manager: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("idx_ats_job_sync", "ats_integration_id", "ats_job_id", unique=True),
    )


class ATSApplicationSync(Base):
    __tablename__ = "ats_application_syncs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ats_integration_id: Mapped[int] = mapped_column(ForeignKey("ats_integrations.id"))
    job_application_id: Mapped[int] = mapped_column(ForeignKey("job_applications.id"))

    # ATS application details
    ats_application_id: Mapped[str] = mapped_column(String(255))
    ats_candidate_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ats_status: Mapped[str] = mapped_column(String(100))
    ats_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Application tracking
    submitted_to_ats: Mapped[bool] = mapped_column(Boolean, default=False)
    ats_submission_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_status_update: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ATS metadata
    ats_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    recruiter_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    interview_feedback: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Sync status
    sync_status: Mapped[str] = mapped_column(String(50), default="active")
    sync_errors: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index(
            "idx_ats_app_sync", "ats_integration_id", "ats_application_id", unique=True
        ),
    )


# Integration Activity Log
class IntegrationActivityLog(Base):
    __tablename__ = "integration_activity_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organization.id"), nullable=True
    )

    # Integration details
    integration_type: Mapped[str] = mapped_column(String(50))  # linkedin, calendar, ats
    integration_id: Mapped[int] = mapped_column(
        Integer
    )  # ID of the specific integration

    # Activity details
    activity_type: Mapped[str] = mapped_column(
        String(100)
    )  # sync, auth, error, webhook, etc.
    activity_description: Mapped[str] = mapped_column(Text)
    activity_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Status and metadata
    status: Mapped[str] = mapped_column(String(50))  # success, error, warning, info
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index(
            "idx_integration_activity",
            "integration_type",
            "integration_id",
            "created_at",
        ),
    )
