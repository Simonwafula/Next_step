#!/usr/bin/env python3
# ruff: noqa: E402
"""
Unified ingestion test for working scrapers
Tests P0 success criteria: ingestion from multiple sources
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.scrapers.spiders.myjobmag import JobScraper as MyJobMagScraper
from app.scrapers.spiders.jobwebkenya import JobScraper as JobWebKenyaScraper
from app.processors.job_processor import JobProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UnifiedIngester:
    def __init__(self):
        self.processor = JobProcessor()

    async def ingest_from_source(
        self, scraper_class, source_name, max_pages=2, max_jobs=10
    ):
        """Ingest jobs from a specific source"""
        logger.info(f"\n=== Ingesting from {source_name} ===")

        scraper = scraper_class()
        scraper.db.connect()  # Legacy DB for job listings

        jobs_processed = 0
        pages_processed = 0

        for page in range(1, max_pages + 1):
            logger.info(f"Processing {source_name} page {page}...")
            listings = scraper.fetch_job_listings(page)

            if not listings:
                logger.info(f"No jobs found on page {page}, stopping")
                break

            logger.info(f"Found {len(listings)} jobs on page {page}")

            # Process jobs
            page_success = 0
            for job in listings[: max_jobs - jobs_processed]:
                if jobs_processed >= max_jobs:
                    break

                job_id = await self.processor.process_job_url(
                    job.full_link, source_name
                )
                if job_id:
                    jobs_processed += 1
                    page_success += 1
                    logger.info(f"✅ {source_name}: {job.title[:40]}... -> ID {job_id}")
                else:
                    logger.error(f"❌ Failed: {job.title[:40]}...")

            pages_processed += 1
            logger.info(
                f"Page {page} complete: {page_success}/{len(listings)} jobs processed"
            )

            if jobs_processed >= max_jobs:
                break

        scraper.db.close()
        logger.info(
            f"{source_name} ingestion complete: {jobs_processed} jobs from {pages_processed} pages"
        )
        return jobs_processed

    async def run_ingestion_test(self):
        """Run ingestion from multiple sources"""
        logger.info("🚀 Starting unified ingestion test")
        start_time = datetime.now()

        results = {}

        # Test MyJobMag
        try:
            myjobmag_count = await self.ingest_from_source(
                MyJobMagScraper, "myjobmag", max_pages=2, max_jobs=8
            )
            results["myjobmag"] = myjobmag_count
        except Exception as e:
            logger.error(f"MyJobMag ingestion failed: {e}")
            results["myjobmag"] = 0

        # Test JobWebKenya
        try:
            jobwebkenya_count = await self.ingest_from_source(
                JobWebKenyaScraper, "jobwebkenya", max_pages=2, max_jobs=8
            )
            results["jobwebkenya"] = jobwebkenya_count
        except Exception as e:
            logger.error(f"JobWebKenya ingestion failed: {e}")
            results["jobwebkenya"] = 0

        # Analyze results
        total_jobs = sum(results.values())
        duration = (datetime.now() - start_time).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("📊 INGESTION TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"MyJobMag: {results.get('myjobmag', 0)} jobs")
        logger.info(f"JobWebKenya: {results.get('jobwebkenya', 0)} jobs")
        logger.info(f"Total: {total_jobs} jobs")
        logger.info(f"Duration: {duration:.1f} seconds")

        # Check P0 success criteria
        sources_working = sum(1 for count in results.values() if count > 0)

        logger.info("\n🎯 P0 Success Criteria Check:")
        logger.info(f"✅ Sources working: {sources_working} (need ≥1)")
        logger.info(f"✅ Total jobs ingested: {total_jobs} (need >0)")

        if sources_working >= 2 and total_jobs >= 10:
            logger.info("🎉 P0 INGESTION CRITERIA: PASSED")
            logger.info("✅ Multiple sources contributing jobs")
            logger.info("✅ Pipeline: scraper → processor → database working")
            return True
        else:
            logger.error("💥 P0 INGESTION CRITERIA: FAILED")
            logger.error(
                f"Need ≥2 sources and ≥10 jobs, got {sources_working} sources and {total_jobs} jobs"
            )
            return False


if __name__ == "__main__":

    async def main():
        try:
            ingester = UnifiedIngester()
            success = await ingester.run_ingestion_test()

            if success:
                logger.info("\n🏁 INGESTION TEST: COMPLETED SUCCESSFULLY")
                logger.info("Ready for production testing!")
            else:
                logger.error("\n🚨 INGESTION TEST: FAILED")
                logger.error("Review logs and fix issues")

        except Exception as e:
            logger.error(f"Test failed with error: {e}", exc_info=True)

    asyncio.run(main())
