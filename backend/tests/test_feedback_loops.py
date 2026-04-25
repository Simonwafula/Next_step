"""Tests for T-DS-960: feedback loops + outcome learning."""

import types
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.employer_routes import router as employer_router
from app.api.feedback_routes import router as feedback_router
from app.db.database import get_db
from app.db.models import (
    ApplicationFunnelEvent,
    EmployerAccount,
    EmployerCandidateRating,
    EmployerUser,
    JobApplication,
    JobPost,
    Organization,
    RoleSkillBaseline,
    TitleNorm,
    User,
)
from app.services.auth_service import get_current_user
from app.services.feedback import generate_rejection_feedback
from app.services.outcome_intelligence import (
    aggregate_hiring_outcomes,
    aggregate_rating_sentiment,
    aggregate_rejection_patterns,
    get_outcome_summary,
)


# ---------------------------------------------------------------------------
# App factories
# ---------------------------------------------------------------------------


def _employer_app(db_session_factory, user_id: int) -> FastAPI:
    app = FastAPI()
    app.include_router(employer_router)

    def override_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    async def override_user():
        db = db_session_factory()
        try:
            return db.execute(
                select(User).options(joinedload(User.profile)).where(User.id == user_id)
            ).scalar_one()
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return app


def _feedback_app(db_session_factory, user_id: int) -> FastAPI:
    app = FastAPI()
    app.include_router(feedback_router)

    def override_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    async def override_user():
        db = db_session_factory()
        try:
            return db.execute(
                select(User).options(joinedload(User.profile)).where(User.id == user_id)
            ).scalar_one()
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def org(db_session_factory):
    db = db_session_factory()
    obj = Organization(name="FeedbackCorp", verified=True)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    oid = obj.id
    db.close()
    return types.SimpleNamespace(id=oid)


