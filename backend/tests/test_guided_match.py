from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import api_router
from app.db.database import get_db
from app.db.models import (
    JobPost,
    RoleDemandSnapshot,
    RoleEducationBaseline,
    RoleSkillBaseline,
    TitleNorm,
)
from app.services.auth_service import get_current_user_optional


def _create_test_app(db_session_factory, current_user=None):
    app = FastAPI()
    app.include_router(api_router, prefix="/api")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    async def override_current_user_optional():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[
        get_current_user_optional
    ] = override_current_user_optional
    return app


def _seed_match_data(db_session_factory):
    db = db_session_factory()
    now = datetime.utcnow()

    data_family = TitleNorm(
        family="data_analytics",
        canonical_title="Data Analyst",
        aliases=["BI Analyst"],
    )
    design_family = TitleNorm(
        family="product_design",
        canonical_title="Product Designer",
        aliases=["UI Designer"],
    )
    db.add_all([data_family, design_family])
    db.flush()

    db.add_all(
        [
            RoleSkillBaseline(
                role_family="data_analytics",
                skill_name="Python",
                skill_share=0.8,
                sample_job_ids=[1],
                count_total_jobs_used=20,
                low_confidence=False,
                updated_at=now,
            ),
            RoleSkillBaseline(
                role_family="data_analytics",
                skill_name="SQL",
                skill_share=0.7,
                sample_job_ids=[2],
                count_total_jobs_used=20,
                low_confidence=False,
                updated_at=now,
            ),
            RoleSkillBaseline(
                role_family="data_analytics",
                skill_name="Excel",
                skill_share=0.6,
                sample_job_ids=[3],
                count_total_jobs_used=20,
                low_confidence=False,
                updated_at=now,
            ),
            RoleSkillBaseline(
                role_family="product_design",
                skill_name="Figma",
                skill_share=0.9,
                sample_job_ids=[4],
                count_total_jobs_used=12,
                low_confidence=False,
                updated_at=now,
            ),
            RoleSkillBaseline(
                role_family="product_design",
                skill_name="Sketch",
                skill_share=0.7,
                sample_job_ids=[5],
                count_total_jobs_used=12,
                low_confidence=False,
                updated_at=now,
            ),
        ]
    )

    db.add_all(
        [
            RoleEducationBaseline(
                role_family="data_analytics",
                education_level="Master's",
                education_share=0.6,
                sample_job_ids=[1],
                count_total_jobs_used=20,
                low_confidence=False,
                updated_at=now,
            ),
            RoleEducationBaseline(
                role_family="product_design",
                education_level="Bachelor's",
                education_share=0.7,
                sample_job_ids=[4],
                count_total_jobs_used=12,
                low_confidence=False,
                updated_at=now,
            ),
        ]
    )

    db.add_all(
        [
            RoleDemandSnapshot(
                role_family="data_analytics",
                demand_count=10,
                sample_job_ids=[1, 2],
                count_total_jobs_used=20,
                low_confidence=False,
                updated_at=now,
            ),
            RoleDemandSnapshot(
                role_family="product_design",
                demand_count=8,
                sample_job_ids=[4, 5],
                count_total_jobs_used=12,
                low_confidence=False,
                updated_at=now,
            ),
        ]
    )

    db.add_all(
        [
            JobPost(
                source="test",
                url="https://example.com/data-entry",
                title_raw="Junior Data Analyst",
                title_norm_id=data_family.id,
                seniority="entry",
                is_active=True,
                first_seen=now,
                last_seen=now,
            ),
            JobPost(
                source="test",
                url="https://example.com/data-mid",
                title_raw="Data Analyst",
                title_norm_id=data_family.id,
                seniority="mid",
                is_active=True,
                first_seen=now,
                last_seen=now,
            ),
            JobPost(
                source="test",
                url="https://example.com/design-junior",
                title_raw="Junior Product Designer",
                title_norm_id=design_family.id,
                seniority="junior",
                is_active=True,
                first_seen=now,
                last_seen=now,
            ),
        ]
    )

    db.commit()
    db.close()


def test_guided_match_ranks_roles_and_returns_gaps_and_starter_jobs(
    db_session_factory,
):
    _seed_match_data(db_session_factory)
    app = _create_test_app(db_session_factory)

    with TestClient(app) as client:
        response = client.get(
            "/api/guided/match",
            params={
                "skills": "Python,SQL",
                "education": "Bachelor's",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["guided_results"]

    first = payload["guided_results"][0]
    assert first["role_family"] == "data_analytics"
    assert len(payload["guided_results"]) >= 2
    assert first["match_score"] > payload["guided_results"][1]["match_score"]
    assert "Excel" in first["missing_skills"]
    assert first["starter_jobs"]
    assert all(
        job["seniority"] in {"entry", "junior"}
        for job in first["starter_jobs"]
    )
    assert "salary" not in first


def test_guided_match_uses_authenticated_profile_skills_dict(
    db_session_factory,
):
    _seed_match_data(db_session_factory)

    class ProfileStub:
        skills = {"Python": 0.9}
        education = "Bachelor's"

    class UserStub:
        profile = ProfileStub()

    app = _create_test_app(db_session_factory, current_user=UserStub())

    with TestClient(app) as client:
        response = client.get(
            "/api/guided/match",
            params={"q": "data"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["guided_results"]

    first = payload["guided_results"][0]
    assert "Python" in first["matching_skills"]
    assert "SQL" in first["missing_skills"]
