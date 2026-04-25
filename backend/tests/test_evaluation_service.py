"""Tests for offline evaluation harness and intelligence quality dashboard.

Covers:
- T-DS-914 search + recommendation evaluation
- T-DS-915 intelligence quality dashboard
- T-DS-918 held-out ranking quality metrics
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.intelligence_routes import router as intelligence_router
from app.db.database import get_db
from app.db.models import (
    JobApplication,
    JobPost,
    Location,
    Organization,
    RoleDemandSnapshot,
    RoleSkillBaseline,
    SavedJob,
    SearchServingLog,
    TitleNorm,
    User,
    UserAnalytics,
    UserJobRecommendation,
)
from app.services.evaluation_service import (
    build_intelligence_quality_dashboard,
    evaluate_ranking_quality,
    evaluate_recommendations_offline,
    evaluate_search_offline,
)


def _build_app(db_session_factory):
    app = FastAPI()
    app.include_router(intelligence_router)

    def override_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return app


def _seed_common_entities(db):
    title_norm = TitleNorm(
        family="data_analytics",
        canonical_title="Data Analyst",
        aliases={},
    )
    location = Location(
        country="Kenya",
        region="Nairobi",
        city="Nairobi",
        raw="Nairobi, Kenya",
    )
    organization = Organization(name="Insight Labs", sector="technology", verified=True)
    user = User(
        uuid="eval-user",
        email="eval@example.com",
        hashed_password="hash",
        full_name="Eval User",
        is_active=True,
        is_verified=True,
    )
    db.add_all([title_norm, location, organization, user])
    db.flush()
    return title_norm, location, organization, user


def _seed_jobs(db, title_norm, location, organization, count: int = 8):
    now = datetime.utcnow()
    jobs = []
    for idx in range(count):
        job = JobPost(
            source="brightermonday",
            url=f"https://example.com/jobs/{idx}",
            url_hash=f"job-hash-{idx}",
            title_raw=f"Data Analyst {idx}",
            title_norm_id=title_norm.id,
            location_id=location.id,
            org_id=organization.id,
            first_seen=now - timedelta(days=idx + 1),
            is_active=True,
        )
        db.add(job)
        db.flush()
        jobs.append(job)
    return jobs


def test_evaluate_search_offline_computes_metrics(db_session_factory):
    db = db_session_factory()
    title_norm, location, organization, user = _seed_common_entities(db)
    jobs = _seed_jobs(db, title_norm, location, organization, count=5)
    now = datetime.utcnow()

    db.add_all(
        [
            SearchServingLog(
                user_id=user.id,
                session_id="search-1",
                query="data analyst",
                filters={},
                result_job_ids=[jobs[0].id, jobs[1].id, jobs[2].id],
                result_scores=[0.9, 0.8, 0.7],
                served_at=now - timedelta(days=2),
            ),
            SearchServingLog(
                user_id=user.id,
                session_id="search-2",
                query="analytics",
                filters={},
                result_job_ids=[jobs[3].id, jobs[4].id, jobs[2].id],
                result_scores=[0.88, 0.5, 0.4],
                served_at=now - timedelta(days=1),
            ),
            UserAnalytics(
                user_id=user.id,
                session_id="search-1",
                event_type="apply",
                event_data={"job_id": jobs[1].id},
                timestamp=now - timedelta(days=2) + timedelta(minutes=5),
            ),
            UserAnalytics(
                user_id=user.id,
                session_id="search-2",
                event_type="apply",
                event_data={"job_id": jobs[3].id},
                timestamp=now - timedelta(days=1) + timedelta(minutes=5),
            ),
        ]
    )
    db.commit()

    result = evaluate_search_offline(db, days_back=30, k=3)
    db.close()

    assert result["total_logged_searches"] == 2
    assert result["searches_with_positive_feedback"] == 2
    assert result["metrics"]["hit_rate_at_k"] == 1.0
    assert result["metrics"]["mrr_at_k"] == 0.75
    assert result["metrics"]["precision_at_k"] == 0.3333


def test_evaluate_recommendations_offline_uses_outcome_signals(db_session_factory):
    db = db_session_factory()
    title_norm, location, organization, user = _seed_common_entities(db)
    jobs = _seed_jobs(db, title_norm, location, organization, count=4)
    now = datetime.utcnow()

    db.add_all(
        [
            UserJobRecommendation(
                user_id=user.id,
                job_post_id=jobs[0].id,
                match_score=0.95,
                skill_match_score=0.9,
                location_match_score=0.9,
                salary_match_score=0.9,
                experience_match_score=0.9,
                matching_skills=["sql"],
                missing_skills=[],
                recommended_at=now - timedelta(days=2),
            ),
            UserJobRecommendation(
                user_id=user.id,
                job_post_id=jobs[1].id,
                match_score=0.85,
                skill_match_score=0.8,
                location_match_score=0.8,
                salary_match_score=0.8,
                experience_match_score=0.8,
                matching_skills=["python"],
                missing_skills=["excel"],
                clicked=True,
                recommended_at=now - timedelta(days=2),
            ),
            UserJobRecommendation(
                user_id=user.id,
                job_post_id=jobs[2].id,
                match_score=0.75,
                skill_match_score=0.7,
                location_match_score=0.7,
                salary_match_score=0.7,
                experience_match_score=0.7,
                matching_skills=["power bi"],
                missing_skills=["sql"],
                recommended_at=now - timedelta(days=2),
            ),
            SavedJob(
                user_id=user.id,
                job_post_id=jobs[0].id,
                saved_at=now - timedelta(days=1),
            ),
            JobApplication(
                user_id=user.id,
                job_post_id=jobs[2].id,
                applied_at=now - timedelta(days=1),
            ),
        ]
    )
    db.commit()

    result = evaluate_recommendations_offline(db, days_back=30, k=3)
    db.close()

    assert result["recommendations_total"] == 3
    assert result["users_with_positive_feedback"] == 1
    assert result["click_rate_pct"] == 33.3
    assert result["apply_rate_pct"] == 33.3
    assert result["save_rate_pct"] == 33.3
    assert result["metrics"]["precision_at_k"] == 1.0
    assert result["metrics"]["hit_rate_at_k"] == 1.0


def test_evaluate_ranking_quality_splits_holdout_sessions(db_session_factory):
    db = db_session_factory()
    title_norm, location, organization, user = _seed_common_entities(db)
    jobs = _seed_jobs(db, title_norm, location, organization, count=6)
    now = datetime.utcnow()

    for idx in range(5):
        session_id = f"holdout-{idx}"
        db.add(
            SearchServingLog(
                user_id=user.id,
                session_id=session_id,
                query="data analyst",
                filters={},
                result_job_ids=[
                    jobs[idx].id,
                    jobs[(idx + 1) % 6].id,
                    jobs[(idx + 2) % 6].id,
                ],
                result_scores=[0.9, 0.8, 0.7],
                served_at=now - timedelta(days=5 - idx),
            )
        )
        db.add(
            UserAnalytics(
                user_id=user.id,
                session_id=session_id,
                event_type="apply",
                event_data={"job_id": jobs[idx].id},
                timestamp=now - timedelta(days=5 - idx) + timedelta(minutes=10),
            )
        )
    db.commit()

    result = evaluate_ranking_quality(db, days_back=30, k=3, holdout_fraction=0.4)
    db.close()

    assert result["searches_with_positive_feedback"] == 5
    assert result["holdout_examples"] == 2
    assert result["metrics"]["overall"]["mrr_at_k"] == 1.0
    assert result["metrics"]["holdout"]["hit_rate_at_k"] == 1.0


def test_intelligence_quality_dashboard_surfaces_metadata(db_session_factory):
    db = db_session_factory()
    title_norm, location, organization, _user = _seed_common_entities(db)
    _seed_jobs(db, title_norm, location, organization, count=5)
    db.add_all(
        [
            RoleSkillBaseline(
                role_family="data_analytics",
                skill_name="SQL",
                skill_share=0.8,
                low_confidence=False,
                count_total_jobs_used=55,
            ),
            RoleSkillBaseline(
                role_family="data_analytics",
                skill_name="Python",
                skill_share=0.7,
                low_confidence=False,
                count_total_jobs_used=55,
            ),
            RoleDemandSnapshot(
                role_family="data_analytics",
                demand_count=55,
                low_confidence=False,
                count_total_jobs_used=55,
            ),
        ]
    )
    db.commit()

    result = build_intelligence_quality_dashboard(db, window_days=180)
    db.close()

    assert result["summary"]["sample_size"] == 5
    assert result["baseline_health"]["tables"]["role_skill_baseline"]["row_count"] == 2
    assert result["market_metadata"]["source_mix"][0]["source"] == "brightermonday"
    assert result["role_family_quality"][0]["confidence_tier"] == "medium"


def test_intelligence_evaluation_routes(db_session_factory):
    db = db_session_factory()
    title_norm, location, organization, user = _seed_common_entities(db)
    jobs = _seed_jobs(db, title_norm, location, organization, count=4)
    now = datetime.utcnow()

    db.add_all(
        [
            RoleSkillBaseline(
                role_family="data_analytics",
                skill_name="SQL",
                skill_share=0.8,
                low_confidence=False,
                count_total_jobs_used=40,
            ),
            RoleDemandSnapshot(
                role_family="data_analytics",
                demand_count=40,
                low_confidence=False,
                count_total_jobs_used=40,
            ),
            SearchServingLog(
                user_id=user.id,
                session_id="route-search",
                query="analyst",
                filters={},
                result_job_ids=[jobs[0].id, jobs[1].id, jobs[2].id],
                result_scores=[0.9, 0.8, 0.7],
                served_at=now - timedelta(days=1),
            ),
            UserAnalytics(
                user_id=user.id,
                session_id="route-search",
                event_type="apply",
                event_data={"job_id": jobs[1].id},
                timestamp=now - timedelta(days=1) + timedelta(minutes=5),
            ),
            UserJobRecommendation(
                user_id=user.id,
                job_post_id=jobs[0].id,
                match_score=0.92,
                skill_match_score=0.9,
                location_match_score=0.9,
                salary_match_score=0.9,
                experience_match_score=0.9,
                matching_skills=["sql"],
                missing_skills=[],
                clicked=True,
                recommended_at=now - timedelta(days=1),
            ),
        ]
    )
    db.commit()
    db.close()

    client = TestClient(_build_app(db_session_factory))

    search_resp = client.get("/api/intelligence/evaluation/search?days_back=30&k=3")
    assert search_resp.status_code == 200
    assert search_resp.json()["metrics"]["hit_rate_at_k"] == 1.0

    rec_resp = client.get(
        "/api/intelligence/evaluation/recommendations?days_back=30&k=3"
    )
    assert rec_resp.status_code == 200
    assert rec_resp.json()["users_with_positive_feedback"] == 1

    ranking_resp = client.get(
        "/api/intelligence/evaluation/ranking-quality?days_back=30&k=3"
    )
    assert ranking_resp.status_code == 200
    assert "holdout" in ranking_resp.json()["metrics"]

    dashboard_resp = client.get("/api/intelligence/quality-dashboard?window_days=180")
    assert dashboard_resp.status_code == 200
    payload = dashboard_resp.json()
    assert "baseline_health" in payload
    assert "market_metadata" in payload
