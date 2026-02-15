from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import api_router
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import get_current_user


def test_admin_mvil_refresh_requires_auth(db_session_factory):
    app = FastAPI()
    app.include_router(api_router, prefix="/api")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        response = client.post("/api/admin/mvil/refresh")

    assert response.status_code == 401


def test_admin_mvil_refresh_returns_summary_for_admin(
    db_session_factory,
    monkeypatch,
):
    db = db_session_factory()
    admin_user = User(
        uuid="mvil-admin-uuid",
        email="mvil-admin@test.local",
        hashed_password="not-used",
        full_name="MVIL Admin",
        subscription_tier="enterprise",
        is_active=True,
        is_verified=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    db.close()

    monkeypatch.setattr(settings, "ADMIN_EMAILS", "mvil-admin@test.local")

    expected_summary = {
        "status": "ok",
        "baselines_refreshed": 4,
        "role_families_processed": 2,
        "duration_s": 0.12,
        "rows": {
            "role_skill_baseline": 8,
            "role_education_baseline": 6,
            "role_experience_baseline": 5,
            "role_demand_snapshot": 2,
        },
    }

    def fake_refresh_all_baselines(_db):
        return expected_summary

    monkeypatch.setattr(
        "app.api.routes.refresh_all_baselines",
        fake_refresh_all_baselines,
    )

    app = FastAPI()
    app.include_router(api_router, prefix="/api")

    def override_get_db():
        local_db = db_session_factory()
        try:
            yield local_db
        finally:
            local_db.close()

    async def override_get_current_user():
        local_db = db_session_factory()
        try:
            return local_db.get(User, admin_user.id)
        finally:
            local_db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as client:
        response = client.post("/api/admin/mvil/refresh")

    assert response.status_code == 200
    assert response.json() == expected_summary
