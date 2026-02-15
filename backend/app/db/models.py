import os

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if os.getenv("DATABASE_URL", "").startswith("sqlite"):
    from sqlalchemy import JSON as JSONB

    UUID = String(36)
else:
    try:
        from sqlalchemy.dialects.postgresql import JSONB, UUID
    except Exception:
        from sqlalchemy import JSON as JSONB

        UUID = String(36)
import uuid
from datetime import datetime
from typing import List


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
    # Note: This serves as jobs_normalized in the production plan
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(Text, unique=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_hash: Mapped[str | None] = mapped_column(String(32), index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    repost_count: Mapped[int] = mapped_column(Integer, default=0)
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
    description_clean: Mapped[str | None] = mapped_column(Text)
    requirements_raw: Mapped[str | None] = mapped_column(Text)
    education: Mapped[str | None] = mapped_column(String(120))
    attachment_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_score: Mapped[float | None] = mapped_column(Float)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

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


class JobDedupeMap(Base):
    __tablename__ = "job_dedupe_map"
    job_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"), primary_key=True)
    canonical_job_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"), index=True)
    similarity_score: Mapped[float] = mapped_column(Float)


class JobEntities(Base):
    __tablename__ = "job_entities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"), unique=True)
    entities: Mapped[dict] = mapped_column(JSONB, default=dict)
    skills: Mapped[list] = mapped_column(JSONB, default=list)
    tools: Mapped[list] = mapped_column(JSONB, default=list)
    education: Mapped[dict] = mapped_column(JSONB, default=dict)
    experience: Mapped[dict] = mapped_column(JSONB, default=dict)


class JobEmbedding(Base):
    __tablename__ = "job_embeddings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))
    model_name: Mapped[str] = mapped_column(String(100))
    # Note: vector type will be added via pgvector extension in Postgres
    vector_json: Mapped[dict] = mapped_column(JSONB, nullable=True)


class SkillTrendsMonthly(Base):
    __tablename__ = "skill_trends_monthly"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill: Mapped[str] = mapped_column(String(120), index=True)
    title_norm: Mapped[str] = mapped_column(String(120), index=True)
    month: Mapped[datetime] = mapped_column(DateTime, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    share: Mapped[float] = mapped_column(Float, default=0.0)


class RoleEvolution(Base):
    __tablename__ = "role_evolution"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title_norm: Mapped[str] = mapped_column(String(120), index=True)
    month: Mapped[datetime] = mapped_column(DateTime, index=True)
    top_skills: Mapped[dict] = mapped_column(JSONB, default=dict)


class RoleSkillBaseline(Base):
    __tablename__ = "role_skill_baseline"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_family: Mapped[str] = mapped_column(String(120), index=True)
    skill_name: Mapped[str] = mapped_column(String(120), index=True)
    skill_share: Mapped[float] = mapped_column(Float, default=0.0)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    sample_job_ids: Mapped[list] = mapped_column(JSONB, default=list)
    count_total_jobs_used: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


class RoleEducationBaseline(Base):
    __tablename__ = "role_education_baseline"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_family: Mapped[str] = mapped_column(String(120), index=True)
    education_level: Mapped[str] = mapped_column(String(120), index=True)
    education_share: Mapped[float] = mapped_column(Float, default=0.0)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    sample_job_ids: Mapped[list] = mapped_column(JSONB, default=list)
    count_total_jobs_used: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


class RoleExperienceBaseline(Base):
    __tablename__ = "role_experience_baseline"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_family: Mapped[str] = mapped_column(String(120), index=True)
    experience_band: Mapped[str] = mapped_column(String(120), index=True)
    experience_share: Mapped[float] = mapped_column(Float, default=0.0)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    sample_job_ids: Mapped[list] = mapped_column(JSONB, default=list)
    count_total_jobs_used: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


class RoleDemandSnapshot(Base):
    __tablename__ = "role_demand_snapshot"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_family: Mapped[str] = mapped_column(String(120), index=True)
    demand_count: Mapped[int] = mapped_column(Integer, default=0)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    sample_job_ids: Mapped[list] = mapped_column(JSONB, default=list)
    count_total_jobs_used: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


class TitleAdjacency(Base):
    __tablename__ = "title_adjacency"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title_a: Mapped[str] = mapped_column(String(120), index=True)
    title_b: Mapped[str] = mapped_column(String(120), index=True)
    similarity: Mapped[float] = mapped_column(Float)


class TenderNotice(Base):
    __tablename__ = "tender_notice"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(120), index=True)
    external_id: Mapped[str | None] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(255))
    organization: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(120))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    closing_at: Mapped[datetime | None] = mapped_column(DateTime)
    url: Mapped[str | None] = mapped_column(Text)
    description_raw: Mapped[str | None] = mapped_column(Text)
    meta_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SignalEvidence(Base):
    __tablename__ = "signal_evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_type: Mapped[str] = mapped_column(String(120), index=True)
    source: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    meta_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TaskRoleMapping(Base):
    __tablename__ = "task_role_mapping"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_text: Mapped[str] = mapped_column(Text)
    role_family: Mapped[str] = mapped_column(String(120), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("signal_evidence.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HiringSignal(Base):
    __tablename__ = "hiring_signal"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_type: Mapped[str] = mapped_column(String(120), index=True)
    role_family: Mapped[str | None] = mapped_column(String(120), index=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organization.id"))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    window_start: Mapped[datetime | None] = mapped_column(DateTime)
    window_end: Mapped[datetime | None] = mapped_column(DateTime)
    evidence_ids: Mapped[list] = mapped_column(JSONB, default=list)
    meta_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IngestionState(Base):
    __tablename__ = "ingestion_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_item_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_cursor: Mapped[str | None] = mapped_column(String(255))
    last_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str | None] = mapped_column(String(120))
    meta_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class JobSkill(Base):
    __tablename__ = "job_skill"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_post_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

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
    subscription_tier: Mapped[str] = mapped_column(String(50), default="basic")
    subscription_expires: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

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

    current_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    education: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[dict] = mapped_column(JSONB, default=dict)
    career_goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_locations: Mapped[list] = mapped_column(JSONB, default=list)
    salary_expectations: Mapped[dict] = mapped_column(JSONB, default=dict)

    job_alert_preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    notification_preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    privacy_settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    profile_completeness: Mapped[float] = mapped_column(Float, default=0.0)
    cv_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="profile")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_post_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    folder: Mapped[str | None] = mapped_column(String(100), nullable=True)

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
    status: Mapped[str] = mapped_column(String(50), default="applied")
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    application_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    referrer_info: Mapped[dict] = mapped_column(JSONB, default=dict)

    interview_dates: Mapped[list] = mapped_column(JSONB, default=list)
    feedback_received: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_offered: Mapped[dict] = mapped_column(JSONB, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    clicked_jobs: Mapped[list] = mapped_column(JSONB, default=list)
    searched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="search_history")


class UserNotification(Base):
    __tablename__ = "user_notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered_via: Mapped[list] = mapped_column(JSONB, default=list)
    delivery_status: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="notifications")


