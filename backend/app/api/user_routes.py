from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from ..db.database import get_db
from ..services.auth_service import get_current_user, require_subscription
from ..services.personalized_recommendations import personalized_recommendations
from ..services.ai_service import ai_service
from ..services.matching_service import (
    JobNotFoundError,
    ProfileNotCompleteError,
    matching_service,
)
from ..services.skills_gap_service import skills_gap_service
from ..services.subscription_service import subscription_service
from ..services.candidate_evidence_service import (
    add_evidence,
    ingest_cv_data,
    get_evidence,
)
from ..db.models import (
    User,
    SavedJob,
    JobApplication,
    JobAlert,
    SearchHistory,
    UserNotification,
    JobPost,
    JobSkill,
    Organization,
    Location,
    Skill,
)
from sqlalchemy import select, and_, desc, func

router = APIRouter()

APPLICATION_STAGE_ORDER = ["saved", "applied", "interview", "offer", "rejected"]
APPLICATION_STATUS_TO_STAGE = {
    "saved": "saved",
    "applied": "applied",
    "submitted": "applied",
    "in_review": "applied",
    "reviewing": "applied",
    "shortlisted": "interview",
    "interview": "interview",
    "interviewed": "interview",
    "screening": "interview",
    "offer": "offer",
    "offered": "offer",
    "hired": "offer",
    "rejected": "rejected",
    "declined": "rejected",
    "withdrawn": "rejected",
    "closed": "rejected",
}


# Pydantic models
class SaveJobRequest(BaseModel):
    job_id: int
    notes: str = None
    folder: str = None


class JobApplicationRequest(BaseModel):
    job_id: int
    cover_letter: str = None
    cv_version: str = None
    application_source: str = "platform"
    notes: str = None


class JobApplicationUpdate(BaseModel):
    status: str | None = None
    stage: str | None = None
    feedback_received: str = None
    interview_dates: List[str] = None
    salary_offered: Dict[str, Any] = None
    notes: str = None


class JobAlertRequest(BaseModel):
    name: str
    query: str
    filters: Dict[str, Any] = {}
    frequency: str = "daily"
    delivery_methods: List[str] = ["email"]


class CareerAdviceRequest(BaseModel):
    query: str


class SkillsGapScanRequest(BaseModel):
    target_role: str


class SubscriptionCheckoutRequest(BaseModel):
    plan_code: str = "professional_monthly"
    provider: str = "stripe"


class SubscriptionActivationRequest(BaseModel):
    plan_code: str = "professional_monthly"


def _build_location_text(location: Location | None) -> str:
    if not location:
        return ""

    parts = [location.raw, location.city, location.region, location.country]
    return " ".join(str(part) for part in parts if part)


def _application_stage(status_value: str | None) -> str:
    normalized = (status_value or "applied").strip().lower()
    return APPLICATION_STATUS_TO_STAGE.get(normalized, "applied")


def _normalize_stage_update(stage_value: str) -> str:
    normalized = (stage_value or "").strip().lower()
    if normalized not in APPLICATION_STAGE_ORDER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported application stage",
        )
    return normalized


def _safe_json_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_json_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


@router.get("/subscription/plans")
async def get_subscription_plans(
    current_user: User = Depends(get_current_user),
):
    """List available subscription plans for authenticated users."""
    return {
        "plans": subscription_service.list_plans(),
        "current_tier": current_user.subscription_tier,
    }


@router.post("/subscription/checkout")
async def create_subscription_checkout(
    request: SubscriptionCheckoutRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a checkout session for subscription upgrade."""
    return subscription_service.create_checkout(
        user=current_user,
        plan_code=request.plan_code,
        provider=request.provider,
    )


@router.post("/subscription/activate")
async def activate_subscription(
    request: SubscriptionActivationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Activate a subscription plan after payment confirmation."""
    return subscription_service.activate_plan(
        db=db,
        user=current_user,
        plan_code=request.plan_code,
    )


@router.post("/skills-gap-scan")
async def skills_gap_scan(
    request: SkillsGapScanRequest,
    current_user: User = Depends(require_subscription("professional")),
    db: Session = Depends(get_db),
):
    """Run a premium skills gap scan for the authenticated user."""
    profile = current_user.profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete your profile first",
        )

    preferred_location = None
    if isinstance(profile.preferred_locations, list) and profile.preferred_locations:
        preferred_location = str(profile.preferred_locations[0])

    return skills_gap_service.scan_profile(
        profile_skills=profile.skills or {},
        target_role=request.target_role,
        experience_level=profile.experience_level,
        preferred_location=preferred_location,
        db=db,
    )


