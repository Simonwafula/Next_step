"""Tests for analytics and admin dashboard endpoints (T-403d)."""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.analytics_routes import router as analytics_router
from app.api.admin_routes import router as admin_router
from app.db.database import get_db
from app.db.models import (
    EducationNormalization,
    HiringSignal,
    JobPost,
    JobSkill,
    Location,
    Organization,
    ProcessingLog,
    RoleEvolution,
    Skill,
    SkillTrendsMonthly,
    TenderNotice,
    TitleAdjacency,
    TitleNorm,
    User,
    UserNotification,
)
from app.services.auth_service import get_current_user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def admin_user(db_session_factory):
    """Create an admin user in the test DB."""
    db = db_session_factory()
    user = User(
        uuid="test-admin-uuid",
        email="admin@test.local",
        hashed_password="not-used",
        full_name="Test Admin",
        whatsapp_number="+254700111222",
        is_active=True,
        is_verified=True,
        subscription_tier="enterprise",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture()
def app(db_session_factory, admin_user, monkeypatch):
    """FastAPI test app with analytics + admin routers and auth bypass."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ADMIN_EMAILS", "admin@test.local")

    application = FastAPI()
    application.include_router(analytics_router)
    application.include_router(admin_router)

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    async def override_get_current_user():
        return admin_user

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[
        get_current_user
    ] = override_get_current_user
    return application


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded_db(db_session_factory):
    """Seed the test DB with sample data for dashboard queries."""
    db = db_session_factory()
    now = datetime.utcnow()

    org = Organization(name="Acme Corp", sector="tech", verified=True)
    db.add(org)
    db.flush()

    loc = Location(
        country="US",
        region="CA",
        city="San Francisco",
        raw="San Francisco, CA",
    )
    db.add(loc)
    db.flush()

    title_norm = TitleNorm(
        family="engineering",
        canonical_title="Software Engineer",
        aliases=["SWE", "Dev"],
    )
    db.add(title_norm)
    db.flush()

    job = JobPost(
        source="test",
        url="https://example.com/job/1",
        url_hash="abc123",
        title_raw="Software Engineer",
        title_norm_id=title_norm.id,
        org_id=org.id,
        location_id=loc.id,
        description_raw="Build stuff",
        education="Bachelor's Degree",
        salary_min=80000,
        salary_max=120000,
        currency="USD",
        first_seen=now - timedelta(days=2),
    )
    db.add(job)
    db.flush()

    skill = Skill(name="Python")
    db.add(skill)
    db.flush()

    job_skill = JobSkill(
        job_post_id=job.id,
        skill_id=skill.id,
        confidence=0.95,
    )
    db.add(job_skill)

    month_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    db.add(
        SkillTrendsMonthly(
            skill="Python",
            title_norm="engineering",
            month=month_dt,
            count=10,
            share=0.5,
        )
    )
    db.add(
        RoleEvolution(
            title_norm="engineering",
            month=month_dt,
            top_skills=["Python", "SQL"],
        )
    )
    db.add(
        TitleAdjacency(
            title_a="Software Engineer",
            title_b="Backend Engineer",
            similarity=0.85,
        )
    )

    db.add(
        ProcessingLog(
            process_type="ingestion",
            results={
                "status": "success",
                "message": "Ingested 50 jobs",
                "details": {},
            },
        )
    )

    db.add(
        EducationNormalization(
            raw_value="BSc",
            normalized_value="Bachelor's Degree",
        )
    )

    db.add(
        TenderNotice(
            source="gov",
            external_id="T-001",
            title="IT Services Contract",
            organization="Dept of Tech",
            category="IT",
            location="DC",
            published_at=now - timedelta(days=5),
            closing_at=now + timedelta(days=25),
            url="https://gov.example.com/tender/1",
        )
    )

    db.add(
        HiringSignal(
            signal_type="posting_velocity",
            role_family="engineering",
            org_id=org.id,
            score=5.0,
            window_start=now - timedelta(days=30),
            window_end=now,
            meta_json={"org_name": "Acme Corp"},
        )
    )

    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Analytics endpoints (public, no auth required)
# ---------------------------------------------------------------------------


class TestAnalyticsEndpoints:
    def test_skill_trends_empty(self, client):
        resp = client.get("/analytics/skill-trends")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_skill_trends_with_data(self, client, seeded_db):
        resp = client.get("/analytics/skill-trends")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "skill" in item
        assert "month" in item
        assert "count" in item

    def test_skill_trends_filter_by_role(self, client, seeded_db):
        resp = client.get(
            "/analytics/skill-trends", params={"role_family": "engineering"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role_family"] == "engineering"

    def test_skill_trends_query_params(self, client):
        resp = client.get(
            "/analytics/skill-trends",
            params={"months": 3, "limit": 10},
        )
        assert resp.status_code == 200

    def test_skill_trends_invalid_months(self, client):
        resp = client.get("/analytics/skill-trends", params={"months": 0})
        assert resp.status_code == 422

    def test_role_evolution_empty(self, client):
        resp = client.get("/analytics/role-evolution")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_role_evolution_with_data(self, client, seeded_db):
        resp = client.get("/analytics/role-evolution")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "role_family" in item
        assert "top_skills" in item

    def test_title_adjacency_empty(self, client):
        resp = client.get("/analytics/title-adjacency")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_title_adjacency_with_data(self, client, seeded_db):
        resp = client.get("/analytics/title-adjacency")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "title_a" in item
        assert "title_b" in item
        assert "similarity" in item


# ---------------------------------------------------------------------------
# Admin overview
# ---------------------------------------------------------------------------


class TestAdminOverview:
    def test_overview_empty_db(self, client):
        resp = client.get("/api/admin/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "kpis" in data
        assert "coverage" in data
        assert "sources" in data
        assert "recent" in data
        assert data["kpis"]["users_total"] >= 1  # admin user exists

    def test_overview_with_data(self, client, seeded_db):
        resp = client.get("/api/admin/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["kpis"]["jobs_total"] >= 1
        assert data["kpis"]["organizations_total"] >= 1
        assert data["kpis"]["locations_total"] >= 1
        assert data["coverage"]["salary"]["count"] >= 1


class TestAdminLmiQuality:
    def test_lmi_quality_empty_db(self, client):
        resp = client.get("/api/admin/lmi-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert "scraping_health" in data
        assert "skills_extraction" in data
        assert "engagement" in data
        assert "revenue" in data

    def test_lmi_quality_with_seeded_data(self, client, seeded_db):
        resp = client.get("/api/admin/lmi-quality")
        assert resp.status_code == 200
        data = resp.json()

        scraping = data["scraping_health"]
        assert scraping["total_runs_7d"] >= 1
        assert 0 <= scraping["success_rate_7d"] <= 100

        skills = data["skills_extraction"]
        assert skills["jobs_with_skills"] >= 1
        assert 0 <= skills["coverage_percentage"] <= 100

        engagement = data["engagement"]
        assert "active_search_users_30d" in engagement
        assert 0 <= engagement["lmi_engagement_rate_30d"] <= 100

        revenue = data["revenue"]
        assert "estimated_mrr_kes" in revenue
        assert "estimated_arpu_kes" in revenue
        assert "estimated_churn_rate" in revenue
        assert "upgraded_users_30d" in revenue
        assert "conversion_rate_30d" in revenue
        assert "conversion_trend_14d" in revenue
        assert "conversion_alert" in revenue

    def test_lmi_quality_includes_conversion_metrics(
        self,
        client,
        db_session_factory,
    ):
        db = db_session_factory()
        now = datetime.utcnow()

        user = User(
            uuid="conversion-user-uuid",
            email="conversion@test.local",
            hashed_password="not-used",
            full_name="Conversion User",
            is_active=True,
            is_verified=True,
            subscription_tier="professional",
            created_at=now - timedelta(days=3),
        )
        db.add(user)
        db.flush()

        db.add(
            UserNotification(
                user_id=user.id,
                type="subscription_upgrade",
                title="Subscription upgraded",
                message="Upgrade completed",
                data={"plan_code": "professional_monthly"},
                created_at=now - timedelta(days=2),
            )
        )
        db.commit()
        db.close()

        resp = client.get("/api/admin/lmi-quality")
        assert resp.status_code == 200

        revenue = resp.json()["revenue"]
        assert revenue["upgraded_users_30d"] >= 1
        assert revenue["new_users_30d"] >= 1
        assert revenue["conversion_rate_30d"] >= 0

    def test_lmi_quality_includes_conversion_trend_series(
        self,
        client,
        db_session_factory,
    ):
        db = db_session_factory()
        now = datetime.utcnow()

        user_recent = User(
            uuid="trend-user-1",
            email="trend1@test.local",
            hashed_password="not-used",
            full_name="Trend One",
            is_active=True,
            is_verified=True,
            subscription_tier="professional",
            created_at=now - timedelta(days=1),
        )
        user_old = User(
            uuid="trend-user-2",
            email="trend2@test.local",
            hashed_password="not-used",
            full_name="Trend Two",
            is_active=True,
            is_verified=True,
            subscription_tier="basic",
            created_at=now - timedelta(days=10),
        )
        db.add_all([user_recent, user_old])
        db.flush()

        db.add(
            UserNotification(
                user_id=user_recent.id,
                type="subscription_upgrade",
                title="Subscription upgraded",
                message="Upgrade completed",
                data={"plan_code": "professional_monthly"},
                created_at=now - timedelta(days=1),
            )
        )
        db.commit()
        db.close()

        resp = client.get("/api/admin/lmi-quality")
        assert resp.status_code == 200

        trend = resp.json()["revenue"]["conversion_trend_14d"]
        assert len(trend) == 14
        assert all("date" in row for row in trend)
        assert all("upgrades" in row for row in trend)
        assert any(row["upgrades"] > 0 for row in trend)

    def test_lmi_quality_flags_low_conversion_alert(
        self,
        client,
        db_session_factory,
    ):
        db = db_session_factory()
        now = datetime.utcnow()

        user = User(
            uuid="low-conversion-user",
            email="low-conversion@test.local",
            hashed_password="not-used",
            full_name="Low Conversion User",
            is_active=True,
            is_verified=True,
            subscription_tier="basic",
            created_at=now - timedelta(days=1),
        )
        db.add(user)
        db.commit()
        db.close()

        resp = client.get("/api/admin/lmi-quality")
        assert resp.status_code == 200

        alert = resp.json()["revenue"]["conversion_alert"]
        assert alert["status"] == "warning"
        assert alert["avg_conversion_7d"] >= 0
        assert "threshold" in alert

    def test_lmi_quality_warning_dispatches_admin_notifications(
        self,
        client,
        db_session_factory,
        monkeypatch,
    ):
        email_calls = []
        whatsapp_calls = []

        monkeypatch.setattr(
            "app.services.admin_alert_service.send_email",
            lambda to_address, subject, body: (
                email_calls.append((to_address, subject, body)) or True
            ),
        )

        async def fake_whatsapp_send(to_number, message):
            whatsapp_calls.append((to_number, message))
            return True

        monkeypatch.setattr(
            "app.services.admin_alert_service.send_whatsapp_message",
            fake_whatsapp_send,
        )

        db = db_session_factory()
        db.add(
            User(
                uuid="dispatch-low-conversion-user",
                email="dispatch-low-conversion@test.local",
                hashed_password="not-used",
                full_name="Dispatch Low Conversion User",
                is_active=True,
                is_verified=True,
                subscription_tier="basic",
                created_at=datetime.utcnow() - timedelta(days=1),
            )
        )
        db.commit()
        db.close()

        resp = client.get("/api/admin/lmi-quality")
        assert resp.status_code == 200

        db = db_session_factory()
        admin_notifications = (
            db.query(UserNotification)
            .filter(UserNotification.type == "admin_conversion_dropoff_alert")
            .all()
        )
        assert len(admin_notifications) == 1
        notification = admin_notifications[0]
        assert "in_app" in (notification.delivered_via or [])
        assert "email" in (notification.delivered_via or [])
        assert "whatsapp" in (notification.delivered_via or [])
        assert notification.delivery_status.get("in_app") == "sent"
        assert notification.delivery_status.get("email") == "sent"
        assert notification.delivery_status.get("whatsapp") == "sent"
        db.close()

        assert len(email_calls) == 1
        assert len(whatsapp_calls) == 1

    def test_lmi_quality_warning_dispatch_respects_cooldown(
        self,
        client,
        db_session_factory,
        monkeypatch,
    ):
        email_calls = []

        monkeypatch.setattr(
            "app.services.admin_alert_service.send_email",
            lambda to_address, subject, body: (
                email_calls.append((to_address, subject, body)) or True
            ),
        )

        async def fake_whatsapp_send(_to_number, _message):
            return True

        monkeypatch.setattr(
            "app.services.admin_alert_service.send_whatsapp_message",
            fake_whatsapp_send,
        )

        db = db_session_factory()
        db.add(
            User(
                uuid="cooldown-low-conversion-user",
                email="cooldown-low-conversion@test.local",
                hashed_password="not-used",
                full_name="Cooldown Low Conversion User",
                is_active=True,
                is_verified=True,
                subscription_tier="basic",
                created_at=datetime.utcnow() - timedelta(days=1),
            )
        )
        db.commit()
        db.close()

        first = client.get("/api/admin/lmi-quality")
        second = client.get("/api/admin/lmi-quality")
        assert first.status_code == 200
        assert second.status_code == 200

        db = db_session_factory()
        admin_notifications = (
            db.query(UserNotification)
            .filter(UserNotification.type == "admin_conversion_dropoff_alert")
            .all()
        )
        assert len(admin_notifications) == 1
        db.close()

        assert len(email_calls) == 1

    def test_lmi_quality_uses_configured_conversion_threshold(
        self,
        client,
        db_session_factory,
        monkeypatch,
    ):
        from app.core.config import settings

        monkeypatch.setattr(
            settings,
            "ADMIN_CONVERSION_ALERT_THRESHOLD",
            0.0,
        )

        db = db_session_factory()
        db.add(
            User(
                uuid="threshold-low-conversion-user",
                email="threshold-low-conversion@test.local",
                hashed_password="not-used",
                full_name="Threshold Low Conversion User",
                is_active=True,
                is_verified=True,
                subscription_tier="basic",
                created_at=datetime.utcnow() - timedelta(days=1),
            )
        )
        db.commit()
        db.close()

        resp = client.get("/api/admin/lmi-quality")
        assert resp.status_code == 200
        alert = resp.json()["revenue"]["conversion_alert"]
        assert alert["threshold"] == 0.0
        assert alert["status"] == "healthy"

    def test_lmi_quality_warning_dispatch_honors_channel_toggles(
        self,
        client,
        db_session_factory,
        monkeypatch,
    ):
        from app.core.config import settings

        monkeypatch.setattr(
            settings,
            "ADMIN_CONVERSION_ALERT_EMAIL_ENABLED",
            False,
        )
        monkeypatch.setattr(
            settings,
            "ADMIN_CONVERSION_ALERT_WHATSAPP_ENABLED",
            False,
        )

        db = db_session_factory()
        db.add(
            User(
                uuid="toggle-low-conversion-user",
                email="toggle-low-conversion@test.local",
                hashed_password="not-used",
                full_name="Toggle Low Conversion User",
                is_active=True,
                is_verified=True,
                subscription_tier="basic",
                created_at=datetime.utcnow() - timedelta(days=1),
            )
        )
        db.commit()
        db.close()

        resp = client.get("/api/admin/lmi-quality")
        assert resp.status_code == 200

        db = db_session_factory()
        notification = (
            db.query(UserNotification)
            .filter(UserNotification.type == "admin_conversion_dropoff_alert")
            .one()
        )
        assert "in_app" in (notification.delivered_via or [])
        assert "email" not in (notification.delivered_via or [])
        assert "whatsapp" not in (notification.delivered_via or [])
        assert notification.delivery_status.get("email") == "disabled"
        assert notification.delivery_status.get("whatsapp") == "disabled"
        db.close()

    def test_get_lmi_alert_settings_returns_defaults(self, client):
        resp = client.get("/api/admin/lmi-alert-settings")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["source"] in {"defaults", "override"}
        settings_payload = payload["settings"]
        assert "threshold" in settings_payload
        assert "cooldown_hours" in settings_payload
        assert "in_app_enabled" in settings_payload
        assert "email_enabled" in settings_payload
        assert "whatsapp_enabled" in settings_payload

    def test_update_lmi_alert_settings_persists_overrides(self, client):
        update_payload = {
            "threshold": 7.5,
            "cooldown_hours": 12,
            "in_app_enabled": True,
            "email_enabled": False,
            "whatsapp_enabled": False,
        }
        update_resp = client.put(
            "/api/admin/lmi-alert-settings",
            json=update_payload,
        )
        assert update_resp.status_code == 200

        get_resp = client.get("/api/admin/lmi-alert-settings")
        assert get_resp.status_code == 200
        payload = get_resp.json()
        assert payload["source"] == "override"
        settings_payload = payload["settings"]
        assert settings_payload["threshold"] == 7.5
        assert settings_payload["cooldown_hours"] == 12
        assert settings_payload["email_enabled"] is False
        assert settings_payload["whatsapp_enabled"] is False

        quality_resp = client.get("/api/admin/lmi-quality")
        assert quality_resp.status_code == 200
        threshold = quality_resp.json()["revenue"]["conversion_alert"][
            "threshold"
        ]
        assert threshold == 7.5


# ---------------------------------------------------------------------------
# Admin users
# ---------------------------------------------------------------------------


class TestAdminUsers:
    def test_list_users(self, client):
        resp = client.get("/api/admin/users")
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 1
        user = data["users"][0]
        assert "id" in user
        assert "email" in user

    def test_list_users_pagination(self, client):
        resp = client.get("/api/admin/users", params={"limit": 1, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] <= 1


# ---------------------------------------------------------------------------
# Admin jobs
# ---------------------------------------------------------------------------


class TestAdminJobs:
    def test_list_jobs_empty(self, client):
        resp = client.get("/api/admin/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["jobs"] == []
        assert data["total"] == 0

    def test_list_jobs_with_data(self, client, seeded_db):
        resp = client.get("/api/admin/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        job = data["jobs"][0]
        assert job["title"] == "Software Engineer"
        assert job["organization"] == "Acme Corp"
        assert job["location"] == "San Francisco, CA"


# ---------------------------------------------------------------------------
# Admin sources (reads YAML files — may return empty if files are missing)
# ---------------------------------------------------------------------------


class TestAdminSources:
    def test_list_all_sources(self, client):
        resp = client.get("/api/admin/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert "total" in data

    def test_list_core_sources(self, client):
        resp = client.get("/api/admin/sources", params={"source_type": "core"})
        assert resp.status_code == 200

    def test_list_government_sources(self, client):
        resp = client.get(
            "/api/admin/sources",
            params={"source_type": "government"},
        )
        assert resp.status_code == 200

    def test_invalid_source_type(self, client):
        resp = client.get(
            "/api/admin/sources",
            params={"source_type": "invalid"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Admin operations
# ---------------------------------------------------------------------------


class TestAdminOperations:
    def test_operations_empty(self, client):
        resp = client.get("/api/admin/operations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["operations"] == []
        assert data["latest_by_type"] == {}

    def test_operations_with_data(self, client, seeded_db):
        resp = client.get("/api/admin/operations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["operations"]) >= 1
        op = data["operations"][0]
        assert op["process_type"] == "ingestion"
        assert op["status"] == "success"
        assert "ingestion" in data["latest_by_type"]


# ---------------------------------------------------------------------------
# Admin summaries
# ---------------------------------------------------------------------------


class TestAdminSummaries:
    def test_summaries_title(self, client, seeded_db):
        resp = client.get(
            "/api/admin/summaries",
            params={"dimension": "title"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dimension"] == "title"
        assert len(data["items"]) >= 1

    def test_summaries_skill(self, client, seeded_db):
        resp = client.get(
            "/api/admin/summaries",
            params={"dimension": "skill"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dimension"] == "skill"
        assert len(data["items"]) >= 1
        assert data["items"][0]["specific_value"] == "Python"

    def test_summaries_education(self, client, seeded_db):
        resp = client.get(
            "/api/admin/summaries",
            params={"dimension": "education"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dimension"] == "education"

    def test_summaries_invalid_dimension(self, client):
        resp = client.get(
            "/api/admin/summaries",
            params={"dimension": "invalid"},
        )
        assert resp.status_code == 400

    def test_summary_jobs_by_title(self, client, seeded_db):
        resp = client.get(
            "/api/admin/summaries/title/jobs",
            params={"value": "Software Engineer"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dimension"] == "title"
        assert data["value"] == "Software Engineer"
        assert data["total"] >= 1

    def test_summary_jobs_by_skill(self, client, seeded_db):
        resp = client.get(
            "/api/admin/summaries/skill/jobs",
            params={"value": "Python"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_summary_jobs_invalid_dimension(self, client):
        resp = client.get(
            "/api/admin/summaries/invalid/jobs",
            params={"value": "x"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Admin education mappings
# ---------------------------------------------------------------------------


class TestAdminEducationMappings:
    def test_list_empty(self, client):
        resp = client.get("/api/admin/education-mappings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mappings"] == []
        assert data["total"] == 0

    def test_list_with_data(self, client, seeded_db):
        resp = client.get("/api/admin/education-mappings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        mapping = data["mappings"][0]
        assert mapping["raw_value"] == "BSc"
        assert mapping["normalized_value"] == "Bachelor's Degree"

    def test_create_mapping(self, client):
        resp = client.post(
            "/api/admin/education-mappings",
            json={
                "raw_value": "MSc",
                "normalized_value": "Master's Degree",
                "notes": "test",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["raw_value"] == "MSc"
        assert data["normalized_value"] == "Master's Degree"
        assert data["id"] is not None

    def test_upsert_mapping(self, client, seeded_db):
        resp = client.post(
            "/api/admin/education-mappings",
            json={
                "raw_value": "BSc",
                "normalized_value": "Bachelor's Degree (Updated)",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["normalized_value"] == "Bachelor's Degree (Updated)"

    def test_create_mapping_missing_fields(self, client):
        resp = client.post(
            "/api/admin/education-mappings",
            json={"raw_value": ""},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Admin analytics (same as public but behind auth)
# ---------------------------------------------------------------------------


class TestAdminAnalytics:
    def test_admin_skill_trends(self, client, seeded_db):
        resp = client.get("/api/admin/analytics/skill-trends")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_admin_role_evolution(self, client, seeded_db):
        resp = client.get("/api/admin/analytics/role-evolution")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_admin_title_adjacency(self, client, seeded_db):
        resp = client.get("/api/admin/analytics/title-adjacency")
        assert resp.status_code == 200
        assert "items" in resp.json()


# ---------------------------------------------------------------------------
# Admin monitoring / drift
# ---------------------------------------------------------------------------


class TestAdminDrift:
    def test_drift_empty_db(self, client):
        resp = client.get("/api/admin/monitoring/drift")
        assert resp.status_code == 200
        data = resp.json()
        assert "skills" in data
        assert "titles" in data
        assert "salary" in data

    def test_drift_with_data(self, client, seeded_db):
        resp = client.get("/api/admin/monitoring/drift")
        assert resp.status_code == 200


class TestAdminMonitoringSummary:
    def test_monitoring_summary_flags_drift(self, client, monkeypatch):
        monkeypatch.setenv("DRIFT_SKILL_MAX", "0.5")
        monkeypatch.setenv("DRIFT_TITLE_MAX", "0.5")

        resp = client.get("/api/admin/monitoring/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "fail"
        assert data["drift"]["checks"]["skills"]["status"] == "fail"


# ---------------------------------------------------------------------------
# Admin signals
# ---------------------------------------------------------------------------


class TestAdminSignals:
    def test_tenders_empty(self, client):
        resp = client.get("/api/admin/signals/tenders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenders"] == []
        assert data["total"] == 0

    def test_tenders_with_data(self, client, seeded_db):
        resp = client.get("/api/admin/signals/tenders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        tender = data["tenders"][0]
        assert tender["title"] == "IT Services Contract"

    def test_hiring_signals_empty(self, client):
        resp = client.get("/api/admin/signals/hiring")
        assert resp.status_code == 200
        data = resp.json()
        assert data["signals"] == []
        assert data["total"] == 0

    def test_hiring_signals_with_data(self, client, seeded_db):
        resp = client.get("/api/admin/signals/hiring")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        signal = data["signals"][0]
        assert signal["signal_type"] == "posting_velocity"
        assert signal["role_family"] == "engineering"
