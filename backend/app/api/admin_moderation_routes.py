"""Admin endpoints for content moderation (company reviews)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import CompanyReview, Organization, User
from ..services.auth_service import require_admin
from ..services.processing_log_service import log_monitoring_event

router = APIRouter(prefix="/api/admin/moderation", tags=["admin-moderation"])


class ModerationActionRequest(BaseModel):
    notes: str | None = None


@router.get("/queue")
def moderation_queue(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """List reviews awaiting moderation."""
    del current_user

    stmt = select(
        CompanyReview.id,
        CompanyReview.title,
        CompanyReview.review_text,
        CompanyReview.overall_rating,
        CompanyReview.moderation_status,
        CompanyReview.moderation_notes,
        CompanyReview.created_at,
        CompanyReview.job_title,
        Organization.name.label("company_name"),
    ).outerjoin(Organization, CompanyReview.organization_id == Organization.id)

    if status != "all":
        stmt = stmt.where(CompanyReview.moderation_status == status)

    total = (
        db.execute(
            select(func.count(CompanyReview.id)).where(
                CompanyReview.moderation_status == status if status != "all" else True
            )
        ).scalar()
        or 0
    )

    stmt = stmt.order_by(desc(CompanyReview.created_at)).limit(limit).offset(offset)
    rows = db.execute(stmt).all()

    return {
        "items": [
            {
                "id": row.id,
                "title": row.title or "Untitled Review",
                "review_text": (row.review_text or "")[:200],
                "rating": row.overall_rating,
                "status": row.moderation_status or "pending",
                "reason": row.moderation_notes or "Pending review",
                "company": row.company_name or "Unknown",
                "job_title": row.job_title,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


@router.post("/{review_id}/approve")
def approve_review(
    review_id: int,
    body: ModerationActionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Approve a company review for public display."""
    review = db.execute(
        select(CompanyReview).where(CompanyReview.id == review_id)
    ).scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_approved = True
    review.moderation_status = "approved"
    review.moderation_notes = body.notes if body else None
    review.moderated_at = datetime.utcnow()
    review.moderated_by = current_user.id
    db.commit()

    log_monitoring_event(
        db,
        status="success",
        message="Review approved",
        details={
            "review_id": review_id,
            "admin": current_user.email,
        },
    )

    return {"status": "approved", "review_id": review_id}


@router.post("/{review_id}/reject")
def reject_review(
    review_id: int,
    body: ModerationActionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Reject a company review."""
    review = db.execute(
        select(CompanyReview).where(CompanyReview.id == review_id)
    ).scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_approved = False
    review.moderation_status = "rejected"
    review.moderation_notes = body.notes if body else "Rejected by moderator"
    review.moderated_at = datetime.utcnow()
    review.moderated_by = current_user.id
    db.commit()

    log_monitoring_event(
        db,
        status="success",
        message="Review rejected",
        details={
            "review_id": review_id,
            "admin": current_user.email,
            "notes": review.moderation_notes,
        },
    )

    return {"status": "rejected", "review_id": review_id}


@router.get("/stats")
def moderation_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Aggregate moderation statistics."""
    del current_user

    pending = (
        db.execute(
            select(func.count(CompanyReview.id)).where(
                CompanyReview.moderation_status == "pending"
            )
        ).scalar()
        or 0
    )
    approved = (
        db.execute(
            select(func.count(CompanyReview.id)).where(
                CompanyReview.moderation_status == "approved"
            )
        ).scalar()
        or 0
    )
    rejected = (
        db.execute(
            select(func.count(CompanyReview.id)).where(
                CompanyReview.moderation_status == "rejected"
            )
        ).scalar()
        or 0
    )

    return {
        "pending": int(pending),
        "approved": int(approved),
        "rejected": int(rejected),
        "avg_time": "—",
    }
