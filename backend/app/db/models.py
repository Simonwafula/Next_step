from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import (
    String,
    Integer,
    Text,
    ForeignKey,
    Float,
    DateTime,
    Boolean,
    Index,
)
import os

from .types import VectorString

# Use PostgreSQL JSONB when available, but fall back to generic JSON for SQLite
if os.getenv("DATABASE_URL", "").startswith("sqlite"):
    from sqlalchemy import JSON as JSONB

    UUID = String(36)
else:
    try:
        from sqlalchemy.dialects.postgresql import JSONB, UUID
    except Exception:
        from sqlalchemy import JSON as JSONB

        UUID = String(36)
from datetime import datetime
from typing import List
import uuid

EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organization"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ats: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class Location(Base):
    __tablename__ = "location"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    raw: Mapped[str | None] = mapped_column(String(255))


class TitleNorm(Base):
    __tablename__ = "title_norm"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family: Mapped[str] = mapped_column(String(120), index=True)
    canonical_title: Mapped[str] = mapped_column(String(120), index=True)
    aliases: Mapped[dict] = mapped_column(JSONB, default=dict)


class Skill(Base):
    __tablename__ = "skill"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    taxonomy_ref: Mapped[str | None] = mapped_column(String(120))
    aliases: Mapped[dict] = mapped_column(JSONB, default=dict)


class EducationNormalization(Base):
    __tablename__ = "education_normalization"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_value: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    normalized_value: Mapped[str] = mapped_column(String(120), index=True)
    notes: Mapped[str | None] = mapped_column(String(255))


class JobPost(Base):
    __tablename__ = "job_post"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(Text, unique=True)
    url_hash: Mapped[str | None] = mapped_column(
        String(32), index=True
    )  # MD5 hash of normalized URL
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    repost_count: Mapped[int] = mapped_column(
        Integer, default=0
    )  # How many times job has been reposted
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organization.id"))
    title_raw: Mapped[str] = mapped_column(String(255))
    title_norm_id: Mapped[int | None] = mapped_column(ForeignKey("title_norm.id"))
    location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"))
    tenure: Mapped[str | None] = mapped_column(String(50))
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(10))
    seniority: Mapped[str | None] = mapped_column(String(50))
    description_raw: Mapped[str | None] = mapped_column(Text)
    requirements_raw: Mapped[str | None] = mapped_column(Text)
    education: Mapped[str | None] = mapped_column(String(120))
    attachment_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_score: Mapped[float | None] = mapped_column(
        Float
    )  # Data quality score 0-100
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )  # When job was fully processed
    embedding: Mapped[str | None] = mapped_column(
        Text
    )  # store as JSON string or move to vector type later
    embedding_vector: Mapped[str | None] = mapped_column(
        VectorString(EMBEDDING_DIM),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", foreign_keys=[org_id], lazy="select"
    )
    location: Mapped["Location"] = relationship(
        "Location", foreign_keys=[location_id], lazy="select"
    )
    title_norm: Mapped["TitleNorm"] = relationship(
        "TitleNorm", foreign_keys=[title_norm_id], lazy="select"
    )
    skills: Mapped[List["JobSkill"]] = relationship(
        "JobSkill", back_populates="job_post", lazy="select"
    )


class JobSkill(Base):
    __tablename__ = "job_skill"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_post_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    # Relationships
    job_post: Mapped["JobPost"] = relationship(
        "JobPost", back_populates="skills", lazy="select"
    )


class ProcessingLog(Base):
    __tablename__ = "processing_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_type: Mapped[str] = mapped_column(String(120), index=True)
    results: Mapped[dict] = mapped_column(JSONB, default=dict)
    processed_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)


class MetricsDaily(Base):
    __tablename__ = "metrics_daily"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    role_family: Mapped[str | None] = mapped_column(String(120), index=True)
    location_key: Mapped[str | None] = mapped_column(String(120), index=True)
    postings: Mapped[int] = mapped_column(Integer, default=0)
    salary_p50: Mapped[float | None] = mapped_column(Float)
    tenure_mix_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    top_skills_json: Mapped[dict] = mapped_column(JSONB, default=dict)


# User Authentication & Profile Models
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_tier: Mapped[str] = mapped_column(
        String(50), default="basic"
    )  # basic, professional, enterprise
    subscription_expires: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="user", uselist=False
    )
    saved_jobs: Mapped[List["SavedJob"]] = relationship(
        "SavedJob", back_populates="user"
    )
    job_applications: Mapped[List["JobApplication"]] = relationship(
        "JobApplication", back_populates="user"
    )
    search_history: Mapped[List["SearchHistory"]] = relationship(
        "SearchHistory", back_populates="user"
    )
    notifications: Mapped[List["UserNotification"]] = relationship(
        "UserNotification", back_populates="user"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    # Career Information
    current_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # entry, mid, senior, executive
    education: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # {"skill_name": confidence_score}
    career_goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_locations: Mapped[list] = mapped_column(JSONB, default=list)
    salary_expectations: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # {"min": 50000, "max": 80000, "currency": "KSH"}

    # Preferences
    job_alert_preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    notification_preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    privacy_settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Profile completeness and optimization
    profile_completeness: Mapped[float] = mapped_column(Float, default=0.0)
    cv_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_post_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    folder: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # For organizing saved jobs

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="saved_jobs")
    job_post: Mapped["JobPost"] = relationship("JobPost")

    __table_args__ = (
        Index("idx_user_job_saved", "user_id", "job_post_id", unique=True),
    )


