"""Beta program API endpoints for guerrilla pilot."""

import logging
from datetime import datetime

from app.db.database import get_db
from app.db.models import BetaActivity, BetaSignup
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/beta", tags=["beta"])


class BetaSignupRequest(BaseModel):
    """Beta program signup payload."""

    full_name: str
    email: EmailStr
    phone: str
    university: str
    year_of_study: str
    field_of_study: str
    skills: str = ""
    career_goals: str = ""


class BetaSignupResponse(BaseModel):
    """Beta signup confirmation."""

    message: str
    beta_id: int
    spots_remaining: int


@router.post("/signup", response_model=BetaSignupResponse)
async def beta_signup(
    signup: BetaSignupRequest, session: AsyncSession = Depends(get_db)
):
    """
    Register a student for the VIP beta program.

    - Limited to 50 students (first-come, first-served)
    - Sends confirmation via email + WhatsApp
    - Tracks signup for analytics
    """
    existing = await session.execute(
        select(BetaSignup).where(BetaSignup.email == signup.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Email already registered for beta program"
        )

    count_query = await session.execute(select(func.count()).select_from(BetaSignup))
    current_count = count_query.scalar() or 0

    if current_count >= 50:
        raise HTTPException(
            status_code=400,
            detail="Beta program is full. Join the waitlist instead.",
        )

    beta_user = BetaSignup(
        full_name=signup.full_name,
        email=signup.email,
        phone=signup.phone,
        university=signup.university,
        year_of_study=signup.year_of_study,
        field_of_study=signup.field_of_study,
        skills=signup.skills,
        career_goals=signup.career_goals,
        signed_up_at=datetime.utcnow(),
        status="pending",
    )

    session.add(beta_user)
    await session.commit()
    await session.refresh(beta_user)

    logger.info(f"Beta signup: {signup.email} from {signup.university}")

    # TODO: Send confirmation email
    # TODO: Send WhatsApp message with next steps

    spots_remaining = 50 - (current_count + 1)

    return BetaSignupResponse(
        message=(
            "Successfully registered for beta program! Check your email for next steps."
        ),
        beta_id=beta_user.id,
        spots_remaining=spots_remaining,
    )


@router.get("/stats")
async def beta_stats(session: AsyncSession = Depends(get_db)):
    """Get beta program statistics."""

    total = await session.execute(select(func.count()).select_from(BetaSignup))
    total_signups = total.scalar()

    by_university = await session.execute(
        select(
            BetaSignup.university, func.count(BetaSignup.id).label("count")
        ).group_by(BetaSignup.university)
    )
    university_breakdown = {row.university: row.count for row in by_university}

    by_year = await session.execute(
        select(
            BetaSignup.year_of_study, func.count(BetaSignup.id).label("count")
        ).group_by(BetaSignup.year_of_study)
    )
    year_breakdown = {row.year_of_study: row.count for row in by_year}

    active_query = await session.execute(
        select(func.count())
        .select_from(BetaSignup)
        .where(BetaSignup.status == "active")
    )
    active_users = active_query.scalar()

    return {
        "total_signups": total_signups,
        "spots_remaining": max(0, 50 - total_signups),
        "active_users": active_users,
        "activation_rate": round(active_users / total_signups * 100, 1)
        if total_signups > 0
        else 0,
        "by_university": university_breakdown,
        "by_year": year_breakdown,
    }


@router.get("/activity")
async def beta_activity(
    session: AsyncSession = Depends(get_db), beta_id: int | None = None
):
    """Get beta user activity metrics."""

    query = select(BetaActivity)
    if beta_id:
        query = query.where(BetaActivity.beta_id == beta_id)

    query = query.order_by(BetaActivity.timestamp.desc()).limit(100)

    activities = await session.execute(query)
    activity_list = activities.scalars().all()

    return {
        "activities": [
            {
                "beta_id": act.beta_id,
                "event_type": act.event_type,
                "event_data": act.event_data,
                "timestamp": act.timestamp.isoformat(),
            }
            for act in activity_list
        ]
    }


@router.post("/track")
async def track_beta_activity(
    beta_id: int,
    event_type: str,
    event_data: dict[str, str] | None = None,
    session: AsyncSession = Depends(get_db),
):
    """
    Track beta user activity.

    Event types:
    - login: User logged in
    - profile_complete: Completed profile
    - job_view: Viewed a job
    - job_save: Saved a job
    - job_apply: Applied to a job
    - search: Performed a search
    """
    activity = BetaActivity(
        beta_id=beta_id,
        event_type=event_type,
        event_data=event_data if event_data is not None else {},
        timestamp=datetime.utcnow(),
    )

    session.add(activity)
    await session.commit()

    beta_user = await session.get(BetaSignup, beta_id)
    if beta_user:
        if event_type == "profile_complete":
            beta_user.profile_completed = True
        elif event_type == "job_view":
            beta_user.jobs_viewed += 1
        elif event_type == "job_save":
            beta_user.jobs_saved += 1
        elif event_type == "job_apply":
            beta_user.jobs_applied += 1
        elif event_type == "search":
            beta_user.searches_performed += 1

        beta_user.last_active_at = datetime.utcnow()
        await session.commit()

    return {"message": "Activity tracked"}


@router.get("/metrics")
async def beta_metrics(session: AsyncSession = Depends(get_db)):
    """Detailed metrics for admin dashboard and ROI calculator."""

    profile_complete_query = await session.execute(
        select(func.count())
        .select_from(BetaSignup)
        .where(BetaSignup.profile_completed == True)  # noqa: E712
    )
    profiles_completed = profile_complete_query.scalar() or 0

    jobs_viewed_query = await session.execute(
        select(func.sum(BetaSignup.jobs_viewed)).select_from(BetaSignup)
    )
    total_jobs_viewed = jobs_viewed_query.scalar() or 0

    jobs_saved_query = await session.execute(
        select(func.sum(BetaSignup.jobs_saved)).select_from(BetaSignup)
    )
    total_jobs_saved = jobs_saved_query.scalar() or 0

    jobs_applied_query = await session.execute(
        select(func.sum(BetaSignup.jobs_applied)).select_from(BetaSignup)
    )
    total_applications = jobs_applied_query.scalar() or 0

    searches_query = await session.execute(
        select(func.sum(BetaSignup.searches_performed)).select_from(BetaSignup)
    )
    total_searches = searches_query.scalar() or 0

    total_signups_query = await session.execute(
        select(func.count()).select_from(BetaSignup)
    )
    total_signups = total_signups_query.scalar() or 0

    activated_query = await session.execute(
        select(func.count())
        .select_from(BetaSignup)
        .where(BetaSignup.status == "active")
    )
    funnel_activated = activated_query.scalar() or 0

    first_search_query = await session.execute(
        select(func.count())
        .select_from(BetaSignup)
        .where(BetaSignup.searches_performed > 0)
    )
    funnel_first_search = first_search_query.scalar() or 0

    first_application_query = await session.execute(
        select(func.count()).select_from(BetaSignup).where(BetaSignup.jobs_applied > 0)
    )
    funnel_first_application = first_application_query.scalar() or 0

    return {
        "profiles_completed": profiles_completed,
        "total_jobs_viewed": total_jobs_viewed,
        "total_jobs_saved": total_jobs_saved,
        "total_applications": total_applications,
        "total_searches": total_searches,
        "jobs_secured": 0,  # TODO: Add self-reporting mechanism
        "funnel": {
            "signups": total_signups,
            "activated": funnel_activated,
            "profile_complete": profiles_completed,
            "first_search": funnel_first_search,
            "first_application": funnel_first_application,
        },
    }


@router.get("/users")
async def beta_users(session: AsyncSession = Depends(get_db), limit: int = 20):
    """List beta users for admin dashboard."""

    query = select(BetaSignup).order_by(BetaSignup.signed_up_at.desc()).limit(limit)

    result = await session.execute(query)
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "university": user.university,
                "year_of_study": user.year_of_study,
                "field_of_study": user.field_of_study,
                "status": user.status,
                "signed_up_at": user.signed_up_at.isoformat(),
                "last_active_at": user.last_active_at.isoformat()
                if user.last_active_at
                else None,
                "profile_completed": user.profile_completed,
                "jobs_viewed": user.jobs_viewed,
                "jobs_saved": user.jobs_saved,
                "jobs_applied": user.jobs_applied,
                "searches_performed": user.searches_performed,
            }
            for user in users
        ]
    }
