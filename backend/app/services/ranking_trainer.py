"""Training pipeline for learned ranking model.

Trains a classification-based ranker on implicit feedback from user
interactions (apply clicks from UserAnalytics) cross-joined with the
serve-time context captured in SearchServingLog (T-DS-916).

Positive examples: jobs that a user applied to, joined with the
  SearchServingLog row from the session that surfaced the job.
Negative examples: jobs that appeared in the same search session but
  were *not* applied to (shown-but-not-clicked signals).

Fallback: when no SearchServingLog rows exist (e.g. fresh deployment),
  the trainer falls back to job attributes only — without synthetic
  similarity placeholders.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from ..db.models import UserAnalytics, JobPost, SearchServingLog
from .ranking import (
    RankingModel,
    extract_ranking_features,
    MODEL_PATH,
)

logger = logging.getLogger(__name__)


def _build_result_dict(job: JobPost, score: float, query: str) -> dict[str, Any]:
    """Build the result dict that extract_ranking_features expects."""
    # Load skills from job attributes if available
    skills: list = []
    return {
        "id": job.id,
        "title": job.title_raw,
        "description": job.description_clean or job.description_raw or "",
        "similarity_score": score * 100.0,  # feature extractor normalises /100
        "first_seen": job.first_seen,
        "seniority": job.seniority or "",
        "location": str(job.location_id or ""),
        "salary_min": job.salary_min,
        "salary_range": (
            f"{job.salary_min}-{job.salary_max}" if job.salary_min else None
        ),
        "skills": skills,
    }


def _collect_from_serving_log(
    db: Session,
    apply_job_ids: set[int],
    session_queries: dict[str, str],
    cutoff: datetime,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Derive positive/negative examples from SearchServingLog.

    Positive: (job_id, session) pair where job was applied to.
    Negative: jobs shown in the same session that were NOT applied to.
    """
    stmt = (
        select(SearchServingLog)
        .where(SearchServingLog.served_at > cutoff)
        .order_by(SearchServingLog.served_at.desc())
        .limit(5000)
    )
    log_rows = db.execute(stmt).scalars().all()

    if not log_rows:
        return [], []

    # Index serving log rows by session_id for fast lookup
    session_logs: dict[str, list[SearchServingLog]] = {}
    for row in log_rows:
        sid = row.session_id or str(row.id)
        session_logs.setdefault(sid, []).append(row)

    positive_features: list[np.ndarray] = []
    negative_features: list[np.ndarray] = []

    for log_row in log_rows:
        job_ids = log_row.result_job_ids or []
        scores = log_row.result_scores or []
        query = log_row.query or ""

        # Build score lookup for this serving event
        score_map: dict[int, float] = {}
        for i, jid in enumerate(job_ids):
            score_map[int(jid)] = float(scores[i]) if i < len(scores) else 0.0

        # Pre-fetch jobs in this candidate set
        if not job_ids:
            continue
        jobs_in_log = {
            j.id: j
            for j in db.execute(
                select(JobPost).where(JobPost.id.in_([int(x) for x in job_ids]))
            )
            .scalars()
            .all()
        }

        for jid_raw in job_ids:
            jid = int(jid_raw)
            job = jobs_in_log.get(jid)
            if not job:
                continue
            score = score_map.get(jid, 0.0)
            result = _build_result_dict(job, score, query)
            feat = extract_ranking_features(result, query)
            if jid in apply_job_ids:
                positive_features.append(feat)
            else:
                negative_features.append(feat)

    return positive_features, negative_features


