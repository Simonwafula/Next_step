#!/usr/bin/env python3
# ruff: noqa: E402
"""
Test bridge to connect working scrapers to main pipeline
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

from app.scrapers.spiders.myjobmag import JobScraper as MyJobMagScraper  # noqa: E402
from app.processors.job_processor import JobProcessor  # noqa: E402

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_pipeline_connection():
    """Test connecting scraper to main pipeline"""

    # 1. Get jobs from working scraper
    logger.info("Testing MyJobMag scraper...")
    scraper = MyJobMagScraper()
    scraper.db.connect()

    # Get first page of jobs
    listings = scraper.fetch_job_listings(1)
    logger.info(f"Found {len(listings)} jobs on page 1")

    if not listings:
        logger.error("No jobs found - cannot test pipeline")
        return False

    # 2. Test pipeline with first job
    first_job = listings[0]
    logger.info(f"Testing pipeline with job: {first_job.title}")

    # 3. Initialize job processor
    processor = JobProcessor()

    # 4. Process job through pipeline
    job_id = await processor.process_job_url(first_job.full_link, "myjobmag")

    if job_id:
        logger.info(f"✅ SUCCESS: Job processed and saved with ID {job_id}")
        return True
    else:
        logger.error("❌ FAILED: Job pipeline processing failed")
        return False


async def test_batch_processing():
    """Test processing multiple jobs"""
    logger.info("\n=== Testing Batch Processing ===")

    scraper = MyJobMagScraper()
    scraper.db.connect()

    listings = scraper.fetch_job_listings(1)
    processor = JobProcessor()

    success_count = 0
    total_count = min(5, len(listings))  # Test first 5 jobs

    for i, job in enumerate(listings[:total_count]):
        logger.info(f"Processing job {i + 1}/{total_count}: {job.title[:50]}...")
        job_id = await processor.process_job_url(job.full_link, "myjobmag")
        if job_id:
            success_count += 1
            logger.info(f"✅ Success - ID: {job_id}")
        else:
            logger.error("❌ Failed")

    logger.info(
        f"\nBatch Result: {success_count}/{total_count} jobs processed successfully"
    )
    return success_count > 0


if __name__ == "__main__":

    async def main():
        try:
            # Test single job processing
            success1 = await test_pipeline_connection()

            # Test batch processing
            success2 = await test_batch_processing()

            if success1 and success2:
                logger.info("\n🎉 PIPELINE CONNECTION TEST: PASSED")
                logger.info("Working scrapers can connect to main database!")
            else:
                logger.error("\n💥 PIPELINE CONNECTION TEST: FAILED")

        except Exception as e:
            logger.error(f"Test failed with error: {e}", exc_info=True)

    asyncio.run(main())
