from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import api_router
from app.db.database import get_db
from app.db.models import (
    JobPost,
    RoleDemandSnapshot,
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


def _seed_advance_data(db_session_factory):
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
                family="product_management",
                canonical_title="Product Manager",
                aliases=["PM"],
            ),
            TitleNorm(
                family="cloud_engineering",
                canonical_title="Cloud Engineer",
                aliases=["Cloud DevOps"],
            ),
        ]
    )
    db.flush()

    db.add_all(
        [
            RoleSkillBaseline(
                role_family="product_management",
                skill_name="SQL",
                skill_share=0.7,
                sample_job_ids=[11],
                count_total_jobs_used=30,
                low_confidence=False,
                updated_at=now,
            ),
            RoleSkillBaseline(
                role_family="product_management",
                skill_name="Roadmapping",
                skill_share=0.6,
                sample_job_ids=[12],
                count_total_jobs_used=30,
                low_confidence=False,
                updated_at=now,
            ),
            RoleSkillBaseline(
                role_family="product_management",
                skill_name="Stakeholder Management",
                skill_share=0.6,
                sample_job_ids=[13],
                count_total_jobs_used=30,
                low_confidence=False,
                updated_at=now,
            ),
        ]
    )

    for index, skill_name in enumerate(
        [
            "AWS",
            "Terraform",
            "Kubernetes",
            "Linux",
            "Python",
            "SQL",
            "Networking",
            "Docker",
            "CI/CD",
            "Observability",
        ]
    ):
        db.add(
            RoleSkillBaseline(
                role_family="cloud_engineering",
                skill_name=skill_name,
                skill_share=0.7,
                sample_job_ids=[30 + index],
                count_total_jobs_used=22,
                low_confidence=False,
                updated_at=now,
            )
        )

    db.add_all(
        [
            RoleDemandSnapshot(
                role_family="product_management",
                demand_count=12,
                sample_job_ids=[11, 12],
                count_total_jobs_used=30,
                low_confidence=False,
                updated_at=now,
            ),
            RoleDemandSnapshot(
                role_family="cloud_engineering",
                demand_count=9,
                sample_job_ids=[30, 31],
                count_total_jobs_used=22,
                low_confidence=False,
                updated_at=now,
            ),
        ]
    )

    pm_title = db.execute(
        db.query(TitleNorm).filter(TitleNorm.family == "product_management").statement
    ).scalar_one()
    cloud_title = db.execute(
        db.query(TitleNorm).filter(TitleNorm.family == "cloud_engineering").statement
    ).scalar_one()

    db.add_all(
        [
            JobPost(
                source="test",
                url="https://example.com/pm-1",
                title_raw="Associate Product Manager",
                title_norm_id=pm_title.id,
                seniority="mid",
                is_active=True,
                first_seen=now,
                last_seen=now,
            ),
            JobPost(
                source="test",
                url="https://example.com/cloud-1",
                title_raw="Cloud Engineer",
                title_norm_id=cloud_title.id,
                seniority="senior",
                is_active=True,
                first_seen=now,
                last_seen=now,
            ),
        ]
    )

    db.commit()
    db.close()


def test_guided_advance_returns_transition_cards_with_skill_gaps(
    db_session_factory,
):
    _seed_advance_data(db_session_factory)
    app = _create_test_app(db_session_factory)

    with TestClient(app) as client:
        response = client.get(
            "/api/guided/advance",
            params={
                "current_role": "Data Analyst",
                "skills": "Python,SQL",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["guided_results"]

    first = payload["guided_results"][0]
    assert {
        "target_role",
        "current_role",
        "difficulty_proxy",
        "skill_gap",
        "shared_skills",
        "target_jobs",
        "sample_job_ids",
    }.issubset(first.keys())
    assert "salary" not in first


def test_guided_advance_sorts_by_feasibility_and_sets_difficulty(
    db_session_factory,
):
    _seed_advance_data(db_session_factory)
    app = _create_test_app(db_session_factory)

    with TestClient(app) as client:
        response = client.get(
            "/api/guided/advance",
            params={
                "current_role": "Data Analyst",
                "skills": "Python,SQL",
            },
        )

    assert response.status_code == 200
    results = response.json()["guided_results"]
    assert len(results) >= 2

    assert len(results[0]["skill_gap"]) <= len(results[1]["skill_gap"])
    assert results[0]["difficulty_proxy"] in {"Low", "Medium", "High"}
    assert any(item["difficulty_proxy"] == "High" for item in results)
