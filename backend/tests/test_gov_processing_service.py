from datetime import datetime

from app.db.models import JobEntities, JobPost, JobSkill, Organization, TitleNorm
from app.services.gov_processing_service import (
    government_quality_snapshot,
    process_government_posts,
)


def test_process_government_posts_creates_entities_and_skills(db_session_factory):
    db = db_session_factory()

    org = Organization(
        name="Public Service Commission", verified=False, sector="Government"
    )
    db.add(org)
    db.flush()

    job = JobPost(
        source="gov_careers",
        url="https://example.go.ke/vacancies/data-analyst.pdf",
        url_hash="hash1",
        title_raw="Data Analyst",
        org_id=org.id,
        description_raw=(
            "Minimum of 3 years experience. "
            "Must have SQL and Python skills. "
            "Applicants should have a degree in Statistics."
        ),
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        attachment_flag=True,
    )
    db.add(job)
    db.commit()

    result = process_government_posts(
        db, limit=50, only_unprocessed=True, dry_run=False
    )
    assert result["status"] == "success"
    assert result["processed"] == 1
    assert result["job_skills_created"] >= 1

    # Job updated
    job2 = db.query(JobPost).filter(JobPost.id == job.id).one()
    assert job2.processed_at is not None
    assert job2.quality_score is not None
    assert job2.description_clean is not None
    assert job2.education is not None
    assert job2.title_norm_id is not None

    # TitleNorm row exists
    tn = db.query(TitleNorm).filter(TitleNorm.id == job2.title_norm_id).one()
    assert tn.canonical_title

    # Evidence stored
    ents = db.query(JobEntities).filter(JobEntities.job_id == job.id).one()
    assert isinstance(ents.entities, dict)
    assert "skills" in ents.entities
    assert len(ents.entities["skills"]) >= 1

    # JobSkill rows exist
    jskills = db.query(JobSkill).filter(JobSkill.job_post_id == job.id).all()
    assert len(jskills) >= 1
    db.close()


def test_government_quality_snapshot_counts(db_session_factory):
    db = db_session_factory()
    db.add(
        JobPost(
            source="gov_careers",
            url="https://example.go.ke/vacancies/1",
            url_hash="hash2",
            title_raw="Job posting",
            description_raw=None,
        )
    )
    db.commit()

    snap = government_quality_snapshot(db)
    assert snap["total"] >= 1
    assert "coverage" in snap
    assert "description_raw" in snap["coverage"]
    db.close()
