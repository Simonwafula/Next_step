from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
import yaml

from ..db.database import get_db
from ..db.models import (
    JobDedupeMap,
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
from ..services.analytics import (
    get_skill_trends,
    get_role_evolution,
    get_title_adjacency,
    run_drift_checks,
)
from ..services.processing_log_service import log_monitoring_event
from ..services.monitoring_service import monitoring_summary
from ..services.signals import list_tenders, list_hiring_signals
from ..services.admin_alert_service import admin_alert_service
from ..services.gov_processing_service import (
    government_quality_snapshot,
    process_government_posts,
)
from ..services.gov_quarantine_service import quarantine_government_nonjobs
from ..services.post_ingestion_processing_service import process_job_posts
from ..services.processing_quality import quality_snapshot
from ..core.config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

BASE_DIR = Path(__file__).resolve().parents[1]
CONVERSION_ALERT_SETTINGS_PROCESS_TYPE = "admin_conversion_alert_settings"


def _safe_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


class ConversionAlertSettingsUpdateRequest(BaseModel):
    threshold: float | None = Field(default=None, ge=0.0, le=100.0)
    cooldown_hours: int | None = Field(default=None, ge=1, le=168)
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    whatsapp_enabled: bool | None = None


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


def _default_conversion_alert_settings() -> Dict[str, Any]:
    return {
        "threshold": settings.ADMIN_CONVERSION_ALERT_THRESHOLD,
        "cooldown_hours": settings.ADMIN_CONVERSION_ALERT_COOLDOWN_HOURS,
        "in_app_enabled": settings.ADMIN_CONVERSION_ALERT_IN_APP_ENABLED,
        "email_enabled": settings.ADMIN_CONVERSION_ALERT_EMAIL_ENABLED,
        "whatsapp_enabled": settings.ADMIN_CONVERSION_ALERT_WHATSAPP_ENABLED,
    }


def _load_conversion_alert_settings(db: Session) -> tuple[Dict[str, Any], str]:
    defaults = _default_conversion_alert_settings()
    latest = (
        db.execute(
            select(ProcessingLog)
            .where(ProcessingLog.process_type == CONVERSION_ALERT_SETTINGS_PROCESS_TYPE)
            .order_by(desc(ProcessingLog.processed_at))
            .limit(1)
        )
        .scalars()
        .first()
    )
    if latest is None:
        return defaults, "defaults"

    results = latest.results or {}
    persisted_settings = results.get("settings") or {}
    merged = {
        **defaults,
        **{
            "threshold": persisted_settings.get(
                "threshold",
                defaults["threshold"],
            ),
            "cooldown_hours": persisted_settings.get(
                "cooldown_hours",
                defaults["cooldown_hours"],
            ),
            "in_app_enabled": persisted_settings.get(
                "in_app_enabled",
                defaults["in_app_enabled"],
            ),
            "email_enabled": persisted_settings.get(
                "email_enabled",
                defaults["email_enabled"],
            ),
            "whatsapp_enabled": persisted_settings.get(
                "whatsapp_enabled",
                defaults["whatsapp_enabled"],
            ),
        },
    }
    return merged, "override"


@router.get("/lmi-alert-settings")
def get_lmi_alert_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    settings_payload, source = _load_conversion_alert_settings(db)
    return {
        "settings": settings_payload,
        "source": source,
    }


@router.put("/lmi-alert-settings")
def update_lmi_alert_settings(
    payload: ConversionAlertSettingsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    allowed_editors = {
        email.strip().lower()
        for email in settings.ADMIN_SETTINGS_EDITORS.split(",")
        if email.strip()
    }
    if allowed_editors and current_user.email.lower() not in allowed_editors:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update LMI alert settings",
        )

    current_settings, _ = _load_conversion_alert_settings(db)

    updates = payload.model_dump(exclude_none=True)
    new_settings = {
        **current_settings,
        **updates,
    }

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    db.add(
        ProcessingLog(
            process_type=CONVERSION_ALERT_SETTINGS_PROCESS_TYPE,
            results={
                "status": "success",
                "settings": new_settings,
                "updated_by": current_user.email,
                "updated_at": datetime.utcnow().isoformat(),
                "request_metadata": {
                    "ip": client_ip,
                    "user_agent": user_agent,
                },
            },
            processed_at=datetime.utcnow(),
        )
    )
    db.commit()

    return {
        "message": "LMI alert settings updated",
        "settings": new_settings,
    }


@router.get("/lmi-alert-settings/history")
def get_lmi_alert_settings_history(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    rows = (
        db.execute(
            select(ProcessingLog)
            .where(ProcessingLog.process_type == CONVERSION_ALERT_SETTINGS_PROCESS_TYPE)
            .order_by(desc(ProcessingLog.processed_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )

    history = []
    for row in rows:
        results = row.results or {}
        history.append(
            {
                "id": row.id,
                "processed_at": row.processed_at.isoformat(),
                "updated_by": results.get("updated_by"),
                "settings": results.get("settings") or {},
                "request_metadata": results.get("request_metadata") or {},
            }
        )

    return {
        "history": history,
        "count": len(history),
    }


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


@router.get("/lmi-quality")
def admin_lmi_quality(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    now = datetime.utcnow()
    seven_days = now - timedelta(days=7)
    thirty_days = now - timedelta(days=30)

    ingestion_logs = (
        db.execute(
            select(ProcessingLog).where(
                ProcessingLog.process_type.in_(
                    [
                        "ingestion",
                        "ingest_all",
                        "ingest_government",
                        "daily_workflow",
                    ]
                ),
                ProcessingLog.processed_at >= seven_days,
            )
        )
        .scalars()
        .all()
    )

    total_runs_7d = len(ingestion_logs)
    success_runs_7d = sum(
        1
        for log in ingestion_logs
        if ((log.results or {}).get("status") or "").lower() == "success"
    )
    error_runs_7d = sum(
        1
        for log in ingestion_logs
        if ((log.results or {}).get("status") or "").lower() == "error"
    )
    success_rate_7d = (
        round((success_runs_7d / total_runs_7d) * 100, 1) if total_runs_7d else 0.0
    )

    total_jobs = db.execute(select(func.count(JobPost.id))).scalar() or 0
    jobs_with_skills = (
        db.execute(
            select(func.count(JobPost.id.distinct())).join_from(JobPost, JobSkill)
        ).scalar()
        or 0
    )
    avg_skill_confidence = db.execute(select(func.avg(JobSkill.confidence))).scalar()
    avg_skill_confidence = float(avg_skill_confidence or 0.0)
    skills_coverage = (
        round((jobs_with_skills / total_jobs) * 100, 1) if total_jobs else 0.0
    )

    total_users = db.execute(select(func.count(User.id))).scalar() or 0
    active_search_users_30d = (
        db.execute(
            select(func.count(SearchHistory.user_id.distinct())).where(
                SearchHistory.searched_at >= thirty_days
            )
        ).scalar()
        or 0
    )
    active_application_users_30d = (
        db.execute(
            select(func.count(JobApplication.user_id.distinct())).where(
                JobApplication.applied_at >= thirty_days
            )
        ).scalar()
        or 0
    )
    lmi_engagement_rate = (
        round((active_search_users_30d / total_users) * 100, 1) if total_users else 0.0
    )

    paid_users = (
        db.execute(
            select(func.count(User.id)).where(User.subscription_tier != "basic")
        ).scalar()
        or 0
    )
    users_new_30d = (
        db.execute(
            select(func.count(User.id)).where(User.created_at >= thirty_days)
        ).scalar()
        or 0
    )
    upgraded_users_30d = (
        db.execute(
            select(func.count(UserNotification.user_id.distinct())).where(
                UserNotification.type == "subscription_upgrade",
                UserNotification.created_at >= thirty_days,
            )
        ).scalar()
        or 0
    )
    churned_paid_users = (
        db.execute(
            select(func.count(User.id)).where(
                User.subscription_tier != "basic",
                User.subscription_expires.is_not(None),
                User.subscription_expires < now,
            )
        ).scalar()
        or 0
    )

    estimated_mrr_kes = paid_users * 250
    estimated_arpu_kes = round(estimated_mrr_kes / paid_users, 1) if paid_users else 0.0
    estimated_churn_rate = (
        round((churned_paid_users / paid_users) * 100, 1) if paid_users else 0.0
    )
    conversion_rate_30d = (
        round((upgraded_users_30d / users_new_30d) * 100, 1) if users_new_30d else 0.0
    )
    paid_conversion_overall = (
        round((paid_users / total_users) * 100, 1) if total_users else 0.0
    )

    trend_days = 14
    trend_start = now - timedelta(days=trend_days - 1)

    upgrades_by_date_rows = db.execute(
        select(
            func.date(UserNotification.created_at),
            func.count(UserNotification.id),
        )
        .where(
            UserNotification.type == "subscription_upgrade",
            UserNotification.created_at >= trend_start,
        )
        .group_by(func.date(UserNotification.created_at))
    ).all()
    upgrades_by_date = {
        str(date_key): int(count)
        for date_key, count in upgrades_by_date_rows
        if date_key is not None
    }

    new_users_by_date_rows = db.execute(
        select(
            func.date(User.created_at),
            func.count(User.id),
        )
        .where(User.created_at >= trend_start)
        .group_by(func.date(User.created_at))
    ).all()
    new_users_by_date = {
        str(date_key): int(count)
        for date_key, count in new_users_by_date_rows
        if date_key is not None
    }

    conversion_trend_14d = []
    for offset in range(trend_days):
        day = (trend_start + timedelta(days=offset)).date()
        day_key = day.isoformat()
        upgrades = upgrades_by_date.get(day_key, 0)
        new_users = new_users_by_date.get(day_key, 0)
        day_conversion = round((upgrades / new_users) * 100, 1) if new_users else 0.0
        conversion_trend_14d.append(
            {
                "date": day_key,
                "upgrades": upgrades,
                "new_users": new_users,
                "conversion_rate": day_conversion,
            }
        )

    recent_7d = conversion_trend_14d[-7:]
    avg_conversion_7d = (
        round(
            sum(row["conversion_rate"] for row in recent_7d) / len(recent_7d),
            1,
        )
        if recent_7d
        else 0.0
    )
    alert_settings, _alert_settings_source = _load_conversion_alert_settings(db)
    conversion_threshold = float(alert_settings["threshold"])
    conversion_alert = {
        "status": "warning" if avg_conversion_7d < conversion_threshold else "healthy",
        "avg_conversion_7d": avg_conversion_7d,
        "threshold": conversion_threshold,
        "message": (
            "Conversion is below target"
            if avg_conversion_7d < conversion_threshold
            else "Conversion is on target"
        ),
    }

    if conversion_alert["status"] == "warning":
        admin_alert_service.dispatch_conversion_dropoff_alert(
            db,
            avg_conversion_7d=avg_conversion_7d,
            threshold=conversion_threshold,
            conversion_rate_30d=conversion_rate_30d,
            cooldown_hours=int(alert_settings["cooldown_hours"]),
            in_app_enabled=bool(alert_settings["in_app_enabled"]),
            email_enabled=bool(alert_settings["email_enabled"]),
            whatsapp_enabled=bool(alert_settings["whatsapp_enabled"]),
        )

    return {
        "scraping_health": {
            "total_runs_7d": total_runs_7d,
            "success_runs_7d": success_runs_7d,
            "error_runs_7d": error_runs_7d,
            "success_rate_7d": success_rate_7d,
        },
        "skills_extraction": {
            "jobs_total": total_jobs,
            "jobs_with_skills": jobs_with_skills,
            "coverage_percentage": skills_coverage,
            "avg_confidence": round(avg_skill_confidence, 3),
            "quality_score": round(avg_skill_confidence * 100, 1),
        },
        "engagement": {
            "users_total": total_users,
            "active_search_users_30d": active_search_users_30d,
            "active_application_users_30d": active_application_users_30d,
            "lmi_engagement_rate_30d": lmi_engagement_rate,
        },
        "revenue": {
            "paid_users": paid_users,
            "upgraded_users_30d": upgraded_users_30d,
            "new_users_30d": users_new_30d,
            "conversion_rate_30d": conversion_rate_30d,
            "paid_conversion_overall": paid_conversion_overall,
            "conversion_trend_14d": conversion_trend_14d,
            "conversion_alert": conversion_alert,
            "estimated_mrr_kes": estimated_mrr_kes,
            "estimated_arpu_kes": estimated_arpu_kes,
            "estimated_churn_rate": estimated_churn_rate,
        },
    }


@router.get("/lmi-scorecard")
def admin_lmi_scorecard(
    days_back: int = Query(1, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    del current_user
    since = datetime.utcnow() - timedelta(days=days_back)

    raw_postings = (
        db.execute(
            select(func.count(JobPost.id)).where(JobPost.first_seen >= since)
        ).scalar()
        or 0
    )
    canonical_jobs = (
        db.execute(
            select(func.count(JobPost.id)).where(JobPost.title_norm_id.is_not(None))
        ).scalar()
        or 0
    )
    dedupe_entries = db.execute(select(func.count(JobDedupeMap.job_id))).scalar() or 0
    jobs_with_company = (
        db.execute(
            select(func.count(JobPost.id)).where(JobPost.org_id.is_not(None))
        ).scalar()
        or 0
    )
    jobs_with_role = canonical_jobs
    jobs_with_skills = (
        db.execute(
            select(func.count(JobPost.id.distinct())).join_from(JobPost, JobSkill)
        ).scalar()
        or 0
    )
    total_jobs = db.execute(select(func.count(JobPost.id))).scalar() or 0
    error_runs = (
        db.execute(
            select(func.count(ProcessingLog.id)).where(
                ProcessingLog.processed_at >= since,
                ProcessingLog.results["status"].as_string() == "error",
            )
        ).scalar()
        or 0
    )
    all_runs = (
        db.execute(
            select(func.count(ProcessingLog.id)).where(
                ProcessingLog.processed_at >= since,
            )
        ).scalar()
        or 0
    )

    metrics = {
        "1_raw_postings_ingested": int(raw_postings),
        "2_canonical_jobs_added": int(canonical_jobs),
        "3_canonical_jobs_updated": 0,
        "4_dedupe_collapse_rate_by_source": _safe_pct(
            int(dedupe_entries),
            int(total_jobs),
        ),
        "5_pct_jobs_with_company": _safe_pct(int(jobs_with_company), int(total_jobs)),
        "6_pct_jobs_with_role_family": _safe_pct(int(jobs_with_role), int(total_jobs)),
        "7_pct_jobs_with_3plus_skills": _safe_pct(int(jobs_with_skills), int(total_jobs)),
        "8_error_rate_pct": _safe_pct(int(error_runs), int(all_runs)),
        "9_block_detections": 0,
        "10_trend_spikes": 0,
    }

    return {
        "date": datetime.utcnow().date().isoformat(),
        "metrics": metrics,
    }


@router.get("/lmi-integrity")
def admin_lmi_integrity(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    del current_user

    total_jobs = db.execute(select(func.count(JobPost.id))).scalar() or 0
    dedupe_entries = db.execute(select(func.count(JobDedupeMap.job_id))).scalar() or 0
    canonical_jobs = (
        db.execute(
            select(func.count(JobPost.id)).where(JobPost.title_norm_id.is_not(None))
        ).scalar()
        or 0
    )

    return {
        "total_jobs": int(total_jobs),
        "dedupe_entries": int(dedupe_entries),
        "canonical_jobs": int(canonical_jobs),
        "integrity_checks": {
            "canonical_coverage_pct": _safe_pct(int(canonical_jobs), int(total_jobs)),
            "dedupe_rate_pct": _safe_pct(int(dedupe_entries), int(total_jobs)),
        },
    }


@router.get("/lmi-skills")
def admin_lmi_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    del current_user

    total_unique_skills = db.execute(select(func.count(Skill.id))).scalar() or 0
    top_30_rows = db.execute(
        select(Skill.name, func.count(JobSkill.id))
        .join(JobSkill, JobSkill.skill_id == Skill.id)
        .group_by(Skill.name)
        .order_by(desc(func.count(JobSkill.id)))
        .limit(30)
    ).all()
    top_30_skills = [
        {"skill": skill_name, "count": int(count)}
        for skill_name, count in top_30_rows
    ]

    fragmentation_detected = len(top_30_skills) == 0 and total_unique_skills > 0

    return {
        "total_unique_skills": int(total_unique_skills),
        "top_30_skills": top_30_skills,
        "fragmentation_detected": fragmentation_detected,
        "quality_status": "healthy" if not fragmentation_detected else "warning",
    }


@router.get("/lmi-seniority")
def admin_lmi_seniority(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    del current_user

    total_jobs = db.execute(select(func.count(JobPost.id))).scalar() or 0
    with_seniority = (
        db.execute(
            select(func.count(JobPost.id)).where(JobPost.seniority.is_not(None))
        ).scalar()
        or 0
    )
    coverage_pct = _safe_pct(int(with_seniority), int(total_jobs))

    return {
        "total_jobs": int(total_jobs),
        "with_seniority": int(with_seniority),
        "coverage_pct": coverage_pct,
        "status": "healthy" if coverage_pct >= 60.0 else "warning",
    }


@router.get("/lmi-health")
def admin_lmi_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    del current_user

    scorecard = admin_lmi_scorecard(days_back=1, db=db, current_user=None)
    integrity = admin_lmi_integrity(db=db, current_user=None)
    skills = admin_lmi_skills(db=db, current_user=None)
    seniority = admin_lmi_seniority(db=db, current_user=None)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "daily_scorecard": scorecard,
        "canonical_integrity": integrity,
        "skill_normalization": skills,
        "seniority_coverage": seniority,
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
                "last_login": (
                    user.last_login.isoformat() if user.last_login else None
                ),
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
                "first_seen": (job.first_seen.isoformat() if job.first_seen else None),
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


@router.get("/government/quality")
def admin_government_quality(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Quick visibility into government ingestion and processing coverage."""
    return {
        "source": "gov_careers",
        "snapshot": government_quality_snapshot(db),
    }


@router.post("/government/process")
def admin_government_process(
    limit: int = Query(500, ge=1, le=5000),
    only_unprocessed: bool = Query(True),
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Run deterministic post-processing for `gov_careers` rows."""
    result = process_government_posts(
        db,
        limit=limit,
        only_unprocessed=only_unprocessed,
        dry_run=dry_run,
    )
    log_monitoring_event(
        db,
        status="success" if result.get("status") == "success" else "error",
        message="Government post-processing executed",
        details={"triggered_by": current_user.email, "result": result},
    )
    return result


@router.post("/government/quarantine")
def admin_government_quarantine(
    limit: int = Query(2000, ge=1, le=20000),
    dry_run: bool = Query(True),
    max_quality_score: float = Query(0.5, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Quarantine non-job government pages to protect public search."""
    result = quarantine_government_nonjobs(
        db,
        limit=limit,
        dry_run=dry_run,
        max_quality_score=max_quality_score,
    )
    log_monitoring_event(
        db,
        status="success" if result.get("status") == "success" else "error",
        message="Government quarantine executed",
        details={"triggered_by": current_user.email, "result": result},
    )
    return result


@router.get("/quality")
def admin_quality(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Global visibility into ingestion completeness and coverage."""
    return quality_snapshot(db)


@router.post("/process")
def admin_process(
    limit: int = Query(500, ge=1, le=5000),
    only_unprocessed: bool = Query(True),
    dry_run: bool = Query(False),
    source: str | None = Query(
        None, description="Optional source filter, e.g. gov_careers"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Run deterministic post-processing for any `job_post` rows."""
    result = process_job_posts(
        db,
        source=source,
        limit=limit,
        only_unprocessed=only_unprocessed,
        dry_run=dry_run,
    )
    log_monitoring_event(
        db,
        status="success" if result.get("status") == "success" else "error",
        message="Post-ingestion processing executed",
        details={"triggered_by": current_user.email, "result": result},
    )
    return result


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
            select(
                JobPost.title_raw,
                TitleNorm.canonical_title,
                func.count(JobPost.id),
            )
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
                "first_seen": (job.first_seen.isoformat() if job.first_seen else None),
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


@router.get("/analytics/skill-trends")
def admin_skill_trends(
    role_family: str | None = Query(None),
    months: int = Query(6, ge=1, le=24),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    return get_skill_trends(db, role_family=role_family, months=months, limit=limit)


@router.get("/analytics/role-evolution")
def admin_role_evolution(
    role_family: str | None = Query(None),
    months: int = Query(6, ge=1, le=24),
    limit: int = Query(24, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    return get_role_evolution(db, role_family=role_family, months=months, limit=limit)


@router.get("/analytics/title-adjacency")
def admin_title_adjacency(
    title: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    return get_title_adjacency(db, title=title, limit=limit)


@router.get("/monitoring/drift")
def admin_drift_checks(
    recent_days: int = Query(30, ge=7, le=180),
    baseline_days: int = Query(180, ge=30, le=365),
    top_n: int = Query(20, ge=5, le=100),
    record: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    results = run_drift_checks(
        db, recent_days=recent_days, baseline_days=baseline_days, top_n=top_n
    )
    if record:
        log_monitoring_event(
            db,
            status="success",
            message="Drift checks completed",
            details=results,
        )
    return results


@router.get("/monitoring/summary")
def admin_monitoring_summary(
    recent_days: int = Query(30, ge=7, le=180),
    baseline_days: int = Query(180, ge=30, le=365),
    top_n: int = Query(20, ge=5, le=100),
    record: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    summary = monitoring_summary(
        db,
        recent_days=recent_days,
        baseline_days=baseline_days,
        top_n=top_n,
    )
    if record:
        status = "success" if summary["overall_status"] == "pass" else "warning"
        log_monitoring_event(
            db,
            status=status,
            message="Monitoring summary generated",
            details=summary,
        )
    return summary


@router.get("/signals/tenders")
def admin_tenders(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    return list_tenders(db, limit=limit, offset=offset)


@router.get("/signals/hiring")
def admin_hiring_signals(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    return list_hiring_signals(db, limit=limit)


@router.get("/ranking/model-info")
def admin_ranking_model_info(
    current_user: User = Depends(require_admin()),
):
    """Get information about the current ranking model."""
    from ..services.ranking_trainer import get_model_info

    return get_model_info()


@router.post("/ranking/train")
def admin_train_ranking_model(
    days_back: int = Query(30, ge=1, le=180),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Train the ranking model on recent user interaction data."""
    from ..services.ranking_trainer import train_ranking_model

    result = train_ranking_model(db, days_back=days_back)
    return result
