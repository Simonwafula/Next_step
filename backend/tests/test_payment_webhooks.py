import hashlib
import hmac
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.payment_routes import router as payment_router
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User


def _create_test_app(db_session_factory):
    app = FastAPI()
    app.include_router(payment_router, prefix="/api/payments")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


def _create_basic_user(
    db_session_factory,
    email: str = "webhook.user@example.com",
):
    db = db_session_factory()
    user = User(
        uuid="payment-webhook-user",
        email=email,
        hashed_password="not-used",
        full_name="Webhook User",
        subscription_tier="basic",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    return user_id


def _sign_payload(secret: str, payload: bytes) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def test_stripe_webhook_rejects_missing_signature(
    db_session_factory,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "STRIPE_WEBHOOK_SECRET",
        "stripe-test-secret",
    )
    app = _create_test_app(db_session_factory)

    with TestClient(app) as client:
        response = client.post(
            "/api/payments/webhooks/stripe",
            json={
                "type": "checkout.session.completed",
                "data": {"object": {}},
            },
        )

    assert response.status_code == 403


def test_stripe_webhook_activates_subscription(
    db_session_factory,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "STRIPE_WEBHOOK_SECRET",
        "stripe-test-secret",
    )
    user_id = _create_basic_user(db_session_factory)
    app = _create_test_app(db_session_factory)

    body = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "user_id": str(user_id),
                    "plan_code": "professional_monthly",
                }
            }
        },
    }
    payload = json.dumps(body).encode("utf-8")
    signature = _sign_payload("stripe-test-secret", payload)

    with TestClient(app) as client:
        response = client.post(
            "/api/payments/webhooks/stripe",
            content=payload,
            headers={"Stripe-Signature": f"sha256={signature}"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    db = db_session_factory()
    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
    assert user.subscription_tier == "professional"
    assert user.subscription_expires is not None
    db.close()


def test_mpesa_webhook_activates_subscription(db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "MPESA_WEBHOOK_SECRET", "mpesa-test-secret")
    user_id = _create_basic_user(
        db_session_factory,
        email="mpesa.webhook.user@example.com",
    )
    app = _create_test_app(db_session_factory)

    body = {
        "status": "SUCCESS",
        "reference": {
            "user_id": user_id,
            "plan_code": "professional_monthly",
        },
    }
    payload = json.dumps(body).encode("utf-8")
    signature = _sign_payload("mpesa-test-secret", payload)

    with TestClient(app) as client:
        response = client.post(
            "/api/payments/webhooks/mpesa",
            content=payload,
            headers={"X-Mpesa-Signature": signature},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    db = db_session_factory()
    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
    assert user.subscription_tier == "professional"
    db.close()
