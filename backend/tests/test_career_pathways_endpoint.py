from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.routes import api_router
from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import get_current_user


def _create_test_app(
    db_session_factory=None,
    current_user_id: int | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(api_router, prefix="/api")

    if db_session_factory and current_user_id is not None:
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


def _create_user(db_session_factory, email: str, tier: str) -> int:
    db = db_session_factory()
    user = User(
        uuid=f"pathways-{tier}-user",
        email=email,
        hashed_password="not-used",
        full_name="Pathways User",
        subscription_tier=tier,
        subscription_expires=datetime(2099, 1, 1),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    return user_id


def test_career_pathway_returns_role_specific_roadmap_for_professional_user(
    db_session_factory,
):
    user_id = _create_user(
        db_session_factory,
        email="pathways.professional@example.com",
        tier="professional",
    )
    app = _create_test_app(db_session_factory, user_id)

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


def test_career_pathway_unknown_role_returns_404_for_professional_user(
    db_session_factory,
):
    user_id = _create_user(
        db_session_factory,
        email="pathways.professional.unknown@example.com",
        tier="professional",
    )
    app = _create_test_app(db_session_factory, user_id)

    with TestClient(app) as client:
        response = client.get("/api/career-pathways/unknown-role")

    assert response.status_code == 404
    assert response.json()["detail"] == "Career pathway not found"


def test_career_pathway_requires_authentication():
    app = _create_test_app()

    with TestClient(app) as client:
        response = client.get("/api/career-pathways/data-analyst")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_career_pathway_requires_professional_subscription(db_session_factory):
    user_id = _create_user(
        db_session_factory,
        email="pathways.basic@example.com",
        tier="basic",
    )
    app = _create_test_app(db_session_factory, user_id)

    with TestClient(app) as client:
        response = client.get("/api/career-pathways/data-analyst")

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "This feature requires professional subscription"
    )
