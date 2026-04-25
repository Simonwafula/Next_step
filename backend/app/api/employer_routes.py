"""T-DS-953/954/961: Employer-side pre-screening API.

Endpoints
---------
GET  /api/employer/jobs/{job_post_id}/candidates
    Score and rank all applicants for a job. Returns scored list with
    explanation bundles + intelligence sidecar (T-DS-954).

POST /api/employer/jobs/{job_post_id}/shortlist
    Persist a shortlist (scored candidates) for employer review.

GET  /api/employer/shortlists/{shortlist_id}
    Retrieve a saved shortlist with all entries and the intelligence sidecar.

GET  /api/employer/shortlists
    List all shortlists owned by the caller's employer account.

POST /api/employer/ratings
    Submit a quick-rating for a candidate on a job (T-DS-961).

GET  /api/employer/ratings
    List ratings submitted by this employer account (T-DS-961).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import (
    CandidateShortlist,
    CandidateShortlistEntry,
    EmployerAccount,
    EmployerCandidateRating,
    EmployerUser,
    EMPLOYER_RATING_SENTIMENTS,
    EMPLOYER_RATING_REASONS,
    JobApplication,
    JobPost,
    TitleNorm,
    User,
)
from ..services.auth_service import get_current_user
from ..services.prescreening import (
    build_intelligence_sidecar,
    score_candidate_for_job,
)

router = APIRouter(prefix="/api/employer", tags=["employer"])


# ---------------------------------------------------------------------------
# Auth helper — resolves the EmployerAccount for the current user
# ---------------------------------------------------------------------------


def _get_employer_account(current_user: User, db: Session) -> EmployerAccount:
    """Return the EmployerAccount associated with the current user.

    Raises 403 if the user has no employer membership.
    """
    eu = db.execute(
        select(EmployerUser).where(
            EmployerUser.user_id == current_user.id,
            EmployerUser.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()
    if not eu:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active employer account linked to this user.",
        )
    employer = db.execute(
        select(EmployerAccount).where(EmployerAccount.id == eu.employer_account_id)
    ).scalar_one_or_none()
    if not employer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employer account not found.",
        )
    return employer


def _resolve_role_family(job_post_id: int, db: Session) -> str | None:
    job = db.execute(
        select(JobPost).where(JobPost.id == job_post_id)
    ).scalar_one_or_none()
    if not job or not job.title_norm_id:
        return None
    tn = db.execute(
        select(TitleNorm).where(TitleNorm.id == job.title_norm_id)
    ).scalar_one_or_none()
    return tn.family if tn else None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ShortlistCreateRequest(BaseModel):
    name: str = "Shortlist"
    candidate_user_ids: list[int]


class ShortlistResponse(BaseModel):
    id: int
    name: str
    job_post_id: int
    status: str
    intelligence_sidecar: dict[str, Any]
    entries: list[dict[str, Any]]
    created_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_post_id}/candidates")
def score_candidates_for_job(
    job_post_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Score all applicants for a job and return ranked results.

    Returned list is sorted by overall_score descending (best first).
    Also includes an intelligence sidecar with required skills, demand,
    and salary data from the LMI layer (T-DS-954).
    """
    _get_employer_account(current_user, db)

    # Collect applicants
    applications = (
        db.execute(
            select(JobApplication).where(JobApplication.job_post_id == job_post_id)
        )
        .scalars()
        .all()
    )

    if not applications:
        role_family = _resolve_role_family(job_post_id, db)
        return {
            "job_post_id": job_post_id,
            "total_applicants": 0,
            "results": [],
            "intelligence_sidecar": build_intelligence_sidecar(role_family, db),
        }

    scored: list[dict] = []
    for app in applications:
        score_result = score_candidate_for_job(app.user_id, job_post_id, db)
        scored.append(score_result)

    # Sort best-first, cap at limit
    scored.sort(key=lambda x: x["overall_score"], reverse=True)
    scored = scored[:limit]
    for rank, entry in enumerate(scored, start=1):
        entry["rank"] = rank

    role_family = _resolve_role_family(job_post_id, db)
    return {
        "job_post_id": job_post_id,
        "total_applicants": len(applications),
        "results": scored,
        "intelligence_sidecar": build_intelligence_sidecar(role_family, db),
    }


