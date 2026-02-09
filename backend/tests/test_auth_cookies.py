from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth_routes import router as auth_router
from app.core.config import settings
from app.db.database import get_db


def test_auth_cookie_flow(db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", False)

    app = FastAPI()
    app.include_router(auth_router, prefix="/auth")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        payload = {
            "email": "cookie.user@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Cookie User",
        }
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["token_type"] == "bearer"
        assert data["access_token"]
        assert data["refresh_token"]

        # Cookies should be set for browser clients.
        assert client.cookies.get(settings.AUTH_COOKIE_ACCESS_NAME)
        assert client.cookies.get(settings.AUTH_COOKIE_REFRESH_NAME)

        me = client.get("/auth/me")
        assert me.status_code == 200, me.text
        assert me.json()["email"] == payload["email"]

        # Refresh should work from cookie (no form body required).
        refreshed = client.post("/auth/refresh")
        assert refreshed.status_code == 200, refreshed.text
        refreshed_payload = refreshed.json()
        assert refreshed_payload["access_token"]

        # Logout should clear cookies and make /me unauthenticated.
        logout = client.post("/auth/logout")
        assert logout.status_code == 200, logout.text

        # Some clients may keep cookies until the jar processes deletions.
        assert (
            client.cookies.get(settings.AUTH_COOKIE_ACCESS_NAME) is None
            or client.cookies.get(settings.AUTH_COOKIE_ACCESS_NAME) == ""
        )

        me_after = client.get("/auth/me")
        assert me_after.status_code == 401


def test_bearer_token_still_supported(db_session_factory):
    app = FastAPI()
    app.include_router(auth_router, prefix="/auth")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    payload = {
        "email": "bearer.user@example.com",
        "password": "correct-horse-battery-staple",
        "full_name": "Bearer User",
    }

    with TestClient(app) as client:
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 200, resp.text
        access_token = resp.json()["access_token"]

    # New client with no cookies.
    with TestClient(app) as bare_client:
        me = bare_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me.status_code == 200, me.text
        assert me.json()["email"] == payload["email"]
