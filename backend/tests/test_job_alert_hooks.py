from datetime import datetime, timedelta

from app.db.models import JobAlert, User, UserNotification
from app.tasks.processing_tasks import _process_job_alerts_sync


def test_job_alert_hooks_send_email_and_whatsapp(db_session_factory, monkeypatch):
    db = db_session_factory()
    user = User(
        uuid="user-uuid",
        email="user@test.local",
        hashed_password="not-used",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        whatsapp_number="+254700000000",
    )
    db.add(user)
    db.flush()

    alert = JobAlert(
        user_id=user.id,
        name="Backend Jobs",
        query="backend",
        filters={"location": "nairobi"},
        frequency="daily",
        delivery_methods=["email", "whatsapp"],
        is_active=True,
    )
    db.add(alert)
    db.commit()

    now = datetime.utcnow()
    job_payload = {
        "id": 1,
        "title": "Backend Engineer",
        "organization": "Acme",
        "location": "Nairobi",
        "url": "https://example.com/job/1",
        "first_seen": (now - timedelta(hours=1)).isoformat(),
    }

    def fake_search_jobs(*_args, **_kwargs):
        return [job_payload]

    async def fake_whatsapp_send(_to, _message):
        return True

    monkeypatch.setattr(
        "app.services.search.search_jobs",
        fake_search_jobs,
    )
    monkeypatch.setattr(
        "app.tasks.processing_tasks.SessionLocal",
        db_session_factory,
    )
    monkeypatch.setattr(
        "app.webhooks.whatsapp.send_whatsapp_message",
        fake_whatsapp_send,
    )
    monkeypatch.setattr(
        "app.tasks.processing_tasks.send_email",
        lambda *_args, **_kwargs: True,
    )

    result = _process_job_alerts_sync("daily")
    assert result["notifications_sent"] >= 1

    notification = (
        db.query(UserNotification).filter(UserNotification.user_id == user.id).one()
    )
    assert "email" in (notification.delivered_via or [])
    assert "whatsapp" in (notification.delivered_via or [])
    assert notification.delivery_status.get("email") == "sent"
    assert notification.delivery_status.get("whatsapp") == "sent"
    db.close()