@pytest.fixture()
def employer_user(db_session_factory, org):
    db = db_session_factory()
    user = User(
        uuid="fb-employer-001",
        email="fb.employer@test.com",
        hashed_password="x",
        full_name="FB Employer",
        subscription_tier="enterprise",
        subscription_expires=datetime(2099, 1, 1),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    uid = user.id

    account = EmployerAccount(org_id=org.id, plan="growth", is_verified=True)
    db.add(account)
    db.commit()
    db.refresh(account)
    aid = account.id

    eu = EmployerUser(employer_account_id=aid, user_id=uid, role="admin")
    db.add(eu)
    db.commit()
    db.close()
    return types.SimpleNamespace(id=uid, employer_account_id=aid)


@pytest.fixture()
def candidate_user(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="fb-candidate-001",
        email="fb.candidate@test.com",
        hashed_password="x",
        full_name="FB Candidate",
        subscription_tier="professional",
        subscription_expires=datetime(2099, 1, 1),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    uid = user.id
    db.close()
    return types.SimpleNamespace(id=uid)


@pytest.fixture()
def job(db_session_factory, org):
    db = db_session_factory()
    tn = TitleNorm(
        family="software_engineering", canonical_title="Software Engineer", aliases={}
    )
    db.add(tn)
    db.commit()
    db.refresh(tn)
    tn_id = tn.id

    jp = JobPost(
        source="test",
        url="https://example.com/jobs/se-001",
        org_id=org.id,
        title_raw="Software Engineer",
        title_norm_id=tn_id,
        is_active=True,
    )
    db.add(jp)
    db.commit()
    db.refresh(jp)
    jid = jp.id
    db.close()
    return types.SimpleNamespace(id=jid)


@pytest.fixture()
def application(db_session_factory, candidate_user, job):
    db = db_session_factory()
    app_obj = JobApplication(
        user_id=candidate_user.id,
        job_post_id=job.id,
        status="applied",
    )
    db.add(app_obj)
    db.commit()
    db.refresh(app_obj)
    aid = app_obj.id
    db.close()
    return types.SimpleNamespace(id=aid)


# ---------------------------------------------------------------------------
# T-DS-961: Employer rating tests
# ---------------------------------------------------------------------------


class TestEmployerRating:
    def test_submit_rating_success(
        self, db_session_factory, employer_user, candidate_user, job
    ):
        app = _employer_app(db_session_factory, employer_user.id)
        client = TestClient(app)
        resp = client.post(
            "/api/employer/ratings",
            json={
                "candidate_user_id": candidate_user.id,
                "job_post_id": job.id,
                "sentiment": "yes",
                "reason": "strong_technical_fit",
                "stage_at_rating": "shortlisted",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["sentiment"] == "yes"
        assert data["reason"] == "strong_technical_fit"

    def test_invalid_sentiment_rejected(
        self, db_session_factory, employer_user, candidate_user, job
    ):
        app = _employer_app(db_session_factory, employer_user.id)
        client = TestClient(app)
        resp = client.post(
            "/api/employer/ratings",
            json={
                "candidate_user_id": candidate_user.id,
                "job_post_id": job.id,
                "sentiment": "thumbs_up",
            },
        )
        assert resp.status_code == 422

    def test_list_ratings(self, db_session_factory, employer_user, candidate_user, job):
        db = db_session_factory()
        rating = EmployerCandidateRating(
            employer_account_id=employer_user.employer_account_id,
            rated_by_user_id=employer_user.id,
            candidate_user_id=candidate_user.id,
            job_post_id=job.id,
            sentiment="maybe",
        )
        db.add(rating)
        db.commit()
        db.close()

        app = _employer_app(db_session_factory, employer_user.id)
        client = TestClient(app)
        resp = client.get(f"/api/employer/ratings?job_post_id={job.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["ratings"]) >= 1
        assert data["ratings"][0]["sentiment"] == "maybe"


# ---------------------------------------------------------------------------
# T-DS-962: Rejection feedback tests
# ---------------------------------------------------------------------------


class TestRejectionFeedback:
    def test_no_rejection_event_returns_not_found(
        self, db_session_factory, application
    ):
        db = db_session_factory()
        result = generate_rejection_feedback(application.id, db)
        db.close()
        assert result["found"] is False

    def test_rejection_event_produces_feedback(
        self, db_session_factory, application, candidate_user, job
    ):
        db = db_session_factory()
        event = ApplicationFunnelEvent(
            application_id=application.id,
            user_id=candidate_user.id,
            job_post_id=job.id,
            stage="rejected",
            actor="employer",
            reason="skills_mismatch",
            details="Python and SQL experience required.",
        )
        db.add(event)
        db.commit()

        result = generate_rejection_feedback(application.id, db)
        db.close()

        assert result["found"] is True
        assert result["reason"] == "skills_mismatch"
        assert len(result["suggestions"]) > 0
        assert "Python" in result["message"] or "skill" in result["message"].lower()

    def test_feedback_endpoint_ownership(
        self, db_session_factory, candidate_user, employer_user, application
    ):
        # employer_user should not see candidate's feedback
        app = _feedback_app(db_session_factory, employer_user.id)
        client = TestClient(app)
        resp = client.get(f"/api/users/applications/{application.id}/feedback")
        assert resp.status_code == 403

    def test_feedback_endpoint_owner_can_access(
        self, db_session_factory, candidate_user, application
    ):
        app = _feedback_app(db_session_factory, candidate_user.id)
        client = TestClient(app)
        resp = client.get(f"/api/users/applications/{application.id}/feedback")
        assert resp.status_code == 200

    def test_skills_to_develop_from_baseline(
        self, db_session_factory, application, candidate_user, job
    ):
        db = db_session_factory()
        for skill in ["python", "django", "postgresql"]:
            db.add(
                RoleSkillBaseline(
                    role_family="software_engineering",
                    skill_name=skill,
                    skill_share=0.8,
                    low_confidence=False,
                    sample_job_ids=[],
                    count_total_jobs_used=100,
                )
            )
        event = ApplicationFunnelEvent(
            application_id=application.id,
            user_id=candidate_user.id,
            job_post_id=job.id,
            stage="rejected",
            actor="employer",
            reason="skills_mismatch",
        )
        db.add(event)
        db.commit()

        result = generate_rejection_feedback(application.id, db)
        db.close()
        assert isinstance(result["skills_to_develop"], list)
        assert len(result["skills_to_develop"]) > 0


# ---------------------------------------------------------------------------
# T-DS-964: Outcome intelligence tests
# ---------------------------------------------------------------------------


class TestOutcomeIntelligence:
    def test_empty_db_returns_zeros(self, db_session_factory):
        db = db_session_factory()
        summary = get_outcome_summary(db)
        db.close()
        assert summary["totals"]["hired"] == 0
        assert summary["totals"]["rejected"] == 0
        assert summary["top_rejection_reasons"] == []

    def test_rejection_patterns_aggregated(
        self, db_session_factory, application, candidate_user, job
    ):
        db = db_session_factory()
        for reason in ["skills_mismatch", "skills_mismatch", "experience_insufficient"]:
            db.add(
                ApplicationFunnelEvent(
                    application_id=application.id,
                    user_id=candidate_user.id,
                    job_post_id=job.id,
                    stage="rejected",
                    actor="employer",
                    reason=reason,
                )
            )
        db.commit()

        patterns = aggregate_rejection_patterns(db)
        db.close()
        # At least one role family has data
        assert len(patterns) > 0
        all_counts = sum(sum(v.values()) for v in patterns.values())
        assert all_counts >= 3

    def test_hiring_outcomes_counted(
        self, db_session_factory, application, candidate_user, job
    ):
        db = db_session_factory()
        db.add(
            ApplicationFunnelEvent(
                application_id=application.id,
                user_id=candidate_user.id,
                job_post_id=job.id,
                stage="hired",
                actor="employer",
            )
        )
        db.commit()

        outcomes = aggregate_hiring_outcomes(db)
        db.close()
        total_hired = sum(v.get("hired", 0) for v in outcomes.values())
        assert total_hired >= 1

    def test_rating_sentiment_counted(
        self, db_session_factory, employer_user, candidate_user, job
    ):
        db = db_session_factory()
        db.add(
            EmployerCandidateRating(
                employer_account_id=employer_user.employer_account_id,
                rated_by_user_id=employer_user.id,
                candidate_user_id=candidate_user.id,
                job_post_id=job.id,
                sentiment="strong_yes",
            )
        )
        db.commit()

        sentiment = aggregate_rating_sentiment(db)
        db.close()
        total_strong_yes = sum(v.get("strong_yes", 0) for v in sentiment.values())
        assert total_strong_yes >= 1
