from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.redirect_routes import router as redirect_router
from app.db.database import get_db
from app.db.models import JobPost, UserAnalytics
from app.services.auth_service import get_current_user_optional


def test_apply_redirect_logs_and_redirects(db_session_factory):
    app = FastAPI()
    app.include_router(redirect_router)

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    async def override_current_user_optional():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_optional] = override_current_user_optional

    db = db_session_factory()
    job = JobPost(
        source="test",
        url="https://example.com/source/1",
        source_url="https://example.com/source/1",
        application_url="https://example.com/apply/1",
        title_raw="Example Role",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    db.close()

    with TestClient(app) as client:
        resp = client.get(f"/r/apply/{job.id}", follow_redirects=False)

        assert resp.status_code == 307
        assert resp.headers["location"] == "https://example.com/apply/1"
        assert "set-cookie" in {k.lower() for k in resp.headers.keys()}

    db = db_session_factory()
    events = db.query(UserAnalytics).all()
    assert len(events) == 1
    assert events[0].event_type == "apply"
    assert (events[0].event_data or {}).get("job_id") == job.id
    db.close()
