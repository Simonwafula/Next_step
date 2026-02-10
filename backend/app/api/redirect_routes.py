from __future__ import annotations

import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import JobPost, UserAnalytics
from ..services.auth_service import get_current_user_optional

router = APIRouter()


def _safe_http_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    return url


@router.get("/r/apply/{job_id}")
def apply_redirect(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    Log and redirect a user to the real application page for a job.

    This endpoint is intentionally public (O0) and used by both anonymous and
    logged-in users. It records a lightweight analytics event and then issues
    an HTTP redirect to `JobPost.application_url` (or a safe fallback).
    """

    job = db.execute(select(JobPost).where(JobPost.id == job_id)).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    target = (
        _safe_http_url(getattr(job, "application_url", None))
        or _safe_http_url(getattr(job, "source_url", None))
        or _safe_http_url(job.url)
    )
    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job does not have a valid application URL",
        )

    # Minimal session identifier for anonymous analytics.
    session_id = request.cookies.get("ns_session")
    set_session_cookie = False
    if not session_id:
        session_id = str(uuid.uuid4())
        set_session_cookie = True

    event = UserAnalytics(
        user_id=getattr(current_user, "id", None),
        session_id=session_id,
        event_type="apply",
        event_data={
            "job_id": job_id,
            "job_source": job.source,
            "target_url": target,
        },
        page_url=str(request.url),
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        ip_address=getattr(request.client, "host", None),
    )
    db.add(event)
    db.commit()

    redirect = RedirectResponse(
        url=target, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
    if set_session_cookie:
        redirect.set_cookie(
            key="ns_session",
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )
    return redirect
