"""Admin endpoints for deduplication review and management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import JobDedupeMap, JobPost, Organization, User
from ..services.auth_service import require_admin
from ..services.processing_log_service import log_monitoring_event

router = APIRouter(prefix="/api/admin/dedup", tags=["admin-dedup"])


@router.get("/candidates")
def list_dedup_candidates(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str = Query("pending", pattern="^(pending|merged|dismissed|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """List duplicate candidate pairs for admin review."""
    del current_user

    job_a = JobPost.__table__.alias("job_a")
    job_b = JobPost.__table__.alias("job_b")
    org_a = Organization.__table__.alias("org_a")
    org_b = Organization.__table__.alias("org_b")

    stmt = (
        select(
            JobDedupeMap.job_id,
            JobDedupeMap.canonical_job_id,
            JobDedupeMap.similarity_score,
            JobDedupeMap.status,
            JobDedupeMap.reviewed_at,
            job_a.c.title_raw.label("title_a"),
            job_a.c.source.label("source_a"),
            org_a.c.name.label("company_a"),
            job_b.c.title_raw.label("title_b"),
            job_b.c.source.label("source_b"),
            org_b.c.name.label("company_b"),
        )
        .join(job_a, JobDedupeMap.job_id == job_a.c.id)
        .join(job_b, JobDedupeMap.canonical_job_id == job_b.c.id)
        .outerjoin(org_a, job_a.c.org_id == org_a.c.id)
        .outerjoin(org_b, job_b.c.org_id == org_b.c.id)
    )

    if status != "all":
        stmt = stmt.where(JobDedupeMap.status == status)

    total = (
        db.execute(
            select(func.count(JobDedupeMap.job_id)).where(
                JobDedupeMap.status == status if status != "all" else True
            )
        ).scalar()
        or 0
    )

    stmt = (
        stmt.order_by(desc(JobDedupeMap.similarity_score)).limit(limit).offset(offset)
    )
    rows = db.execute(stmt).all()

    return {
        "candidates": [
            {
                "id": row.job_id,
                "job_id": row.job_id,
                "canonical_job_id": row.canonical_job_id,
                "similarity": row.similarity_score,
                "status": row.status,
                "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
                "title_a": row.title_a or "Untitled",
                "source_a": row.source_a,
                "company_a": row.company_a or "Unknown",
                "title_b": row.title_b or "Untitled",
                "source_b": row.source_b,
                "company_b": row.company_b or "Unknown",
            }
            for row in rows
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


@router.post("/merge")
def merge_dedup_pair(
    job_id: int = Query(..., description="Duplicate job_id to deactivate"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Mark a duplicate pair as merged — keeps canonical, deactivates duplicate."""
    entry = db.execute(
        select(JobDedupeMap).where(JobDedupeMap.job_id == job_id)
    ).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Dedup entry not found")
    if entry.status != "pending":
        raise HTTPException(status_code=400, detail=f"Entry already {entry.status}")

    entry.status = "merged"
    entry.reviewed_at = datetime.utcnow()
    entry.reviewed_by = current_user.id

    # Deactivate the duplicate job
    dup_job = db.execute(
        select(JobPost).where(JobPost.id == job_id)
    ).scalar_one_or_none()
    if dup_job:
        dup_job.is_active = False

    db.commit()

    log_monitoring_event(
        db,
        status="success",
        message="Dedup pair merged",
        details={
            "job_id": job_id,
            "canonical_job_id": entry.canonical_job_id,
            "admin": current_user.email,
        },
    )

    return {"status": "merged", "job_id": job_id}


@router.post("/dismiss")
def dismiss_dedup_pair(
    job_id: int = Query(..., description="Duplicate job_id to dismiss"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Dismiss a duplicate candidate — keeps both jobs active."""
    entry = db.execute(
        select(JobDedupeMap).where(JobDedupeMap.job_id == job_id)
    ).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Dedup entry not found")
    if entry.status != "pending":
        raise HTTPException(status_code=400, detail=f"Entry already {entry.status}")

    entry.status = "dismissed"
    entry.reviewed_at = datetime.utcnow()
    entry.reviewed_by = current_user.id
    db.commit()

    log_monitoring_event(
        db,
        status="success",
        message="Dedup pair dismissed",
        details={
            "job_id": job_id,
            "canonical_job_id": entry.canonical_job_id,
            "admin": current_user.email,
        },
    )

    return {"status": "dismissed", "job_id": job_id}


@router.get("/stats")
def dedup_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """Aggregate dedup review statistics."""
    del current_user

    total = db.execute(select(func.count(JobDedupeMap.job_id))).scalar() or 0
    merged = (
        db.execute(
            select(func.count(JobDedupeMap.job_id)).where(
                JobDedupeMap.status == "merged"
            )
        ).scalar()
        or 0
    )
    dismissed = (
        db.execute(
            select(func.count(JobDedupeMap.job_id)).where(
                JobDedupeMap.status == "dismissed"
            )
        ).scalar()
        or 0
    )
    pending = (
        db.execute(
            select(func.count(JobDedupeMap.job_id)).where(
                JobDedupeMap.status == "pending"
            )
        ).scalar()
        or 0
    )

    return {
        "total": int(total),
        "merged": int(merged),
        "dismissed": int(dismissed),
        "pending": int(pending),
    }
