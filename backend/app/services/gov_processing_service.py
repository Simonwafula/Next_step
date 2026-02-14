from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from .post_ingestion_processing_service import process_job_posts
from .processing_quality import quality_snapshot


def process_government_posts(
    db: Session,
    *,
    limit: int = 500,
    only_unprocessed: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Backwards-compatible wrapper around
    unified post-ingestion processing.
    """
    return process_job_posts(
        db,
        source="gov_careers",
        limit=limit,
        only_unprocessed=only_unprocessed,
        dry_run=dry_run,
    )


def government_quality_snapshot(db: Session) -> Dict[str, Any]:
    """Gov-only quality snapshot derived from the global quality snapshot."""
    snap = quality_snapshot(db)
    gov = next(
        (row for row in snap.get("by_source", []) if row["source"] == "gov_careers"),
        None,
    )
    if not gov:
        return {"total": 0, "processed": 0, "coverage": {}}

    return {
        "total": gov["total"],
        "processed": gov["processed"],
        "coverage": {
            "description_raw": {
                "count": None,
                "percentage": gov["coverage"]["description_raw"],
            },
            "quality_score": {
                "count": None,
                "percentage": gov["coverage"]["quality_score"],
            },
            "processed_at": {
                "count": None,
                "percentage": gov["coverage"]["processed_at"],
            },
        },
    }
