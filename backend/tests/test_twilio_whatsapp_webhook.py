from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import get_db
from app.webhooks.whatsapp import router as whatsapp_router


def test_twilio_webhook_rejects_missing_signature(db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_VALIDATE_WEBHOOK_SIGNATURE", True)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "test_auth_token")
    monkeypatch.setattr(settings, "TWILIO_WEBHOOK_URL", "")

    app = FastAPI()
    app.include_router(whatsapp_router, prefix="/whatsapp")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        resp = client.post("/whatsapp/webhook", data={})
        assert resp.status_code == 403


def test_twilio_webhook_accepts_valid_signature(db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_VALIDATE_WEBHOOK_SIGNATURE", True)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "test_auth_token")
    monkeypatch.setattr(settings, "TWILIO_WEBHOOK_URL", "")

    app = FastAPI()
    app.include_router(whatsapp_router, prefix="/whatsapp")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    params = {"Body": ""}  # empty body triggers the early-return branch (no DB usage)
    url = "http://testserver/whatsapp/webhook"

    from twilio.request_validator import RequestValidator

    signature = RequestValidator(settings.TWILIO_AUTH_TOKEN).compute_signature(
        url, params
    )

    with TestClient(app) as client:
        resp = client.post(
            "/whatsapp/webhook",
            data=params,
            headers={"X-Twilio-Signature": signature},
        )
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert "message" in payload


def test_twilio_webhook_allows_unsigned_when_disabled(db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_VALIDATE_WEBHOOK_SIGNATURE", False)

    app = FastAPI()
    app.include_router(whatsapp_router, prefix="/whatsapp")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        resp = client.post("/whatsapp/webhook", data={"Body": ""})
        assert resp.status_code == 200, resp.text
