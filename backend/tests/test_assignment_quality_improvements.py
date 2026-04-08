from datetime import datetime

from app.db.models import JobDedupeMap, JobPost, Organization
from app.normalization.companies import normalize_company_name
from app.normalization.dedupe import (
    build_title_company_date_key,
    run_incremental_dedup,
)
from app.normalization.locations import normalize_location


def test_normalize_company_name_strips_listing_prefixes_and_artifacts():
    assert normalize_company_name("Jobs at Safaricom Kenya Ltd") == "Safaricom Kenya"
    assert normalize_company_name("Read more about this company") == ""


def test_normalize_location_handles_global_and_cleanup():
    assert normalize_location(" Nairobi \n Kenya ") == ("Nairobi", "Nairobi", "Kenya")
    assert normalize_location("International") == ("International", "International", None)


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
