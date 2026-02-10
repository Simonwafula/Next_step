from __future__ import annotations

from collections import Counter
from typing import Any, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db.models import JobPost

_NON_JOB_TERMS = (
    "tender",
    "rfp",
    "rfq",
    "expression of interest",
    "memoranda",
    "public participation",
    "annual development plan",
    "downloads",
    "resources",
    "news",
    "updates",
)

_JOB_TERMS = (
    "vacan",
    "recruit",
    "career",
    "job",
    "position",
    "apply",
    "application",
    "deadline",
    "closing",
    "qualifications",
    "requirements",
    "how to apply",
)


def _reason_non_job(job: JobPost) -> str | None:
    title = (job.title_raw or "").strip().lower()
    url = (job.url or "").strip().lower()
    desc = (job.description_raw or "").strip().lower()

    combined = f"{title} {url} {desc}"

    if any(t in combined for t in _NON_JOB_TERMS) and not any(
        t in combined for t in _JOB_TERMS
    ):
        return "non_job_terms"

    # Common gov pattern: sites publish "opportunities" sections that are not
    # hiring. If it doesn't contain job signals and isn't a document, treat it
    # as non-job.
    if "/opportunities/" in url and not any(t in combined for t in _JOB_TERMS):
        return "opportunities_non_job"

    # Low-information pages.
    if (
        not job.attachment_flag
        and len(desc) < 120
        and not any(t in combined for t in _JOB_TERMS)
    ):
        return "low_info_non_job"

    return None


def quarantine_government_nonjobs(
    db: Session,
    *,
    limit: int = 2000,
    dry_run: bool = True,
    max_quality_score: float = 0.5,
) -> Dict[str, Any]:
    """Quarantine obvious non-job pages already ingested under gov_careers.

    Sets JobPost.is_active = False for candidates. This keeps history intact but
    prevents public search/counts from being polluted.
    """

    # Normalize empty descriptions so quality snapshot and filters behave.
    if not dry_run:
        db.query(JobPost).filter(JobPost.source == "gov_careers").filter(
            JobPost.description_raw.is_not(None)
        ).filter(func.length(func.trim(JobPost.description_raw)) == 0).update(
            {JobPost.description_raw: None},
            synchronize_session=False,
        )

    q = (
        db.query(JobPost)
        .filter(JobPost.source == "gov_careers")
        .filter(JobPost.is_active.is_(True))
        .order_by(JobPost.first_seen.desc())
    )
    # Guardrail: only quarantine low-quality items by default.
    q = q.filter(
        (JobPost.quality_score.is_(None)) | (JobPost.quality_score < max_quality_score)
    )

    jobs = q.limit(limit).all()

    reasons = Counter()
    quarantined_ids: list[int] = []

    for job in jobs:
        reason = _reason_non_job(job)
        if not reason:
            continue
        reasons[reason] += 1
        quarantined_ids.append(job.id)
        if not dry_run:
            job.is_active = False
            db.add(job)

    if not dry_run:
        db.commit()
    else:
        db.rollback()

    return {
        "status": "success",
        "dry_run": dry_run,
        "scanned": len(jobs),
        "quarantined": len(quarantined_ids),
        "reasons": dict(reasons),
        "sample_job_ids": quarantined_ids[:10],
        "max_quality_score": max_quality_score,
    }
