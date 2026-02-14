"""Training pipeline for learned ranking model.

Trains a classification-based ranker on implicit feedback from user
interactions (apply clicks). Positive labels from UserAnalytics events,
negative labels from random sampling of non-clicked jobs.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from ..db.models import UserAnalytics, JobPost
from .ranking import (
    RankingModel,
    extract_ranking_features,
    MODEL_PATH,
)

logger = logging.getLogger(__name__)


def collect_training_data(
    db: Session, days_back: int = 30, min_positives: int = 10
) -> tuple[np.ndarray, np.ndarray] | None:
    """Collect training data from user interactions.

    Args:
        db: Database session
        days_back: How many days of history to use
        min_positives: Minimum positive examples required

    Returns:
        (features, labels) tuple or None if insufficient data
    """
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    # Get apply events (positive signals)
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

    # Extract positive examples
    positive_features = []
    for event in apply_events:
        job_id = event.event_data.get("job_id")
        if not job_id:
            continue

        # Fetch job details
        job = db.execute(
            select(JobPost).where(JobPost.id == job_id)
        ).scalar_one_or_none()
        if not job:
            continue

        # Reconstruct search context (approximation)
        # In production, you'd log search queries with results
        query = ""  # Placeholder - would come from search log
        user_context = {}

        # Build result dict for feature extraction
        result = {
            "id": job.id,
            "title": job.title_raw,
            "similarity_score": 70.0,  # Placeholder
            "seniority": job.seniority,
            "location": job.location_id,  # Simplified
            "salary_range": (
                f"{job.salary_min}-{job.salary_max}" if job.salary_min else None
            ),
        }

        features = extract_ranking_features(result, query, user_context)
        positive_features.append(features)

    # Sample negative examples (random jobs not applied to)
    # Get IDs of applied jobs
    applied_job_ids = {
        e.event_data.get("job_id") for e in apply_events if e.event_data.get("job_id")
    }

    # Sample non-applied jobs from the same time period
    neg_conditions = [JobPost.first_seen > cutoff]
    if applied_job_ids:
        neg_conditions.append(JobPost.id.notin_(applied_job_ids))

    stmt_neg = (
        select(JobPost)
        .where(and_(*neg_conditions))
        .order_by(func.random())
        .limit(len(positive_features) * 2)
    )
    neg_jobs = db.execute(stmt_neg).scalars().all()

    negative_features = []
    for job in neg_jobs:
        result = {
            "id": job.id,
            "title": job.title_raw,
            "similarity_score": 40.0,  # Lower baseline
            "seniority": job.seniority,
            "location": job.location_id,
            "salary_range": (
                f"{job.salary_min}-{job.salary_max}" if job.salary_min else None
            ),
        }
        features = extract_ranking_features(result, "", {})
        negative_features.append(features)

    # Combine features and labels
    X_pos = np.array(positive_features, dtype=np.float32)
    X_neg = np.array(negative_features, dtype=np.float32)
    X = np.vstack([X_pos, X_neg])

    y_pos = np.ones(len(positive_features), dtype=np.int32)
    y_neg = np.zeros(len(negative_features), dtype=np.int32)
    y = np.hstack([y_pos, y_neg])

    logger.info(f"Collected {len(y_pos)} positive, {len(y_neg)} negative examples")
    return X, y


def train_ranking_model(db: Session, days_back: int = 30) -> dict[str, Any]:
    """Train the ranking model on recent interaction data.

    Args:
        db: Database session
        days_back: Days of history to use for training

    Returns:
        Training metrics dict
    """
    logger.info(f"Training ranking model on {days_back} days of data")

    # Collect training data
    data = collect_training_data(db, days_back=days_back)
    if data is None:
        return {
            "success": False,
            "error": "Insufficient training data",
            "trained_at": None,
        }

    X, y = data

    # Train model
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
    """Get information about the current ranking model.

    Returns:
        Model metadata dict
    """
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
