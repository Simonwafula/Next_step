"""Tests for admin dedup, moderation, audit, and system-events endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin_dedup_routes import router as dedup_router
from app.api.admin_moderation_routes import router as moderation_router
from app.api.admin_audit_routes import router as audit_router
from app.db.database import get_db
from app.db.models import (
    CompanyReview,
    JobDedupeMap,
    JobPost,
    Organization,
    ProcessingLog,
    User,
)
from app.services.auth_service import get_current_user


# ── Fixtures ──────────────────────────────────────────────


@pytest.fixture()
def admin_user(db_session_factory):
    db = db_session_factory()
    user = User(
        uuid="admin-sections-uuid",
        email="admin-sections@test.local",
        hashed_password="not-used",
        full_name="Section Admin",
        is_active=True,
        is_verified=True,
        subscription_tier="enterprise",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _make_app(db_session_factory, admin_user, monkeypatch, *routers):
    """Build a test FastAPI app with given routers and overrides."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ADMIN_EMAILS", admin_user.email)

    application = FastAPI()
    for r in routers:
        application.include_router(r)

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    async def override_get_current_user():
        return admin_user

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_current_user] = override_get_current_user
    return application


# ── Dedup endpoints ──────────────────────────────────────


@pytest.fixture()
def dedup_app(db_session_factory, admin_user, monkeypatch):
    return _make_app(db_session_factory, admin_user, monkeypatch, dedup_router)


@pytest.fixture()
def seed_dedup(db_session_factory):
    db = db_session_factory()
    org = Organization(name="TestCorp")
    db.add(org)
    db.flush()

    job_a = JobPost(
        title_raw="Software Engineer",
        source="test",
        url="https://test.local/1",
        org_id=org.id,
    )
    job_b = JobPost(
        title_raw="Software Eng.",
        source="test",
        url="https://test.local/2",
        org_id=org.id,
    )
    db.add_all([job_a, job_b])
    db.flush()

    entry = JobDedupeMap(
        job_id=job_a.id,
        canonical_job_id=job_b.id,
        similarity_score=0.92,
        status="pending",
    )
    db.add(entry)
    db.commit()
    result = {"job_a_id": job_a.id, "job_b_id": job_b.id}
    db.close()
    return result


