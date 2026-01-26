"""
Notification service for sending alerts about new job opportunities
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..db.database import SessionLocal
from ..db.models import JobPost, User, NotificationPreference, NotificationLog
from ..services.data_processing_service import data_processing_service
from ..webhooks.whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing and sending notifications about new job opportunities
    """

    def __init__(self):
        self.is_running = False
        self.check_interval = 3600  # 1 hour
        self.processed_jobs = set()

    async def start_notification_service(self):
        """Start the continuous notification service"""
        if self.is_running:
            logger.warning("Notification service is already running")
            return

        self.is_running = True
        logger.info("Starting notification service")

        while self.is_running:
            try:
                await self.process_new_opportunities()
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in notification cycle: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    def stop_notification_service(self):
        """Stop the notification service"""
        self.is_running = False
        logger.info("Stopping notification service")

    async def process_new_opportunities(self) -> Dict:
        """Process and send notifications for new job opportunities"""
        db = SessionLocal()
        try:
            # Get new opportunities from data processing service
            new_opportunities = (
                await data_processing_service.process_new_opportunities()
            )

            if not new_opportunities:
                logger.debug("No new opportunities to process")
                return {"processed": 0, "sent": 0}

            logger.info(f"Processing {len(new_opportunities)} new opportunities")

            # Get users with notification preferences
            users_with_prefs = (
                db.query(User)
                .join(NotificationPreference)
                .filter(NotificationPreference.enabled == True)
                .all()
            )

            notifications_sent = 0

            for user in users_with_prefs:
                matching_jobs = self._find_matching_jobs(user, new_opportunities)

                if matching_jobs:
                    await self._send_user_notifications(user, matching_jobs)
                    notifications_sent += len(matching_jobs)

            # Log the processing results
            self._log_notification_batch(len(new_opportunities), notifications_sent)

            return {
                "processed": len(new_opportunities),
                "sent": notifications_sent,
                "users_notified": len(users_with_prefs),
            }

        except Exception as e:
            logger.error(f"Error processing new opportunities: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    def _find_matching_jobs(self, user: User, opportunities: List[Dict]) -> List[Dict]:
        """Find job opportunities that match user preferences"""
        matching_jobs = []

        # Get user preferences
        prefs = (
            user.notification_preferences[0] if user.notification_preferences else None
        )
        if not prefs:
            return matching_jobs

        for job in opportunities:
            if self._job_matches_preferences(job, prefs):
                matching_jobs.append(job)

        return matching_jobs

    def _job_matches_preferences(
        self, job: Dict, prefs: NotificationPreference
    ) -> bool:
        """Check if a job matches user notification preferences"""
        # Location matching
        if prefs.preferred_locations:
            locations = [
                loc.strip().lower() for loc in prefs.preferred_locations.split(",")
            ]
            job_location = job.get("location", "").lower()
            if not any(loc in job_location for loc in locations):
                return False

        # Role family matching
        if prefs.preferred_roles:
            roles = [role.strip().lower() for role in prefs.preferred_roles.split(",")]
            job_role = job.get("role_family", "").lower()
            job_title = job.get("title", "").lower()
            if not any(role in job_role or role in job_title for role in roles):
                return False

        # Seniority matching
        if prefs.preferred_seniority:
            seniority_levels = [
                level.strip().lower() for level in prefs.preferred_seniority.split(",")
            ]
            job_seniority = job.get("seniority", "").lower()
            if not any(level in job_seniority for level in seniority_levels):
                return False

        # Salary matching
        if prefs.min_salary and job.get("salary_range"):
            try:
                # Extract minimum salary from range
                salary_parts = job["salary_range"].split("-")
                if salary_parts:
                    min_salary = int(salary_parts[0].replace(",", ""))
                    if min_salary < prefs.min_salary:
                        return False
            except (ValueError, IndexError):
                pass  # Skip salary filtering if parsing fails

        return True

    async def _send_user_notifications(self, user: User, matching_jobs: List[Dict]):
        """Send notifications to a user for matching jobs"""
        try:
            # Group jobs by notification type preference
            prefs = user.notification_preferences[0]

            if prefs.whatsapp_enabled and user.phone_number:
                await self._send_whatsapp_notifications(user, matching_jobs)

            if prefs.email_enabled and user.email:
                await self._send_email_notifications(user, matching_jobs)

            # Log successful notifications
            self._log_user_notifications(user.id, len(matching_jobs))

        except Exception as e:
            logger.error(f"Error sending notifications to user {user.id}: {e}")

    async def _send_whatsapp_notifications(self, user: User, jobs: List[Dict]):
        """Send WhatsApp notifications for new job opportunities"""
        try:
            # Create summary message
            if len(jobs) == 1:
                job = jobs[0]
                message = f"""🎯 *New Job Alert!*

*{job["title"]}*
🏢 {job["company"]}
📍 {job["location"]}
{f"💰 {job['salary_range']}" if job.get("salary_range") else ""}

🔗 Apply: {job["url"]}

Reply STOP to unsubscribe from job alerts."""
            else:
                message = f"""🎯 *{len(jobs)} New Job Alerts!*

"""
                for i, job in enumerate(jobs[:3], 1):  # Show first 3 jobs
                    message += f"""*{i}. {job["title"]}*
🏢 {job["company"]} | 📍 {job["location"]}
{f"💰 {job['salary_range']}" if job.get("salary_range") else ""}

"""

                if len(jobs) > 3:
                    message += f"...and {len(jobs) - 3} more opportunities!\n\n"

                message += "Visit CareerSearch to see all opportunities.\nReply STOP to unsubscribe."

            # Send WhatsApp message
            await send_whatsapp_message(user.phone_number, message)
            logger.info(f"Sent WhatsApp notification to {user.phone_number}")

        except Exception as e:
            logger.error(f"Error sending WhatsApp notification: {e}")

    async def _send_email_notifications(self, user: User, jobs: List[Dict]):
        """Send email notifications for new job opportunities"""
        # Email functionality would be implemented here
        # For now, we'll log that an email would be sent
        logger.info(
            f"Would send email notification to {user.email} for {len(jobs)} jobs"
        )

    def _log_notification_batch(self, total_jobs: int, notifications_sent: int):
        """Log notification batch processing results"""
        db = SessionLocal()
        try:
            log_entry = NotificationLog(
                notification_type="batch_processing",
                total_jobs=total_jobs,
                notifications_sent=notifications_sent,
                processed_at=datetime.utcnow(),
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Error logging notification batch: {e}")
            db.rollback()
        finally:
            db.close()

    def _log_user_notifications(self, user_id: int, job_count: int):
        """Log notifications sent to a specific user"""
        db = SessionLocal()
        try:
            log_entry = NotificationLog(
                notification_type="user_notification",
                user_id=user_id,
                notifications_sent=job_count,
                processed_at=datetime.utcnow(),
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Error logging user notification: {e}")
            db.rollback()
        finally:
            db.close()

    async def send_custom_notification(
        self, user_id: int, message: str, notification_type: str = "custom"
    ) -> bool:
        """Send a custom notification to a specific user"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found")
                return False

            prefs = (
                user.notification_preferences[0]
                if user.notification_preferences
                else None
            )
            if not prefs or not prefs.enabled:
                logger.info(f"Notifications disabled for user {user_id}")
                return False

            # Send via preferred channels
            success = False

            if prefs.whatsapp_enabled and user.phone_number:
                await send_whatsapp_message(user.phone_number, message)
                success = True

            if prefs.email_enabled and user.email:
                # Email sending would be implemented here
                logger.info(f"Would send email to {user.email}")
                success = True

            if success:
                self._log_user_notifications(user_id, 1)

            return success

        except Exception as e:
            logger.error(f"Error sending custom notification: {e}")
            return False
        finally:
            db.close()

    async def get_notification_stats(self) -> Dict:
        """Get notification service statistics"""
        db = SessionLocal()
        try:
            from sqlalchemy import func

            # Get stats for the last 24 hours
            yesterday = datetime.utcnow() - timedelta(hours=24)

            total_sent = (
                db.query(func.sum(NotificationLog.notifications_sent))
                .filter(NotificationLog.processed_at > yesterday)
                .scalar()
                or 0
            )

            unique_users = (
                db.query(func.count(NotificationLog.user_id.distinct()))
                .filter(
                    NotificationLog.processed_at > yesterday,
                    NotificationLog.user_id.is_not(None),
                )
                .scalar()
                or 0
            )

            total_users_with_prefs = (
                db.query(func.count(User.id))
                .join(NotificationPreference)
                .filter(NotificationPreference.enabled == True)
                .scalar()
                or 0
            )

            return {
                "is_running": self.is_running,
                "check_interval_minutes": self.check_interval // 60,
                "last_24h_notifications": total_sent,
                "last_24h_users_notified": unique_users,
                "total_users_with_notifications": total_users_with_prefs,
                "last_check": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {"error": str(e)}
        finally:
            db.close()


# Global service instance
notification_service = NotificationService()
