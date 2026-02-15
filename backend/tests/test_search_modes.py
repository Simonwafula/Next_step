from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import api_router
from app.db.database import get_db
from app.services.auth_service import get_current_user_optional


class _ProfileStub:
    def __init__(self):
        self.skills = {"Python": 0.9}
        self.education = "Bachelor's"
        self.current_role = "Data Analyst"


class _UserStub:
    def __init__(self):
        self.profile = _ProfileStub()


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


def test_search_mode_requires_auth_for_guided_results(
    db_session_factory,
    monkeypatch,
):
    app = _create_test_app(db_session_factory, current_user=None)

    monkeypatch.setattr(
        "app.api.routes.search_jobs",
        lambda *args, **kwargs: {
            "jobs": [{"id": 1, "title": "Data Analyst"}],
            "title_clusters": [],
            "companies_hiring": [],
            "total": 1,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        },
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/search",
            params={"q": "data", "mode": "explore"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["guided_results"] is None
    assert payload["mode"] is None
    assert payload["mode_error"] == "Authentication required for guided search"


def test_search_mode_returns_guided_results_for_authenticated_user(
    db_session_factory,
    monkeypatch,
):
    app = _create_test_app(db_session_factory, current_user=_UserStub())

    monkeypatch.setattr(
        "app.api.routes.search_jobs",
        lambda *args, **kwargs: {
            "jobs": [{"id": 1, "title": "Data Analyst"}],
            "title_clusters": [{"title": "Data Analyst", "count_ads": 1}],
            "companies_hiring": [{"title": "Data Analyst", "company": "Acme"}],
            "total": 1,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        },
    )

    monkeypatch.setattr(
        "app.api.routes.explore_careers",
        lambda db, query, limit: {
            "guided_results": [{"role_family": "data_analytics"}]
        },
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/search",
            params={"q": "data", "mode": "explore"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["guided_results"] == [{"role_family": "data_analytics"}]
    assert payload["mode"] == "explore"
    assert payload["mode_error"] is None
    assert payload["jobs"]
    assert payload["title_clusters"]
    assert payload["companies_hiring"]


def test_search_mode_match_uses_profile_skills_when_skills_missing(
    db_session_factory,
    monkeypatch,
):
    app = _create_test_app(db_session_factory, current_user=_UserStub())

    monkeypatch.setattr(
        "app.api.routes.search_jobs",
        lambda *args, **kwargs: {
            "jobs": [],
            "title_clusters": [],
            "companies_hiring": [],
            "total": 0,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        },
    )

    observed = {}

    def fake_match_roles(db, query, user_skills, education, limit):
        observed["user_skills"] = user_skills
        observed["education"] = education
        return {"guided_results": [{"role_family": "data_analytics"}]}

    monkeypatch.setattr("app.api.routes.match_roles", fake_match_roles)

    with TestClient(app) as client:
        response = client.get(
            "/api/search",
            params={"q": "data", "mode": "match"},
        )

    assert response.status_code == 200
    assert observed["user_skills"] == ["Python"]
    assert observed["education"] == "Bachelor's"
