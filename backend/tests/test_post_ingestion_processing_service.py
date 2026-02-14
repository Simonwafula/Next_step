from datetime import datetime

from app.db.models import (
    JobEntities,
    JobPost,
    JobSkill,
    Organization,
    TitleNorm,
)
from app.services.post_ingestion_processing_service import process_job_posts
from app.services.processing_quality import quality_snapshot


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
        description_raw=("Minimum of 2 years experience. Must have SQL and Excel."),
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


def test_process_job_posts_clamps_long_titles(db_session_factory):
    db = db_session_factory()
    job = JobPost(
        source="gov_careers",
        url="https://example.com/long-title",
        title_raw="X" * 500,  # Longer than TitleNorm.canonical_title (120)
        description_raw="We need a data analyst with Python and SQL.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    result = process_job_posts(
        db, source="gov_careers", limit=10, only_unprocessed=True
    )
    assert result["status"] == "success"
    assert result["processed"] >= 1

    # Ensure TitleNorm exists and respects length constraints.
    tn = db.query(TitleNorm).filter(TitleNorm.id == job.title_norm_id).one_or_none()
    assert tn is not None
    assert tn.canonical_title is not None
    assert len(tn.canonical_title) <= 120
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
            description_raw="",
        )
    )
    db.commit()

    snap = quality_snapshot(db)
    assert "by_source" in snap
    rss = next(row for row in snap["by_source"] if row["source"] == "rss")
    assert rss["coverage"]["description_raw"] == 0
    db.close()


def test_quality_snapshot_flags_failing_gates(db_session_factory, monkeypatch):
    monkeypatch.setenv("QUALITY_GATE_DESCRIPTION_PCT", "80")
    monkeypatch.setenv("QUALITY_GATE_ENTITIES_PCT", "80")
    monkeypatch.setenv("QUALITY_GATE_PROCESSED_PCT", "80")
    monkeypatch.setenv("QUALITY_GATE_QUALITY_SCORE_PCT", "80")

    db = db_session_factory()

    job_ok = JobPost(
        source="rss",
        url="https://example.com/jobs/3",
        url_hash="hash-rss-3",
        title_raw="Data Analyst",
        description_raw="We need SQL and Excel skills.",
        quality_score=0.7,
    )
    job_ok.processed_at = datetime.utcnow()
    db.add(job_ok)
    db.flush()
    db.add(JobEntities(job_id=job_ok.id, entities={}, skills=[], tools=[]))

    db.add(
        JobPost(
            source="rss",
            url="https://example.com/jobs/4",
            url_hash="hash-rss-4",
            title_raw="Job posting",
            description_raw=None,
        )
    )
    db.commit()

    snap = quality_snapshot(db)
    assert "gates" in snap
    assert snap["gates"]["overall_status"] == "fail"
    assert snap["gates"]["checks"]["description_raw"]["status"] == "fail"
    db.close()