class JobApplication(Base):
    __tablename__ = "job_applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_post_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))
    status: Mapped[str] = mapped_column(
        String(50), default="applied"
    )  # applied, screening, interview, offer, rejected, withdrawn
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Application details
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    application_source: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # direct, platform, referral
    referrer_info: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Interview and follow-up tracking
    interview_dates: Mapped[list] = mapped_column(JSONB, default=list)
    feedback_received: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_offered: Mapped[dict] = mapped_column(JSONB, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="job_applications")
    job_post: Mapped["JobPost"] = relationship("JobPost")

    __table_args__ = (
        Index("idx_user_job_application", "user_id", "job_post_id", unique=True),
    )


class SearchHistory(Base):
    __tablename__ = "search_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    query: Mapped[str] = mapped_column(String(500))
    filters: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # location, seniority, etc.
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    clicked_jobs: Mapped[list] = mapped_column(
        JSONB, default=list
    )  # job_post_ids that were clicked
    searched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="search_history")


class UserNotification(Base):
    __tablename__ = "user_notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(
        String(50)
    )  # job_alert, career_advice, system, marketing
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # Additional structured data

    # Delivery tracking
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered_via: Mapped[list] = mapped_column(
        JSONB, default=list
    )  # email, whatsapp, push, in_app
    delivery_status: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")


# Enhanced Job Matching and Recommendations
class UserJobRecommendation(Base):
    __tablename__ = "user_job_recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_post_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))

    # Recommendation scoring
    match_score: Mapped[float] = mapped_column(Float)  # 0.0 to 1.0
    skill_match_score: Mapped[float] = mapped_column(Float)
    location_match_score: Mapped[float] = mapped_column(Float)
    salary_match_score: Mapped[float] = mapped_column(Float)
    experience_match_score: Mapped[float] = mapped_column(Float)

    # Explanation and reasoning
    match_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_skills: Mapped[list] = mapped_column(JSONB, default=list)
    matching_skills: Mapped[list] = mapped_column(JSONB, default=list)

    # Recommendation metadata
    recommended_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    algorithm_version: Mapped[str] = mapped_column(String(50), default="v1.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # User interaction tracking
    viewed: Mapped[bool] = mapped_column(Boolean, default=False)
    clicked: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_user_job_recommendation", "user_id", "job_post_id", unique=True),
    )


# Company Reviews and Ratings
class CompanyReview(Base):
    __tablename__ = "company_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )  # Anonymous reviews allowed

    # Review content
    overall_rating: Mapped[float] = mapped_column(Float)  # 1.0 to 5.0
    work_life_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    compensation: Mapped[float | None] = mapped_column(Float, nullable=True)
    career_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    management: Mapped[float | None] = mapped_column(Float, nullable=True)
    culture: Mapped[float | None] = mapped_column(Float, nullable=True)

    title: Mapped[str] = mapped_column(String(255))
    review_text: Mapped[str] = mapped_column(Text)
    pros: Mapped[str | None] = mapped_column(Text, nullable=True)
    cons: Mapped[str | None] = mapped_column(Text, nullable=True)
    advice_to_management: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Review metadata
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # current, former
    employment_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Moderation
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    moderation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# Skills Assessment and Certification
class SkillAssessment(Base):
    __tablename__ = "skill_assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"))

    # Assessment results
    score: Mapped[float] = mapped_column(Float)  # 0.0 to 100.0
    level: Mapped[str] = mapped_column(
        String(50)
    )  # beginner, intermediate, advanced, expert
    percentile: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # Compared to other users

    # Assessment metadata
    assessment_type: Mapped[str] = mapped_column(
        String(50)
    )  # quiz, practical, portfolio
    questions_total: Mapped[int] = mapped_column(Integer)
    questions_correct: Mapped[int] = mapped_column(Integer)
    time_taken_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Certification
    is_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    certificate_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    taken_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_user_skill_assessment", "user_id", "skill_id"),)


# Real-time Job Alerts
class JobAlert(Base):
    __tablename__ = "job_alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Alert criteria
    name: Mapped[str] = mapped_column(String(255))
    query: Mapped[str] = mapped_column(String(500))
    filters: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # location, salary, seniority, etc.

    # Alert settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    frequency: Mapped[str] = mapped_column(
        String(50), default="daily"
    )  # immediate, daily, weekly
    delivery_methods: Mapped[list] = mapped_column(
        JSONB, default=list
    )  # email, whatsapp, push

    # Alert performance
    jobs_found_total: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_jobs_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Interview Preparation and Tracking
class InterviewPreparation(Base):
    __tablename__ = "interview_preparations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_application_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_applications.id"), nullable=True
    )

    # Interview details
    company_name: Mapped[str] = mapped_column(String(255))
    role_title: Mapped[str] = mapped_column(String(255))
    interview_type: Mapped[str] = mapped_column(
        String(50)
    )  # phone, video, in_person, technical
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Preparation materials
    questions_practiced: Mapped[list] = mapped_column(JSONB, default=list)
    research_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    preparation_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0.0 to 100.0

    # AI-generated content
    suggested_questions: Mapped[list] = mapped_column(JSONB, default=list)
    company_insights: Mapped[dict] = mapped_column(JSONB, default=dict)
    role_specific_tips: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Analytics and User Behavior Tracking
class UserAnalytics(Base):
    __tablename__ = "user_analytics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Session tracking
    session_id: Mapped[str] = mapped_column(String(100))
    event_type: Mapped[str] = mapped_column(
        String(50)
    )  # search, view_job, save_job, apply, etc.
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Context
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
