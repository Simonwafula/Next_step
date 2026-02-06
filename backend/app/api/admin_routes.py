from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
import yaml

from ..db.database import get_db
from ..db.models import (
    JobApplication,
    JobPost,
    JobSkill,
    JobAlert,
    Location,
    Organization,
    ProcessingLog,
    EducationNormalization,
    Skill,
    TitleNorm,
    SavedJob,
    SearchHistory,
    User,
    UserNotification,
)
from ..services.auth_service import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])

BASE_DIR = Path(__file__).resolve().parents[1]


def _load_sources(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        return []
    return sources


def _source_summary(sources: List[Dict[str, Any]]) -> Dict[str, int]:
    active = 0
    inactive = 0
    for source in sources:
        status = str(source.get("status", "active")).strip().lower()
        if status in {"active", "live", "enabled"}:
            active += 1
        else:
            inactive += 1
    return {"total": len(sources), "active": active, "inactive": inactive}


@router.get("/overview")
def admin_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    now = datetime.utcnow()
    seven_days = now - timedelta(days=7)

    users_total = db.execute(select(func.count(User.id))).scalar() or 0
    users_new = (
        db.execute(
            select(func.count(User.id)).where(User.created_at >= seven_days)
        ).scalar()
        or 0
    )
    users_active = (
        db.execute(
            select(func.count(User.id)).where(User.last_login >= seven_days)
        ).scalar()
        or 0
    )

    jobs_total = db.execute(select(func.count(JobPost.id))).scalar() or 0
    jobs_new = (
        db.execute(
            select(func.count(JobPost.id)).where(JobPost.first_seen >= seven_days)
        ).scalar()
        or 0
    )
    latest_job = db.execute(select(func.max(JobPost.first_seen))).scalar()

    orgs_total = db.execute(select(func.count(Organization.id))).scalar() or 0
    locations_total = db.execute(select(func.count(Location.id))).scalar() or 0
    saved_jobs_total = db.execute(select(func.count(SavedJob.id))).scalar() or 0
    applications_total = db.execute(select(func.count(JobApplication.id))).scalar() or 0
    searches_total = db.execute(select(func.count(SearchHistory.id))).scalar() or 0
    alerts_total = db.execute(select(func.count(JobAlert.id))).scalar() or 0
    notifications_total = (
        db.execute(select(func.count(UserNotification.id))).scalar() or 0
    )

    posts_with_salary = (
        db.execute(
            select(func.count(JobPost.id)).where(JobPost.salary_min.is_not(None))
        ).scalar()
        or 0
    )
    posts_with_skills = (
        db.execute(
            select(func.count(JobPost.id.distinct())).join_from(JobPost, JobSkill)
        ).scalar()
        or 0
    )

    core_sources = _load_sources(BASE_DIR / "ingestion" / "sources.yaml")
    gov_sources = _load_sources(BASE_DIR / "ingestion" / "government_sources.yaml")
    core_summary = _source_summary(core_sources)
    gov_summary = _source_summary(gov_sources)

    return {
        "kpis": {
            "users_total": users_total,
            "users_new_7d": users_new,
            "users_active_7d": users_active,
            "jobs_total": jobs_total,
            "jobs_new_7d": jobs_new,
            "organizations_total": orgs_total,
            "locations_total": locations_total,
            "saved_jobs_total": saved_jobs_total,
            "applications_total": applications_total,
            "searches_total": searches_total,
            "alerts_total": alerts_total,
            "notifications_total": notifications_total,
        },
        "coverage": {
            "salary": {
                "count": posts_with_salary,
                "percentage": round(posts_with_salary / jobs_total * 100, 1)
                if jobs_total
                else 0,
            },
            "skills": {
                "count": posts_with_skills,
                "percentage": round(posts_with_skills / jobs_total * 100, 1)
                if jobs_total
                else 0,
            },
        },
        "sources": {
            "core": core_summary,
            "government": gov_summary,
            "total": core_summary["total"] + gov_summary["total"],
            "active": core_summary["active"] + gov_summary["active"],
        },
        "recent": {
            "latest_job_seen": latest_job.isoformat() if latest_job else None,
        },
    }


@router.get("/users")
def admin_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    stmt = select(User).order_by(desc(User.created_at)).offset(offset).limit(limit)
    users = db.execute(stmt).scalars().all()
    return {
        "users": [
            {
                "id": user.id,
                "uuid": user.uuid,
                "email": user.email,
                "full_name": user.full_name,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }
            for user in users
        ],
        "total": len(users),
    }


@router.get("/jobs")
def admin_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    stmt = (
        select(JobPost, Organization, Location)
        .outerjoin(Organization, Organization.id == JobPost.org_id)
        .outerjoin(Location, Location.id == JobPost.location_id)
        .order_by(desc(JobPost.first_seen))
        .offset(offset)
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return {
        "jobs": [
            {
                "id": job.id,
                "title": job.title_raw,
                "organization": org.name if org else None,
                "location": location.raw if location else None,
                "source": job.source,
                "url": job.url,
                "first_seen": job.first_seen.isoformat() if job.first_seen else None,
            }
            for job, org, location in rows
        ],
        "total": len(rows),
    }


@router.get("/sources")
def admin_sources(
    source_type: str = Query("all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    if source_type not in {"all", "core", "government"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_type must be one of: all, core, government",
        )
    core_sources = _load_sources(BASE_DIR / "ingestion" / "sources.yaml")
    gov_sources = _load_sources(BASE_DIR / "ingestion" / "government_sources.yaml")

    sources = []
    if source_type in {"all", "core"}:
        sources.extend(
            {
                "source_type": "core",
                "name": source.get("name"),
                "type": source.get("type"),
                "org": source.get("org"),
                "status": source.get("status", "active"),
                "url": source.get("url") or source.get("board_token"),
            }
            for source in core_sources
        )
    if source_type in {"all", "government"}:
        sources.extend(
            {
                "source_type": "government",
                "name": source.get("name"),
                "type": source.get("type"),
                "org": source.get("org"),
                "status": source.get("status", "active"),
                "group": source.get("group"),
                "category": source.get("category"),
                "url": (source.get("list_urls") or [None])[0],
            }
            for source in gov_sources
        )

    return {
        "sources": sources,
        "total": len(sources),
    }


@router.get("/operations")
def admin_operations(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    stmt = select(ProcessingLog).order_by(desc(ProcessingLog.processed_at)).limit(limit)
    logs = db.execute(stmt).scalars().all()

    latest_by_type = {}
    for log in logs:
        if log.process_type not in latest_by_type:
            latest_by_type[log.process_type] = log

    return {
        "operations": [
            {
                "id": log.id,
                "process_type": log.process_type,
                "status": (log.results or {}).get("status"),
                "message": (log.results or {}).get("message"),
                "details": (log.results or {}).get("details"),
                "processed_at": log.processed_at.isoformat()
                if log.processed_at
                else None,
            }
            for log in logs
        ],
        "latest_by_type": {
            process_type: {
                "id": log.id,
                "process_type": log.process_type,
                "status": (log.results or {}).get("status"),
                "message": (log.results or {}).get("message"),
                "details": (log.results or {}).get("details"),
                "processed_at": log.processed_at.isoformat()
                if log.processed_at
                else None,
            }
            for process_type, log in latest_by_type.items()
        },
    }


@router.get("/summaries")
def admin_summaries(
    dimension: str = Query("title"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    if dimension not in {"title", "skill", "education"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dimension must be one of: title, skill, education",
        )

    if dimension == "title":
        stmt = (
            select(JobPost.title_raw, TitleNorm.canonical_title, func.count(JobPost.id))
            .outerjoin(TitleNorm, TitleNorm.id == JobPost.title_norm_id)
            .where(JobPost.title_raw.is_not(None))
            .group_by(JobPost.title_raw, TitleNorm.canonical_title)
            .order_by(desc(func.count(JobPost.id)))
            .limit(limit)
        )
        rows = db.execute(stmt).all()
    elif dimension == "skill":
        stmt = (
            select(Skill.name, func.count(JobSkill.id))
            .join(JobSkill, JobSkill.skill_id == Skill.id)
            .group_by(Skill.name)
            .order_by(desc(func.count(JobSkill.id)))
            .limit(limit)
        )
        rows = db.execute(stmt).all()
    else:
        stmt = (
            select(
                JobPost.education,
                EducationNormalization.normalized_value,
                func.count(JobPost.id),
            )
            .outerjoin(
                EducationNormalization,
                EducationNormalization.raw_value == JobPost.education,
            )
            .where(JobPost.education.is_not(None))
            .group_by(JobPost.education, EducationNormalization.normalized_value)
            .order_by(desc(func.count(JobPost.id)))
            .limit(limit)
        )
        rows = db.execute(stmt).all()

    return {
        "dimension": dimension,
        "items": [
            {
                "specific_value": value,
                "normalized_value": normalized,
                "count": count,
            }
            for value, normalized, count in (
                [(value, value, count) for value, count in rows]
                if dimension == "skill"
                else rows
            )
            if value
        ],
    }


@router.get("/summaries/{dimension}/jobs")
def admin_summary_jobs(
    dimension: str,
    value: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    if dimension not in {"title", "skill", "education"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dimension must be one of: title, skill, education",
        )

    stmt = (
        select(JobPost, Organization, Location)
        .outerjoin(Organization, Organization.id == JobPost.org_id)
        .outerjoin(Location, Location.id == JobPost.location_id)
        .order_by(desc(JobPost.first_seen))
        .limit(limit)
    )

    if dimension == "title":
        stmt = stmt.where(JobPost.title_raw == value)
    elif dimension == "skill":
        stmt = (
            stmt.join(JobSkill, JobSkill.job_post_id == JobPost.id)
            .join(Skill, Skill.id == JobSkill.skill_id)
            .where(Skill.name == value)
        )
    else:
        stmt = stmt.where(JobPost.education == value)

    rows = db.execute(stmt).all()
    return {
        "dimension": dimension,
        "value": value,
        "jobs": [
            {
                "id": job.id,
                "title": job.title_raw,
                "organization": org.name if org else None,
                "location": location.raw if location else None,
                "source": job.source,
                "url": job.url,
                "first_seen": job.first_seen.isoformat() if job.first_seen else None,
            }
            for job, org, location in rows
        ],
        "total": len(rows),
    }


@router.get("/education-mappings")
def list_education_mappings(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    stmt = (
        select(EducationNormalization)
        .order_by(EducationNormalization.raw_value)
        .limit(limit)
    )
    mappings = db.execute(stmt).scalars().all()
    return {
        "mappings": [
            {
                "id": mapping.id,
                "raw_value": mapping.raw_value,
                "normalized_value": mapping.normalized_value,
                "notes": mapping.notes,
            }
            for mapping in mappings
        ],
        "total": len(mappings),
    }


@router.post("/education-mappings")
def upsert_education_mapping(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    raw_value = str(payload.get("raw_value", "")).strip()
    normalized_value = str(payload.get("normalized_value", "")).strip()
    notes = payload.get("notes")
    if not raw_value or not normalized_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="raw_value and normalized_value are required",
        )

    mapping = db.execute(
        select(EducationNormalization).where(
            EducationNormalization.raw_value == raw_value
        )
    ).scalar_one_or_none()
    if mapping:
        mapping.normalized_value = normalized_value
        mapping.notes = notes
    else:
        mapping = EducationNormalization(
            raw_value=raw_value,
            normalized_value=normalized_value,
            notes=notes,
        )
        db.add(mapping)
    db.commit()
    db.refresh(mapping)

    return {
        "id": mapping.id,
        "raw_value": mapping.raw_value,
        "normalized_value": mapping.normalized_value,
        "notes": mapping.notes,
    }
