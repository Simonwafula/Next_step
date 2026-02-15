from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import api_router
from app.db.database import get_db
from app.db.models import (
    RoleDemandSnapshot,
    RoleEducationBaseline,
    RoleExperienceBaseline,
    RoleSkillBaseline,
    TitleNorm,
)


def _create_test_app(db_session_factory):
    app = FastAPI()
    app.include_router(api_router, prefix="/api")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


def _seed_guided_data(db_session_factory):
    db = db_session_factory()
    now = datetime.utcnow()

    db.add_all(
        [
            TitleNorm(
                family="data_analytics",
                canonical_title="Data Analyst",
                aliases=["BI Analyst"],
            ),
            TitleNorm(
                family="data_analytics",
                canonical_title="Business Intelligence Analyst",
                aliases=["BI"],
            ),
            TitleNorm(
                family="software_engineering",
                canonical_title="Software Engineer",
                aliases=["Backend Engineer"],
            ),
        ]
    )

    db.add_all(
        [
            RoleSkillBaseline(
                role_family="data_analytics",
                skill_name="SQL",
                skill_share=0.8,
                sample_job_ids=[101, 102],
                count_total_jobs_used=25,
                updated_at=now,
                low_confidence=False,
            ),
            RoleSkillBaseline(
                role_family="data_analytics",
                skill_name="Python",
                skill_share=0.6,
                sample_job_ids=[103],
                count_total_jobs_used=25,
                updated_at=now,
                low_confidence=False,
            ),
            RoleSkillBaseline(
                role_family="software_engineering",
                skill_name="Python",
                skill_share=0.7,
                sample_job_ids=[201],
                count_total_jobs_used=6,
                updated_at=now,
                low_confidence=True,
            ),
        ]
    )

    db.add_all(
        [
            RoleEducationBaseline(
                role_family="data_analytics",
                education_level="Bachelor's",
                education_share=0.7,
                sample_job_ids=[101],
                count_total_jobs_used=25,
                updated_at=now,
                low_confidence=False,
            ),
            RoleEducationBaseline(
                role_family="software_engineering",
                education_level="Bachelor's",
                education_share=0.6,
                sample_job_ids=[201],
                count_total_jobs_used=6,
                updated_at=now,
                low_confidence=True,
            ),
        ]
    )

    db.add_all(
        [
            RoleExperienceBaseline(
                role_family="data_analytics",
                experience_band="0-2 years",
                experience_share=0.5,
                sample_job_ids=[101],
                count_total_jobs_used=25,
                updated_at=now,
                low_confidence=False,
            ),
            RoleExperienceBaseline(
                role_family="software_engineering",
                experience_band="3-5 years",
                experience_share=0.6,
                sample_job_ids=[201],
                count_total_jobs_used=6,
                updated_at=now,
                low_confidence=True,
            ),
        ]
    )

    db.add_all(
        [
            RoleDemandSnapshot(
                role_family="data_analytics",
                demand_count=12,
                sample_job_ids=[102, 101],
                count_total_jobs_used=25,
                updated_at=now,
                low_confidence=False,
            ),
            RoleDemandSnapshot(
                role_family="software_engineering",
                demand_count=8,
                sample_job_ids=[201],
                count_total_jobs_used=6,
                updated_at=now - timedelta(hours=1),
                low_confidence=True,
            ),
        ]
    )

    db.commit()
    db.close()


def test_guided_explore_returns_empty_message_when_baselines_missing(
    db_session_factory,
):
    app = _create_test_app(db_session_factory)

    with TestClient(app) as client:
        response = client.get("/api/guided/explore", params={"q": "data"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["guided_results"] == []
    assert "Insights not yet available" in payload["message"]


def test_guided_explore_returns_career_cards_with_evidence(
    db_session_factory,
):
    _seed_guided_data(db_session_factory)
    app = _create_test_app(db_session_factory)

    with TestClient(app) as client:
        response = client.get("/api/guided/explore", params={"q": "data"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["guided_results"]

    card = payload["guided_results"][0]
    assert card["role_family"] == "data_analytics"
    assert card["canonical_titles"]
    assert card["top_skills"]
    assert card["education_distribution"]
    assert card["experience_distribution"]
    assert card["demand"]["count_ads"] == 12
    assert card["sample_job_ids"]
    assert "salary" not in card
    assert card["low_confidence"] is False
