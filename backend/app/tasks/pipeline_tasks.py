import os
import logging
from datetime import datetime
from typing import Any, Dict

from ..core.celery_app import celery_app
from ..core.locks import redis_lock
from ..db.database import SessionLocal
from ..services.pipeline_service import PipelineOptions, run_incremental_pipeline
from ..services.processing_log_service import log_processing_event

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.pipeline_tasks.run_incremental_pipeline")
def run_incremental_pipeline_task(self) -> Dict[str, Any]:
    """Run the production incremental pipeline on a schedule (Celery beat).

    This is guarded by env `ENABLE_CELERY_PIPELINE=true` to prevent accidental
    double-scheduling when systemd timers are used in production.
    """
    if os.getenv("ENABLE_CELERY_PIPELINE", "false").lower() != "true":
        return {"status": "skipped", "reason": "ENABLE_CELERY_PIPELINE != true"}

    lock_key = "nextstep:pipeline_incremental"
    with redis_lock(lock_key, ttl_seconds=60 * 60) as acquired:
        if not acquired:
            return {"status": "skipped", "reason": f"lock_not_acquired:{lock_key}"}

        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting incremental pipeline", "progress": 0},
        )

        db = SessionLocal()
        try:
            opts = PipelineOptions(strict=False)
            result = run_incremental_pipeline(db, opts=opts)
            self.update_state(
                state="SUCCESS",
                meta={
                    "status": "Pipeline completed",
                    "progress": 100,
                    "result": result,
                },
            )
            return result
        except Exception as exc:
            logger.error("Incremental pipeline failed: %s", exc)
            try:
                log_processing_event(
                    db,
                    process_type="pipeline_incremental_task",
                    status="error",
                    message=str(exc),
                    details={"failed_at": datetime.utcnow().isoformat()},
                )
            except Exception:
                pass
            self.update_state(
                state="FAILURE",
                meta={"status": f"Pipeline failed: {exc}", "progress": 0},
            )
            raise
        finally:
            db.close()
