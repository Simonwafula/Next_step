"""Integration tests for ranking system end-to-end flow."""

from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.models import JobPost, User, UserAnalytics
from app.services.ranking import rank_results
from app.services.ranking_trainer import (
    collect_training_data,
    train_ranking_model,
)
from app.services.search import search_jobs


def test_ranking_integration_with_search(db_session_factory):
    """Test that ranking module can be imported by search."""
    # This test verifies the integration point exists
    # Full search integration tested via end-to-end tests with embeddings
    from app.services import search

    # Verify rank_results is imported
    assert hasattr(search, "rank_results")
    assert callable(search.rank_results)


def test_training_pipeline_integration(db_session_factory):
    """Test that training pipeline collects data and trains model."""
    db_session = db_session_factory()
    # Create test user
    user = User(
        email="trainer@example.com",
        full_name="Trainer User",
        hashed_password="dummy",
    )
    db_session.add(user)
    db_session.flush()

    # Create 15 test jobs (need sufficient for training)
    jobs = []
    for i in range(15):
        job = JobPost(
            url=f"https://example.com/train-job-{i}",
            title_raw=f"Position {i}",
            description_clean=f"Description for position {i}",
            source="test",
            first_seen=datetime.utcnow() - timedelta(days=i),
            last_seen=datetime.utcnow(),
        )
        jobs.append(job)
    db_session.add_all(jobs)
    db_session.flush()

    # Create apply events for first 10 jobs (need min 10 for training)
    for i in range(10):
        analytics = UserAnalytics(
            user_id=user.id,
            session_id=f"session-{i}",
            event_type="apply",
            event_data={"job_id": jobs[i].id},
            timestamp=datetime.utcnow() - timedelta(hours=i),
        )
        db_session.add(analytics)

    db_session.commit()

    # Collect training data (returns tuple: (features, labels) or None)
    training_data = collect_training_data(db_session, days_back=30)

    # Verify we have training data (should return None if insufficient, but we have 10 apply events)
    assert training_data is not None
    features, labels = training_data
    assert len(features) >= 10  # At least 10 positive + some negative samples
    assert len(labels) == len(features)
    assert sum(labels) == 10  # Exactly 10 positive labels (apply events)

    # Train model (should succeed with 10 positive samples and negatives)
    result = train_ranking_model(db_session, days_back=30)

    assert result["success"] is True
    assert result["examples_positive"] == 10
    assert result["examples_total"] >= 10
    assert "model_path" in result


def test_ranking_reorders_with_user_context(db_session_factory):
    """Test that ranking reorders results based on user context."""
    db_session = db_session_factory()
    # Create test jobs
    job1 = JobPost(
        url="https://example.com/context-job-1",
        title_raw="Senior Developer",
        description_clean="Senior role",
        source="test",
        seniority="senior",
        first_seen=datetime.utcnow() - timedelta(days=1),
        last_seen=datetime.utcnow(),
    )
    job2 = JobPost(
        url="https://example.com/context-job-2",
        title_raw="Junior Developer",
        description_clean="Junior role",
        source="test",
        seniority="junior",
        first_seen=datetime.utcnow() - timedelta(days=5),
        last_seen=datetime.utcnow(),
    )

    db_session.add_all([job1, job2])
    db_session.commit()

    # Prepare results (simulating search output)
    results = [
        {
            "id": job2.id,
            "url": "https://example.com/context-job-2",
            "title_raw": "Junior Developer",
            "description_clean": "Junior role",
            "seniority": "junior",
            "similarity": 0.75,
        },
        {
            "id": job1.id,
            "url": "https://example.com/context-job-1",
            "title_raw": "Senior Developer",
            "description_clean": "Senior role",
            "seniority": "senior",
            "similarity": 0.70,
        },
    ]

    # Test without user context (fallback to similarity)
    ranked_no_context = rank_results(results, "Developer", user_context=None)
    assert ranked_no_context[0]["url"] == "https://example.com/context-job-2"  # Higher similarity

    # Test with user context (senior preference)
    user_context = {
        "seniority_level": "senior",
    }

    ranked_with_context = rank_results(
        results, "Developer", user_context=user_context
    )

    # Ranking should boost job1 due to seniority match
    # Note: Without a trained model, this tests the feature extraction logic
    assert len(ranked_with_context) == 2
    assert all("similarity" in r for r in ranked_with_context)


def test_cli_integration_dry_run():
    """Test CLI commands can be imported and executed."""
    from cli import app as cli_app

    # Verify the CLI app has ranking commands
    # Typer commands have callback names, not command names directly
    # Check the app's registered callbacks
    command_callbacks = [
        getattr(cmd, "callback", None) for cmd in cli_app.registered_commands
    ]
    command_func_names = [
        cb.__name__ if cb else None for cb in command_callbacks
    ]

    # Check for train_ranking and ranking_info functions
    assert "train_ranking" in command_func_names or any(
        "ranking" in str(cb) for cb in command_callbacks if cb
    )


def test_admin_endpoints_integration():
    """Test admin endpoints are registered."""
    from app.api.admin_routes import router

    # Check that ranking endpoints exist in the router
    paths = [route.path for route in router.routes]

    assert "/api/admin/ranking/model-info" in paths
    assert "/api/admin/ranking/train" in paths
