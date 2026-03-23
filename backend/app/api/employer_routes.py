"""T-DS-953/954: Employer-side pre-screening API.

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
    EmployerUser,
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
