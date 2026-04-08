import re
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.auth_routes import router as auth_router
from app.api.user_routes import router as user_router
from app.db.database import get_db
from app.db.models import (
    JobApplication,
    JobPost,
    JobSkill,
    Location,
    Organization,
    SavedJob,
    Skill,
    User,
    UserJobRecommendation,
    UserNotification,
    UserProfile,
)
from app.services.auth_service import get_current_user

EXPECTED_DASHBOARD_TABS = [
    "market-fit",
    "smart-feed",
    "applications",
    "plan",
    "profile",
]


def _frontend_path(*parts: str) -> Path:
    return Path(__file__).resolve().parents[2].joinpath("frontend", *parts)


def _create_dashboard_boot_app(db_session_factory, current_user_id: int) -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/auth")
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


def _seed_dashboard_boot_data(db_session_factory) -> int:
    db = db_session_factory()
    now = datetime.utcnow()

    user = User(
        uuid="dashboard-boot-user",
        email="dashboard-boot@example.com",
        hashed_password="not-used",
        full_name="Dashboard Boot User",
        subscription_tier="professional",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    db.add(
        UserProfile(
            user_id=user.id,
            current_role="Data Analyst",
            experience_level="mid",
            skills={"Python": 0.95, "Power BI": 0.8},
            preferred_locations=["Nairobi County"],
            profile_completeness=80.0,
        )
    )

    org = Organization(name="Acme Analytics", sector="technology", verified=True)
    location = Location(
        country="Kenya",
        region="Nairobi County",
        city="Nairobi",
        raw="Nairobi County, Kenya",
    )
    db.add_all([org, location])
    db.flush()

    jobs = [
        JobPost(
            source="test",
            url="https://example.com/jobs/boot-1",
            url_hash="boot-1",
            title_raw="Senior Data Analyst",
            org_id=org.id,
            location_id=location.id,
            description_raw="Python SQL dashboarding stakeholder reporting",
            first_seen=now - timedelta(days=1),
            is_active=True,
        ),
        JobPost(
            source="test",
            url="https://example.com/jobs/boot-2",
            url_hash="boot-2",
            title_raw="BI Analyst",
            org_id=org.id,
            location_id=location.id,
            description_raw="Power BI SQL reporting and analytics",
            first_seen=now - timedelta(days=2),
            is_active=True,
        ),
        JobPost(
            source="test",
            url="https://example.com/jobs/boot-3",
            url_hash="boot-3",
            title_raw="Insights Associate",
            org_id=org.id,
            location_id=location.id,
            description_raw="Excel SQL business analysis",
            first_seen=now - timedelta(days=3),
            is_active=True,
        ),
    ]
    db.add_all(jobs)
    db.flush()

    python_skill = Skill(name="Python")
    sql_skill = Skill(name="SQL")
    excel_skill = Skill(name="Excel")
    db.add_all([python_skill, sql_skill, excel_skill])
    db.flush()

    db.add_all(
        [
            JobSkill(job_post_id=jobs[0].id, skill_id=python_skill.id, confidence=0.95),
            JobSkill(job_post_id=jobs[0].id, skill_id=sql_skill.id, confidence=0.92),
            JobSkill(job_post_id=jobs[1].id, skill_id=sql_skill.id, confidence=0.9),
            JobSkill(job_post_id=jobs[2].id, skill_id=excel_skill.id, confidence=0.88),
        ]
    )

    db.add(
        SavedJob(
            user_id=user.id,
            job_post_id=jobs[0].id,
            notes="Priority lead",
            folder="top-picks",
        )
    )

    db.add_all(
        [
            JobApplication(
                user_id=user.id,
                job_post_id=jobs[1].id,
                status="saved",
                applied_at=now - timedelta(days=2),
            ),
            JobApplication(
                user_id=user.id,
                job_post_id=jobs[2].id,
                status="interviewed",
                applied_at=now - timedelta(days=4),
                notes="Panel booked",
            ),
        ]
    )

    db.add(
        UserNotification(
            user_id=user.id,
            type="job_alert",
            title="Fresh analyst roles",
            message="Three new analyst roles match your profile.",
            data={"count": 3},
        )
    )

    db.add_all(
        [
            UserJobRecommendation(
                user_id=user.id,
                job_post_id=jobs[0].id,
                match_score=0.91,
                skill_match_score=0.94,
                location_match_score=0.9,
                salary_match_score=0.5,
                experience_match_score=0.82,
                match_explanation="Strong skill overlap",
                matching_skills=["Python"],
                missing_skills=["SQL"],
            ),
            UserJobRecommendation(
                user_id=user.id,
                job_post_id=jobs[1].id,
                match_score=0.84,
                skill_match_score=0.86,
                location_match_score=0.9,
                salary_match_score=0.5,
                experience_match_score=0.79,
                match_explanation="Good reporting fit",
                matching_skills=["Power BI"],
                missing_skills=["SQL"],
            ),
        ]
    )

    db.commit()
    user_id = user.id
    db.close()
    return user_id


def test_dashboard_boot_contract_matches_shipped_html_and_js():
    dashboard_html = _frontend_path("dashboard.html").read_text(encoding="utf-8")
    dashboard_js = _frontend_path("js", "dashboard-ui.js").read_text(encoding="utf-8")

    tab_order = re.findall(r'data-tab="([^"]+)"', dashboard_html)
    content_tabs = re.findall(r'data-tab-content="([^"]+)"', dashboard_html)

    assert tab_order == EXPECTED_DASHBOARD_TABS
    assert content_tabs == EXPECTED_DASHBOARD_TABS
    assert 'button class="dashboard-tab active" data-tab="market-fit"' in dashboard_html
    assert (
        "const lastTab = localStorage.getItem('dashboard_active_tab') || 'smart-feed';"
        in dashboard_js
    )
    assert "requestJson(`${apiBase}/users/market-fit`" in dashboard_js
    assert "requestJson(`${apiBase}/users/applications/by-stage`" in dashboard_js

    boot_sequence = [
        "await loadMarketFit(auth.access_token);",
        "await refreshRecommendations();",
        "await loadApplicationsKanban(auth.access_token);",
        "restoreActiveTab();",
        "dashboardApp.hidden = false;",
    ]
    boot_indexes = [dashboard_js.index(step) for step in boot_sequence]
    assert boot_indexes == sorted(boot_indexes)


def test_dashboard_boot_routes_return_shapes_consumed_by_shipped_ui(
    db_session_factory,
):
    user_id = _seed_dashboard_boot_data(db_session_factory)
    app = _create_dashboard_boot_app(db_session_factory, user_id)

    with TestClient(app) as client:
        me_response = client.get("/api/auth/me")
        profile_response = client.get("/api/auth/profile")
        recommendations_response = client.get("/api/users/recommendations?limit=5")
        saved_jobs_response = client.get("/api/users/saved-jobs?limit=5")
        applications_response = client.get("/api/users/applications?limit=5")
        notifications_response = client.get("/api/users/notifications?limit=5")
        market_fit_response = client.get("/api/users/market-fit")
        by_stage_response = client.get("/api/users/applications/by-stage")

    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["full_name"] == "Dashboard Boot User"
    assert me_payload["subscription_tier"] == "professional"
    assert me_payload["is_admin"] is False

    assert profile_response.status_code == 200
    profile_payload = profile_response.json()
    assert profile_payload["current_role"] == "Data Analyst"
    assert profile_payload["preferred_locations"] == ["Nairobi County"]
    assert profile_payload["profile_completeness"] == 80.0

    assert recommendations_response.status_code == 200
    recommendations_payload = recommendations_response.json()
    assert len(recommendations_payload["recommendations"]) == 2
    assert {
        "title",
        "company",
        "url",
        "match_score",
        "matching_skills",
        "missing_skills",
    } <= recommendations_payload["recommendations"][0].keys()

    assert saved_jobs_response.status_code == 200
    saved_jobs_payload = saved_jobs_response.json()
    assert saved_jobs_payload["saved_jobs"][0]["organization"] == "Acme Analytics"
    assert saved_jobs_payload["saved_jobs"][0]["location"] == "Nairobi County, Kenya"

    assert applications_response.status_code == 200
    applications_payload = applications_response.json()
    assert applications_payload["total"] == 2
    assert {"id", "job_id", "status", "stage"} <= applications_payload["applications"][
        0
    ].keys()

    assert notifications_response.status_code == 200
    notifications_payload = notifications_response.json()
    assert notifications_payload["notifications"][0]["title"] == "Fresh analyst roles"
    assert notifications_payload["notifications"][0]["message"].startswith("Three new")

    assert market_fit_response.status_code == 200
    market_fit_payload = market_fit_response.json()
    assert market_fit_payload["target_roles"] == ["Data Analyst"]
    assert market_fit_payload["total_jobs_analyzed"] == 3
    assert sum(market_fit_payload["match_distribution"].values()) == 3
    assert any(skill["name"] == "SQL" for skill in market_fit_payload["missing_skills"])
    assert market_fit_payload["top_counties"] == [
        {"name": "Nairobi County", "count": 3}
    ]

    assert by_stage_response.status_code == 200
    by_stage_payload = by_stage_response.json()
    assert by_stage_payload["stage_order"] == [
        "saved",
        "applied",
        "interview",
        "offer",
        "rejected",
    ]
    assert by_stage_payload["analytics"]["total_applications"] == 2
    assert len(by_stage_payload["stages"]["saved"]) == 1
    assert len(by_stage_payload["stages"]["interview"]) == 1
    assert by_stage_payload["stages"]["interview"][0]["status"] == "interviewed"
    assert (
        by_stage_payload["stages"]["interview"][0]["job_title"] == "Insights Associate"
    )
