from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.user_routes import router as user_router
from app.db.database import get_db
from app.db.models import User, UserProfile
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
def professional_user_with_profile(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="scan-pro-user",
        email="scan.pro@example.com",
        hashed_password="not-used",
        full_name="Pro User",
        subscription_tier="professional",
        subscription_expires=datetime(2099, 1, 1),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    profile = UserProfile(
        user_id=user.id,
        current_role="Data Analyst",
        experience_level="mid",
        skills={"python": 0.9, "excel": 0.8},
        preferred_locations=["Nairobi"],
    )
    db.add(profile)
    db.commit()
    user_id = user.id
    db.close()
    return user_id


@pytest.fixture()
def basic_user_with_profile(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="scan-basic-user",
        email="scan.basic@example.com",
        hashed_password="not-used",
        full_name="Basic User",
        subscription_tier="basic",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    profile = UserProfile(
        user_id=user.id,
        current_role="Office Assistant",
        experience_level="junior",
        skills={"excel": 0.7},
        preferred_locations=["Nairobi"],
    )
    db.add(profile)
    db.commit()
    user_id = user.id
    db.close()
    return user_id


@pytest.fixture()
def professional_user_without_profile(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="scan-no-profile-user",
        email="scan.no.profile@example.com",
        hashed_password="not-used",
        full_name="No Profile User",
        subscription_tier="professional",
        subscription_expires=datetime(2099, 1, 1),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    return user_id


def test_skills_gap_scan_returns_gap_analysis(
    db_session_factory,
    professional_user_with_profile,
):
    app = _create_test_app(db_session_factory, professional_user_with_profile)

    with TestClient(app) as client:
        response = client.post(
            "/api/users/skills-gap-scan",
            json={"target_role": "Data Scientist"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["target_role"] == "Data Scientist"
    assert isinstance(payload["missing_skills"], list)
    assert isinstance(payload["recommended_projects"], list)
    assert payload["match_percentage"] >= 0
    assert payload["match_percentage"] <= 100


def test_skills_gap_scan_requires_professional_subscription(
    db_session_factory,
    basic_user_with_profile,
):
    app = _create_test_app(db_session_factory, basic_user_with_profile)

    with TestClient(app) as client:
        response = client.post(
            "/api/users/skills-gap-scan",
            json={"target_role": "Data Scientist"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "This feature requires professional subscription"


def test_skills_gap_scan_requires_completed_profile(
    db_session_factory,
    professional_user_without_profile,
):
    app = _create_test_app(db_session_factory, professional_user_without_profile)

    with TestClient(app) as client:
        response = client.post(
            "/api/users/skills-gap-scan",
            json={"target_role": "Data Scientist"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Please complete your profile first"
