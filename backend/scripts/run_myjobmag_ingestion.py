#!/usr/bin/env python3
# ruff: noqa: E402
"""
Run MyJobMag ingestion into the main job database.

This script:
1. Scrapes jobs from MyJobMag Kenya
2. Processes each job through the main pipeline
3. Saves to the main database with proper normalization
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from urllib.parse import urljoin

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Set database URL for main database
os.environ.setdefault("DATABASE_URL", "sqlite:///var/nextstep.sqlite")

import requests
from bs4 import BeautifulSoup
from app.processors.job_processor import JobProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def scrape_myjobmag_page(page_number: int) -> list:
    """Scrape a single page of MyJobMag jobs."""
    url = f"https://www.myjobmag.co.ke/jobs/page/{page_number}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find job listings - MyJobMag uses li.mag-b elements
        job_items = soup.select("li.mag-b a")

        job_list = []
        seen_urls = set()

        for job in job_items:
            link = job.get("href", "")
            title = job.get_text(strip=True)

            # Skip if no link or already seen
            if not link or link in seen_urls:
                continue

            # Ensure absolute URL
            if not link.startswith("http"):
                link = urljoin("https://www.myjobmag.co.ke", link)

            # Only include job detail pages
            if "/jobs/" not in link or "/page/" in link:
                continue

            seen_urls.add(link)

            if title and link:
                job_list.append({"title": title, "link": link, "source": "myjobmag"})

        return job_list

    except Exception as e:
        logger.error(f"Error scraping page {page_number}: {e}")
        return []


async def run_ingestion(pages: int = 5, batch_size: int = 10):
    """Run the MyJobMag ingestion process."""
    logger.info(f"Starting MyJobMag ingestion for {pages} pages")

    # Scrape all pages
    all_jobs = []
    for page in range(1, pages + 1):
        logger.info(f"Scraping page {page}/{pages}...")
        jobs = scrape_myjobmag_page(page)
        all_jobs.extend(jobs)
        logger.info(f"Found {len(jobs)} jobs on page {page}")

        # Small delay to be respectful
        await asyncio.sleep(1)

    # Remove duplicates by URL
    seen_urls = set()
    unique_jobs = []
    for job in all_jobs:
        if job["link"] not in seen_urls:
            seen_urls.add(job["link"])
            unique_jobs.append(job)

    logger.info(f"Total unique jobs found: {len(unique_jobs)}")

    # Process through pipeline
    processor = JobProcessor()

    successful = 0
    failed = 0

    for i in range(0, len(unique_jobs), batch_size):
        batch = unique_jobs[i : i + batch_size]
        logger.info(
            f"Processing batch {i // batch_size + 1}/{(len(unique_jobs) + batch_size - 1) // batch_size}"
        )

        for job in batch:
            try:
                job_id = await processor.process_job_url(job["link"], "myjobmag")
                if job_id:
                    successful += 1
                    logger.info(f"✓ Processed: {job['title'][:50]}... -> ID {job_id}")
                else:
                    failed += 1
                    logger.warning(f"✗ Failed: {job['title'][:50]}...")
            except Exception as e:
                failed += 1
                logger.error(f"Error processing {job['link']}: {e}")

        # Delay between batches
        await asyncio.sleep(2)

    logger.info(f"\n{'=' * 60}")
    logger.info("INGESTION COMPLETE")
    logger.info(f"{'=' * 60}")
    logger.info(f"Total scraped: {len(unique_jobs)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(
        f"Success rate: {successful / len(unique_jobs) * 100:.1f}%"
        if unique_jobs
        else "N/A"
    )

    return {"total": len(unique_jobs), "successful": successful, "failed": failed}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run MyJobMag job ingestion")
    parser.add_argument(
        "--pages", type=int, default=5, help="Number of pages to scrape (default: 5)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Batch size for processing (default: 5)",
    )

    args = parser.parse_args()

    asyncio.run(run_ingestion(pages=args.pages, batch_size=args.batch_size))
