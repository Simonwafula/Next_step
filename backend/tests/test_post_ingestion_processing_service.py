from datetime import datetime

from app.db.models import JobEntities, JobPost, JobSkill, Organization
from app.services.post_ingestion_processing_service import (
    process_job_posts,
    quality_snapshot,
)


def test_process_job_posts_generic_source(db_session_factory):
    db = db_session_factory()

    org = Organization(name="Example Org", verified=False, sector="Tech")
    db.add(org)
    db.flush()

    job = JobPost(
        source="rss",
        url="https://example.com/jobs/1",
        url_hash="hash-rss-1",
        title_raw="Junior Data Analyst",
        org_id=org.id,
        description_raw="Minimum of 2 years experience. Must have SQL and Excel.",
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )
    db.add(job)
    db.commit()

    result = process_job_posts(
        db, source=None, limit=50, only_unprocessed=True, dry_run=False
    )
    assert result["status"] == "success"
    assert result["processed"] == 1
    assert result["job_skills_created"] >= 1

    job2 = db.query(JobPost).filter(JobPost.id == job.id).one()
    assert job2.processed_at is not None
    assert job2.quality_score is not None
    assert job2.description_clean is not None

    ents = db.query(JobEntities).filter(JobEntities.job_id == job.id).one()
    assert "skills" in ents.entities

    skills = db.query(JobSkill).filter(JobSkill.job_post_id == job.id).all()
    assert len(skills) >= 1
    db.close()


def test_quality_snapshot_includes_source_breakdown(db_session_factory):
    db = db_session_factory()
    db.add(
        JobPost(
            source="rss",
            url="https://example.com/jobs/2",
            url_hash="hash-rss-2",
            title_raw="Job posting",
            description_raw=None,
        )
    )
    db.commit()

    snap = quality_snapshot(db)
    assert "by_source" in snap
    assert any(row["source"] == "rss" for row in snap["by_source"])
    db.close()
