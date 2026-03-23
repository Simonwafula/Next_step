"""Tests for T-DS-951/952/953/954: employer pre-screening system."""

import types
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.employer_routes import router as employer_router
from app.db.database import get_db
from app.db.models import (
    AssessmentSession,
    CandidateEvidence,
    EmployerAccount,
    EmployerUser,
    JobApplication,
    JobEntities,
    JobPost,
    Organization,
    RoleDemandSnapshot,
    RoleSkillBaseline,
    TitleNorm,
    User,
)
from app.services.auth_service import get_current_user
from app.services.prescreening import (
    build_intelligence_sidecar,
    score_candidate_for_job,
)


# ---------------------------------------------------------------------------
# Test app factory
# ---------------------------------------------------------------------------


def _make_app(db_session_factory, current_user_id: int) -> FastAPI:
    app = FastAPI()
    app.include_router(employer_router)

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


# ---------------------------------------------------------------------------
# Fixtures — return SimpleNamespace with captured integer IDs
# ---------------------------------------------------------------------------


@pytest.fixture()
def org(db_session_factory):
    db = db_session_factory()
    obj = Organization(name="TestCorp Employer", verified=True)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    org_id = obj.id
    db.close()
    return types.SimpleNamespace(id=org_id)


@pytest.fixture()
def employer_user(db_session_factory, org):
    db = db_session_factory()
    user = User(
        uuid="employer-user-001",
        email="employer@testcorp.com",
        hashed_password="x",
        full_name="Employer User",
        subscription_tier="enterprise",
        subscription_expires=datetime(2099, 1, 1),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id

    account = EmployerAccount(org_id=org.id, plan="growth", is_verified=True)
    db.add(account)
    db.commit()
    db.refresh(account)
    account_id = account.id

    eu = EmployerUser(employer_account_id=account_id, user_id=user_id, role="admin")
    db.add(eu)
    db.commit()
    db.close()
    return types.SimpleNamespace(id=user_id, employer_account_id=account_id)


@pytest.fixture()
def candidate_user(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="candidate-user-001",
        email="candidate@example.com",
        hashed_password="x",
        full_name="Candidate User",
        subscription_tier="professional",
        subscription_expires=datetime(2099, 1, 1),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()
    return types.SimpleNamespace(id=user_id)


@pytest.fixture()
def job_with_entities(db_session_factory, org):
    db = db_session_factory()
    tn = TitleNorm(family="data_science", canonical_title="Data Scientist", aliases={})
    db.add(tn)
    db.commit()
    db.refresh(tn)
    tn_id = tn.id

    job = JobPost(
        source="test",
        url="https://example.com/jobs/ds-001",
        org_id=org.id,
        title_raw="Data Scientist",
        title_norm_id=tn_id,
        is_active=True,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id

    entities = JobEntities(
        job_id=job_id,
        entities={},
        skills=["python", "sql", "machine learning"],
        tools=[],
        education={},
        experience={},
    )
    db.add(entities)
    db.commit()
    db.close()
    return types.SimpleNamespace(id=job_id)


# ---------------------------------------------------------------------------
# Unit tests: prescreening service
# ---------------------------------------------------------------------------


class TestScoringService:
    def test_score_returns_required_shape(
        self, db_session_factory, candidate_user, job_with_entities
    ):
        db = db_session_factory()
        result = score_candidate_for_job(candidate_user.id, job_with_entities.id, db)
        db.close()

        assert "overall_score" in result
        assert "score_breakdown" in result
        assert "explanation" in result
        assert 0.0 <= result["overall_score"] <= 1.0
        bd = result["score_breakdown"]
        assert "verified_skill_score" in bd
        assert "evidence_score" in bd
        assert "profile_score" in bd

    def test_score_with_no_evidence_gives_zero_evidence_score(
        self, db_session_factory, candidate_user, job_with_entities
    ):
        db = db_session_factory()
        result = score_candidate_for_job(candidate_user.id, job_with_entities.id, db)
        db.close()
        assert result["score_breakdown"]["evidence_score"] == 0.0

    def test_score_with_matching_evidence_raises_score(
        self, db_session_factory, candidate_user, job_with_entities
    ):
        db = db_session_factory()
        evidence = CandidateEvidence(
            user_id=candidate_user.id,
            evidence_type="project",
            title="DS Project",
            skills_demonstrated=["python", "sql"],
        )
        db.add(evidence)
        db.commit()

        result = score_candidate_for_job(candidate_user.id, job_with_entities.id, db)
        db.close()
        assert result["score_breakdown"]["evidence_score"] > 0.0
        assert "python" in result["explanation"]["matched_skills"]

    def test_verified_assessment_boosts_score(
        self, db_session_factory, candidate_user, job_with_entities
    ):
        db = db_session_factory()
        session = AssessmentSession(
            user_id=candidate_user.id,
            role_family="data_science",
            status="completed",
            score=0.85,
            questions_total=10,
            questions_correct=9,
            question_ids=[],
        )
        db.add(session)
        db.commit()

        result = score_candidate_for_job(candidate_user.id, job_with_entities.id, db)
        db.close()
        assert result["score_breakdown"]["verified_skill_score"] == pytest.approx(0.85, abs=0.01)
        assert result["overall_score"] > 0.4

    def test_score_missing_job_entities_gives_zero(
        self, db_session_factory, candidate_user, org
    ):
        db = db_session_factory()
        job = JobPost(
            source="test",
            url="https://example.com/jobs/no-entities",
            org_id=org.id,
            title_raw="Mystery Role",
            is_active=True,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

        result = score_candidate_for_job(candidate_user.id, job_id, db)
        db.close()
        assert result["overall_score"] == 0.0


class TestIntelligenceSidecar:
    def test_sidecar_no_role_family(self, db_session_factory):
        db = db_session_factory()
        sidecar = build_intelligence_sidecar(None, db)
        db.close()
        assert sidecar["role_family"] is None
        assert sidecar["confidence"] == "low"

    def test_sidecar_with_baseline_data(self, db_session_factory):
        db = db_session_factory()
        for skill in ["python", "sql"]:
            db.add(
                RoleSkillBaseline(
                    role_family="data_science",
                    skill_name=skill,
                    skill_share=0.7 if skill == "python" else 0.5,
                    low_confidence=False,
                    sample_job_ids=[],
                    count_total_jobs_used=50,
                )
            )
        db.add(
            RoleDemandSnapshot(
                role_family="data_science",
                demand_count=120,
                low_confidence=False,
                sample_job_ids=[],
                count_total_jobs_used=50,
            )
        )
        db.commit()

        sidecar = build_intelligence_sidecar("data_science", db)
        db.close()

        assert sidecar["role_family"] == "data_science"
        assert len(sidecar["required_skills"]) == 2
        assert sidecar["demand"]["count"] == 120
        assert sidecar["confidence"] in {"medium", "high"}


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestEmployerAPI:
    def test_score_candidates_no_applications(
        self, db_session_factory, employer_user, job_with_entities
    ):
        app = _make_app(db_session_factory, employer_user.id)
        client = TestClient(app)
        resp = client.get(f"/api/employer/jobs/{job_with_entities.id}/candidates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applicants"] == 0
        assert data["results"] == []
        assert "intelligence_sidecar" in data

    def test_score_candidates_with_applicant(
        self, db_session_factory, employer_user, candidate_user, job_with_entities
    ):
        db = db_session_factory()
        app_obj = JobApplication(
            user_id=candidate_user.id,
            job_post_id=job_with_entities.id,
            status="applied",
        )
        db.add(app_obj)
        db.commit()
        db.close()

        app = _make_app(db_session_factory, employer_user.id)
        client = TestClient(app)
        resp = client.get(f"/api/employer/jobs/{job_with_entities.id}/candidates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applicants"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["rank"] == 1
        assert "overall_score" in data["results"][0]

    def test_create_shortlist(
        self, db_session_factory, employer_user, candidate_user, job_with_entities
    ):
        app = _make_app(db_session_factory, employer_user.id)
        client = TestClient(app)
        resp = client.post(
            f"/api/employer/jobs/{job_with_entities.id}/shortlist",
            json={"name": "DS Final Round", "candidate_user_ids": [candidate_user.id]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "DS Final Round"
        assert data["total_candidates"] == 1
        assert "intelligence_sidecar" in data

    def test_get_shortlist(
        self, db_session_factory, employer_user, candidate_user, job_with_entities
    ):
        app = _make_app(db_session_factory, employer_user.id)
        client = TestClient(app)

        create_resp = client.post(
            f"/api/employer/jobs/{job_with_entities.id}/shortlist",
            json={"name": "Shortlist A", "candidate_user_ids": [candidate_user.id]},
        )
        assert create_resp.status_code == 201
        shortlist_id = create_resp.json()["id"]

        get_resp = client.get(f"/api/employer/shortlists/{shortlist_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == shortlist_id
        assert len(data["entries"]) == 1
        assert data["entries"][0]["rank"] == 1

    def test_list_shortlists(
        self, db_session_factory, employer_user, candidate_user, job_with_entities
    ):
        app = _make_app(db_session_factory, employer_user.id)
        client = TestClient(app)

        client.post(
            f"/api/employer/jobs/{job_with_entities.id}/shortlist",
            json={"name": "List Test", "candidate_user_ids": [candidate_user.id]},
        )

        resp = client.get("/api/employer/shortlists")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["shortlists"]) >= 1

    def test_no_employer_account_returns_403(
        self, db_session_factory, candidate_user, job_with_entities
    ):
        app = _make_app(db_session_factory, candidate_user.id)
        client = TestClient(app)
        resp = client.get(f"/api/employer/jobs/{job_with_entities.id}/candidates")
        assert resp.status_code == 403

    def test_shortlist_not_found_returns_404(self, db_session_factory, employer_user):
        app = _make_app(db_session_factory, employer_user.id)
        client = TestClient(app)
        resp = client.get("/api/employer/shortlists/99999")
        assert resp.status_code == 404
