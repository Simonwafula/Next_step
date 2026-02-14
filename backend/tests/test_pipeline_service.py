from datetime import datetime

from app.db.models import JobEntities, JobPost, ProcessingLog
from app.services.pipeline_service import PipelineOptions, run_incremental_pipeline


def test_incremental_pipeline_can_post_process(db_session_factory):
    db = db_session_factory()
    db.add(
        JobPost(
            source="rss",
            url="https://example.com/jobs/pipeline-1",
            url_hash="hash-pipeline-1",
            title_raw="Junior Data Analyst",
            description_raw="We need SQL and Excel skills with 2 years experience.",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
    )
    db.commit()

    opts = PipelineOptions(
        ingest_incremental=False,
        scrape_sites=False,
        post_process=True,
        post_process_limit=25,
        dedupe=False,
        embed=False,
        analytics=False,
        strict=True,
    )

    result = run_incremental_pipeline(db, opts=opts)
    assert result["status"] == "success"
    assert result["steps"]["post_process"]["status"] == "success"

    job = (
        db.query(JobPost)
        .filter(JobPost.url == "https://example.com/jobs/pipeline-1")
        .one()
    )
    assert job.processed_at is not None

    ents = db.query(JobEntities).filter(JobEntities.job_id == job.id).one_or_none()
    assert ents is not None

    log = (
        db.query(ProcessingLog)
        .filter(ProcessingLog.process_type == "pipeline_incremental")
        .order_by(ProcessingLog.id.desc())
        .first()
    )
    assert log is not None
    db.close()
