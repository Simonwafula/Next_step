from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.user_routes import router as user_router
from app.db.database import get_db
from app.db.models import (
    JobAlert,
    JobApplication,
    JobPost,
    JobSkill,
    Location,
    Organization,
    SavedJob,
    Skill,
    User,
    UserProfile,
)
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


def _create_user(db_session_factory, with_profile: bool) -> int:
    db = db_session_factory()
    user = User(
        uuid=f"dashboard-user-{with_profile}",
        email=f"dashboard-{with_profile}@example.com",
        hashed_password="not-used",
        full_name="Dashboard User",
        subscription_tier="professional",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    if with_profile:
        db.add(
            UserProfile(
                user_id=user.id,
                current_role="Data Analyst",
                experience_level="mid",
                skills={"Python": 0.95, "Power BI": 0.8},
                preferred_locations=["Nairobi County"],
                profile_completeness=70.0,
            )
        )

    db.commit()
    user_id = user.id
    db.close()
    return user_id


def test_market_fit_returns_empty_contract_without_profile(db_session_factory):
    user_id = _create_user(db_session_factory, with_profile=False)
    app = _create_test_app(db_session_factory, user_id)

    with TestClient(app) as client:
        response = client.get("/api/users/market-fit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["match_distribution"] == {"strong": 0, "close": 0, "pivot": 0}
    assert payload["missing_skills"] == []
    assert payload["top_counties"] == []
    assert payload["top_industries"] == []
    assert payload["target_roles"] == []
    assert payload["total_jobs_analyzed"] == 0


def test_market_fit_returns_dashboard_data(db_session_factory):
    user_id = _create_user(db_session_factory, with_profile=True)
    app = _create_test_app(db_session_factory, user_id)

    db = db_session_factory()
    now = datetime.utcnow()

    tech_org = Organization(name="Acme Analytics", sector="technology", verified=True)
    finance_org = Organization(name="FinServe", sector="finance", verified=True)
    nairobi = Location(
        country="Kenya",
        region="Nairobi County",
        city="Nairobi",
        raw="Nairobi County, Kenya",
    )
    mombasa = Location(
        country="Kenya",
        region="Mombasa County",
        city="Mombasa",
        raw="Mombasa County, Kenya",
    )
    db.add_all([tech_org, finance_org, nairobi, mombasa])
    db.flush()

    db.add_all(
        [
            JobPost(
                source="test",
                url="https://example.com/jobs/market-1",
                url_hash="market-1",
                title_raw="Data Analyst",
                org_id=tech_org.id,
                location_id=nairobi.id,
                description_raw="Python SQL dashboards analytics reporting",
                first_seen=now - timedelta(days=1),
                is_active=True,
            ),
            JobPost(
                source="test",
                url="https://example.com/jobs/market-2",
                url_hash="market-2",
                title_raw="Business Intelligence Analyst",
                org_id=tech_org.id,
                location_id=nairobi.id,
                description_raw="Excel SQL Power BI stakeholder reporting",
                first_seen=now - timedelta(days=2),
                is_active=True,
            ),
            JobPost(
                source="test",
                url="https://example.com/jobs/market-3",
                url_hash="market-3",
                title_raw="Research Associate",
                org_id=finance_org.id,
                location_id=mombasa.id,
                description_raw="Excel surveys fieldwork data collection",
                first_seen=now - timedelta(days=5),
                is_active=True,
            ),
        ]
    )
    db.flush()

    python_skill = Skill(name="Python")
    sql_skill = Skill(name="SQL")
    excel_skill = Skill(name="Excel")
    db.add_all([python_skill, sql_skill, excel_skill])
    db.flush()

    market_jobs = (
        db.execute(
            select(JobPost).where(
                JobPost.url_hash.in_(["market-1", "market-2", "market-3"])
            )
        )
        .scalars()
        .all()
    )
    market_job_by_hash = {job.url_hash: job for job in market_jobs}
    db.add_all(
        [
            JobSkill(
                job_post_id=market_job_by_hash["market-1"].id,
                skill_id=python_skill.id,
                confidence=0.95,
            ),
            JobSkill(
                job_post_id=market_job_by_hash["market-1"].id,
                skill_id=sql_skill.id,
                confidence=0.9,
            ),
            JobSkill(
                job_post_id=market_job_by_hash["market-2"].id,
                skill_id=excel_skill.id,
                confidence=0.9,
            ),
            JobSkill(
                job_post_id=market_job_by_hash["market-2"].id,
                skill_id=sql_skill.id,
                confidence=0.85,
            ),
            JobSkill(
                job_post_id=market_job_by_hash["market-3"].id,
                skill_id=excel_skill.id,
                confidence=0.85,
            ),
        ]
    )
    db.commit()
    db.close()

    with TestClient(app) as client:
        response = client.get("/api/users/market-fit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["target_roles"] == ["Data Analyst"]
    assert payload["total_jobs_analyzed"] == 3
    assert sum(payload["match_distribution"].values()) == 3
    assert any(skill["name"] in {"SQL", "Excel"} for skill in payload["missing_skills"])
    assert "Python" not in {skill["name"] for skill in payload["missing_skills"]}
    assert {item["name"] for item in payload["top_counties"]} >= {
        "Nairobi County",
        "Mombasa County",
    }
    assert {item["name"] for item in payload["top_industries"]} >= {
        "technology",
        "finance",
    }


def test_applications_by_stage_groups_dashboard_columns(db_session_factory):
    user_id = _create_user(db_session_factory, with_profile=True)
    app = _create_test_app(db_session_factory, user_id)

    db = db_session_factory()
    now = datetime.utcnow()
    org = Organization(name="Pipeline Org", sector="technology", verified=True)
    db.add(org)
    db.flush()

    jobs = []
    for idx in range(5):
        job = JobPost(
            source="test",
            url=f"https://example.com/jobs/app-{idx}",
            url_hash=f"app-{idx}",
            title_raw=f"Pipeline Role {idx}",
            org_id=org.id,
            description_raw="Pipeline role description",
            first_seen=now - timedelta(days=idx),
            is_active=True,
        )
        db.add(job)
        jobs.append(job)
    db.flush()

    db.add_all(
        [
            JobApplication(
                user_id=user_id,
                job_post_id=jobs[0].id,
                status="saved",
                applied_at=now - timedelta(days=1),
            ),
            JobApplication(
                user_id=user_id,
                job_post_id=jobs[1].id,
                status="applied",
                applied_at=now - timedelta(days=2),
            ),
            JobApplication(
                user_id=user_id,
                job_post_id=jobs[2].id,
                status="interviewed",
                applied_at=now - timedelta(days=3),
                notes="Panel booked",
            ),
            JobApplication(
                user_id=user_id,
                job_post_id=jobs[3].id,
                status="offer",
                applied_at=now - timedelta(days=4),
            ),
            JobApplication(
                user_id=user_id,
                job_post_id=jobs[4].id,
                status="rejected",
                applied_at=now - timedelta(days=5),
            ),
        ]
    )
    db.commit()
    db.close()

    with TestClient(app) as client:
        response = client.get("/api/users/applications/by-stage")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analytics"]["total_applications"] == 5
    assert payload["stage_order"] == [
        "saved",
        "applied",
        "interview",
        "offer",
        "rejected",
    ]
    assert len(payload["stages"]["saved"]) == 1
    assert len(payload["stages"]["applied"]) == 1
    assert len(payload["stages"]["interview"]) == 1
    assert len(payload["stages"]["offer"]) == 1
    assert len(payload["stages"]["rejected"]) == 1
    interview_card = payload["stages"]["interview"][0]
    assert interview_card["stage"] == "interview"
    assert interview_card["status"] == "interviewed"
    assert interview_card["company"] == "Pipeline Org"
    assert interview_card["job_title"] == "Pipeline Role 2"
    assert interview_card["days_since_applied"] >= 0


def test_application_update_accepts_dashboard_stage_payload(db_session_factory):
    user_id = _create_user(db_session_factory, with_profile=True)
    app = _create_test_app(db_session_factory, user_id)

    db = db_session_factory()
    job = JobPost(
        source="test",
        url="https://example.com/jobs/update-1",
        url_hash="update-1",
        title_raw="Update Role",
        description_raw="Update role description",
        is_active=True,
    )
    db.add(job)
    db.flush()

    application = JobApplication(
        user_id=user_id,
        job_post_id=job.id,
        status="applied",
    )
    db.add(application)
    db.commit()
    application_id = application.id
    db.close()

    with TestClient(app) as client:
        response = client.put(
            f"/api/users/applications/{application_id}",
            json={"stage": "offer", "notes": "Awaiting signature"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "offer"
    assert payload["stage"] == "offer"

    db = db_session_factory()
    updated = db.execute(
        select(JobApplication).where(JobApplication.id == application_id)
    ).scalar_one()
    assert updated.status == "offer"
    assert updated.notes == "Awaiting signature"
    db.close()


def test_save_job_creates_saved_job_record(db_session_factory):
    user_id = _create_user(db_session_factory, with_profile=True)
    app = _create_test_app(db_session_factory, user_id)

    db = db_session_factory()
    job = JobPost(
        source="test",
        url="https://example.com/jobs/save-1",
        url_hash="save-1",
        title_raw="Save Role",
        description_raw="Save role description",
        is_active=True,
    )
    db.add(job)
    db.commit()
    job_id = job.id
    db.close()

    with TestClient(app) as client:
        response = client.post(
            "/api/users/saved-jobs",
            json={"job_id": job_id, "notes": "Homepage save"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Job saved successfully"

    db = db_session_factory()
    saved = db.execute(
        select(SavedJob).where(
            SavedJob.user_id == user_id,
            SavedJob.job_post_id == job_id,
        )
    ).scalar_one()
    assert saved.notes == "Homepage save"
    db.close()


def test_create_job_application_records_tracking_source(db_session_factory):
    user_id = _create_user(db_session_factory, with_profile=True)
    app = _create_test_app(db_session_factory, user_id)

    db = db_session_factory()
    job = JobPost(
        source="test",
        url="https://example.com/jobs/track-1",
        url_hash="track-1",
        title_raw="Track Role",
        description_raw="Track role description",
        is_active=True,
    )
    db.add(job)
    db.commit()
    job_id = job.id
    db.close()

    with TestClient(app) as client:
        response = client.post(
            "/api/users/applications",
            json={"job_id": job_id, "application_source": "homepage_search"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Application recorded successfully"

    db = db_session_factory()
    application = db.execute(
        select(JobApplication).where(
            JobApplication.user_id == user_id,
            JobApplication.job_post_id == job_id,
        )
    ).scalar_one()
    assert application.status == "applied"
    assert application.application_source == "homepage_search"
    db.close()


def test_create_job_alert_persists_query_and_filters(db_session_factory):
    user_id = _create_user(db_session_factory, with_profile=True)
    app = _create_test_app(db_session_factory, user_id)

    with TestClient(app) as client:
        response = client.post(
            "/api/users/job-alerts",
            json={
                "name": "Data roles Nairobi",
                "query": "data analyst",
                "filters": {"location": "Nairobi", "high_confidence_only": True},
                "frequency": "weekly",
                "delivery_methods": ["email"],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Job alert created successfully"

    db = db_session_factory()
    alert = db.execute(select(JobAlert).where(JobAlert.user_id == user_id)).scalar_one()
    assert alert.name == "Data roles Nairobi"
    assert alert.query == "data analyst"
    assert alert.filters["location"] == "Nairobi"
    assert alert.frequency == "weekly"
    db.close()


def test_delete_job_alert_removes_record(db_session_factory):
    user_id = _create_user(db_session_factory, with_profile=True)
    app = _create_test_app(db_session_factory, user_id)

    db = db_session_factory()
    alert = JobAlert(
        user_id=user_id,
        name="Delete me",
        query="sql",
        filters={"location": "Remote"},
        frequency="daily",
        delivery_methods=["email"],
        is_active=True,
    )
    db.add(alert)
    db.commit()
    alert_id = alert.id
    db.close()

    with TestClient(app) as client:
        response = client.delete(f"/api/users/job-alerts/{alert_id}")

    assert response.status_code == 200
    assert response.json()["message"] == "Job alert deleted successfully"

    db = db_session_factory()
    deleted = db.execute(
        select(JobAlert).where(JobAlert.id == alert_id)
    ).scalar_one_or_none()
    assert deleted is None
    db.close()
