"""Tests for user activity feed and momentum chart endpoints."""

import pytest
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.user_routes import router as user_router
from app.db.database import get_db
from app.db.models import JobApplication, JobPost, SavedJob, SearchHistory, User
from app.services.auth_service import get_current_user


@pytest.fixture()
def regular_user(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="activity-user-uuid",
        email="user@test.local",
        hashed_password="not-used",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        subscription_tier="basic",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture()
def app(db_session_factory, regular_user):
    application = FastAPI()
    application.include_router(user_router, prefix="/api/users")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    async def override_get_current_user():
        return regular_user

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_current_user] = override_get_current_user
    return application


@pytest.fixture()
def seed_activity(db_session_factory, regular_user):
    db = db_session_factory()

    job = JobPost(
        title_raw="Demo Job",
        source="test",
        url="https://test.local/demo",
    )
    db.add(job)
    db.flush()

    search = SearchHistory(
        user_id=regular_user.id,
        query="python developer",
        results_count=5,
        searched_at=datetime.utcnow() - timedelta(hours=1),
    )
    save = SavedJob(
        user_id=regular_user.id,
        job_post_id=job.id,
        saved_at=datetime.utcnow() - timedelta(hours=2),
    )
    application = JobApplication(
        user_id=regular_user.id,
        job_post_id=job.id,
        applied_at=datetime.utcnow() - timedelta(hours=3),
    )
    db.add_all([search, save, application])
    db.commit()
    db.close()


def test_activity_feed_empty(app):
    with TestClient(app) as client:
        resp = client.get("/api/users/activity")
        assert resp.status_code == 200
        assert resp.json()["activities"] == []


def test_activity_feed_with_data(app, seed_activity):
    with TestClient(app) as client:
        resp = client.get("/api/users/activity")
        assert resp.status_code == 200
        activities = resp.json()["activities"]
        assert len(activities) == 3
        types = {a["type"] for a in activities}
        assert types == {"search", "save", "application"}
        # Should be sorted by time descending
        times = [a["time"] for a in activities]
        assert times == sorted(times, reverse=True)


def test_momentum_empty(app):
    with TestClient(app) as client:
        resp = client.get("/api/users/momentum")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["days"]) == 7
        assert all(d["count"] == 0 for d in data["days"])


def test_momentum_with_data(app, seed_activity):
    with TestClient(app) as client:
        resp = client.get("/api/users/momentum")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["days"]) == 7
        # Today should have some activity
        total = sum(d["count"] for d in data["days"])
        assert total == 3
