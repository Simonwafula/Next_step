"""Assessment delivery and verification endpoints (T-DS-942/944/945)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import User
from ..services.auth_service import get_current_user, require_subscription
from ..services.assessment_service import (
    start_assessment,
    submit_answer,
    complete_assessment,
    seed_question_bank,
    get_verification_summary,
    get_verification_qa,
)

router = APIRouter(tags=["assessments"])


# ---------------------------------------------------------------------------
# T-DS-942: Assessment delivery
# ---------------------------------------------------------------------------


class StartAssessmentRequest(BaseModel):
    role_family: str


class SubmitAnswerRequest(BaseModel):
    question_id: int
    selected_index: int


@router.post("/assessment/start")
def start_assessment_endpoint(
    request: StartAssessmentRequest,
    current_user: User = Depends(require_subscription("professional")),
    db: Session = Depends(get_db),
):
    """Start a new assessment session for a role family."""
    try:
        return start_assessment(current_user.id, request.role_family, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post("/assessment/{session_id}/answer")
def submit_answer_endpoint(
    session_id: int,
    request: SubmitAnswerRequest,
    current_user: User = Depends(require_subscription("professional")),
    db: Session = Depends(get_db),
):
    """Submit an answer for a question in an active session."""
    try:
        return submit_answer(
            session_id, request.question_id, request.selected_index, db
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post("/assessment/{session_id}/complete")
def complete_assessment_endpoint(
    session_id: int,
    current_user: User = Depends(require_subscription("professional")),
    db: Session = Depends(get_db),
):
    """Finalise the session — compute score, level, percentile, certifications."""
    try:
        return complete_assessment(session_id, current_user.id, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


# ---------------------------------------------------------------------------
# T-DS-944: Employer-visible verification summary
# ---------------------------------------------------------------------------


@router.get("/candidates/{user_id}/verification")
def candidate_verification_summary(
    user_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the verification bundle for a candidate (employer-accessible)."""
    return get_verification_summary(user_id, db)


# ---------------------------------------------------------------------------
# T-DS-941/945: Admin — seed question bank + QA check
# ---------------------------------------------------------------------------


@router.post("/admin/assessment/seed-questions")
def seed_questions_endpoint(
    role_family: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Seed the question bank for a role family from RoleSkillBaseline data."""
    created = seed_question_bank(role_family, db)
    return {"role_family": role_family.lower(), "questions_created": created}


@router.get("/admin/assessment/verification-qa")
def verification_qa_endpoint(
    role_family: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if a role family is ready for assessment launch (T-DS-945)."""
    return get_verification_qa(role_family, db)
