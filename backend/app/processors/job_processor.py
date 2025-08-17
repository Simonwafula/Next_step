"""
Main job processor that orchestrates extraction, cleaning, and saving of job data
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from .job_extractor import JobDataExtractor
from .data_cleaner import JobDataCleaner
from .database_saver import JobDatabaseSaver

logger = logging.getLogger(__name__)

class JobProcessor:
    """
    Main processor that orchestrates the complete job data processing pipeline
    """
    
    def __init__(self):
        self.extractor = None
        self.cleaner = JobDataCleaner()
        self.saver = JobDatabaseSaver()
        
    async def process_job_url(self, url: str, source: str) -> Optional[int]:
        """
        Process a single job URL through the complete pipeline
        
        Args:
            url: Job post URL
            source: Source identifier (e.g., 'brightermonday', 'linkedin')
            
        Returns:
            Job post ID if successful, None otherwise
        """
        try:
            logger.info(f"Processing job URL: {url}")
            
            # Extract job data
            async with JobDataExtractor() as extractor:
                raw_data = await extractor.extract_job_details(url, source)
                
            if not raw_data:
                logger.warning(f"Failed to extract data from {url}")
                return None
                
            # Clean and normalize data
            cleaned_data = self.cleaner.clean_job_data(raw_data)
            
            # Save to database
            job_id = self.saver.save_job_data(cleaned_data)
            
            if job_id:
                logger.info(f"Successfully processed job {job_id} from {url}")
            else:
                logger.error(f"Failed to save job data from {url}")
                
            return job_id
            
        except Exception as e:
            logger.error(f"Error processing job URL {url}: {e}")
            return None
            
    async def process_job_urls_batch(self, job_urls: List[Dict]) -> List[Optional[int]]:
        """
        Process multiple job URLs in batch
        
        Args:
            job_urls: List of dicts with 'url' and 'source' keys
            
        Returns:
            List of job post IDs (None for failed processes)
        """
        results = []
        
        # Process in batches to avoid overwhelming the system
        batch_size = 10
        for i in range(0, len(job_urls), batch_size):
            batch = job_urls[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [
                self.process_job_url(job_data['url'], job_data['source'])
                for job_data in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Exception in batch processing: {result}")
                    results.append(None)
                else:
                    results.append(result)
                    
            # Small delay between batches to be respectful
            await asyncio.sleep(1)
            
        return results
        
    async def process_scraped_jobs(self, scraped_jobs: List[Dict]) -> Dict:
        """
        Process jobs that have been scraped (title + link only)
        
        Args:
            scraped_jobs: List of scraped job records with basic info
            
        Returns:
            Processing statistics
        """
        logger.info(f"Processing {len(scraped_jobs)} scraped jobs")
        
        # Convert to format expected by batch processor
        job_urls = [
            {
                'url': job.get('link', ''),
                'source': job.get('source', 'unknown')
            }
            for job in scraped_jobs
            if job.get('link')
        ]
        
        # Process all jobs
        results = await self.process_job_urls_batch(job_urls)
        
        # Calculate statistics
        successful = sum(1 for r in results if r is not None)
        failed = len(results) - successful
        
        stats = {
            'total_processed': len(results),
            'successful': successful,
            'failed': failed,
            'success_rate': successful / len(results) if results else 0,
            'processed_at': datetime.utcnow(),
            'job_ids': [r for r in results if r is not None]
        }
        
        logger.info(f"Processing complete: {successful}/{len(results)} successful")
        return stats
        
    def get_processing_stats(self) -> Dict:
        """Get overall processing statistics"""
        return self.saver.get_job_stats()
        
    async def reprocess_failed_jobs(self, max_retries: int = 3) -> Dict:
        """
        Reprocess jobs that failed to extract properly
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            Reprocessing statistics
        """
        # This would require tracking failed jobs in the database
        # For now, return empty stats
        logger.info("Reprocessing failed jobs not implemented yet")
        return {
            'reprocessed': 0,
            'successful': 0,
            'still_failed': 0
        }
        
    async def update_existing_jobs(self, days_old: int = 7) -> Dict:
        """
        Update existing jobs that are older than specified days
        
        Args:
            days_old: Update jobs older than this many days
            
        Returns:
            Update statistics
        """
        from ..db.database import SessionLocal
        from ..db.models import JobPost
        from datetime import timedelta
        
        db = SessionLocal()
        try:
            # Get jobs older than specified days
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            old_jobs = db.query(JobPost).filter(
                JobPost.last_seen < cutoff_date
            ).all()
            
            logger.info(f"Found {len(old_jobs)} jobs to update")
            
            # Convert to format for batch processing
            job_urls = [
                {
                    'url': job.url,
                    'source': job.source
                }
                for job in old_jobs
            ]
            
            # Process updates
            results = await self.process_job_urls_batch(job_urls)
            
            successful = sum(1 for r in results if r is not None)
            
            return {
                'total_checked': len(old_jobs),
                'successful_updates': successful,
                'failed_updates': len(results) - successful,
                'updated_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error updating existing jobs: {e}")
            return {'error': str(e)}
        finally:
            db.close()


class JobProcessorService:
    """
    Service wrapper for job processor with additional utilities
    """
    
    def __init__(self):
        self.processor = JobProcessor()
        
    async def process_from_scraper_output(self, scraper_name: str, scraped_data: List[Dict]) -> Dict:
        """
        Process jobs from scraper output
        
        Args:
            scraper_name: Name of the scraper
            scraped_data: Raw scraped data
            
        Returns:
            Processing results
        """
        logger.info(f"Processing {len(scraped_data)} jobs from {scraper_name}")
        
        # Add source information to each job
        for job in scraped_data:
            job['source'] = scraper_name
            
        return await self.processor.process_scraped_jobs(scraped_data)
        
    async def process_single_url(self, url: str, source: str = 'manual') -> Optional[int]:
        """
        Process a single URL (useful for testing or manual processing)
        
        Args:
            url: Job post URL
            source: Source identifier
            
        Returns:
            Job post ID if successful
        """
        return await self.processor.process_job_url(url, source)
        
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return self.processor.get_processing_stats()
        
    async def health_check(self) -> Dict:
        """
        Perform health check on the processing pipeline
        
        Returns:
            Health status
        """
        try:
            # Test database connection
            stats = self.get_stats()
            
            # Test extractor
            async with JobDataExtractor() as extractor:
                # This just tests that we can create the extractor
                pass
                
            return {
                'status': 'healthy',
                'database_connected': True,
                'extractor_available': True,
                'total_jobs_in_db': stats.get('total_jobs', 0),
                'checked_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'checked_at': datetime.utcnow()
            }
