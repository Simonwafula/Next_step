#!/usr/bin/env python3
"""Refresh the Postgres analysis.job_post_cleaned_mv materialized view."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


def refresh_job_post_analysis_view() -> None:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                """
                SELECT 1
                FROM pg_matviews
                WHERE schemaname = 'analysis'
                  AND matviewname = 'job_post_cleaned_mv'
                """
            )
        ).scalar()
        if not exists:
            raise RuntimeError(
                "analysis.job_post_cleaned_mv does not exist. Run create_job_post_analysis_view.py first."
            )
        conn.execute(text("REFRESH MATERIALIZED VIEW analysis.job_post_cleaned_mv"))


def main() -> None:
    refresh_job_post_analysis_view()
    print("Refreshed analysis.job_post_cleaned_mv")


if __name__ == "__main__":
    main()
