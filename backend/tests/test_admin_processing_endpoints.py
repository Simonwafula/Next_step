import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin_routes import router as admin_router
from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import get_current_user


@pytest.fixture()
def admin_user(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="test-admin-uuid",
        email="admin@test.local",
        hashed_password="not-used",
        full_name="Test Admin",
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
    from app.core.config import settings

    monkeypatch.setattr(settings, "ADMIN_EMAILS", "admin@test.local")

    application = FastAPI()
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
    application.dependency_overrides[get_current_user] = override_get_current_user
    return application


def test_admin_quality_endpoint(app):
    with TestClient(app) as client:
        resp = client.get("/api/admin/quality")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "totals" in data
        assert "by_source" in data


def test_admin_process_endpoint(app):
    with TestClient(app) as client:
        resp = client.post("/api/admin/process", params={"limit": 10, "dry_run": True})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "success"


def test_admin_lmi_scorecard_endpoint(app):
    with TestClient(app) as client:
        resp = client.get("/api/admin/lmi-scorecard", params={"days_back": 1})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "metrics" in data
        assert "date" in data
        # Check all 10 metrics are present
        metrics = data["metrics"]
        assert "1_raw_postings_ingested" in metrics
        assert "2_canonical_jobs_added" in metrics
        assert "3_canonical_jobs_updated" in metrics
        assert "4_dedupe_collapse_rate_by_source" in metrics
        assert "5_pct_jobs_with_company" in metrics
        assert "6_pct_jobs_with_role_family" in metrics
        assert "7_pct_jobs_with_3plus_skills" in metrics
        assert "8_error_rate_pct" in metrics
        assert "9_block_detections" in metrics
        assert "10_trend_spikes" in metrics


def test_admin_lmi_health_endpoint(app):
    with TestClient(app) as client:
        resp = client.get("/api/admin/lmi-health")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "generated_at" in data
        assert "daily_scorecard" in data
        assert "canonical_integrity" in data
        assert "skill_normalization" in data
        assert "seniority_coverage" in data


def test_admin_lmi_integrity_endpoint(app):
    with TestClient(app) as client:
        resp = client.get("/api/admin/lmi-integrity")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "total_jobs" in data
        assert "dedupe_entries" in data
        assert "canonical_jobs" in data
        assert "integrity_checks" in data


def test_admin_lmi_skills_endpoint(app):
    with TestClient(app) as client:
        resp = client.get("/api/admin/lmi-skills")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "total_unique_skills" in data
        assert "top_30_skills" in data
        assert "fragmentation_detected" in data
        assert "quality_status" in data


def test_admin_lmi_seniority_endpoint(app):
    with TestClient(app) as client:
        resp = client.get("/api/admin/lmi-seniority")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "total_jobs" in data
        assert "with_seniority" in data
        assert "coverage_pct" in data
        assert "status" in data