def test_dedup_candidates_empty(dedup_app):
    with TestClient(dedup_app) as client:
        resp = client.get("/api/admin/dedup/candidates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["candidates"] == []
        assert data["total"] == 0


def test_dedup_candidates_with_data(dedup_app, seed_dedup):
    with TestClient(dedup_app) as client:
        resp = client.get("/api/admin/dedup/candidates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["similarity"] == 0.92


def test_dedup_stats(dedup_app, seed_dedup):
    with TestClient(dedup_app) as client:
        resp = client.get("/api/admin/dedup/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pending"] == 1
        assert data["merged"] == 0


def test_dedup_merge(dedup_app, seed_dedup):
    job_id = seed_dedup["job_a_id"]
    with TestClient(dedup_app) as client:
        resp = client.post(f"/api/admin/dedup/merge?job_id={job_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "merged"

        # Stats should update
        stats = client.get("/api/admin/dedup/stats").json()
        assert stats["merged"] == 1
        assert stats["pending"] == 0


def test_dedup_dismiss(dedup_app, seed_dedup):
    job_id = seed_dedup["job_a_id"]
    with TestClient(dedup_app) as client:
        resp = client.post(f"/api/admin/dedup/dismiss?job_id={job_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "dismissed"


def test_dedup_merge_not_found(dedup_app):
    with TestClient(dedup_app) as client:
        resp = client.post("/api/admin/dedup/merge?job_id=99999")
        assert resp.status_code == 404


def test_dedup_double_action(dedup_app, seed_dedup):
    job_id = seed_dedup["job_a_id"]
    with TestClient(dedup_app) as client:
        client.post(f"/api/admin/dedup/merge?job_id={job_id}")
        resp = client.post(f"/api/admin/dedup/dismiss?job_id={job_id}")
        assert resp.status_code == 400


# ── Moderation endpoints ──────────────────────────────────


@pytest.fixture()
def moderation_app(db_session_factory, admin_user, monkeypatch):
    return _make_app(db_session_factory, admin_user, monkeypatch, moderation_router)


@pytest.fixture()
def seed_reviews(db_session_factory):
    db = db_session_factory()
    org = Organization(name="ReviewCorp")
    db.add(org)
    db.flush()

    reviews = [
        CompanyReview(
            organization_id=org.id,
            title=f"Review {i}",
            review_text=f"Review text {i}",
            overall_rating=3.5,
            moderation_status="pending",
        )
        for i in range(3)
    ]
    db.add_all(reviews)
    db.commit()
    ids = [r.id for r in reviews]
    db.close()
    return ids


def test_moderation_queue_empty(moderation_app):
    with TestClient(moderation_app) as client:
        resp = client.get("/api/admin/moderation/queue")
        assert resp.status_code == 200
        assert resp.json()["items"] == []


def test_moderation_queue_with_data(moderation_app, seed_reviews):
    with TestClient(moderation_app) as client:
        resp = client.get("/api/admin/moderation/queue")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 3


def test_moderation_approve(moderation_app, seed_reviews):
    rid = seed_reviews[0]
    with TestClient(moderation_app) as client:
        resp = client.post(f"/api/admin/moderation/{rid}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"


def test_moderation_reject(moderation_app, seed_reviews):
    rid = seed_reviews[1]
    with TestClient(moderation_app) as client:
        resp = client.post(
            f"/api/admin/moderation/{rid}/reject",
            json={"notes": "Spam content"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"


def test_moderation_stats(moderation_app, seed_reviews):
    with TestClient(moderation_app) as client:
        # Approve one
        client.post(f"/api/admin/moderation/{seed_reviews[0]}/approve")
        resp = client.get("/api/admin/moderation/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["approved"] == 1
        assert data["pending"] == 2


def test_moderation_not_found(moderation_app):
    with TestClient(moderation_app) as client:
        resp = client.post("/api/admin/moderation/99999/approve")
        assert resp.status_code == 404


# ── Audit & System Events endpoints ──────────────────────


@pytest.fixture()
def audit_app(db_session_factory, admin_user, monkeypatch):
    return _make_app(db_session_factory, admin_user, monkeypatch, audit_router)


@pytest.fixture()
def seed_logs(db_session_factory):
    db = db_session_factory()
    logs = [
        ProcessingLog(
            process_type="monitoring",
            results={
                "status": "success",
                "message": "Health check OK",
                "details": {"triggered_by": "admin@test.local"},
            },
        ),
        ProcessingLog(
            process_type="post_processing",
            results={
                "status": "error",
                "message": "Processing failed",
                "details": {"count": 42},
            },
        ),
        ProcessingLog(
            process_type="ingestion",
            results={
                "status": "success",
                "message": "Ingested 100 jobs",
            },
        ),
    ]
    db.add_all(logs)
    db.commit()
    db.close()


def test_audit_log_empty(audit_app):
    with TestClient(audit_app) as client:
        resp = client.get("/api/admin/audit-log")
        assert resp.status_code == 200
        assert resp.json()["entries"] == []


def test_audit_log_with_data(audit_app, seed_logs):
    with TestClient(audit_app) as client:
        resp = client.get("/api/admin/audit-log")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) == 3
        assert data["total"] == 3


def test_audit_log_filter(audit_app, seed_logs):
    with TestClient(audit_app) as client:
        resp = client.get("/api/admin/audit-log?action_filter=monitoring")
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["action"] == "monitoring"


def test_system_events_empty(audit_app):
    with TestClient(audit_app) as client:
        resp = client.get("/api/admin/system-events")
        assert resp.status_code == 200
        assert resp.json()["events"] == []


def test_system_events_with_data(audit_app, seed_logs):
    with TestClient(audit_app) as client:
        resp = client.get("/api/admin/system-events")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 3


def test_system_events_level_filter(audit_app, seed_logs):
    with TestClient(audit_app) as client:
        resp = client.get("/api/admin/system-events?level=error")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 1
        assert events[0]["level"] == "error"
