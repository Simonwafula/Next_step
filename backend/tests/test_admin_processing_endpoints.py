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
