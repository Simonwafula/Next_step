"""Tests for T-DS-910 (instrumentation) and T-DS-920 (intelligence baseline repair).

Covers:
- SearchServingLog model and log_search_serving helper (T-DS-911)
- ApplicationFunnelEvent model (T-DS-912/913)
- Real recency and description features in extract_ranking_features (T-DS-917)
- generate_role_evolution stub replaced with real computation (T-DS-921)
- aggregate_skill_trends computes real share values (T-DS-922)
- get_intelligence_metadata returns standardised provenance block (T-DS-925)
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import (
    ApplicationFunnelEvent,
    Base,
    JobApplication,
    JobEntities,
    JobPost,
    RoleEvolution,
    SearchServingLog,
    SkillTrendsMonthly,
    TitleNorm,
    User,
)
from app.services.analytics import (
    aggregate_skill_trends,
    generate_role_evolution,
    get_intelligence_metadata,
)
from app.services.ranking import (
    _recency_score,
    _token_overlap,
    extract_ranking_features,
)
from app.services.search import log_search_serving


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# Ranking feature helpers (T-DS-917)
# ---------------------------------------------------------------------------


def test_token_overlap_exact():
    assert _token_overlap("python developer", "python developer") == 1.0


def test_token_overlap_partial():
    result = _token_overlap("python", "python developer")
    assert 0.0 < result < 1.0


def test_token_overlap_no_match():
    assert _token_overlap("frontend", "backend engineer") == 0.0


def test_token_overlap_empty():
    assert _token_overlap("", "python") == 0.0
    assert _token_overlap("python", "") == 0.0


def test_recency_score_today():
    score = _recency_score(datetime.utcnow())
    assert score == pytest.approx(1.0, abs=0.02)


def test_recency_score_old():
    old = datetime.utcnow() - timedelta(days=200)
    score = _recency_score(old)
    assert score == 0.0


def test_recency_score_midpoint():
    mid = datetime.utcnow() - timedelta(days=90)
    score = _recency_score(mid)
    assert 0.0 < score < 1.0


def test_recency_score_none_returns_neutral():
    assert _recency_score(None) == 0.5


def test_recency_score_iso_string():
    recent = (datetime.utcnow() - timedelta(days=10)).isoformat()
    score = _recency_score(recent)
    assert score > 0.9


def test_extract_ranking_features_recency_populated():
    """Feature[3] (recency) is populated from first_seen, not hardcoded 0.5."""
    result = {
        "title": "Engineer",
        "first_seen": datetime.utcnow() - timedelta(days=5),
        "similarity_score": 60.0,
    }
    features = extract_ranking_features(result, "")
    assert features[3] > 0.9  # very recent posting


def test_extract_ranking_features_desc_match():
    """Feature[2] (desc_match) fires on description token overlap."""
    result = {
        "title": "Engineer",
        "description": "Python Django REST API developer",
        "similarity_score": 60.0,
    }
    features = extract_ranking_features(result, "python api")
    assert features[2] > 0.0


def test_extract_ranking_features_skill_overlap():
    """Feature[7] (skill_overlap) uses user skills vs job skills."""
    result = {
        "title": "Engineer",
        "similarity_score": 60.0,
        "skills": [{"value": "python"}, {"value": "sql"}],
    }
    user_context = {"skills": ["Python", "SQL", "Excel"]}
    features = extract_ranking_features(result, "", user_context)
    assert features[7] > 0.0


def test_extract_ranking_features_skill_overlap_no_match():
    result = {
        "title": "Engineer",
        "similarity_score": 60.0,
        "skills": [{"value": "java"}],
    }
    user_context = {"skills": ["Python", "SQL"]}
    features = extract_ranking_features(result, "", user_context)
    assert features[7] == 0.0


# ---------------------------------------------------------------------------
# SearchServingLog model + log_search_serving (T-DS-911)
# ---------------------------------------------------------------------------


def test_search_serving_log_model_exists(db):
    row = SearchServingLog(
        query="python developer",
        filters={"location": "Nairobi"},
        result_job_ids=[1, 2, 3],
        result_scores=[0.9, 0.7, 0.5],
        mode="standard",
    )
    db.add(row)
    db.commit()
    assert row.id is not None


def test_log_search_serving_persists(db):
    results = [
        {"id": 10, "similarity_score": 85.0},
        {"id": 11, "similarity_score": 60.0},
    ]
    log_search_serving(
        db,
        query="data analyst",
        filters={"seniority": "entry"},
        results=results,
        mode="standard",
    )
    rows = db.query(SearchServingLog).all()
    assert len(rows) == 1
    assert rows[0].query == "data analyst"
    assert rows[0].result_job_ids == [10, 11]
    # Scores are normalised to [0,1]
    assert rows[0].result_scores[0] == pytest.approx(0.85)


def test_log_search_serving_empty_results_is_safe(db):
    log_search_serving(db, query="", filters={}, results=[], mode="standard")
    rows = db.query(SearchServingLog).all()
    assert len(rows) == 1
    assert rows[0].result_job_ids == []


# ---------------------------------------------------------------------------
# ApplicationFunnelEvent model (T-DS-912/913)
# ---------------------------------------------------------------------------


def _seed_user_and_application(db):
    user = User(
        email="funnel@test.com",
        hashed_password="x",
        full_name="Funnel Test",
    )
    db.add(user)
    db.flush()

    job = JobPost(source="test", url="http://test.com/1", title_raw="Dev")
    db.add(job)
    db.flush()

    app = JobApplication(user_id=user.id, job_post_id=job.id, status="applied")
    db.add(app)
    db.flush()
    return user, job, app


def test_application_funnel_event_model_stores_stage(db):
    user, job, app = _seed_user_and_application(db)
    event = ApplicationFunnelEvent(
        application_id=app.id,
        user_id=user.id,
        job_post_id=job.id,
        stage="shortlisted",
        actor="employer",
        reason=None,
    )
    db.add(event)
    db.commit()
    assert event.id is not None
    assert event.stage == "shortlisted"


def test_application_funnel_event_rejection_reason(db):
    user, job, app = _seed_user_and_application(db)
    event = ApplicationFunnelEvent(
        application_id=app.id,
        user_id=user.id,
        job_post_id=job.id,
        stage="rejected",
        actor="employer",
        reason="skills_mismatch",
        details="Missing 3+ years Python experience",
    )
    db.add(event)
    db.commit()
    loaded = db.query(ApplicationFunnelEvent).filter_by(id=event.id).one()
    assert loaded.reason == "skills_mismatch"
    assert "Python" in loaded.details


# ---------------------------------------------------------------------------
# generate_role_evolution — real computation replacing stub (T-DS-921)
# ---------------------------------------------------------------------------


def _seed_jobs_with_entities(db, family: str, n: int):
    tn = TitleNorm(family=family, canonical_title=family, aliases={})
    db.add(tn)
    db.flush()
    for i in range(n):
        job = JobPost(
            source="test",
            url=f"http://test.com/{family}/{i}",
            title_raw=family,
            title_norm_id=tn.id,
            first_seen=datetime.utcnow() - timedelta(days=i),
            is_active=True,
        )
        db.add(job)
        db.flush()
        skills = [{"value": "python"}, {"value": "sql"}]
        if i % 2 == 0:
            skills.append({"value": "excel"})
        entity = JobEntities(job_id=job.id, skills=skills)
        db.add(entity)
    db.commit()
    return tn


def test_generate_role_evolution_populates_table(db):
    _seed_jobs_with_entities(db, "software_engineer", 5)
    result = generate_role_evolution(db)
    assert result["status"] == "success"
    assert result["rows_inserted"] > 0

    rows = db.query(RoleEvolution).all()
    assert len(rows) > 0
    for row in rows:
        assert isinstance(row.top_skills, dict)
        assert "python" in row.top_skills


def test_generate_role_evolution_empty_db_returns_warning(db):
    result = generate_role_evolution(db)
    assert result["status"] == "warning"


def test_generate_role_evolution_uses_top_k(db):
    # Seed 15 distinct skill mentions; top_k=5 should limit output
    tn = TitleNorm(family="analyst", canonical_title="analyst", aliases={})
    db.add(tn)
    db.flush()
    job = JobPost(
        source="t",
        url="http://t.com/1",
        title_raw="analyst",
        title_norm_id=tn.id,
        first_seen=datetime.utcnow(),
        is_active=True,
    )
    db.add(job)
    db.flush()
    skills = [{"value": f"skill_{i}"} for i in range(15)]
    db.add(JobEntities(job_id=job.id, skills=skills))
    db.commit()

    generate_role_evolution(db, top_k=5)
    row = db.query(RoleEvolution).first()
    assert len(row.top_skills) <= 5


# ---------------------------------------------------------------------------
# aggregate_skill_trends — real share computation (T-DS-922)
# ---------------------------------------------------------------------------


def test_aggregate_skill_trends_computes_real_share(db):
    _seed_jobs_with_entities(db, "data_analyst", 4)
    result = aggregate_skill_trends(db)
    assert result["status"] == "success"

    rows = db.query(SkillTrendsMonthly).all()
    # All shares should be > 0.0 (no longer hardcoded 0.0)
    assert all(r.share > 0.0 for r in rows)
    # Shares within a (month, family) group should sum to ~1.0
    from collections import defaultdict

    bucket_shares: dict = defaultdict(float)
    for r in rows:
        key = (r.month.strftime("%Y-%m"), r.title_norm)
        bucket_shares[key] += r.share
    for total in bucket_shares.values():
        assert abs(total - 1.0) < 0.02, f"Shares should sum to ~1.0, got {total}"


# ---------------------------------------------------------------------------
# get_intelligence_metadata — standardised provenance (T-DS-925)
# ---------------------------------------------------------------------------


def test_get_intelligence_metadata_returns_all_keys(db):
    _seed_jobs_with_entities(db, "marketing", 3)
    meta = get_intelligence_metadata(db, window_days=365)
    assert "sample_size" in meta
    assert "date_range" in meta
    assert "source_mix" in meta
    assert "confidence_note" in meta
    assert meta["date_range"]["window_days"] == 365


def test_get_intelligence_metadata_low_sample_flags_low_confidence(db):
    # Only 2 jobs — below low threshold of 30
    _seed_jobs_with_entities(db, "rare_role", 2)
    meta = get_intelligence_metadata(db, role_family="rare_role", window_days=365)
    assert "low" in meta["confidence_note"]


def test_get_intelligence_metadata_high_sample_flags_high(db):
    _seed_jobs_with_entities(db, "big_role", 110)
    meta = get_intelligence_metadata(db, role_family="big_role", window_days=365)
    assert meta["confidence_note"] == "high"
