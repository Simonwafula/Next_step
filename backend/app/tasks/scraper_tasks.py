import asyncio
import logging
from typing import Dict, Any

from ..core.celery_app import celery_app
from ..db.database import get_db
from ..services.automated_workflow_service import automated_workflow_service
from ..services.scraper_service import scraper_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.scraper_tasks.test_all_scrapers")
def health_check_all_scrapers(self):
    """
    Test all scraper configurations for health monitoring
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting scraper health check", "progress": 0},
        )

        result = asyncio.run(_test_scrapers_async())

        # Calculate health score
        total_scrapers = len(result.get("detailed_results", {}))
        successful_scrapers = sum(
            1
            for test_result in result.get("detailed_results", {}).values()
            if test_result.get("status") == "success"
        )

        health_score = successful_scrapers / total_scrapers if total_scrapers > 0 else 0

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Scraper health check completed",
                "progress": 100,
                "health_score": health_score,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Scraper health check failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Scraper health check failed: {str(e)}", "progress": 0},
        )
        raise


# Backwards-compatible alias for imports that expect `test_all_scrapers`.
# This is intentionally an assignment (not a function def) so pytest does not
# mistakenly collect it as a test function during discovery.
test_all_scrapers = health_check_all_scrapers
try:
    # Prevent pytest from treating this task object as a test function
    setattr(test_all_scrapers, "__test__", False)
except Exception:
    pass


@celery_app.task(bind=True, name="app.tasks.scraper_tasks.run_single_scraper")
def run_single_scraper(self, site_name: str):
    """
    Run a single scraper for a specific site
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": f"Starting scraper for {site_name}", "progress": 0},
        )

        result = asyncio.run(_run_single_scraper_async(site_name))

        self.update_state(
            state="SUCCESS",
            meta={
                "status": f"Scraper for {site_name} completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Scraper for {site_name} failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Scraper for {site_name} failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.scraper_tasks.run_all_scrapers")
def run_all_scrapers(self):
    """
    Run all configured scrapers
    """
    try:
        self.update_state(
            state="PROGRESS", meta={"status": "Starting all scrapers", "progress": 0}
        )

        result = asyncio.run(_run_all_scrapers_async())

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "All scrapers completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"All scrapers execution failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"All scrapers execution failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.scraper_tasks.migrate_scraper_data")
def migrate_scraper_data(self):
    """
    Migrate scraped data from SQLite to PostgreSQL
    """
    try:
        self.update_state(
            state="PROGRESS", meta={"status": "Starting data migration", "progress": 0}
        )

        result = asyncio.run(_migrate_data_async())

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Data migration completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Data migration failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Data migration failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.scraper_tasks.validate_scraper_config")
def validate_scraper_config(self, site_name: str, config: Dict[str, Any]):
    """
    Validate a scraper configuration
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": f"Validating config for {site_name}", "progress": 0},
        )

        result = asyncio.run(_validate_config_async(site_name, config))

        self.update_state(
            state="SUCCESS",
            meta={
                "status": f"Config validation for {site_name} completed",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Config validation for {site_name} failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Config validation for {site_name} failed: {str(e)}",
                "progress": 0,
            },
        )
        raise


@celery_app.task(bind=True, name="app.tasks.scraper_tasks.cleanup_old_jobs")
def cleanup_old_jobs(self, days_old: int = 30):
    """
    Clean up old job postings from the database
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "status": f"Starting cleanup of jobs older than {days_old} days",
                "progress": 0,
            },
        )

        result = asyncio.run(_cleanup_old_jobs_async(days_old))

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Cleanup completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Job cleanup failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Job cleanup failed: {str(e)}", "progress": 0},
        )
        raise


# Async helper functions
async def _test_scrapers_async() -> Dict[str, Any]:
    """Test all scrapers asynchronously"""
    try:
        # Get scraper configs
        scraper_configs = await automated_workflow_service._get_scraper_configs()

        test_results = {}
        for site_name, config in scraper_configs.items():
            test_result = await automated_workflow_service._test_scraper(
                site_name, config
            )
            test_results[site_name] = test_result

        # Calculate summary
        total_scrapers = len(test_results)
        successful_scrapers = sum(
            1 for result in test_results.values() if result["status"] == "success"
        )

        return {
            "status": "completed",
            "summary": {
                "total_scrapers": total_scrapers,
                "successful_scrapers": successful_scrapers,
                "success_rate": successful_scrapers / total_scrapers
                if total_scrapers > 0
                else 0,
            },
            "detailed_results": test_results,
        }

    except Exception as e:
        logger.error(f"Async scraper testing failed: {str(e)}")
        raise


async def _run_single_scraper_async(site_name: str) -> Dict[str, Any]:
    """Run a single scraper asynchronously"""
    try:
        result = await scraper_service.run_scraper_for_site(site_name)
        return {"status": "completed", "site_name": site_name, "result": result}
    except Exception as e:
        logger.error(f"Single scraper execution failed for {site_name}: {str(e)}")
        raise


async def _run_all_scrapers_async() -> Dict[str, Any]:
    """Run all scrapers asynchronously"""
    try:
        # Get scraper configs
        scraper_configs = await automated_workflow_service._get_scraper_configs()

        results = {}
        total_jobs_scraped = 0

        for site_name in scraper_configs.keys():
            try:
                site_result = await scraper_service.run_scraper_for_site(site_name)
                results[site_name] = site_result
                total_jobs_scraped += site_result.get("jobs_scraped", 0)
            except Exception as e:
                logger.error(f"Scraper failed for {site_name}: {str(e)}")
                results[site_name] = {"status": "failed", "error": str(e)}

        return {
            "status": "completed",
            "total_jobs_scraped": total_jobs_scraped,
            "site_results": results,
        }

    except Exception as e:
        logger.error(f"All scrapers execution failed: {str(e)}")
        raise


async def _migrate_data_async() -> Dict[str, Any]:
    """Migrate data from SQLite to PostgreSQL asynchronously"""
    try:
        result = await scraper_service.migrate_sqlite_to_postgres()
        return {"status": "completed", "migration_result": result}
    except Exception as e:
        logger.error(f"Data migration failed: {str(e)}")
        raise


async def _validate_config_async(
    site_name: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate scraper configuration asynchronously"""
    try:
        test_result = await automated_workflow_service._test_scraper(site_name, config)

        validation_result = {
            "site_name": site_name,
            "config_valid": test_result["status"] == "success",
            "test_result": test_result,
        }

        # Additional validation checks
        required_fields = ["base_url", "listing_path", "listing_selector"]
        missing_fields = [field for field in required_fields if field not in config]

        if missing_fields:
            validation_result["config_valid"] = False
            validation_result["missing_fields"] = missing_fields

        return validation_result

    except Exception as e:
        logger.error(f"Config validation failed for {site_name}: {str(e)}")
        raise


async def _cleanup_old_jobs_async(days_old: int) -> Dict[str, Any]:
    """Clean up old jobs asynchronously"""
    async for db in get_db():
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import delete
            from ..db.models import JobPost

            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Delete old jobs
            delete_stmt = delete(JobPost).where(JobPost.first_seen < cutoff_date)
            result = await db.execute(delete_stmt)
            await db.commit()

            deleted_count = result.rowcount

            return {
                "status": "completed",
                "deleted_jobs": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Job cleanup failed: {str(e)}")
            raise
        finally:
            await db.close()
