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
def professional_user(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="evidence-pro-user",
        email="evidence.pro@example.com",
        hashed_password="not-used",
        full_name="Evidence Pro",
        subscription_tier="professional",
        subscription_expires=datetime(2099, 1, 1),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    db.add(
        UserProfile(
            user_id=user.id,
            skills={"python": 0.9},
            preferred_locations=["Nairobi"],
            cv_data={
                "projects": [
                    {
                        "title": "Sales Dashboard",
                        "description": "Built a Power BI dashboard for regional sales.",
                        "skills": ["Power BI", "SQL"],
                        "start_date": "2025-01",
                        "end_date": "2025-03",
                    }
                ],
                "certifications": [
                    {
                        "title": "Google Data Analytics",
                        "url": "https://example.com/cert",
                    }
                ],
            },
        )
    )
    db.commit()
    user_id = user.id
    db.close()
    return user_id


def test_submit_evidence_creates_item(db_session_factory, professional_user):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        response = client.post(
            "/api/users/evidence",
            json={
                "evidence_type": "project",
                "title": "Churn Prediction Model",
                "description": "End-to-end ML model for telecom churn.",
                "skills_demonstrated": ["python", "scikit-learn"],
                "start_date": "2024-06",
            },
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["evidence_type"] == "project"
    assert payload["title"] == "Churn Prediction Model"
    assert payload["source"] == "self_reported"
    assert payload["id"] > 0


def test_submit_evidence_rejects_invalid_type(db_session_factory, professional_user):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        response = client.post(
            "/api/users/evidence",
            json={"evidence_type": "invalid_type", "title": "Some Thing"},
        )

    assert response.status_code == 422


def test_list_evidence_returns_submitted_items(db_session_factory, professional_user):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        client.post(
            "/api/users/evidence",
            json={"evidence_type": "gig", "title": "Freelance Analytics Gig"},
        )
        response = client.get("/api/users/evidence")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload["evidence"], list)
    titles = [e["title"] for e in payload["evidence"]]
    assert "Freelance Analytics Gig" in titles


def test_ingest_cv_extracts_projects_and_certifications(
    db_session_factory, professional_user
):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        response = client.post("/api/users/evidence/ingest-cv")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["extracted"] == 2  # 1 project + 1 certification

    types = {item["evidence_type"] for item in payload["items"]}
    assert "project" in types
    assert "certification" in types


def test_ingest_cv_is_idempotent(db_session_factory, professional_user):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        first = client.post("/api/users/evidence/ingest-cv").json()
        second = client.post("/api/users/evidence/ingest-cv").json()

    assert first["extracted"] == 2
    assert second["extracted"] == 0  # duplicates skipped


def test_evidence_response_includes_provenance(db_session_factory, professional_user):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        client.post(
            "/api/users/evidence",
            json={"evidence_type": "work_sample", "title": "Quarterly Report"},
        )
        items = client.get("/api/users/evidence").json()["evidence"]

    item = next(i for i in items if i["title"] == "Quarterly Report")
    assert item["provenance"] is not None
    assert item["provenance"]["evidence_source"] == "self_reported"
    assert "confidence" in item["provenance"]