def _collect_fallback(
    db: Session,
    apply_events: list,
    cutoff: datetime,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Fallback when no SearchServingLog data exists.

    Uses job attributes only — no synthetic similarity placeholders.
    """
    positive_features: list[np.ndarray] = []
    applied_job_ids: set[int] = set()

    for event in apply_events:
        job_id = event.event_data.get("job_id")
        if not job_id:
            continue
        job = db.execute(
            select(JobPost).where(JobPost.id == job_id)
        ).scalar_one_or_none()
        if not job:
            continue
        applied_job_ids.add(job_id)
        # Use 0.0 similarity — no search context available; recency + salary
        # + seniority features still carry signal.
        result = _build_result_dict(job, score=0.0, query="")
        positive_features.append(extract_ranking_features(result, ""))

    # Negatives: random recent jobs not applied to
    neg_stmt = (
        select(JobPost)
        .where(
            and_(
                JobPost.first_seen > cutoff,
                JobPost.id.notin_(applied_job_ids) if applied_job_ids else True,
            )
        )
        .order_by(func.random())
        .limit(max(len(positive_features) * 2, 20))
    )
    neg_features: list[np.ndarray] = []
    for job in db.execute(neg_stmt).scalars().all():
        result = _build_result_dict(job, score=0.0, query="")
        neg_features.append(extract_ranking_features(result, ""))

    return positive_features, neg_features


def collect_training_data(
    db: Session, days_back: int = 30, min_positives: int = 10
) -> tuple[np.ndarray, np.ndarray] | None:
    """Collect training data from user interactions and serve-time logs.

    Strategy:
      1. Load apply events from UserAnalytics (positive signal source).
      2. Try to join with SearchServingLog for real serve-time features.
      3. Fall back to job-attributes-only features if no log data exists.

    Returns (features, labels) or None when data is insufficient.
    """
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    stmt_apply = (
        select(UserAnalytics)
        .where(
            and_(
                UserAnalytics.event_type == "apply",
                UserAnalytics.timestamp > cutoff,
            )
        )
        .order_by(UserAnalytics.timestamp.desc())
    )
    apply_events = db.execute(stmt_apply).scalars().all()

    if len(apply_events) < min_positives:
        logger.warning(
            f"Insufficient apply events: {len(apply_events)} < {min_positives}"
        )
        return None

    apply_job_ids: set[int] = {
        int(e.event_data["job_id"]) for e in apply_events if e.event_data.get("job_id")
    }
    session_queries: dict[str, str] = {
        e.session_id: e.event_data.get("query", "")
        for e in apply_events
        if e.session_id
    }

    # Prefer serve-time log data
    positive_features, negative_features = _collect_from_serving_log(
        db, apply_job_ids, session_queries, cutoff
    )

    if len(positive_features) < min_positives:
        logger.info(
            "SearchServingLog has insufficient coverage — using job-attribute fallback"
        )
        positive_features, negative_features = _collect_fallback(
            db, apply_events, cutoff
        )

    if len(positive_features) < min_positives:
        logger.warning("Still insufficient positives after fallback")
        return None

    X_pos = np.array(positive_features, dtype=np.float32)
    X_neg = (
        np.array(negative_features, dtype=np.float32)
        if negative_features
        else X_pos[:0]
    )
    X = np.vstack([X_pos, X_neg]) if len(X_neg) else X_pos

    y_pos = np.ones(len(positive_features), dtype=np.int32)
    y_neg = np.zeros(len(negative_features), dtype=np.int32)
    y = np.hstack([y_pos, y_neg])

    logger.info(f"Collected {len(y_pos)} positive, {len(y_neg)} negative examples")
    return X, y


def train_ranking_model(db: Session, days_back: int = 30) -> dict[str, Any]:
    """Train the ranking model on recent interaction data."""
    logger.info(f"Training ranking model on {days_back} days of data")

    data = collect_training_data(db, days_back=days_back)
    if data is None:
        return {
            "success": False,
            "error": "Insufficient training data",
            "trained_at": None,
        }

    X, y = data

    model = RankingModel()
    try:
        model.train(X, y)
        logger.info(
            f"Model trained successfully: {len(y)} examples, {y.sum()} positive"
        )
        return {
            "success": True,
            "examples_total": int(len(y)),
            "examples_positive": int(y.sum()),
            "examples_negative": int(len(y) - y.sum()),
            "model_path": str(MODEL_PATH),
            "trained_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "trained_at": None,
        }


def get_model_info() -> dict[str, Any]:
    """Get information about the current ranking model."""
    if not MODEL_PATH.exists():
        return {
            "exists": False,
            "path": str(MODEL_PATH),
            "size_bytes": None,
            "modified_at": None,
        }

    stat = MODEL_PATH.stat()
    return {
        "exists": True,
        "path": str(MODEL_PATH),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }
