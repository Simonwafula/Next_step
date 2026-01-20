"""
Scraper service to integrate scrapers with the main application
"""

import logging
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Ensure package root (app/) is on sys.path so `import scrapers.*` works
sys.path.append(str(Path(__file__).parent.parent))

from scrapers.main import scrape_site, scrape_all_sites
from scrapers.config import SITES, USE_POSTGRES
from scrapers.postgres_db import PostgresJobDatabase
from scrapers.migrate_to_postgres import JobDataMigrator

from sqlalchemy.orm import Session
from ..db.database import get_db
from ..db.models import JobPost, Organization
from ..processors.job_processor import JobProcessorService

logging.basicConfig(level=logging.INFO)

class ScraperService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.job_processor = JobProcessorService()
    
    async def run_scraper_for_site(
        self,
        site_name: str,
        process_jobs: bool = True,
        include_recent_jobs: bool = False,
        recent_jobs_limit: int = 10,
    ) -> Dict[str, Any]:
        """Run scraper for a specific site and optionally process job details"""
        if site_name not in SITES:
            return {
                "success": False,
                "error": f"Unknown site: {site_name}. Available sites: {list(SITES.keys())}"
            }
        
        try:
            self.logger.info(f"Starting scraper for {site_name}")
            
            # Run scraper in a separate thread to avoid blocking
            loop = asyncio.get_running_loop()
            scraped_data = await loop.run_in_executor(None, self._scrape_site_with_data, site_name)
            
            if scraped_data:
                result = {
                    "success": True,
                    "site": site_name,
                    "scraped_jobs": len(scraped_data),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Process job details if requested
                if process_jobs and scraped_data:
                    self.logger.info(f"Processing {len(scraped_data)} jobs from {site_name}")
                    processing_stats = await self.job_processor.process_from_scraper_output(
                        site_name, scraped_data
                    )
                    result.update({
                        "processing_stats": processing_stats,
                        "processed_jobs": processing_stats.get('successful', 0),
                        "failed_jobs": processing_stats.get('failed', 0)
                    })
                
                # Get final job count
                job_count = await self.get_job_count()
                result["total_jobs_in_db"] = job_count
                if include_recent_jobs:
                    recent = await self.get_recent_jobs(recent_jobs_limit)
                    result["recent_jobs"] = recent
                
                return result
            else:
                return {
                    "success": False,
                    "site": site_name,
                    "error": "Scraping failed - no data returned"
                }
                
        except Exception as e:
            self.logger.error(f"Error running scraper for {site_name}: {e}")
            return {
                "success": False,
                "site": site_name,
                "error": str(e)
            }
    
    async def run_all_scrapers(
        self,
        process_jobs: bool = True,
        include_recent_jobs: bool = False,
        recent_jobs_limit: int = 10,
    ) -> Dict[str, Any]:
        """Run scrapers for all configured sites and optionally process job details"""
        try:
            self.logger.info("Starting scrapers for all sites")
            
            results = {}
            total_scraped = 0
            total_processed = 0
            total_failed = 0
            
            # Run scrapers for each site
            for site_name in SITES.keys():
                site_result = await self.run_scraper_for_site(site_name, process_jobs)
                results[site_name] = site_result
                
                if site_result.get("success"):
                    total_scraped += site_result.get("scraped_jobs", 0)
                    if process_jobs:
                        total_processed += site_result.get("processed_jobs", 0)
                        total_failed += site_result.get("failed_jobs", 0)
            
            # Get final job count
            job_count = await self.get_job_count()
            
            summary = {
                "success": True,
                "sites_scraped": list(SITES.keys()),
                "total_scraped_jobs": total_scraped,
                "total_jobs_in_db": job_count,
                "timestamp": datetime.utcnow().isoformat(),
                "site_results": results
            }
            
            if process_jobs:
                summary.update({
                    "total_processed_jobs": total_processed,
                    "total_failed_jobs": total_failed,
                    "processing_success_rate": total_processed / total_scraped if total_scraped > 0 else 0
                })
            if include_recent_jobs:
                summary["recent_jobs"] = await self.get_recent_jobs(recent_jobs_limit)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error running all scrapers: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_job_count(self) -> int:
        """Get total number of jobs in the database"""
        try:
            if USE_POSTGRES:
                db = PostgresJobDatabase()
                db.connect()
                count = db.get_job_count()
                db.close()
                return count
            else:
                # For SQLite, we'd need to implement this differently
                return 0
        except Exception as e:
            self.logger.error(f"Error getting job count: {e}")
            return 0
    
    async def get_recent_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent jobs from the database"""
        try:
            if USE_POSTGRES:
                db = PostgresJobDatabase()
                db.connect()
                jobs = db.get_recent_jobs(limit)
                db.close()
                return jobs
            else:
                return []
        except Exception as e:
            self.logger.error(f"Error getting recent jobs: {e}")
            return []
    
    async def migrate_sqlite_to_postgres(self) -> Dict[str, Any]:
        """Migrate data from SQLite to PostgreSQL"""
        try:
            self.logger.info("Starting migration from SQLite to PostgreSQL")
            
            migrator = JobDataMigrator()
            
            # Run migration in a separate thread
            loop = asyncio.get_running_loop()
            migrated_count = await loop.run_in_executor(None, self._run_migration, migrator)
            
            return {
                "success": True,
                "migrated_jobs": migrated_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error during migration: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _run_migration(self, migrator: JobDataMigrator) -> int:
        """Helper method to run migration synchronously"""
        try:
            migrator.connect_postgres()
            migrated_count = migrator.migrate_jobs()
            return migrated_count
        finally:
            migrator.close()
    
    def _scrape_site_with_data(self, site_name: str) -> List[Dict]:
        """Helper method to scrape site and return data instead of just success/failure"""
        try:
            # Import the specific scraper modules
            from scrapers.brighter_monday_scraper import BrighterMondayScraper
            from scrapers.indeed_scraper import IndeedScraper
            from scrapers.linkedin_scraper import LinkedInScraper

            # Map site names to scraper classes
            scraper_map = {
                'brightermonday': BrighterMondayScraper,
                'indeed': IndeedScraper,
                'linkedin': LinkedInScraper,
            }

            if site_name not in scraper_map:
                self.logger.warning(f"No scraper implementation for {site_name}")
                return []

            scraper_class = scraper_map[site_name]
            return asyncio.run(self._execute_scraper(scraper_class))

        except Exception as e:
            self.logger.error(f"Error in _scrape_site_with_data for {site_name}: {e}")
            return []

    async def _execute_scraper(self, scraper_class) -> List[Dict]:
        """Run the async scraper inside a temporary event loop"""
        try:
            async with scraper_class() as scraper:
                return await scraper.scrape_job_listings()
        except Exception as e:
            self.logger.error(f"Async scraper execution failed: {e}")
            return []
    
    async def process_existing_job_urls(self, job_urls: List[Dict]) -> Dict[str, Any]:
        """Process a list of job URLs through the job processor"""
        try:
            self.logger.info(f"Processing {len(job_urls)} job URLs")
            
            # Process jobs through the job processor
            results = await self.job_processor.processor.process_job_urls_batch(job_urls)
            
            successful = sum(1 for r in results if r is not None)
            failed = len(results) - successful
            
            return {
                "success": True,
                "total_processed": len(results),
                "successful": successful,
                "failed": failed,
                "success_rate": successful / len(results) if results else 0,
                "job_ids": [r for r in results if r is not None],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing job URLs: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_processor_health(self) -> Dict[str, Any]:
        """Get health status of the job processor"""
        try:
            return await self.job_processor.health_check()
        except Exception as e:
            self.logger.error(f"Error getting processor health: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.utcnow()
            }
    
    async def get_scraper_status(self) -> Dict[str, Any]:
        """Get status of scrapers and database"""
        try:
            job_count = await self.get_job_count()
            recent_jobs = await self.get_recent_jobs(5)
            processor_health = await self.get_processor_health()
            processor_stats = self.job_processor.get_stats()
            
            return {
                "database_type": "PostgreSQL" if USE_POSTGRES else "SQLite",
                "total_jobs": job_count,
                "available_sites": list(SITES.keys()),
                "recent_jobs": recent_jobs,
                "processor_health": processor_health,
                "processor_stats": processor_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting scraper status: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Global instance
scraper_service = ScraperService()
