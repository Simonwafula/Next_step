#!/usr/bin/env python3
"""
Smoke checks for Next Step MVP.

This file lives in `scripts/` as an operational tool, not a unit-test module.
Pytest still imports `*_test.py` files by default, so we keep imports side-effect
free and avoid `test_*` symbols to prevent accidental collection.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

_BOOTSTRAPPED = False


def _bootstrap_backend_imports() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    # Load environment variables from `.env` if present.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        # Keep smoke checks runnable even if python-dotenv isn't installed.
        pass

    backend_path = (Path(__file__).parent.parent / "backend").resolve()
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    _BOOTSTRAPPED = True


def _get_engine():
    _bootstrap_backend_imports()
    from app.db.database import engine

    return engine


def check_database_connection(*, engine) -> None:
    """Check database connection and schema."""
    logger.info("🔌 Checking database connection...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM job_post"))
        count = result.scalar()
        logger.info("✅ Database connected. Total jobs in DB: %s", count)
        assert count is not None, "Database connection failed"


def check_job_data_quality(*, engine, min_id: int, coverage_min: float) -> None:
    """Check basic completeness ratios over a job ID window."""
    logger.info("📊 Checking job data quality... (min_id=%s)", min_id)

    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN title_raw IS NOT NULL AND title_raw != '' THEN 1 END) as has_title,
                COUNT(CASE WHEN org_id IS NOT NULL THEN 1 END) as has_company,
                COUNT(CASE WHEN location_id IS NOT NULL THEN 1 END) as has_location,
                COUNT(CASE WHEN salary_min IS NOT NULL OR salary_max IS NOT NULL THEN 1 END) as has_salary,
                COUNT(CASE WHEN description_raw IS NOT NULL AND description_raw != '' THEN 1 END) as has_description
            FROM job_post
            WHERE id >= :min_id
        """),
            {"min_id": min_id},
        )
        metrics = result.fetchone()

        total = int(metrics[0] or 0)
        if total == 0:
            raise AssertionError(f"No jobs found for id >= {min_id}")

        has_title = int(metrics[1] or 0)
        has_company = int(metrics[2] or 0)
        has_location = int(metrics[3] or 0)
        has_salary = int(metrics[4] or 0)
        has_description = int(metrics[5] or 0)

        logger.info("Sample size: %s", total)
        logger.info("Has Title: %.1f%%", has_title / total * 100)
        logger.info("Has Company: %.1f%%", has_company / total * 100)
        logger.info("Has Location: %.1f%%", has_location / total * 100)
        logger.info("Has Salary: %.1f%%", has_salary / total * 100)
        logger.info("Has Description: %.1f%%", has_description / total * 100)

        title_ok = has_title / total >= coverage_min
        company_ok = has_company / total >= coverage_min
        location_ok = has_location / total >= coverage_min
        description_ok = has_description / total >= coverage_min

        quality_passed = title_ok and company_ok and location_ok and description_ok
        assert quality_passed, (
            f"Data quality criteria not met (coverage_min={coverage_min})"
        )

        logger.info("✅ Data quality criteria PASSED")


def check_source_diversity(*, engine, min_id: int, min_sources: int) -> None:
    """Check that multiple sources are contributing jobs."""
    logger.info("🌐 Checking source diversity... (min_id=%s)", min_id)

    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT source, COUNT(*) as count
            FROM job_post
            WHERE id >= :min_id
            GROUP BY source
        """),
            {"min_id": min_id},
        )
        sources = result.fetchall()

        logger.info("Active sources: %s", len(sources))
        for source, count in sources:
            logger.info("  %s: %s jobs", source, count)

        assert len(sources) >= min_sources, (
            f"Expected >= {min_sources} sources, got {len(sources)}"
        )

        logger.info("✅ Source diversity criteria PASSED")


def check_ingestion_pipeline(*, engine, min_id: int, min_jobs: int) -> None:
    """Check ingestion can run end-to-end (heuristic: enough recent-ish rows exist)."""
    logger.info("🔄 Checking ingestion pipeline... (min_id=%s)", min_id)

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM job_post WHERE id >= :min_id"),
            {"min_id": min_id},
        )
        recent_jobs = int(result.scalar() or 0)

        assert recent_jobs >= min_jobs, (
            f"Expected at least {min_jobs} jobs for id >= {min_id}, got {recent_jobs}"
        )

        logger.info(
            "✅ Ingestion pipeline looks healthy: %s jobs in window", recent_jobs
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Next Step operational smoke checks."
    )
    parser.add_argument(
        "--min-id",
        type=int,
        default=int(os.getenv("NEXTSTEP_SMOKE_MIN_ID", "0")),
        help="Only consider jobs with id >= MIN_ID (default: $NEXTSTEP_SMOKE_MIN_ID or 0).",
    )
    parser.add_argument(
        "--min-jobs",
        type=int,
        default=int(os.getenv("NEXTSTEP_SMOKE_MIN_JOBS", "10")),
        help="Minimum required job count in the window (default: $NEXTSTEP_SMOKE_MIN_JOBS or 10).",
    )
    parser.add_argument(
        "--min-sources",
        type=int,
        default=int(os.getenv("NEXTSTEP_SMOKE_MIN_SOURCES", "2")),
        help="Minimum number of distinct sources in the window (default: $NEXTSTEP_SMOKE_MIN_SOURCES or 2).",
    )
    parser.add_argument(
        "--coverage-min",
        type=float,
        default=float(os.getenv("NEXTSTEP_SMOKE_COVERAGE_MIN", "0.8")),
        help="Minimum field coverage ratio required (default: $NEXTSTEP_SMOKE_COVERAGE_MIN or 0.8).",
    )
    args = parser.parse_args(argv)

    logger.info("🚀 Starting Next Step MVP Smoke Checks")
    logger.info("=" * 60)

    engine = _get_engine()

    checks = [
        ("Database Connection", lambda: check_database_connection(engine=engine)),
        (
            "Ingestion Pipeline",
            lambda: check_ingestion_pipeline(
                engine=engine, min_id=args.min_id, min_jobs=args.min_jobs
            ),
        ),
        (
            "Source Diversity",
            lambda: check_source_diversity(
                engine=engine, min_id=args.min_id, min_sources=args.min_sources
            ),
        ),
        (
            "Job Data Quality",
            lambda: check_job_data_quality(
                engine=engine, min_id=args.min_id, coverage_min=args.coverage_min
            ),
        ),
    ]

    results: list[tuple[str, bool]] = []
    for name, fn in checks:
        logger.info("\n--- %s ---", name)
        try:
            fn()
            results.append((name, True))
        except AssertionError as exc:
            logger.error("❌ Check failed: %s", exc)
            results.append((name, False))
        except Exception as exc:
            logger.exception("💥 Check crashed: %s", exc)
            results.append((name, False))

    logger.info("\n" + "=" * 60)
    logger.info("📋 SMOKE CHECK SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _name, ok in results if ok)
    for name, ok in results:
        logger.info("%s: %s", name, "✅ PASSED" if ok else "❌ FAILED")

    logger.info("Overall: %s/%s checks passed", passed, len(results))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
