from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.user_routes import router as user_router
from app.db.database import get_db
from app.db.models import JobPost, Location, User, UserProfile
from app.services.auth_service import get_current_user


def _create_test_app(db_session_factory, current_user_id: int) -> FastAPI:
    app = FastAPI()
    app.include_router(user_router, prefix="/api/users")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    async def override_get_current_user():
        db = db_session_factory()
        try:
            return db.execute(
                select(User)
                .options(joinedload(User.profile))
                .where(User.id == current_user_id)
            ).scalar_one()
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return app


@pytest.fixture()
def user_with_profile(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="match-user-uuid",
        email="match.user@example.com",
        hashed_password="not-used",
        full_name="Match User",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    profile = UserProfile(
        user_id=user.id,
        current_role="Data Analyst",
        experience_level="mid",
        skills={"python": 1.0},
        preferred_locations=["Nairobi"],
    )
    db.add(profile)
    db.commit()

    user_id = user.id
    db.close()
    return user_id


@pytest.fixture()
def user_without_profile(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="no-profile-user-uuid",
        email="no.profile@example.com",
        hashed_password="not-used",
        full_name="No Profile User",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    return user_id


@pytest.fixture()
def seeded_job(db_session_factory):
    db = db_session_factory()
    location = Location(city="Nairobi", region="Nairobi", country="Kenya")
    db.add(location)
    db.flush()

    job = JobPost(
        source="test",
        url="https://example.com/jobs/1",
        source_url="https://example.com/jobs/1",
        title_raw="Data Analyst",
        location_id=location.id,
        description_raw="Need strong Python and SQL skills for analytics.",
        requirements_raw="Python, SQL, and dashboarding experience",
        first_seen=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    job_id = job.id
    db.close()
    return job_id


def test_job_match_returns_match_percentage_and_skill_gaps(
    db_session_factory, user_with_profile, seeded_job
):
    app = _create_test_app(db_session_factory, user_with_profile)

    with TestClient(app) as client:
        response = client.get(f"/api/users/job-match/{seeded_job}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["job_id"] == seeded_job
    assert 0 <= payload["match_percentage"] <= 100
    assert "python" in [s.lower() for s in payload["matching_skills"]]
    assert "sql" in [s.lower() for s in payload["missing_skills"]]


def test_job_match_returns_404_when_job_not_found(
    db_session_factory, user_with_profile
):
    app = _create_test_app(db_session_factory, user_with_profile)

    with TestClient(app) as client:
        response = client.get("/api/users/job-match/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_job_match_requires_user_profile(
    db_session_factory, user_without_profile, seeded_job
):
    app = _create_test_app(db_session_factory, user_without_profile)

    with TestClient(app) as client:
        response = client.get(f"/api/users/job-match/{seeded_job}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Please complete your profile first"
