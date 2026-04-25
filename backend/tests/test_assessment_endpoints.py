from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.routes import api_router
from app.db.database import get_db
from app.db.models import (
    User,
    RoleSkillBaseline,
    Skill,
)
from app.services.auth_service import get_current_user


def _create_test_app(db_session_factory, current_user_id: int) -> FastAPI:
    app = FastAPI()
    app.include_router(api_router, prefix="/api")

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
        uuid="assess-pro-user",
        email="assess.pro@example.com",
        hashed_password="not-used",
        full_name="Assess Pro",
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


@pytest.fixture()
def seeded_role_family(db_session_factory):
    """Seed RoleSkillBaseline + Skill rows for 'data analyst'."""
    db = db_session_factory()
    for skill_name, share in [
        ("SQL", 0.85),
        ("Python", 0.72),
        ("Excel", 0.68),
        ("Power BI", 0.55),
        ("Reporting", 0.50),
    ]:
        db.add(
            RoleSkillBaseline(
                role_family="data analyst",
                skill_name=skill_name,
                skill_share=share,
                low_confidence=False,
                count_total_jobs_used=50,
            )
        )
        db.add(Skill(name=skill_name, aliases={}))
    db.commit()
    db.close()


def test_seed_questions_creates_question_bank(
    db_session_factory, professional_user, seeded_role_family
):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        response = client.post(
            "/api/admin/assessment/seed-questions?role_family=data+analyst"
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["questions_created"] > 0
    assert payload["role_family"] == "data analyst"


def test_start_assessment_returns_questions(
    db_session_factory, professional_user, seeded_role_family
):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        response = client.post(
            "/api/assessment/start",
            json={"role_family": "data analyst"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["session_id"] > 0
    assert payload["question_count"] > 0
    assert isinstance(payload["questions"], list)
    first_q = payload["questions"][0]
    assert "question_text" in first_q
    assert len(first_q["options"]) == 4


def test_submit_answer_records_correctness(
    db_session_factory, professional_user, seeded_role_family
):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        session = client.post(
            "/api/assessment/start", json={"role_family": "data analyst"}
        ).json()
        session_id = session["session_id"]
        first_q = session["questions"][0]

        response = client.post(
            f"/api/assessment/{session_id}/answer",
            json={"question_id": first_q["id"], "selected_index": 0},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "is_correct" in payload
    assert payload["question_id"] == first_q["id"]


def test_complete_assessment_returns_score_and_level(
    db_session_factory, professional_user, seeded_role_family
):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        session = client.post(
            "/api/assessment/start", json={"role_family": "data analyst"}
        ).json()
        session_id = session["session_id"]

        # Answer all questions correctly (index 0 is always correct in seeded data)
        for q in session["questions"]:
            client.post(
                f"/api/assessment/{session_id}/answer",
                json={"question_id": q["id"], "selected_index": 0},
            )

        response = client.post(f"/api/assessment/{session_id}/complete")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["score"] == 1.0
    assert payload["level"] == "advanced"
    assert payload["is_certified"] is True
    assert "percentile" in payload


def test_verification_summary_reflects_completed_assessment(
    db_session_factory, professional_user, seeded_role_family
):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        # Complete an assessment first
        session = client.post(
            "/api/assessment/start", json={"role_family": "data analyst"}
        ).json()
        session_id = session["session_id"]
        for q in session["questions"]:
            client.post(
                f"/api/assessment/{session_id}/answer",
                json={"question_id": q["id"], "selected_index": 0},
            )
        client.post(f"/api/assessment/{session_id}/complete")

        response = client.get(f"/api/candidates/{professional_user}/verification")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["user_id"] == professional_user
    assert len(payload["assessments"]) == 1
    assert payload["assessments"][0]["role_family"] == "data analyst"
    assert payload["has_certified_skills"] is True


def test_verification_qa_reports_readiness(
    db_session_factory, professional_user, seeded_role_family
):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        # Seed first, then check QA
        client.post("/api/admin/assessment/seed-questions?role_family=data+analyst")
        response = client.get(
            "/api/admin/assessment/verification-qa?role_family=data+analyst"
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["role_family"] == "data analyst"
    assert "ready_for_launch" in payload
    assert "baseline" in payload
    assert "question_bank" in payload


def test_unknown_role_family_returns_error(db_session_factory, professional_user):
    app = _create_test_app(db_session_factory, professional_user)

    with TestClient(app) as client:
        response = client.post(
            "/api/assessment/start",
            json={"role_family": "nonexistent-role-xyz"},
        )

    assert response.status_code == 422
