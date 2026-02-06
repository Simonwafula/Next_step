"""
Automated data processing service that runs continuously to process scraped job data
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import func, or_
from ..db.database import SessionLocal
from ..db.models import JobPost, ProcessingLog
from ..processors.job_processor import JobProcessorService

logger = logging.getLogger(__name__)


class DataProcessingService:
    """
    Service that automatically processes scraped job data and maintains data quality
    """

    def __init__(self):
        self.processor_service = JobProcessorService()
        self.is_running = False
        self.processing_interval = 300  # 5 minutes

    async def start_continuous_processing(self):
        """Start continuous data processing"""
        if self.is_running:
            logger.warning("Data processing service is already running")
            return

        self.is_running = True
        logger.info("Starting continuous data processing service")

        while self.is_running:
            try:
                await self.process_pending_jobs()
                await self.cleanup_old_data()
                await self.update_job_statistics()

                # Wait before next processing cycle
                await asyncio.sleep(self.processing_interval)

            except Exception as e:
                logger.error(f"Error in processing cycle: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    def stop_continuous_processing(self):
        """Stop continuous data processing"""
        self.is_running = False
        logger.info("Stopping continuous data processing service")

    async def process_pending_jobs(self) -> Dict:
        """Process jobs that have been scraped but not yet processed"""
        db = SessionLocal()
        try:
            # Get jobs with minimal/empty descriptions; prioritize recent postings.
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            unprocessed_jobs = (
                db.query(JobPost)
                .filter(
                    or_(
                        JobPost.description_raw.is_(None),
                        JobPost.description_raw == "",
                    ),
                    JobPost.first_seen >= recent_cutoff,
                )
                .limit(50)
                .all()
            )

            if not unprocessed_jobs:
                logger.debug("No pending jobs to process")
                return {"processed": 0, "message": "No pending jobs"}

            logger.info(f"Processing {len(unprocessed_jobs)} pending jobs")

            # Convert to format expected by processor
            job_data = [
                {"url": job.url, "source": job.source, "link": job.url}
                for job in unprocessed_jobs
            ]

            # Process the jobs
            results = await self.processor_service.process_from_scraper_output(
                "automated_processing", job_data
            )

            # Log processing results
            self._log_processing_results("pending_jobs", results)

            return results

        except Exception as e:
            logger.error(f"Error processing pending jobs: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    async def cleanup_old_data(self) -> Dict:
        """Clean up old job postings and maintain data quality"""
        db = SessionLocal()
        try:
            # Remove jobs not seen in a long time (treat as inactive).
            cutoff_date = datetime.utcnow() - timedelta(days=90)

            old_jobs = db.query(JobPost).filter(JobPost.last_seen < cutoff_date).count()

            if old_jobs > 0:
                db.query(JobPost).filter(JobPost.last_seen < cutoff_date).delete(
                    synchronize_session=False
                )
                db.commit()
                logger.info(f"Cleaned up {old_jobs} old job postings")

            return {"cleaned_jobs": old_jobs}

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()

    async def update_job_statistics(self) -> Dict:
        """Update job statistics and market insights"""
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            active_cutoff = now - timedelta(days=30)
            recent_cutoff = now - timedelta(days=7)

            total_jobs = db.query(func.count(JobPost.id)).scalar() or 0
            active_jobs = (
                db.query(func.count(JobPost.id))
                .filter(JobPost.last_seen >= active_cutoff)
                .scalar()
                or 0
            )
            recent_jobs = (
                db.query(func.count(JobPost.id))
                .filter(JobPost.first_seen >= recent_cutoff)
                .scalar()
                or 0
            )

            stats = {
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "recent_jobs": recent_jobs,
                "updated_at": now,
            }

            logger.info(f"Updated job statistics: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    async def process_new_opportunities(self) -> List[Dict]:
        """Identify and process new job opportunities for notifications"""
        db = SessionLocal()
        try:
            # Get jobs posted in the last 24 hours
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)

            new_jobs = (
                db.query(JobPost).filter(JobPost.first_seen >= recent_cutoff).all()
            )

            opportunities = []
            for job in new_jobs:
                opportunity = {
                    "id": job.id,
                    "title": job.title_raw,
                    "company": job.organization.name if job.organization else "Unknown",
                    "location": (
                        job.location.city
                        if job.location and job.location.city
                        else (job.location.raw if job.location else "Remote")
                    ),
                    "salary_range": f"{job.salary_min}-{job.salary_max}"
                    if job.salary_min
                    else None,
                    "url": job.url,
                    "posted_at": job.first_seen,
                    "role_family": job.title_norm.family if job.title_norm else None,
                    "seniority": job.seniority,
                }
                opportunities.append(opportunity)

            logger.info(f"Found {len(opportunities)} new opportunities")
            return opportunities

        except Exception as e:
            logger.error(f"Error processing new opportunities: {e}")
            return []
        finally:
            db.close()

    def _log_processing_results(self, process_type: str, results: Dict):
        """Log processing results to database"""
        db = SessionLocal()
        try:
            log_entry = ProcessingLog(
                process_type=process_type,
                results=results,
                processed_at=datetime.utcnow(),
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Error logging processing results: {e}")
            db.rollback()
        finally:
            db.close()

    async def get_processing_status(self) -> Dict:
        """Get current processing status"""
        return {
            "is_running": self.is_running,
            "processing_interval": self.processing_interval,
            "last_health_check": await self.processor_service.health_check(),
        }

    async def trigger_manual_processing(self) -> Dict:
        """Manually trigger a processing cycle"""
        logger.info("Manual processing triggered")

        results = {
            "pending_jobs": await self.process_pending_jobs(),
            "cleanup": await self.cleanup_old_data(),
            "statistics": await self.update_job_statistics(),
            "triggered_at": datetime.utcnow(),
        }

        return results


# Global service instance
data_processing_service = DataProcessingService()
