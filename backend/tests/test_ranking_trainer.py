"""Tests for ranking model training pipeline."""

from datetime import datetime, timedelta

import pytest

from app.db.models import UserAnalytics, JobPost, User
from app.services.ranking_trainer import (
    collect_training_data,
    train_ranking_model,
    get_model_info,
)


def test_get_model_info_no_model():
    """Model info returns exists=False when no model trained."""
    from app.services.ranking import MODEL_PATH

    if MODEL_PATH.exists():
        MODEL_PATH.unlink()

    info = get_model_info()
    assert info["exists"] is False
    assert info["path"] == str(MODEL_PATH)
    assert info["size_bytes"] is None


def test_collect_training_data_insufficient_events(db_session_factory):
    """Training data collection fails with too few apply events."""
    db = db_session_factory()

    # Create a user
    user = User(
        uuid="user-1",
        email="test@test.local",
        hashed_password="hash",
        full_name="Test User",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    # Create 1 apply event (below min_positives=10)
    job = JobPost(
        source="test",
        url="https://test.com/job/1",
        url_hash="hash1",
        title_raw="Engineer",
        first_seen=datetime.utcnow(),
    )
    db.add(job)
    db.flush()

    event = UserAnalytics(
        user_id=user.id,
        session_id="session-1",
        event_type="apply",
        event_data={"job_id": job.id},
        timestamp=datetime.utcnow(),
    )
    db.add(event)
    db.commit()

    result = collect_training_data(db, days_back=30, min_positives=10)
    assert result is None  # Insufficient data
    db.close()


def test_train_ranking_model_insufficient_data(db_session_factory):
    """Training fails gracefully when insufficient data."""
    db = db_session_factory()

    result = train_ranking_model(db, days_back=30)
    assert result["success"] is False
    assert "Insufficient" in result["error"]
    assert result["trained_at"] is None
    db.close()


def test_collect_training_data_with_sufficient_events(
    db_session_factory,
):
    """Training data collection succeeds with enough apply events."""
    db = db_session_factory()

    # Create user
    user = User(
        uuid="user-1",
        email="test@test.local",
        hashed_password="hash",
        full_name="Test User",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    # Create 15 jobs
    jobs = []
    for i in range(15):
        job = JobPost(
            source="test",
            url=f"https://test.com/job/{i}",
            url_hash=f"hash{i}",
            title_raw=f"Engineer {i}",
            first_seen=datetime.utcnow() - timedelta(days=5),
            seniority="mid-level",
        )
        db.add(job)
        db.flush()
        jobs.append(job)

    # Create 12 apply events (above min_positives=10)
    for i in range(12):
        event = UserAnalytics(
            user_id=user.id,
            session_id=f"session-{i}",
            event_type="apply",
            event_data={"job_id": jobs[i].id},
            timestamp=datetime.utcnow() - timedelta(days=3),
        )
        db.add(event)
    db.commit()

    result = collect_training_data(db, days_back=30, min_positives=10)
    assert result is not None
    X, y = result
    assert len(X) > 0
    assert len(y) > 0
    assert X.shape[1] == 8  # 8 features
    assert y.sum() == 12  # 12 positive examples
    db.close()


def test_train_ranking_model_success(db_session_factory):
    """Training succeeds with sufficient interaction data."""
    pytest.importorskip("sklearn", reason="scikit-learn not installed")

    db = db_session_factory()

    # Create user
    user = User(
        uuid="user-1",
        email="test@test.local",
        hashed_password="hash",
        full_name="Test User",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    # Create 20 jobs
    jobs = []
    for i in range(20):
        job = JobPost(
            source="test",
            url=f"https://test.com/job/{i}",
            url_hash=f"hash{i}",
            title_raw=f"Engineer {i}",
            first_seen=datetime.utcnow() - timedelta(days=5),
            seniority="mid-level" if i % 2 == 0 else "senior",
            salary_min=100000.0 + (i * 10000),
        )
        db.add(job)
        db.flush()
        jobs.append(job)

    # Create 15 apply events
    for i in range(15):
        event = UserAnalytics(
            user_id=user.id,
            session_id=f"session-{i}",
            event_type="apply",
            event_data={"job_id": jobs[i].id},
            timestamp=datetime.utcnow() - timedelta(days=3),
        )
        db.add(event)
    db.commit()

    result = train_ranking_model(db, days_back=30)
    assert result["success"] is True
    assert result["examples_total"] > 15  # Positives + negatives
    assert result["examples_positive"] == 15
    assert result["trained_at"] is not None

    # Check model file exists
    info = get_model_info()
    assert info["exists"] is True
    assert info["size_bytes"] > 0
    db.close()