@router.get("/job-match/{job_id}")
async def get_job_match(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get match score details between current user profile and a job."""
    try:
        return matching_service.get_job_match(db, current_user, job_id)
    except ProfileNotCompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate job match",
        )


@router.get("/market-fit")
async def get_market_fit(
    window_days: int = Query(60, ge=7, le=180),
    limit: int = Query(200, ge=10, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Summarize market fit from the user profile and recent active jobs."""
    profile = current_user.profile
    if not profile:
        return {
            "match_distribution": {"strong": 0, "close": 0, "pivot": 0},
            "missing_skills": [],
            "top_counties": [],
            "top_industries": [],
            "target_roles": [],
            "total_jobs_analyzed": 0,
            "window_days": window_days,
        }

    window_start = datetime.utcnow() - timedelta(days=window_days)
    jobs = (
        db.execute(
            select(JobPost)
            .options(
                joinedload(JobPost.location),
                joinedload(JobPost.organization),
                joinedload(JobPost.title_norm),
            )
            .where(
                JobPost.is_active.is_(True),
                JobPost.first_seen >= window_start,
            )
            .order_by(desc(JobPost.first_seen))
            .limit(limit)
        )
        .scalars()
        .all()
    )
    job_ids = [job.id for job in jobs]
    normalized_skills_by_job: dict[int, list[str]] = {}
    if job_ids:
        skill_rows = db.execute(
            select(JobSkill.job_post_id, Skill.name)
            .join(Skill, Skill.id == JobSkill.skill_id)
            .where(JobSkill.job_post_id.in_(job_ids))
        ).all()
        for job_id, skill_name in skill_rows:
            normalized_skills_by_job.setdefault(job_id, []).append(skill_name)

    match_distribution = {"strong": 0, "close": 0, "pivot": 0}
    county_counts: Counter[str] = Counter()
    industry_counts: Counter[str] = Counter()
    missing_skill_counts: Counter[str] = Counter()
    target_roles = [profile.current_role] if profile.current_role else []
    profile_skills = {
        str(skill).strip().lower() for skill in (profile.skills or {}).keys()
    }

    for job in jobs:
        location_text = _build_location_text(job.location)
        scores = ai_service.calculate_job_match_score(
            profile,
            job,
            job_location_text=location_text,
        )
        overall_score = float(scores.get("overall_score") or 0.0)
        if overall_score >= 0.65:
            match_distribution["strong"] += 1
        elif overall_score >= 0.35:
            match_distribution["close"] += 1
        else:
            match_distribution["pivot"] += 1

        county_name = None
        if job.location:
            county_name = (
                job.location.region
                or job.location.city
                or job.location.raw
                or job.location.country
            )
        if county_name:
            county_counts[str(county_name)] += 1

        if job.organization and job.organization.sector:
            industry_counts[str(job.organization.sector)] += 1

        job_skill_names = normalized_skills_by_job.get(job.id)
        if not job_skill_names:
            job_text = " ".join(
                part
                for part in [job.title_raw, job.description_raw, job.requirements_raw]
                if part
            )
            job_skill_names = list(ai_service.extract_skills_from_text(job_text).keys())

        for skill_name in job_skill_names[:5]:
            normalized_skill = str(skill_name).strip()
            if not normalized_skill:
                continue
            if normalized_skill.lower() in profile_skills:
                continue
            missing_skill_counts[normalized_skill] += 1

    total_jobs_analyzed = len(jobs)
    missing_skills = [
        {
            "name": skill_name,
            "demand_count": demand_count,
            "percentage": round((demand_count / total_jobs_analyzed) * 100, 1)
            if total_jobs_analyzed
            else 0.0,
        }
        for skill_name, demand_count in missing_skill_counts.most_common(8)
    ]
    top_counties = [
        {"name": county_name, "count": count}
        for county_name, count in county_counts.most_common(5)
    ]
    top_industries = [
        {"name": sector_name, "count": count}
        for sector_name, count in industry_counts.most_common(5)
    ]

    return {
        "match_distribution": match_distribution,
        "missing_skills": missing_skills,
        "top_counties": top_counties,
        "top_industries": top_industries,
        "target_roles": target_roles,
        "total_jobs_analyzed": total_jobs_analyzed,
        "window_days": window_days,
    }


# Personalized Recommendations
@router.get("/recommendations")
async def get_recommendations(
    limit: int = Query(20, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get personalized job recommendations for the current user."""
    try:
        # Try to get stored recommendations first
        recommendations = await personalized_recommendations.get_stored_recommendations(
            db, current_user.id, limit
        )

        # If no stored recommendations or too few, generate new ones
        if len(recommendations) < limit // 2:
            new_recommendations = (
                await personalized_recommendations.generate_recommendations_for_user(
                    db, current_user, limit
                )
            )

            # Combine and deduplicate
            existing_job_ids = {rec["job_id"] for rec in recommendations}
            for new_rec in new_recommendations:
                if new_rec["job_id"] not in existing_job_ids:
                    recommendations.append(new_rec)

            # Sort by match score and limit
            recommendations.sort(key=lambda x: x["match_score"], reverse=True)
            recommendations = recommendations[:limit]

        return {
            "recommendations": recommendations,
            "total": len(recommendations),
            "message": "Personalized recommendations based on your profile and preferences",
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recommendations",
        )


@router.post("/recommendations/{job_id}/interaction")
async def mark_recommendation_interaction(
    job_id: int,
    interaction_type: str = Query(..., pattern="^(viewed|clicked|dismissed)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark user interaction with a recommendation."""
    success = await personalized_recommendations.mark_recommendation_interaction(
        db, current_user.id, job_id, interaction_type
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found"
        )

    return {"message": f"Marked as {interaction_type}"}


@router.get("/recommendations/insights")
async def get_recommendation_insights(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get insights about user's recommendation performance."""
    insights = await personalized_recommendations.get_recommendation_insights(
        db, current_user.id
    )
    return insights


# Saved Jobs
@router.get("/saved-jobs")
async def get_saved_jobs(
    folder: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's saved jobs."""
    stmt = (
        select(SavedJob, JobPost, Organization, Location)
        .join(JobPost, JobPost.id == SavedJob.job_post_id)
        .outerjoin(Organization, Organization.id == JobPost.org_id)
        .outerjoin(Location, Location.id == JobPost.location_id)
        .where(SavedJob.user_id == current_user.id)
    )

    if folder:
        stmt = stmt.where(SavedJob.folder == folder)

    stmt = stmt.order_by(desc(SavedJob.saved_at)).limit(limit)

    saved_jobs = db.execute(stmt).all()

    return {
        "saved_jobs": [
            {
                "id": saved.id,
                "job_id": saved.job_post_id,
                "saved_at": saved.saved_at.isoformat(),
                "notes": saved.notes,
                "folder": saved.folder,
                "title": job.title_raw,
                "url": job.url,
                "organization": org.name if org else None,
                "location": location.raw if location else None,
            }
            for saved, job, org, location in saved_jobs
        ],
        "total": len(saved_jobs),
    }


@router.post("/saved-jobs")
async def save_job(
    request: SaveJobRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a job for later."""
    # Check if already saved
    existing = db.execute(
        select(SavedJob).where(
            and_(
                SavedJob.user_id == current_user.id,
                SavedJob.job_post_id == request.job_id,
            )
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Job already saved"
        )

    saved_job = SavedJob(
        user_id=current_user.id,
        job_post_id=request.job_id,
        notes=request.notes,
        folder=request.folder,
    )

    db.add(saved_job)
    db.commit()
    db.refresh(saved_job)

    return {"message": "Job saved successfully", "id": saved_job.id}


@router.delete("/saved-jobs/{saved_job_id}")
async def unsave_job(
    saved_job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a saved job."""
    saved_job = db.execute(
        select(SavedJob).where(
            and_(SavedJob.id == saved_job_id, SavedJob.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    if not saved_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Saved job not found"
        )

    db.delete(saved_job)
    db.commit()

    return {"message": "Job removed from saved list"}


# Job Applications
@router.get("/applications")
async def get_job_applications(
    status_filter: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's job applications."""
    stmt = select(JobApplication).where(JobApplication.user_id == current_user.id)

    if status_filter:
        stmt = stmt.where(JobApplication.status == status_filter)

    stmt = stmt.order_by(desc(JobApplication.applied_at)).limit(limit)

    applications = db.execute(stmt).scalars().all()

    return {
        "applications": [
            {
                "id": app.id,
                "job_id": app.job_post_id,
                "status": app.status,
                "stage": _application_stage(app.status),
                "applied_at": app.applied_at.isoformat(),
                "last_updated": app.last_updated.isoformat(),
                "application_source": app.application_source,
                "interview_dates": app.interview_dates,
                "notes": app.notes,
            }
            for app in applications
        ],
        "total": len(applications),
    }


@router.get("/applications/by-stage")
async def get_job_applications_by_stage(
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return dashboard-friendly application kanban data grouped by stage."""
    stmt = (
        select(JobApplication)
        .options(
            joinedload(JobApplication.job_post).joinedload(JobPost.organization),
            joinedload(JobApplication.job_post).joinedload(JobPost.location),
        )
        .where(JobApplication.user_id == current_user.id)
        .order_by(desc(JobApplication.applied_at))
        .limit(limit)
    )
    applications = db.execute(stmt).scalars().all()

    stages: dict[str, list[dict[str, Any]]] = {
        stage_name: [] for stage_name in APPLICATION_STAGE_ORDER
    }
    now = datetime.utcnow()

    for application in applications:
        job = application.job_post
        organization = job.organization if job else None
        application_stage = _application_stage(application.status)
        applied_at = application.applied_at or application.last_updated or now

        stages[application_stage].append(
            {
                "id": application.id,
                "job_id": application.job_post_id,
                "stage": application_stage,
                "status": application.status,
                "job_title": job.title_raw
                if job
                else f"Job #{application.job_post_id}",
                "company": organization.name
                if organization
                else "Unknown organization",
                "job_url": job.application_url or job.url if job else None,
                "applied_at": application.applied_at.isoformat()
                if application.applied_at
                else None,
                "last_updated": application.last_updated.isoformat()
                if application.last_updated
                else None,
                "days_since_applied": max((now - applied_at).days, 0),
                "deadline": None,
                "notes": application.notes,
                "application_source": application.application_source,
                "interview_dates": _safe_json_list(application.interview_dates),
                "feedback_received": application.feedback_received,
                "salary_offered": _safe_json_dict(application.salary_offered),
            }
        )

    active_pipeline = sum(
        len(stages[stage_name]) for stage_name in ["applied", "interview", "offer"]
    )
    interview_candidates = len(stages["interview"]) + len(stages["offer"])
    interview_rate = (
        round((interview_candidates / active_pipeline) * 100) if active_pipeline else 0
    )

    return {
        "analytics": {
            "total_applications": len(applications),
            "interview_rate": interview_rate,
        },
        "stages": stages,
        "stage_order": APPLICATION_STAGE_ORDER,
    }


@router.post("/applications")
async def create_job_application(
    request: JobApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a job application."""
    # Check if already applied
    existing = db.execute(
        select(JobApplication).where(
            and_(
                JobApplication.user_id == current_user.id,
                JobApplication.job_post_id == request.job_id,
            )
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already applied to this job",
        )

    application = JobApplication(
        user_id=current_user.id,
        job_post_id=request.job_id,
        cover_letter=request.cover_letter,
        cv_version=request.cv_version,
        application_source=request.application_source,
        notes=request.notes,
        status="applied",
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return {"message": "Application recorded successfully", "id": application.id}


@router.put("/applications/{application_id}")
async def update_job_application(
    application_id: int,
    request: JobApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update job application status."""
    application = db.execute(
        select(JobApplication).where(
            and_(
                JobApplication.id == application_id,
                JobApplication.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )

    update_data = request.model_dump(exclude_unset=True)
    stage_value = update_data.pop("stage", None)
    if stage_value is not None:
        update_data["status"] = _normalize_stage_update(stage_value)

    status_value = update_data.get("status")
    if status_value is not None:
        update_data["status"] = str(status_value).strip().lower()

    # Update fields
    for field, value in update_data.items():
        if hasattr(application, field):
            setattr(application, field, value)

    db.commit()
    db.refresh(application)

    return {
        "message": "Application updated successfully",
        "id": application.id,
        "status": application.status,
        "stage": _application_stage(application.status),
    }


# Job Alerts
@router.get("/job-alerts")
async def get_job_alerts(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user's job alerts."""
    stmt = (
        select(JobAlert)
        .where(JobAlert.user_id == current_user.id)
        .order_by(desc(JobAlert.created_at))
    )
    alerts = db.execute(stmt).scalars().all()

    return {
        "alerts": [
            {
                "id": alert.id,
                "name": alert.name,
                "query": alert.query,
                "filters": alert.filters,
                "is_active": alert.is_active,
                "frequency": alert.frequency,
                "delivery_methods": alert.delivery_methods,
                "jobs_found_total": alert.jobs_found_total,
                "last_triggered": alert.last_triggered.isoformat()
                if alert.last_triggered
                else None,
                "created_at": alert.created_at.isoformat(),
            }
            for alert in alerts
        ],
        "total": len(alerts),
    }


@router.post("/job-alerts")
async def create_job_alert(
    request: JobAlertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new job alert."""
    alert = JobAlert(
        user_id=current_user.id,
        name=request.name,
        query=request.query,
        filters=request.filters,
        frequency=request.frequency,
        delivery_methods=request.delivery_methods,
        is_active=True,
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {"message": "Job alert created successfully", "id": alert.id}


@router.put("/job-alerts/{alert_id}")
async def update_job_alert(
    alert_id: int,
    request: JobAlertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a job alert."""
    alert = db.execute(
        select(JobAlert).where(
            and_(JobAlert.id == alert_id, JobAlert.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job alert not found"
        )

    # Update fields
    alert.name = request.name
    alert.query = request.query
    alert.filters = request.filters
    alert.frequency = request.frequency
    alert.delivery_methods = request.delivery_methods

    db.commit()

    return {"message": "Job alert updated successfully"}


@router.delete("/job-alerts/{alert_id}")
async def delete_job_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a job alert."""
    alert = db.execute(
        select(JobAlert).where(
            and_(JobAlert.id == alert_id, JobAlert.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job alert not found"
        )

    db.delete(alert)
    db.commit()

    return {"message": "Job alert deleted successfully"}


# AI Career Advice
@router.post("/career-advice")
async def get_career_advice(
    request: CareerAdviceRequest,
    current_user: User = Depends(require_subscription("professional")),
):
    """Get AI-powered career advice."""
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete your profile to get personalized advice",
        )

    advice = await ai_service.generate_career_advice(
        current_user.profile, request.query
    )

    return {"advice": advice, "query": request.query, "generated_at": "now"}


# Notifications
@router.get("/notifications")
async def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user notifications."""
    stmt = select(UserNotification).where(UserNotification.user_id == current_user.id)

    if unread_only:
        stmt = stmt.where(UserNotification.is_read.is_(False))

    stmt = stmt.order_by(desc(UserNotification.created_at)).limit(limit)

    notifications = db.execute(stmt).scalars().all()

    return {
        "notifications": [
            {
                "id": notif.id,
                "type": notif.type,
                "title": notif.title,
                "message": notif.message,
                "data": notif.data,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat(),
                "read_at": notif.read_at.isoformat() if notif.read_at else None,
            }
            for notif in notifications
        ],
        "total": len(notifications),
    }


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    notification = db.execute(
        select(UserNotification).where(
            and_(
                UserNotification.id == notification_id,
                UserNotification.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    notification.is_read = True
    notification.read_at = db.execute(select(func.now())).scalar()

    db.commit()

    return {"message": "Notification marked as read"}


@router.put("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Mark all notifications as read."""
    db.execute(
        UserNotification.__table__.update()
        .where(
            and_(
                UserNotification.user_id == current_user.id,
                UserNotification.is_read.is_(False),
            )
        )
        .values(is_read=True, read_at=func.now())
    )

    db.commit()

    return {"message": "All notifications marked as read"}


# Activity Feed
@router.get("/activity")
async def get_activity_feed(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recent user activity composed from searches, saves, and applications."""
    activities: list[dict] = []

    searches = (
        db.execute(
            select(SearchHistory)
            .where(SearchHistory.user_id == current_user.id)
            .order_by(desc(SearchHistory.searched_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )
    for s in searches:
        activities.append(
            {
                "icon": "🔍",
                "text": f'Searched for "{s.query}"',
                "time": s.searched_at.isoformat() if s.searched_at else None,
                "type": "search",
            }
        )

    saves = (
        db.execute(
            select(SavedJob)
            .where(SavedJob.user_id == current_user.id)
            .order_by(desc(SavedJob.saved_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )
    for sv in saves:
        activities.append(
            {
                "icon": "\u2764\ufe0f",
                "text": "Saved a role",
                "time": sv.saved_at.isoformat() if sv.saved_at else None,
                "type": "save",
            }
        )

    applications = (
        db.execute(
            select(JobApplication)
            .where(JobApplication.user_id == current_user.id)
            .order_by(desc(JobApplication.applied_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )
    for app in applications:
        activities.append(
            {
                "icon": "📝",
                "text": "Submitted application",
                "time": app.applied_at.isoformat() if app.applied_at else None,
                "type": "application",
            }
        )

    # Sort combined activity by time descending, take top N
    activities.sort(key=lambda a: a["time"] or "", reverse=True)
    activities = activities[:limit]

    return {"activities": activities}


@router.get("/momentum")
async def get_momentum_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Weekly activity counts for momentum chart (last 7 days)."""
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    days = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)

        search_count = (
            db.execute(
                select(func.count(SearchHistory.id)).where(
                    SearchHistory.user_id == current_user.id,
                    SearchHistory.searched_at >= day_start,
                    SearchHistory.searched_at < day_end,
                )
            ).scalar()
            or 0
        )

        save_count = (
            db.execute(
                select(func.count(SavedJob.id)).where(
                    SavedJob.user_id == current_user.id,
                    SavedJob.saved_at >= day_start,
                    SavedJob.saved_at < day_end,
                )
            ).scalar()
            or 0
        )

        app_count = (
            db.execute(
                select(func.count(JobApplication.id)).where(
                    JobApplication.user_id == current_user.id,
                    JobApplication.applied_at >= day_start,
                    JobApplication.applied_at < day_end,
                )
            ).scalar()
            or 0
        )

        days.append(
            {
                "date": day_start.date().isoformat(),
                "count": int(search_count) + int(save_count) + int(app_count),
            }
        )

    return {"days": days}


# ---------------------------------------------------------------------------
# T-DS-932: Candidate evidence endpoints
# ---------------------------------------------------------------------------

_VALID_EVIDENCE_TYPES = {
    "portfolio_item",
    "project",
    "work_sample",
    "gig",
    "informal_work",
    "certification",
}


class EvidenceSubmitRequest(BaseModel):
    evidence_type: str
    title: str
    description: str | None = None
    url: str | None = None
    skills_demonstrated: list[str] = []
    start_date: str | None = None
    end_date: str | None = None


@router.post("/evidence")
async def submit_evidence(
    request: EvidenceSubmitRequest,
    current_user: User = Depends(require_subscription("professional")),
    db: Session = Depends(get_db),
):
    """Submit a candidate evidence item (self-reported)."""
    if request.evidence_type not in _VALID_EVIDENCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"evidence_type must be one of: {sorted(_VALID_EVIDENCE_TYPES)}",
        )
    item = add_evidence(
        user_id=current_user.id,
        evidence_type=request.evidence_type,
        title=request.title,
        description=request.description,
        url=request.url,
        skills_demonstrated=request.skills_demonstrated,
        start_date=request.start_date,
        end_date=request.end_date,
        source="self_reported",
        provenance_confidence=0.5,
        db=db,
    )
    return {
        "id": item.id,
        "evidence_type": item.evidence_type,
        "title": item.title,
        "source": item.source,
        "created_at": item.created_at.isoformat(),
    }


@router.get("/evidence")
async def list_evidence(
    current_user: User = Depends(require_subscription("professional")),
    db: Session = Depends(get_db),
):
    """List all evidence items for the authenticated user."""
    return {"evidence": get_evidence(current_user.id, db)}


@router.post("/evidence/ingest-cv")
async def ingest_cv_evidence(
    current_user: User = Depends(require_subscription("professional")),
    db: Session = Depends(get_db),
):
    """Extract evidence items from the user's stored cv_data.

    Idempotent — safe to call multiple times; duplicate titles are skipped.
    """
    created = ingest_cv_data(current_user.id, db)
    return {
        "extracted": len(created),
        "items": [
            {"id": i.id, "evidence_type": i.evidence_type, "title": i.title}
            for i in created
        ],
    }