@router.post("/jobs/{job_post_id}/shortlist", status_code=status.HTTP_201_CREATED)
def create_shortlist(
    job_post_id: int,
    body: ShortlistCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create and persist a named shortlist for a job.

    Scores each listed candidate and stores the result + intelligence sidecar.
    """
    employer = _get_employer_account(current_user, db)

    # Verify job exists
    job = db.execute(
        select(JobPost).where(JobPost.id == job_post_id)
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job post not found."
        )

    role_family = _resolve_role_family(job_post_id, db)
    sidecar = build_intelligence_sidecar(role_family, db)

    shortlist = CandidateShortlist(
        employer_account_id=employer.id,
        created_by_user_id=current_user.id,
        job_post_id=job_post_id,
        name=body.name,
        status="active",
        intelligence_sidecar=sidecar,
    )
    db.add(shortlist)
    db.flush()  # get shortlist.id before creating entries

    entries: list[CandidateShortlistEntry] = []
    scored_candidates: list[dict] = []
    for user_id in body.candidate_user_ids:
        score_result = score_candidate_for_job(user_id, job_post_id, db)
        scored_candidates.append(score_result)

    scored_candidates.sort(key=lambda x: x["overall_score"], reverse=True)
    for rank, sc in enumerate(scored_candidates, start=1):
        entry = CandidateShortlistEntry(
            shortlist_id=shortlist.id,
            candidate_user_id=sc["user_id"],
            overall_score=sc["overall_score"],
            score_breakdown=sc["score_breakdown"],
            explanation=sc["explanation"],
            rank=rank,
        )
        db.add(entry)
        entries.append(entry)

    db.commit()
    db.refresh(shortlist)

    return {
        "id": shortlist.id,
        "name": shortlist.name,
        "job_post_id": job_post_id,
        "status": shortlist.status,
        "total_candidates": len(scored_candidates),
        "intelligence_sidecar": sidecar,
        "created_at": shortlist.created_at.isoformat(),
    }


@router.get("/shortlists/{shortlist_id}")
def get_shortlist(
    shortlist_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieve a saved shortlist with all entries and explanation bundles."""
    employer = _get_employer_account(current_user, db)

    shortlist = db.execute(
        select(CandidateShortlist).where(
            CandidateShortlist.id == shortlist_id,
            CandidateShortlist.employer_account_id == employer.id,
        )
    ).scalar_one_or_none()
    if not shortlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shortlist not found."
        )

    entries = (
        db.execute(
            select(CandidateShortlistEntry)
            .where(CandidateShortlistEntry.shortlist_id == shortlist_id)
            .order_by(CandidateShortlistEntry.rank)
        )
        .scalars()
        .all()
    )

    return {
        "id": shortlist.id,
        "name": shortlist.name,
        "job_post_id": shortlist.job_post_id,
        "status": shortlist.status,
        "intelligence_sidecar": shortlist.intelligence_sidecar,
        "entries": [
            {
                "rank": e.rank,
                "candidate_user_id": e.candidate_user_id,
                "overall_score": e.overall_score,
                "score_breakdown": e.score_breakdown,
                "explanation": e.explanation,
            }
            for e in entries
        ],
        "created_at": shortlist.created_at.isoformat(),
    }


@router.get("/shortlists")
def list_shortlists(
    job_post_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List all shortlists for the caller's employer account."""
    employer = _get_employer_account(current_user, db)

    stmt = select(CandidateShortlist).where(
        CandidateShortlist.employer_account_id == employer.id
    )
    if job_post_id is not None:
        stmt = stmt.where(CandidateShortlist.job_post_id == job_post_id)
    stmt = stmt.order_by(CandidateShortlist.created_at.desc())

    rows = db.execute(stmt).scalars().all()
    return {
        "employer_account_id": employer.id,
        "shortlists": [
            {
                "id": s.id,
                "name": s.name,
                "job_post_id": s.job_post_id,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
            }
            for s in rows
        ],
    }


# ---------------------------------------------------------------------------
# T-DS-961: Employer quick-rating capture
# ---------------------------------------------------------------------------


class RatingCreateRequest(BaseModel):
    candidate_user_id: int
    job_post_id: int
    sentiment: str
    reason: str | None = None
    comment: str | None = None
    stage_at_rating: str | None = None


@router.post("/ratings", status_code=status.HTTP_201_CREATED)
def submit_rating(
    body: RatingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Submit a quick employer rating for a candidate on a job.

    sentiment must be one of: strong_yes, yes, maybe, no, strong_no.
    reason (optional) must be one of EMPLOYER_RATING_REASONS.
    """
    employer = _get_employer_account(current_user, db)

    if body.sentiment not in EMPLOYER_RATING_SENTIMENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sentiment. Must be one of: {EMPLOYER_RATING_SENTIMENTS}",
        )
    if body.reason and body.reason not in EMPLOYER_RATING_REASONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid reason. Must be one of: {EMPLOYER_RATING_REASONS}",
        )

    rating = EmployerCandidateRating(
        employer_account_id=employer.id,
        rated_by_user_id=current_user.id,
        candidate_user_id=body.candidate_user_id,
        job_post_id=body.job_post_id,
        sentiment=body.sentiment,
        reason=body.reason,
        comment=body.comment,
        stage_at_rating=body.stage_at_rating,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)

    return {
        "id": rating.id,
        "candidate_user_id": rating.candidate_user_id,
        "job_post_id": rating.job_post_id,
        "sentiment": rating.sentiment,
        "reason": rating.reason,
        "rated_at": rating.rated_at.isoformat(),
    }


@router.get("/ratings")
def list_ratings(
    job_post_id: int | None = Query(default=None),
    candidate_user_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List ratings submitted by this employer account."""
    employer = _get_employer_account(current_user, db)

    stmt = select(EmployerCandidateRating).where(
        EmployerCandidateRating.employer_account_id == employer.id
    )
    if job_post_id is not None:
        stmt = stmt.where(EmployerCandidateRating.job_post_id == job_post_id)
    if candidate_user_id is not None:
        stmt = stmt.where(
            EmployerCandidateRating.candidate_user_id == candidate_user_id
        )
    stmt = stmt.order_by(EmployerCandidateRating.rated_at.desc())

    rows = db.execute(stmt).scalars().all()
    return {
        "employer_account_id": employer.id,
        "ratings": [
            {
                "id": r.id,
                "candidate_user_id": r.candidate_user_id,
                "job_post_id": r.job_post_id,
                "sentiment": r.sentiment,
                "reason": r.reason,
                "comment": r.comment,
                "stage_at_rating": r.stage_at_rating,
                "rated_at": r.rated_at.isoformat(),
            }
            for r in rows
        ],
    }
