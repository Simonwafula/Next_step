"""Tests for T-DS-970: Production-grade intelligence products.

Covers T-DS-971, T-DS-972, T-DS-973, T-DS-974.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.intelligence_routes import router as intelligence_router
from app.db.database import get_db
from app.db.models import (
    JobPost,
    Location,
    Organization,
    RoleDemandSnapshot,
    RoleEducationBaseline,
    RoleExperienceBaseline,
    RoleSkillBaseline,
    TitleNorm,
)
from app.services.intelligence_products import (
    _confidence_tier,
    build_county_report,
    build_employer_report,
    build_training_provider_report,
    build_university_report,
    get_baseline_health,
    get_confidence_aware_skill_baseline,
    get_salary_confidence_summary,
    get_salary_low_confidence_log,
    get_salary_with_market_context,
)


# ---------------------------------------------------------------------------
# App factory for HTTP tests
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(db_session_factory):
    session = db_session_factory()
    yield session
    session.close()


@pytest.fixture()
def seeded_db(db_session_factory):
    """Seed minimal baseline + job post data for intelligence tests."""
    db = db_session_factory()

    # Title norm
    tn = TitleNorm(
        family="software_engineering", canonical_title="Software Engineer", aliases={}
    )
    db.add(tn)
    db.flush()

    # Location
    loc = Location(
        country="Kenya", region="Nairobi", city="Nairobi", raw="Nairobi, Kenya"
    )
    db.add(loc)
    db.flush()

    # Org
    org = Organization(name="TechCo", sector="technology", verified=True)
    db.add(org)
    db.flush()

    # Job posts with salary
    for i in range(15):
        jp = JobPost(
            source="test",
            url=f"https://jobs.example.com/{i}",
            title_raw="Software Engineer",
            title_norm_id=tn.id,
            location_id=loc.id,
            org_id=org.id,
            salary_min=80000 + i * 5000,
            salary_max=150000 + i * 5000,
            currency="KES",
            is_active=True,
        )
        db.add(jp)
    db.flush()

    # Role skill baseline
    for skill in ["Python", "Django", "SQL", "Docker", "Git"]:
        db.add(
            RoleSkillBaseline(
                role_family="software_engineering",
                skill_name=skill,
                skill_share=0.7 if skill == "Python" else 0.3,
                low_confidence=False,
                count_total_jobs_used=50,
            )
        )

    # Role education baseline
    db.add(
        RoleEducationBaseline(
            role_family="software_engineering",
            education_level="bachelors",
            education_share=0.65,
            low_confidence=False,
            count_total_jobs_used=50,
        )
    )

    # Role experience baseline
    db.add(
        RoleExperienceBaseline(
            role_family="software_engineering",
            experience_band="2-4 years",
            experience_share=0.45,
            low_confidence=False,
            count_total_jobs_used=50,
        )
    )

    # Role demand snapshot
    db.add(
        RoleDemandSnapshot(
            role_family="software_engineering",
            demand_count=50,
            low_confidence=False,
            count_total_jobs_used=50,
        )
    )

    db.commit()
    db.close()
    return db_session_factory


# ---------------------------------------------------------------------------
# T-DS-971: Baseline health tests
# ---------------------------------------------------------------------------


def test_confidence_tier_thresholds():
    assert _confidence_tier(150) == "high"
    assert _confidence_tier(50) == "medium"
    assert _confidence_tier(5) == "low"
    assert _confidence_tier(0) == "low"


def test_get_baseline_health_empty_db(db):
    result = get_baseline_health(db)
    assert "overall_status" in result
    assert "tables" in result
    assert "role_skill_baseline" in result["tables"]
    assert "recommendations" in result
    # Empty DB → needs refresh
    assert result["overall_status"] == "needs_refresh"


def test_get_baseline_health_with_data(seeded_db):
    db = seeded_db()
    result = get_baseline_health(db)
    db.close()
    assert result["overall_status"] in ("healthy", "needs_refresh")
    assert "software_engineering" in result["role_families_covered"]
    tables = result["tables"]
    assert tables["role_skill_baseline"]["row_count"] == 5
    assert tables["role_education_baseline"]["row_count"] == 1
    assert tables["role_experience_baseline"]["row_count"] == 1
    assert tables["role_demand_snapshot"]["row_count"] == 1


def test_baseline_health_http(seeded_db):
    client = TestClient(_build_app(seeded_db))
    resp = client.get("/api/intelligence/baseline-health")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_status" in data
    assert "tables" in data


def test_confidence_aware_skill_baseline_empty(db):
    result = get_confidence_aware_skill_baseline(db, "nonexistent_family")
    assert result["skills"] == []
    assert result["confidence"]["tier"] == "low"


def test_confidence_aware_skill_baseline_with_data(seeded_db):
    db = seeded_db()
    result = get_confidence_aware_skill_baseline(db, "software_engineering")
    db.close()
    assert len(result["skills"]) == 5
    assert result["confidence"]["sample_size"] == 50
    assert result["confidence"]["tier"] == "medium"


def test_skill_baseline_http(seeded_db):
    client = TestClient(_build_app(seeded_db))
    resp = client.get("/api/intelligence/skill-baseline/software_engineering")
    assert resp.status_code == 200
    data = resp.json()
    assert "skills" in data
    assert "confidence" in data


# ---------------------------------------------------------------------------
# T-DS-972: Report builder tests
# ---------------------------------------------------------------------------


def test_university_report_empty_db(db):
    result = build_university_report(db)
    assert result["report_type"] == "university"
    assert isinstance(result["role_families"], list)


def test_university_report_with_data(seeded_db):
    db = seeded_db()
    result = build_university_report(db)
    db.close()
    assert result["role_families_included"] >= 1
    fam = next(
        (
            f
            for f in result["role_families"]
            if f["role_family"] == "software_engineering"
        ),
        None,
    )
    assert fam is not None
    assert len(fam["top_skills"]) == 5
    assert any(s["skill"] == "Python" for s in fam["top_skills"])


def test_university_report_family_filter(seeded_db):
    db = seeded_db()
    result = build_university_report(db, role_families=["software_engineering"])
    db.close()
    assert result["role_families_included"] == 1


def test_employer_report_with_data(seeded_db):
    db = seeded_db()
    result = build_employer_report(db, role_family="software_engineering")
    db.close()
    assert result["report_type"] == "employer"
    assert len(result["roles"]) >= 1
    role = result["roles"][0]
    assert "key_skills" in role
    assert "experience_distribution" in role


def test_county_report_with_data(seeded_db):
    db = seeded_db()
    result = build_county_report(db, county="Nairobi")
    db.close()
    assert result["report_type"] == "county"
    assert result["county"] == "Nairobi"
    assert result["total_postings"] >= 0


def test_county_report_no_filter(seeded_db):
    db = seeded_db()
    result = build_county_report(db)
    db.close()
    assert result["county"] == "All counties"
    assert isinstance(result["demand_by_role_family"], list)


def test_training_provider_report_with_data(seeded_db):
    db = seeded_db()
    result = build_training_provider_report(db)
    db.close()
    assert result["report_type"] == "training_provider"
    assert isinstance(result["top_demanded_skills"], list)


def test_training_provider_report_skill_focus(seeded_db):
    db = seeded_db()
    result = build_training_provider_report(db, skill_focus=["Python", "SQL"])
    db.close()
    skills = [s["skill"] for s in result["top_demanded_skills"]]
    assert all(s in ("Python", "SQL") for s in skills)


def test_report_endpoints_http(seeded_db):
    client = TestClient(_build_app(seeded_db))
    for path in [
        "/api/intelligence/reports/university",
        "/api/intelligence/reports/employer",
        "/api/intelligence/reports/county",
        "/api/intelligence/reports/training-provider",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200, f"Failed: {path} → {resp.status_code}"


# ---------------------------------------------------------------------------
# T-DS-973: Salary intelligence tests
# ---------------------------------------------------------------------------


def test_salary_with_market_context_heuristic_fallback(db):
    """When no salary data in DB, falls back to heuristic estimate."""
    result = get_salary_with_market_context(db, role_family="software_engineering")
    assert "salary" in result
    assert "confidence" in result
    assert result["confidence"]["data_source"] in (
        "market_data",
        "heuristic_estimate",
    )


def test_salary_with_market_context_with_data(seeded_db):
    db = seeded_db()
    result = get_salary_with_market_context(db, role_family="software_engineering")
    db.close()
    assert result["salary"]["sample_size"] == 15
    assert result["confidence"]["data_source"] == "market_data"
    assert result["salary"]["min"] > 0
    assert result["salary"]["median"] >= result["salary"]["min"]


def test_salary_confidence_summary(seeded_db):
    db = seeded_db()
    result = get_salary_confidence_summary(db)
    db.close()
    assert "by_role_family" in result
    assert "overall_salary_coverage_pct" in result


def test_salary_low_confidence_log_returns_list():
    result = get_salary_low_confidence_log(limit=10)
    assert isinstance(result, list)


def test_salary_endpoints_http(seeded_db):
    client = TestClient(_build_app(seeded_db))
    resp = client.get("/api/intelligence/salary/software_engineering")
    assert resp.status_code == 200
    data = resp.json()
    assert "salary" in data
    assert "confidence" in data

    resp2 = client.get("/api/intelligence/salary/confidence-summary")
    assert resp2.status_code == 200

    resp3 = client.get("/api/intelligence/salary/low-confidence-log")
    assert resp3.status_code == 200
    assert "entries" in resp3.json()


# ---------------------------------------------------------------------------
# T-DS-974: Export endpoints tests
# ---------------------------------------------------------------------------


def test_export_skills_gap_json(seeded_db):
    client = TestClient(_build_app(seeded_db))
    resp = client.get("/api/intelligence/export/skills-gap?fmt=json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "university"


def test_export_skills_gap_csv(seeded_db):
    client = TestClient(_build_app(seeded_db))
    resp = client.get("/api/intelligence/export/skills-gap?fmt=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    # Should have header row
    body = resp.text
    assert "role_family" in body
    assert "skill_share" in body


def test_export_market_snapshot_json(seeded_db):
    client = TestClient(_build_app(seeded_db))
    resp = client.get("/api/intelligence/export/market-snapshot?fmt=json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "county"


def test_export_market_snapshot_csv(seeded_db):
    client = TestClient(_build_app(seeded_db))
    resp = client.get("/api/intelligence/export/market-snapshot?fmt=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
