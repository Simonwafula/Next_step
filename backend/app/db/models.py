from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, ForeignKey, Float, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

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

class JobPost(Base):
    __tablename__ = "job_post"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(Text, unique=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
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
    embedding: Mapped[str | None] = mapped_column(Text)  # store as JSON string or move to vector type later

class JobSkill(Base):
    __tablename__ = "job_skill"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_post_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

class MetricsDaily(Base):
    __tablename__ = "metrics_daily"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    role_family: Mapped[str | None] = mapped_column(String(120), index=True)
    location_key: Mapped[str | None] = mapped_column(String(120), index=True)
    postings: Mapped[int] = mapped_column(Integer, default=0)
    salary_p50: Mapped[float | None] = mapped_column(Float)
    tenure_mix_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    top_skills_json: Mapped[dict] = mapped_column(JSONB, default=dict)