class UserJobRecommendation(Base):
    __tablename__ = "user_job_recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_post_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))

    match_score: Mapped[float] = mapped_column(Float)
    skill_match_score: Mapped[float] = mapped_column(Float)
    location_match_score: Mapped[float] = mapped_column(Float)
    salary_match_score: Mapped[float] = mapped_column(Float)
    experience_match_score: Mapped[float] = mapped_column(Float)

    match_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_skills: Mapped[list] = mapped_column(JSONB, default=list)
    matching_skills: Mapped[list] = mapped_column(JSONB, default=list)

    recommended_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    algorithm_version: Mapped[str] = mapped_column(String(50), default="v1.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    viewed: Mapped[bool] = mapped_column(Boolean, default=False)
    clicked: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_user_job_recommendation", "user_id", "job_post_id", unique=True),
    )


class CompanyReview(Base):
    __tablename__ = "company_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    overall_rating: Mapped[float] = mapped_column(Float)
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

    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    employment_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    moderation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SkillAssessment(Base):
    __tablename__ = "skill_assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"))

    score: Mapped[float] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(50))
    percentile: Mapped[float | None] = mapped_column(Float, nullable=True)

    assessment_type: Mapped[str] = mapped_column(String(50))
    questions_total: Mapped[int] = mapped_column(Integer)
    questions_correct: Mapped[int] = mapped_column(Integer)
    time_taken_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    certificate_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    taken_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_user_skill_assessment", "user_id", "skill_id"),)


class JobAlert(Base):
    __tablename__ = "job_alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    name: Mapped[str] = mapped_column(String(255))
    query: Mapped[str] = mapped_column(String(500))
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    frequency: Mapped[str] = mapped_column(String(50), default="daily")
    delivery_methods: Mapped[list] = mapped_column(JSONB, default=list)

    jobs_found_total: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_jobs_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class InterviewPreparation(Base):
    __tablename__ = "interview_preparations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_application_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_applications.id"), nullable=True
    )

    company_name: Mapped[str] = mapped_column(String(255))
    role_title: Mapped[str] = mapped_column(String(255))
    interview_type: Mapped[str] = mapped_column(String(50))
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    questions_practiced: Mapped[list] = mapped_column(JSONB, default=list)
    research_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    preparation_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    suggested_questions: Mapped[list] = mapped_column(JSONB, default=list)
    company_insights: Mapped[dict] = mapped_column(JSONB, default=dict)
    role_specific_tips: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserAnalytics(Base):
    __tablename__ = "user_analytics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    session_id: Mapped[str] = mapped_column(String(100))
    event_type: Mapped[str] = mapped_column(String(50))
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )


class BetaSignup(Base):
    """Beta program participant (VIP Beta Program for proof generation)."""

    __tablename__ = "beta_signups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20))
    university: Mapped[str] = mapped_column(String(255), index=True)
    year_of_study: Mapped[str] = mapped_column(String(50))
    field_of_study: Mapped[str] = mapped_column(String(255))
    skills: Mapped[str] = mapped_column(Text)
    career_goals: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(50), default="pending")
    signed_up_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rewarded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    jobs_viewed: Mapped[int] = mapped_column(Integer, default=0)
    jobs_saved: Mapped[int] = mapped_column(Integer, default=0)
    jobs_applied: Mapped[int] = mapped_column(Integer, default=0)
    searches_performed: Mapped[int] = mapped_column(Integer, default=0)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BetaActivity(Base):
    """Track beta user activity for analytics and ROI proof."""

    __tablename__ = "beta_activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    beta_id: Mapped[int] = mapped_column(ForeignKey("beta_signups.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
