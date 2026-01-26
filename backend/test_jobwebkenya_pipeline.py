#!/usr/bin/env python3
"""
Extend pipeline connection to JobWebKenya scraper
"""

import asyncio
import logging
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.scrapers.spiders.jobwebkenya import JobScraper as JobWebKenyaScraper  # noqa: E402
from app.processors.job_processor import JobProcessor  # noqa: E402

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_jobwebkenya_pipeline():
    """Test JobWebKenya scraper with main pipeline"""

    # 1. Get jobs from JobWebKenya scraper
    logger.info("Testing JobWebKenya scraper...")
    scraper = JobWebKenyaScraper()
    scraper.db.connect()

    # Get first page of jobs
    listings = scraper.fetch_job_listings(1)
    logger.info(f"Found {len(listings)} jobs on page 1")

    if not listings:
        logger.error("No jobs found - cannot test pipeline")
        return False

    # 2. Test pipeline with first 3 jobs
    processor = JobProcessor()
    success_count = 0

    for i, job in enumerate(listings[:3]):
        logger.info(f"Testing job {i + 1}/3: {job.title[:50]}...")
        job_id = await processor.process_job_url(job.full_link, "jobwebkenya")
        if job_id:
            success_count += 1
            logger.info(f"✅ Success - ID: {job_id}")
        else:
            logger.error("❌ Failed")

    logger.info(
        f"JobWebKenya pipeline result: {success_count}/3 jobs processed successfully"
    )
    return success_count > 0


async def test_multiple_sources():
    """Test both working scrapers together"""
    logger.info("\n=== Testing Multiple Sources ===")

    processor = JobProcessor()
    all_success = True

    # Test MyJobMag (2 jobs)
    logger.info("Testing MyJobMag...")
    myjobmag_scraper = __import__(
        "app.scrapers.spiders.myjobmag", fromlist=["JobScraper"]
    ).JobScraper()
    myjobmag_scraper.db.connect()
    myjobmag_jobs = myjobmag_scraper.fetch_job_listings(1)[:2]

    for job in myjobmag_jobs:
        job_id = await processor.process_job_url(job.full_link, "myjobmag")
        if job_id:
            logger.info(f"✅ MyJobMag: {job.title[:30]}... -> ID {job_id}")
        else:
            logger.error(f"❌ MyJobMag: {job.title[:30]}...")
            all_success = False

    # Test JobWebKenya (2 jobs)
    logger.info("Testing JobWebKenya...")
    jobwebkenya_scraper = JobWebKenyaScraper()
    jobwebkenya_scraper.db.connect()
    jobwebkenya_jobs = jobwebkenya_scraper.fetch_job_listings(1)[:2]

    for job in jobwebkenya_jobs:
        job_id = await processor.process_job_url(job.full_link, "jobwebkenya")
        if job_id:
            logger.info(f"✅ JobWebKenya: {job.title[:30]}... -> ID {job_id}")
        else:
            logger.error(f"❌ JobWebKenya: {job.title[:30]}...")
            all_success = False

    return all_success


if __name__ == "__main__":

    async def main():
        try:
            # Test JobWebKenya pipeline
            success1 = await test_jobwebkenya_pipeline()

            # Test multiple sources
            success2 = await test_multiple_sources()

            if success1 and success2:
                logger.info("\n🎉 MULTI-SOURCE PIPELINE TEST: PASSED")
                logger.info(
                    "Both MyJobMag and JobWebKenya can connect to main database!"
                )
                logger.info("Ready for ingestion testing!")
            else:
                logger.error("\n💥 MULTI-SOURCE PIPELINE TEST: FAILED")

        except Exception as e:
            logger.error(f"Test failed with error: {e}", exc_info=True)

    asyncio.run(main())
