import asyncio
import logging

from ..core.celery_app import celery_app
from ..db.database import get_db
from ..ingestion.runner import run_government_sources
from ..services.post_ingestion_processing_service import process_job_posts

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.gov_monitor_tasks.run_government_sources")
def run_government_sources_task(self):
    """
    Monitor government career pages and ingest new postings.
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting government source monitoring", "progress": 0},
        )

        result = asyncio.run(_run_government_sources_async())

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Government source monitoring completed",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as exc:
        logger.error("Government source monitoring failed: %s", exc)
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Government source monitoring failed: {exc}",
                "progress": 0,
            },
        )
        raise


async def _run_government_sources_async():
    async for db in get_db():
        try:
            ingested = run_government_sources(db)
            processed = process_job_posts(
                db,
                source="gov_careers",
                limit=2000,
                only_unprocessed=True,
                dry_run=False,
            )
            return {"ingested": ingested, "post_process": processed}
        finally:
            await db.close()
