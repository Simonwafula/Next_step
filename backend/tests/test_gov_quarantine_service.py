from app.db.models import JobPost
from app.services.gov_quarantine_service import quarantine_government_nonjobs


def test_quarantine_marks_non_job_pages_inactive(db_session_factory):
    db = db_session_factory()

    good = JobPost(
        source="gov_careers",
        url="https://example.go.ke/vacancies/role-1",
        title_raw="Research Officer",
        description_raw="How to apply. Closing date 2026-03-01. Qualifications: degree.",
        quality_score=0.7,
    )
    bad = JobPost(
        source="gov_careers",
        url="https://example.go.ke/opportunities/news-updates/",
        title_raw="News Updates",
        description_raw="Latest updates and resources.",
        quality_score=0.3,
    )
    db.add_all([good, bad])
    db.commit()
    db.refresh(good)
    db.refresh(bad)

    result = quarantine_government_nonjobs(db, limit=50, dry_run=False)
    assert result["status"] == "success"
    assert result["quarantined"] == 1

    bad2 = db.query(JobPost).filter(JobPost.id == bad.id).one()
    good2 = db.query(JobPost).filter(JobPost.id == good.id).one()
    assert bad2.is_active is False
    assert good2.is_active is True
