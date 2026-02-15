from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.user_routes import router as user_router
from app.db.database import get_db
from app.db.models import User
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


def _create_basic_user(db_session_factory) -> int:
    db = db_session_factory()
    user = User(
        uuid="paywall-basic-user",
        email="paywall.basic@example.com",
        hashed_password="not-used",
        full_name="Paywall Basic User",
        subscription_tier="basic",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    return user_id


def test_subscription_plans_returns_catalog(db_session_factory):
    user_id = _create_basic_user(db_session_factory)
    app = _create_test_app(db_session_factory, user_id)

    with TestClient(app) as client:
        response = client.get("/api/users/subscription/plans")

    assert response.status_code == 200
    payload = response.json()
    assert "plans" in payload
    assert any(
        plan["code"] == "professional_monthly" for plan in payload["plans"]
    )


def test_subscription_checkout_returns_checkout_url(db_session_factory):
    user_id = _create_basic_user(db_session_factory)
    app = _create_test_app(db_session_factory, user_id)

    with TestClient(app) as client:
        response = client.post(
            "/api/users/subscription/checkout",
            json={"plan_code": "professional_monthly", "provider": "stripe"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_code"] == "professional_monthly"
    assert payload["provider"] == "stripe"
    assert payload["status"] == "pending"
    assert payload["checkout_url"].startswith("https://")


def test_subscription_checkout_rejects_unsupported_provider(
    db_session_factory,
):
    user_id = _create_basic_user(db_session_factory)
    app = _create_test_app(db_session_factory, user_id)

    with TestClient(app) as client:
        response = client.post(
            "/api/users/subscription/checkout",
            json={"plan_code": "professional_monthly", "provider": "paypal"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported payment provider"


def test_subscription_activate_upgrades_user_tier(db_session_factory):
    user_id = _create_basic_user(db_session_factory)
    app = _create_test_app(db_session_factory, user_id)

    with TestClient(app) as client:
        response = client.post(
            "/api/users/subscription/activate",
            json={"plan_code": "professional_monthly"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["subscription_tier"] == "professional"
    assert payload["plan_code"] == "professional_monthly"

    db = db_session_factory()
    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
    assert user.subscription_tier == "professional"
    assert user.subscription_expires is not None
    assert user.subscription_expires > datetime.utcnow()
    db.close()
