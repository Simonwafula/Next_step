from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import api_router


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    return app


def test_career_pathway_returns_role_specific_roadmap():
    app = _create_test_app()

    with TestClient(app) as client:
        response = client.get("/api/career-pathways/data-analyst")

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["role_slug"] == "data-analyst"
    assert payload["title"]
    assert isinstance(payload["required_skills"], list)
    assert len(payload["required_skills"]) > 0
    assert isinstance(payload["experience_ladder"], list)
    assert len(payload["experience_ladder"]) >= 3
    assert isinstance(payload["learning_resources"], list)


def test_career_pathway_unknown_role_returns_404():
    app = _create_test_app()

    with TestClient(app) as client:
        response = client.get("/api/career-pathways/unknown-role")

    assert response.status_code == 404
    assert response.json()["detail"] == "Career pathway not found"
