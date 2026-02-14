from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict

from sqlalchemy.orm import Session

from ..ingestion.runner import run_incremental_sources
from ..ml.embeddings import run_incremental_embeddings
from ..normalization.dedupe import run_incremental_dedup
from ..scrapers.main import scrape_all_sites
from ..services.analytics import refresh_analytics_baseline
from ..services.post_ingestion_processing_service import process_job_posts
from ..services.processing_log_service import log_processing_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineOptions:
    ingest_incremental: bool = True
    scrape_sites: bool = True
    post_process: bool = True
    post_process_limit: int = 2000
    post_process_source: str | None = None
    dedupe: bool = True
    dedupe_batch_size: int = 500
    embed: bool = True
    embed_batch_size: int = 100
    analytics: bool = True
    scraper_max_pages: int | None = 5
    scraper_use_postgres: bool | None = True
    strict: bool = True


def run_incremental_pipeline(db: Session, *, opts: PipelineOptions) -> Dict[str, Any]:
    """Run the production incremental pipeline (scrape/ingest -> process -> dedupe -> embed -> analytics).

    Designed to be runnable from both CLI and Celery/systemd.
    """
    started = time.time()
    steps: Dict[str, Dict[str, Any]] = {}
    status = "success"

    def _record(step: str, payload: Dict[str, Any]) -> None:
        nonlocal status
        steps[step] = payload
        if payload.get("status") == "error":
            status = "error"

    # Step 1: Incremental ingestion from configured sources.yaml.
    if opts.ingest_incremental:
        try:
            count = int(run_incremental_sources(db) or 0)
            _record("ingest_incremental", {"status": "success", "ingested": count})
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            _record("ingest_incremental", {"status": "error", "error": str(exc)})
    else:
        _record("ingest_incremental", {"status": "skipped"})

    # Step 2: Scrape configured HTML sites (SiteSpider). This step writes directly to app DB
    # when scraper_use_postgres is True.
    if opts.scrape_sites:
        try:
            scrape_result = scrape_all_sites(
                use_postgres=opts.scraper_use_postgres,
                max_pages=opts.scraper_max_pages,
            )
            _record("scrape_sites", {"status": "success", "result": scrape_result})
        except Exception as exc:
            _record("scrape_sites", {"status": "error", "error": str(exc)})
    else:
        _record("scrape_sites", {"status": "skipped"})

    # Step 3: Deterministic post-ingestion processing (title_norm, skills, entities, quality_score).
    if opts.post_process:
        try:
            process_result = process_job_posts(
                db,
                source=opts.post_process_source,
                limit=int(opts.post_process_limit),
                only_unprocessed=True,
                dry_run=False,
            )
            _record("post_process", {"status": "success", "result": process_result})
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            _record("post_process", {"status": "error", "error": str(exc)})
    else:
        _record("post_process", {"status": "skipped"})

    # Step 4: Incremental deduplication.
    if opts.dedupe:
        try:
            dedupe_result = run_incremental_dedup(
                db, batch_size=int(opts.dedupe_batch_size)
            )
            _record("dedupe", {"status": "success", "result": dedupe_result})
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            _record("dedupe", {"status": "error", "error": str(exc)})
    else:
        _record("dedupe", {"status": "skipped"})

    # Step 5: Incremental embeddings.
    if opts.embed:
        try:
            embed_result = run_incremental_embeddings(
                db, batch_size=int(opts.embed_batch_size)
            )
            _record("embed", {"status": "success", "result": embed_result})
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            _record("embed", {"status": "error", "error": str(exc)})
    else:
        _record("embed", {"status": "skipped"})

    # Step 6: Refresh analytics baselines.
    if opts.analytics:
        try:
            analytics_result = refresh_analytics_baseline(db)
            _record("analytics", {"status": "success", "result": analytics_result})
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            _record("analytics", {"status": "error", "error": str(exc)})
    else:
        _record("analytics", {"status": "skipped"})

    duration_s = round(time.time() - started, 2)
    result: Dict[str, Any] = {
        "status": status,
        "duration_seconds": duration_s,
        "steps": steps,
    }

    # Always attempt to record an audit log in the DB (best effort).
    try:
        log_processing_event(
            db,
            process_type="pipeline_incremental",
            status=status,
            message=f"Pipeline completed with status={status}",
            details=result,
        )
    except Exception as exc:
        logger.warning("Failed to write processing log for pipeline: %s", exc)

    if status != "success" and opts.strict:
        # Keep the summary for debugging in callers, but fail fast in strict mode.
        raise RuntimeError(f"pipeline_incremental failed: {result}")

    return result
