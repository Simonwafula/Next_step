from datetime import datetime

from app.db.models import JobDedupeMap, JobEntities, JobPost, Location, Organization
from app.services.search import (
    build_job_data_quality,
    extract_entity_skills,
    get_source_quality_score,
    search_jobs,
)


def test_extract_entity_skills_filters_low_confidence_but_keeps_scored_matches():
    skills = extract_entity_skills(
        [
            {"value": "Python", "confidence": 0.91},
            {"value": "Excel", "confidence": 0.55},
            {"value": "SQL", "confidence": 0.74},
        ]
    )

    assert [item["value"] for item in skills] == ["Python", "SQL"]


def test_build_job_data_quality_returns_explicit_flags():
    org = Organization(name="Jobs at Example Ltd", verified=False)
    loc = Location(raw="International")
    job = JobPost(
        source="rss",
        url="https://example.com/jobs/1",
        title_raw="Jobs at Example Ltd",
        description_raw="Short text",
    )

    payload = build_job_data_quality(job, org, loc, dedupe_cluster_id=99)

    assert payload["flags"]["listing_page"] is True
    assert payload["flags"]["company_noise"] is True
    assert payload["flags"]["location_confidence"] == "low"
    assert payload["flags"]["dedupe_cluster"] == 99
    assert "duplicate_candidate" in payload["issues"]
    assert "description_short" in payload["issues"]


def test_search_jobs_prioritizes_cleaner_sources_and_exposes_quality_fields(
    db_session_factory,
):
    db = db_session_factory()
    seen_at = datetime(2026, 4, 8, 12, 0, 0)

    clean_org = Organization(name="Safaricom Kenya", sector="tech", verified=True)
    noisy_org = Organization(name="Jobs at Example Ltd", sector="tech", verified=False)
    clean_loc = Location(city="Nairobi", region="Nairobi", country="Kenya", raw="Nairobi, Kenya")
    noisy_loc = Location(raw="International")
    db.add_all([clean_org, noisy_org, clean_loc, noisy_loc])
    db.flush()

    clean_job = JobPost(
        source="greenhouse",
        url="https://example.com/jobs/greenhouse",
        url_hash="g-1",
        title_raw="Data Analyst",
        org_id=clean_org.id,
        location_id=clean_loc.id,
        description_raw="Python SQL dashboards reporting " * 20,
        first_seen=seen_at,
        last_seen=seen_at,
        quality_score=0.92,
        is_active=True,
    )
    noisy_job = JobPost(
        source="telegram:jobs",
        url="https://example.com/jobs/telegram",
        url_hash="t-1",
        title_raw="Jobs at Example Ltd",
        org_id=noisy_org.id,
        location_id=noisy_loc.id,
        description_raw="Apply now",
        first_seen=seen_at,
        last_seen=seen_at,
        quality_score=0.92,
        is_active=True,
    )
    db.add_all([clean_job, noisy_job])
    db.flush()
    db.add_all(
        [
            JobEntities(
                job_id=clean_job.id,
                skills=[
                    {"value": "Python", "confidence": 0.91},
                    {"value": "SQL", "confidence": 0.87},
                    {"value": "Excel", "confidence": 0.51},
                ],
            ),
            JobEntities(
                job_id=noisy_job.id,
                skills=[{"value": "Excel", "confidence": 0.72}],
            ),
            JobDedupeMap(
                job_id=clean_job.id,
                canonical_job_id=clean_job.id,
                similarity_score=1.0,
            ),
            JobDedupeMap(
                job_id=noisy_job.id,
                canonical_job_id=clean_job.id,
                similarity_score=0.88,
            ),
        ]
    )
    db.commit()

    payload = search_jobs(db, limit=10, offset=0)

    assert payload["results"][0]["id"] == clean_job.id
    assert payload["results"][0]["quality_tag"] == "High confidence"
    assert payload["results"][0]["top_skills"] == ["Python", "SQL"]
    assert payload["results"][0]["data_quality_flags"]["listing_page"] is False
    assert payload["results"][0]["source_quality_tier"] == "high"

    noisy_result = next(item for item in payload["results"] if item["id"] == noisy_job.id)
    assert noisy_result["quality_tag"] == "Needs review"
    assert noisy_result["data_quality_flags"]["listing_page"] is True
    assert noisy_result["data_quality_flags"]["company_noise"] is True
    assert noisy_result["data_quality_flags"]["dedupe_cluster"] == clean_job.id
    assert noisy_result["source_quality_score"] == get_source_quality_score("telegram:jobs")
