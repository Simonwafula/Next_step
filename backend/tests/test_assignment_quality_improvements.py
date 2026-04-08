from datetime import datetime

from app.db.models import JobDedupeMap, JobPost, Location, Organization
from app.normalization.companies import normalize_company_name
from app.normalization.dedupe import (
    build_title_company_date_key,
    run_incremental_dedup,
)
from app.normalization.locations import normalize_location
from app.services.search import (
    build_job_data_quality,
    get_source_quality_score,
    get_source_quality_tier,
    search_jobs,
)


def test_normalize_company_name_strips_listing_prefixes_and_artifacts():
    assert normalize_company_name("Jobs at Safaricom Kenya Ltd") == "Safaricom Kenya"
    assert normalize_company_name("Read more about this company") == ""


def test_normalize_location_handles_global_and_cleanup():
    assert normalize_location(" Nairobi \n Kenya ") == ("Nairobi", "Nairobi", "Kenya")
    assert normalize_location("International") == (
        "International",
        "International",
        None,
    )


def test_build_title_company_date_key_normalizes_inputs():
    seen_at = datetime(2026, 4, 8, 10, 30, 0)
    key = build_title_company_date_key(
        "Jobs at Data Analyst",
        "Vacancies at Example Limited",
        seen_at,
    )
    assert key == "data analyst|example|2026-04-08"


def test_incremental_dedup_marks_title_company_date_duplicates(db_session_factory):
    db = db_session_factory()
    org = Organization(name="Example", verified=False)
    db.add(org)
    db.flush()

    job1 = JobPost(
        source="rss",
        url="https://example.com/jobs/1",
        url_hash="hash-1",
        title_raw="Data Analyst",
        org_id=org.id,
        description_raw="SQL Excel dashboards and reporting.",
        first_seen=datetime(2026, 4, 8, 9, 0, 0),
        last_seen=datetime(2026, 4, 8, 9, 0, 0),
    )
    job2 = JobPost(
        source="rss",
        url="https://example.com/jobs/2",
        url_hash="hash-2",
        title_raw="Data Analyst",
        org_id=org.id,
        description_raw="Different text but same role and day.",
        first_seen=datetime(2026, 4, 8, 12, 0, 0),
        last_seen=datetime(2026, 4, 8, 12, 0, 0),
    )
    db.add_all([job1, job2])
    db.commit()

    result = run_incremental_dedup(db, batch_size=10)
    assert result["processed"] == 2
    assert result["duplicates_found"] == 1

    rows = {
        row.job_id: row
        for row in db.query(JobDedupeMap).order_by(JobDedupeMap.job_id.asc()).all()
    }
    assert rows[job1.id].canonical_job_id == job1.id
    assert rows[job2.id].canonical_job_id == job1.id


def test_source_quality_scoring_uses_source_type_defaults():
    assert get_source_quality_score("telegram:job_vacancy_kenya") == 0.58
    assert get_source_quality_tier(0.9) == "high"
    assert get_source_quality_tier(0.75) == "medium"
    assert get_source_quality_tier(0.5) == "low"


def test_build_job_data_quality_flags_listing_company_noise_and_low_location():
    job = JobPost(
        id=7,
        source="rss",
        url="https://example.com/jobs/listing",
        title_raw="Jobs at Data Analyst",
        description_raw="Short role summary",
        first_seen=datetime(2026, 4, 8, 9, 0, 0),
        last_seen=datetime(2026, 4, 8, 9, 0, 0),
    )
    org = Organization(name="Read more about this company", verified=False)
    location = Location(raw="International")

    quality = build_job_data_quality(
        job,
        org,
        location,
        dedupe_cluster_id=42,
    )

    assert quality["flags"]["listing_page"] is True
    assert quality["flags"]["company_noise"] is True
    assert quality["flags"]["location_confidence"] == "low"
    assert quality["flags"]["dedupe_cluster"] == 42
    assert set(quality["issues"]) >= {
        "listing_page",
        "company_noise",
        "location_low_confidence",
        "description_short",
        "duplicate_candidate",
    }
    assert quality["location_confidence"] == "low"
    assert quality["is_duplicate_candidate"] is True


def test_search_jobs_exposes_quality_metadata_for_results(db_session_factory):
    db = db_session_factory()
    org = Organization(name="Jobs at Example Limited", verified=False)
    location = Location(city="Nairobi", region="Nairobi", country="Kenya")
    db.add_all([org, location])
    db.flush()

    job = JobPost(
        source="telegram:job_vacancy_kenya",
        url="https://example.com/jobs/analyst",
        url_hash="hash-analyst",
        title_raw="Jobs at Data Analyst",
        org_id=org.id,
        location_id=location.id,
        description_raw="SQL Excel dashboards and reporting " * 20,
        quality_score=0.82,
        first_seen=datetime(2026, 4, 8, 9, 0, 0),
        last_seen=datetime(2026, 4, 8, 9, 0, 0),
        is_active=True,
    )
    db.add(job)
    db.commit()

    db.add(
        JobDedupeMap(
            job_id=job.id,
            canonical_job_id=999,
            similarity_score=0.95,
        )
    )
    db.commit()

    payload = search_jobs(db, q="", limit=5)
    result = payload["results"][0]

    assert result["top_skills"] == []
    assert result["source_quality_score"] == 0.58
    assert result["source_quality_tier"] == "low"
    assert result["location_confidence"] == "high"
    assert result["dedupe_cluster_id"] == 999
    assert result["is_duplicate_candidate"] is True
    assert result["data_quality_flags"]["listing_page"] is True
    assert "listing_page" in result["data_quality_issues"]
