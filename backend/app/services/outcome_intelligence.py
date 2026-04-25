"""T-DS-964: Outcome intelligence — feed hiring outcomes back into LMI products.

Functions
---------
aggregate_rejection_patterns(db, days_back)
    Counts rejection reasons by role family from ApplicationFunnelEvent.
    Result structure: {role_family: {reason: count, ...}, ...}

aggregate_hiring_outcomes(db, days_back)
    Counts hired/offered/rejected transitions by role family.
    Result structure: {role_family: {hired, offered, rejected, total}, ...}

aggregate_rating_sentiment(db, days_back)
    Counts employer quick-rating sentiments by job role family.
    Result structure: {role_family: {strong_yes, yes, maybe, no, strong_no}, ...}

get_outcome_summary(db, days_back)
    Combined summary for the intelligence dashboard.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import (
    ApplicationFunnelEvent,
    EmployerCandidateRating,
    JobPost,
    TitleNorm,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _role_family_for_job(job_post_id: int, db: Session) -> str:
    job = db.execute(
        select(JobPost).where(JobPost.id == job_post_id)
    ).scalar_one_or_none()
    if not job or not job.title_norm_id:
        return "unknown"
    tn = db.execute(
        select(TitleNorm).where(TitleNorm.id == job.title_norm_id)
    ).scalar_one_or_none()
    return tn.family if tn else "unknown"


def _cutoff(days_back: int) -> datetime:
    return datetime.utcnow() - timedelta(days=days_back)


# ---------------------------------------------------------------------------
# Aggregators
# ---------------------------------------------------------------------------


def aggregate_rejection_patterns(
    db: Session, days_back: int = 90
) -> dict[str, dict[str, int]]:
    """Count rejection reasons by role family."""
    events = (
        db.execute(
            select(ApplicationFunnelEvent).where(
                ApplicationFunnelEvent.stage == "rejected",
                ApplicationFunnelEvent.event_at > _cutoff(days_back),
            )
        )
        .scalars()
        .all()
    )

    result: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for event in events:
        family = _role_family_for_job(event.job_post_id, db)
        reason = event.reason or "other"
        result[family][reason] += 1

    return {fam: dict(counts) for fam, counts in result.items()}


def aggregate_hiring_outcomes(
    db: Session, days_back: int = 90
) -> dict[str, dict[str, int]]:
    """Count hired/offered/rejected transitions by role family."""
    events = (
        db.execute(
            select(ApplicationFunnelEvent).where(
                ApplicationFunnelEvent.stage.in_(["hired", "offered", "rejected"]),
                ApplicationFunnelEvent.event_at > _cutoff(days_back),
            )
        )
        .scalars()
        .all()
    )

    result: dict[str, dict[str, int]] = defaultdict(
        lambda: {"hired": 0, "offered": 0, "rejected": 0, "total": 0}
    )
    for event in events:
        family = _role_family_for_job(event.job_post_id, db)
        result[family][event.stage] += 1
        result[family]["total"] += 1

    return {fam: dict(counts) for fam, counts in result.items()}


def aggregate_rating_sentiment(
    db: Session, days_back: int = 90
) -> dict[str, dict[str, int]]:
    """Count employer quick-rating sentiments by role family."""
    ratings = (
        db.execute(
            select(EmployerCandidateRating).where(
                EmployerCandidateRating.rated_at > _cutoff(days_back)
            )
        )
        .scalars()
        .all()
    )

    sentiments = ["strong_yes", "yes", "maybe", "no", "strong_no"]
    result: dict[str, dict[str, int]] = defaultdict(lambda: {s: 0 for s in sentiments})
    for rating in ratings:
        family = _role_family_for_job(rating.job_post_id, db)
        if rating.sentiment in sentiments:
            result[family][rating.sentiment] += 1

    return {fam: dict(counts) for fam, counts in result.items()}


def get_outcome_summary(db: Session, days_back: int = 90) -> dict:
    """Combined outcome intelligence summary for dashboards and reports."""
    rejection_patterns = aggregate_rejection_patterns(db, days_back)
    hiring_outcomes = aggregate_hiring_outcomes(db, days_back)
    rating_sentiment = aggregate_rating_sentiment(db, days_back)

    # Top rejection reasons across all roles
    all_reason_counts: dict[str, int] = defaultdict(int)
    for counts in rejection_patterns.values():
        for reason, count in counts.items():
            all_reason_counts[reason] += count
    top_rejection_reasons = sorted(
        all_reason_counts.items(), key=lambda x: x[1], reverse=True
    )[:5]

    # Total hiring outcomes
    total_hired = sum(v.get("hired", 0) for v in hiring_outcomes.values())
    total_offered = sum(v.get("offered", 0) for v in hiring_outcomes.values())
    total_rejected = sum(v.get("rejected", 0) for v in hiring_outcomes.values())

    return {
        "period_days": days_back,
        "generated_at": datetime.utcnow().isoformat(),
        "totals": {
            "hired": total_hired,
            "offered": total_offered,
            "rejected": total_rejected,
        },
        "top_rejection_reasons": [
            {"reason": r, "count": c} for r, c in top_rejection_reasons
        ],
        "by_role_family": {
            "rejection_patterns": rejection_patterns,
            "hiring_outcomes": hiring_outcomes,
            "rating_sentiment": rating_sentiment,
        },
    }
