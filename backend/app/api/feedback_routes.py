"""T-DS-962: Candidate-facing feedback API.

Endpoints
---------
GET  /api/users/applications/{application_id}/feedback
    Returns the rejection feedback bundle for a candidate's application.
    Only accessible by the candidate who owns the application.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import JobApplication, User
from ..services.auth_service import get_current_user
from ..services.feedback import generate_rejection_feedback

router = APIRouter(prefix="/api/users", tags=["feedback"])


@router.get("/applications/{application_id}/feedback")
def get_application_feedback(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return rejection feedback for an application owned by the current user."""
    app_obj = db.execute(
        select(JobApplication).where(JobApplication.id == application_id)
    ).scalar_one_or_none()

    if not app_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found."
        )
    if app_obj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to view this application's feedback.",
        )

    return generate_rejection_feedback(application_id, db)
