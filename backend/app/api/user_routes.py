from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.database import get_db
from ..services.auth_service import get_current_user, require_subscription
from ..services.personalized_recommendations import personalized_recommendations
from ..services.ai_service import ai_service
from ..db.models import User, SavedJob, JobApplication, JobAlert, UserNotification, JobPost, Organization, Location
from sqlalchemy import select, and_, desc, func

router = APIRouter()

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
    status: str
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

# Personalized Recommendations
@router.get("/recommendations")
async def get_recommendations(
    limit: int = Query(20, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized job recommendations for the current user."""
    try:
        # Try to get stored recommendations first
        recommendations = await personalized_recommendations.get_stored_recommendations(
            db, current_user.id, limit
        )
        
        # If no stored recommendations or too few, generate new ones
        if len(recommendations) < limit // 2:
            new_recommendations = await personalized_recommendations.generate_recommendations_for_user(
                db, current_user, limit
            )
            
            # Combine and deduplicate
            existing_job_ids = {rec['job_id'] for rec in recommendations}
            for new_rec in new_recommendations:
                if new_rec['job_id'] not in existing_job_ids:
                    recommendations.append(new_rec)
            
            # Sort by match score and limit
            recommendations.sort(key=lambda x: x['match_score'], reverse=True)
            recommendations = recommendations[:limit]
        
        return {
            "recommendations": recommendations,
            "total": len(recommendations),
            "message": "Personalized recommendations based on your profile and preferences"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recommendations"
        )

@router.post("/recommendations/{job_id}/interaction")
async def mark_recommendation_interaction(
    job_id: int,
    interaction_type: str = Query(..., regex="^(viewed|clicked|dismissed)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark user interaction with a recommendation."""
    success = await personalized_recommendations.mark_recommendation_interaction(
        db, current_user.id, job_id, interaction_type
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )
    
    return {"message": f"Marked as {interaction_type}"}

@router.get("/recommendations/insights")
async def get_recommendation_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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
        "total": len(saved_jobs)
    }

@router.post("/saved-jobs")
async def save_job(
    request: SaveJobRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a job for later."""
    # Check if already saved
    existing = db.execute(
        select(SavedJob).where(
            and_(
                SavedJob.user_id == current_user.id,
                SavedJob.job_post_id == request.job_id
            )
        )
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job already saved"
        )
    
    saved_job = SavedJob(
        user_id=current_user.id,
        job_post_id=request.job_id,
        notes=request.notes,
        folder=request.folder
    )
    
    db.add(saved_job)
    db.commit()
    db.refresh(saved_job)
    
    return {"message": "Job saved successfully", "id": saved_job.id}

@router.delete("/saved-jobs/{saved_job_id}")
async def unsave_job(
    saved_job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a saved job."""
    saved_job = db.execute(
        select(SavedJob).where(
            and_(
                SavedJob.id == saved_job_id,
                SavedJob.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    
    if not saved_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved job not found"
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
    db: Session = Depends(get_db)
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
                "applied_at": app.applied_at.isoformat(),
                "last_updated": app.last_updated.isoformat(),
                "application_source": app.application_source,
                "interview_dates": app.interview_dates,
                "notes": app.notes
            }
            for app in applications
        ],
        "total": len(applications)
    }

@router.post("/applications")
async def create_job_application(
    request: JobApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record a job application."""
    # Check if already applied
    existing = db.execute(
        select(JobApplication).where(
            and_(
                JobApplication.user_id == current_user.id,
                JobApplication.job_post_id == request.job_id
            )
        )
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already applied to this job"
        )
    
    application = JobApplication(
        user_id=current_user.id,
        job_post_id=request.job_id,
        cover_letter=request.cover_letter,
        cv_version=request.cv_version,
        application_source=request.application_source,
        notes=request.notes,
        status="applied"
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
    db: Session = Depends(get_db)
):
    """Update job application status."""
    application = db.execute(
        select(JobApplication).where(
            and_(
                JobApplication.id == application_id,
                JobApplication.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(application, field):
            setattr(application, field, value)
    
    db.commit()
    db.refresh(application)
    
    return {"message": "Application updated successfully"}

# Job Alerts
@router.get("/job-alerts")
async def get_job_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's job alerts."""
    stmt = select(JobAlert).where(JobAlert.user_id == current_user.id).order_by(desc(JobAlert.created_at))
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
                "last_triggered": alert.last_triggered.isoformat() if alert.last_triggered else None,
                "created_at": alert.created_at.isoformat()
            }
            for alert in alerts
        ],
        "total": len(alerts)
    }

@router.post("/job-alerts")
async def create_job_alert(
    request: JobAlertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new job alert."""
    alert = JobAlert(
        user_id=current_user.id,
        name=request.name,
        query=request.query,
        filters=request.filters,
        frequency=request.frequency,
        delivery_methods=request.delivery_methods,
        is_active=True
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
    db: Session = Depends(get_db)
):
    """Update a job alert."""
    alert = db.execute(
        select(JobAlert).where(
            and_(
                JobAlert.id == alert_id,
                JobAlert.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found"
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
    db: Session = Depends(get_db)
):
    """Delete a job alert."""
    alert = db.execute(
        select(JobAlert).where(
            and_(
                JobAlert.id == alert_id,
                JobAlert.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found"
        )
    
    db.delete(alert)
    db.commit()
    
    return {"message": "Job alert deleted successfully"}

# AI Career Advice
@router.post("/career-advice")
async def get_career_advice(
    request: CareerAdviceRequest,
    current_user: User = Depends(require_subscription("professional"))
):
    """Get AI-powered career advice."""
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete your profile to get personalized advice"
        )
    
    advice = await ai_service.generate_career_advice(current_user.profile, request.query)
    
    return {
        "advice": advice,
        "query": request.query,
        "generated_at": "now"
    }

# Notifications
@router.get("/notifications")
async def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notifications."""
    stmt = select(UserNotification).where(UserNotification.user_id == current_user.id)
    
    if unread_only:
        stmt = stmt.where(UserNotification.is_read == False)
    
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
                "read_at": notif.read_at.isoformat() if notif.read_at else None
            }
            for notif in notifications
        ],
        "total": len(notifications)
    }

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    notification = db.execute(
        select(UserNotification).where(
            and_(
                UserNotification.id == notification_id,
                UserNotification.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    notification.read_at = db.execute(select(func.now())).scalar()
    
    db.commit()
    
    return {"message": "Notification marked as read"}

@router.put("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read."""
    db.execute(
        UserNotification.__table__.update().where(
            and_(
                UserNotification.user_id == current_user.id,
                UserNotification.is_read == False
            )
        ).values(is_read=True, read_at=func.now())
    )
    
    db.commit()
    
    return {"message": "All notifications marked as read"}
