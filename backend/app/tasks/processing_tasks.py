import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..core.celery_app import celery_app
from ..db.database import get_db, SessionLocal
from ..services.automated_workflow_service import automated_workflow_service
from ..services.email_service import send_email
from ..processors.job_processor import JobProcessor

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.processing_tasks.process_raw_jobs")
def process_raw_jobs(self, batch_size: int = 100):
    """
    Process raw job data in batches
    """
    try:
        self.update_state(
            state="PROGRESS", meta={"status": "Starting job processing", "progress": 0}
        )

        result = asyncio.run(_process_raw_jobs_async(batch_size))

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Job processing completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Job processing failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Job processing failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.processing_tasks.clean_duplicate_jobs")
def clean_duplicate_jobs(self):
    """
    Clean duplicate job postings from the database
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting duplicate cleanup", "progress": 0},
        )

        result = asyncio.run(_clean_duplicate_jobs_async())

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Duplicate cleanup completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Duplicate cleanup failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Duplicate cleanup failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.processing_tasks.extract_job_skills")
def extract_job_skills(self, job_ids: List[int] = None):
    """
    Extract skills from job descriptions
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting skill extraction", "progress": 0},
        )

        result = asyncio.run(_extract_job_skills_async(job_ids))

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Skill extraction completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Skill extraction failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Skill extraction failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.processing_tasks.normalize_job_titles")
def normalize_job_titles(self, job_ids: List[int] = None):
    """
    Normalize job titles using the title normalization service
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting title normalization", "progress": 0},
        )

        result = asyncio.run(_normalize_job_titles_async(job_ids))

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Title normalization completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Title normalization failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Title normalization failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(
    bind=True, name="app.tasks.processing_tasks.calculate_job_quality_scores"
)
def calculate_job_quality_scores(self, job_ids: List[int] = None):
    """
    Calculate quality scores for job postings
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting quality score calculation", "progress": 0},
        )

        result = asyncio.run(_calculate_job_quality_scores_async(job_ids))

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Quality score calculation completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Quality score calculation failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Quality score calculation failed: {str(e)}",
                "progress": 0,
            },
        )
        raise


@celery_app.task(bind=True, name="app.tasks.processing_tasks.update_job_embeddings")
def update_job_embeddings(self, job_ids: List[int] = None):
    """
    Update embeddings for job postings
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting embedding updates", "progress": 0},
        )

        result = asyncio.run(_update_job_embeddings_async(job_ids))

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Embedding updates completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Embedding updates failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Embedding updates failed: {str(e)}", "progress": 0},
        )
        raise


@celery_app.task(bind=True, name="app.tasks.processing_tasks.validate_job_data")
def validate_job_data(self, job_ids: List[int] = None):
    """
    Validate job data quality and completeness
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting job data validation", "progress": 0},
        )

        result = asyncio.run(_validate_job_data_async(job_ids))

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Job data validation completed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Job data validation failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Job data validation failed: {str(e)}", "progress": 0},
        )
        raise


# Async helper functions
async def _process_raw_jobs_async(batch_size: int) -> Dict[str, Any]:
    """Process raw jobs asynchronously"""
    async for db in get_db():
        try:
            from sqlalchemy import select
            from ..db.models import JobPost

            # Get unprocessed jobs
            result = await db.execute(
                select(JobPost).where(JobPost.processed_at.is_(None)).limit(batch_size)
            )
            unprocessed_jobs = result.scalars().all()

            job_processor = JobProcessor()
            processed_count = 0
            failed_count = 0

            for job in unprocessed_jobs:
                try:
                    # Process job data
                    job_data = {
                        "id": job.id,
                        "title": job.title_raw,
                        "description": job.description_raw,
                        "requirements": job.requirements_raw,
                        "url": job.url,
                        "source": job.source,
                    }

                    await job_processor.process_job(job_data)

                    # Update job with processed data
                    job.processed_at = datetime.utcnow()
                    processed_count += 1

                except Exception as e:
                    logger.error(f"Failed to process job {job.id}: {str(e)}")
                    failed_count += 1
                    continue

            await db.commit()

            return {
                "status": "completed",
                "processed_jobs": processed_count,
                "failed_jobs": failed_count,
                "total_jobs": len(unprocessed_jobs),
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Job processing failed: {str(e)}")
            raise
        finally:
            await db.close()


async def _clean_duplicate_jobs_async() -> Dict[str, Any]:
    """Clean duplicate jobs asynchronously"""
    async for db in get_db():
        try:
            from sqlalchemy import select, func, delete
            from ..db.models import JobPost

            # Find duplicates based on URL and title
            duplicate_query = (
                select(
                    JobPost.url,
                    JobPost.title_raw,
                    func.count(JobPost.id).label("count"),
                    func.min(JobPost.id).label("keep_id"),
                )
                .group_by(JobPost.url, JobPost.title_raw)
                .having(func.count(JobPost.id) > 1)
            )

            duplicates = await db.execute(duplicate_query)
            duplicate_groups = duplicates.fetchall()

            deleted_count = 0

            for group in duplicate_groups:
                # Delete all but the first occurrence
                delete_stmt = delete(JobPost).where(
                    JobPost.url == group.url,
                    JobPost.title_raw == group.title_raw,
                    JobPost.id != group.keep_id,
                )

                result = await db.execute(delete_stmt)
                deleted_count += result.rowcount

            await db.commit()

            return {
                "status": "completed",
                "duplicate_groups_found": len(duplicate_groups),
                "jobs_deleted": deleted_count,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Duplicate cleanup failed: {str(e)}")
            raise
        finally:
            await db.close()


async def _extract_job_skills_async(job_ids: List[int] = None) -> Dict[str, Any]:
    """Extract job skills asynchronously"""
    async for db in get_db():
        try:
            from sqlalchemy import select
            from ..db.models import JobPost, Skill, JobSkill
            from ..normalization.skills import extract_and_normalize_skills

            # Get jobs to process
            query = select(JobPost)
            if job_ids:
                query = query.where(JobPost.id.in_(job_ids))
            else:
                # Process jobs without skills
                query = query.where(~JobPost.skills.any())

            result = await db.execute(query.limit(500))
            jobs = result.scalars().all()

            skills_extracted = 0
            jobs_processed = 0

            for job in jobs:
                try:
                    # Extract skills from job description and requirements
                    text = f"{job.description_raw or ''} {job.requirements_raw or ''}"
                    skills = extract_and_normalize_skills(text)

                    for skill_name, confidence in skills.items():
                        if confidence > 0.7:  # Only high-confidence skills
                            # Get or create skill
                            skill_result = await db.execute(
                                select(Skill).where(Skill.name == skill_name)
                            )
                            skill = skill_result.scalar_one_or_none()

                            if not skill:
                                skill = Skill(name=skill_name)
                                db.add(skill)
                                await db.flush()

                            # Create job-skill relationship
                            job_skill = JobSkill(
                                job_id=job.id, skill_id=skill.id, confidence=confidence
                            )
                            db.add(job_skill)
                            skills_extracted += 1

                    jobs_processed += 1

                except Exception as e:
                    logger.error(f"Failed to extract skills for job {job.id}: {str(e)}")
                    continue

            await db.commit()

            return {
                "status": "completed",
                "jobs_processed": jobs_processed,
                "skills_extracted": skills_extracted,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Skill extraction failed: {str(e)}")
            raise
        finally:
            await db.close()


async def _normalize_job_titles_async(job_ids: List[int] = None) -> Dict[str, Any]:
    """Normalize job titles asynchronously"""
    async for db in get_db():
        try:
            from sqlalchemy import select
            from ..db.models import JobPost, TitleNorm
            from ..normalization.titles import normalize_title

            # Get jobs to process
            query = select(JobPost).where(JobPost.title_norm_id.is_(None))
            if job_ids:
                query = query.where(JobPost.id.in_(job_ids))

            result = await db.execute(query.limit(1000))
            jobs = result.scalars().all()

            normalized_count = 0

            for job in jobs:
                try:
                    if not job.title_raw:
                        continue

                    # Normalize the title
                    family, canonical = normalize_title(job.title_raw)

                    # Get or create title normalization
                    title_norm_result = await db.execute(
                        select(TitleNorm).where(
                            TitleNorm.canonical == canonical, TitleNorm.family == family
                        )
                    )
                    title_norm = title_norm_result.scalar_one_or_none()

                    if not title_norm:
                        title_norm = TitleNorm(canonical=canonical, family=family)
                        db.add(title_norm)
                        await db.flush()

                    # Update job with normalized title
                    job.title_norm_id = title_norm.id
                    normalized_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to normalize title for job {job.id}: {str(e)}"
                    )
                    continue

            await db.commit()

            return {"status": "completed", "jobs_normalized": normalized_count}

        except Exception as e:
            await db.rollback()
            logger.error(f"Title normalization failed: {str(e)}")
            raise
        finally:
            await db.close()


async def _calculate_job_quality_scores_async(
    job_ids: List[int] = None,
) -> Dict[str, Any]:
    """Calculate job quality scores asynchronously"""
    async for db in get_db():
        try:
            from sqlalchemy import select
            from ..db.models import JobPost

            # Get jobs to process
            query = select(JobPost).where(JobPost.quality_score.is_(None))
            if job_ids:
                query = query.where(JobPost.id.in_(job_ids))

            result = await db.execute(query.limit(1000))
            jobs = result.scalars().all()

            scored_count = 0

            for job in jobs:
                try:
                    # Calculate quality score
                    job_data = {
                        "title": job.title_raw,
                        "description": job.description_raw,
                        "requirements": job.requirements_raw,
                        "company": getattr(job.organization, "name", None)
                        if job.organization
                        else None,
                        "location": getattr(job.location, "name", None)
                        if job.location
                        else None,
                        "salary_min": job.salary_min,
                        "salary_max": job.salary_max,
                    }

                    quality_score = (
                        await automated_workflow_service._calculate_job_quality_score(
                            job_data
                        )
                    )
                    job.quality_score = quality_score
                    scored_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to calculate quality score for job {job.id}: {str(e)}"
                    )
                    continue

            await db.commit()

            return {"status": "completed", "jobs_scored": scored_count}

        except Exception as e:
            await db.rollback()
            logger.error(f"Quality score calculation failed: {str(e)}")
            raise
        finally:
            await db.close()


async def _update_job_embeddings_async(job_ids: List[int] = None) -> Dict[str, Any]:
    """Update job embeddings asynchronously"""
    async for db in get_db():
        try:
            import json
            from sqlalchemy import select, or_
            from ..db.models import JobPost
            from ..ml.embeddings import generate_embeddings, parse_embedding

            # Get jobs to process
            query = select(JobPost).where(
                or_(JobPost.embedding.is_(None), JobPost.embedding_vector.is_(None))
            )
            if job_ids:
                query = query.where(JobPost.id.in_(job_ids))

            result = await db.execute(query.limit(500))
            jobs = result.scalars().all()

            updated_count = 0

            for job in jobs:
                try:
                    # Prefer cheap backfill from existing values before recomputing.
                    if job.embedding_vector is None and job.embedding:
                        embedding = parse_embedding(job.embedding)
                        if embedding is not None:
                            job.embedding_vector = embedding
                            updated_count += 1
                            continue

                    if job.embedding is None and job.embedding_vector is not None:
                        embedding = parse_embedding(job.embedding_vector)
                        if embedding is not None:
                            job.embedding = json.dumps(embedding)
                            updated_count += 1
                            continue

                    # Generate embedding when neither representation is available.
                    text = f"{job.title_raw or ''} {job.description_raw or ''}"
                    if text.strip():
                        embedding = generate_embeddings([text])[0]
                        # Persist as JSON for portability and safe parsing.
                        job.embedding = json.dumps(embedding)
                        job.embedding_vector = embedding
                        updated_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to generate embedding for job {job.id}: {str(e)}"
                    )
                    continue

            await db.commit()

            return {"status": "completed", "embeddings_updated": updated_count}

        except Exception as e:
            await db.rollback()
            logger.error(f"Embedding updates failed: {str(e)}")
            raise
        finally:
            await db.close()


async def _validate_job_data_async(job_ids: List[int] = None) -> Dict[str, Any]:
    """Validate job data asynchronously"""
    async for db in get_db():
        try:
            from sqlalchemy import select
            from ..db.models import JobPost

            # Get jobs to validate
            query = select(JobPost)
            if job_ids:
                query = query.where(JobPost.id.in_(job_ids))

            result = await db.execute(query.limit(1000))
            jobs = result.scalars().all()

            validation_results = {
                "total_jobs": len(jobs),
                "valid_jobs": 0,
                "invalid_jobs": 0,
                "validation_issues": [],
            }

            for job in jobs:
                issues = []

                # Check required fields
                if not job.title_raw or len(job.title_raw.strip()) < 3:
                    issues.append("Missing or too short title")

                if not job.description_raw or len(job.description_raw.strip()) < 50:
                    issues.append("Missing or too short description")

                if not job.url or not job.url.startswith(("http://", "https://")):
                    issues.append("Invalid or missing URL")

                # Check data quality
                if (
                    job.salary_min
                    and job.salary_max
                    and job.salary_min > job.salary_max
                ):
                    issues.append("Invalid salary range")

                if issues:
                    validation_results["invalid_jobs"] += 1
                    validation_results["validation_issues"].append(
                        {"job_id": job.id, "issues": issues}
                    )
                else:
                    validation_results["valid_jobs"] += 1

            return {"status": "completed", "validation_results": validation_results}

        except Exception as e:
            logger.error(f"Job data validation failed: {str(e)}")
            raise
        finally:
            await db.close()


# Job Alert Processing Tasks
@celery_app.task(bind=True, name="app.tasks.processing_tasks.process_job_alerts")
def process_job_alerts(self, frequency: str = "daily"):
    """
    Process job alerts and send notifications to users.

    Args:
        frequency: Alert frequency to process ("immediate", "daily", "weekly")
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": f"Processing {frequency} job alerts", "progress": 0},
        )

        result = _process_job_alerts_sync(frequency)

        self.update_state(
            state="SUCCESS",
            meta={
                "status": f"{frequency.title()} job alerts processed successfully",
                "progress": 100,
                "result": result,
            },
        )

        return result

    except Exception as e:
        logger.error(f"Job alert processing failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"status": f"Job alert processing failed: {str(e)}", "progress": 0},
        )
        raise


def _process_job_alerts_sync(frequency: str) -> Dict[str, Any]:
    """Process job alerts synchronously (Celery-compatible)"""
    from sqlalchemy import select, and_
    from ..db.models import JobAlert, User, UserNotification
    from ..services.search import search_jobs

    db = SessionLocal()
    try:
        # Get active alerts for the specified frequency
        stmt = select(JobAlert).where(
            and_(JobAlert.is_active.is_(True), JobAlert.frequency == frequency)
        )
        alerts = db.execute(stmt).scalars().all()

        alerts_processed = 0
        notifications_sent = 0

        # Calculate time window for new jobs
        if frequency == "immediate":
            hours_back = 1
        elif frequency == "daily":
            hours_back = 24
        else:  # weekly
            hours_back = 168

        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        for alert in alerts:
            try:
                # Search for matching jobs
                matching_jobs = search_jobs(
                    db,
                    q=alert.query,
                    location=alert.filters.get("location"),
                    seniority=alert.filters.get("seniority"),
                )

                # Filter for new jobs only
                new_jobs = [
                    job
                    for job in matching_jobs
                    if job.get("first_seen")
                    and datetime.fromisoformat(job["first_seen"].replace("Z", ""))
                    > cutoff_time
                ]

                if new_jobs:
                    # Get user for this alert
                    user = db.execute(
                        select(User).where(User.id == alert.user_id)
                    ).scalar_one_or_none()

                    if user:
                        # Create notification
                        notification = UserNotification(
                            user_id=user.id,
                            type="job_alert",
                            title=f"🎯 {len(new_jobs)} new jobs match '{alert.name}'",
                            message=_format_job_alert_message(new_jobs[:5], alert.name),
                            data={
                                "alert_id": alert.id,
                                "job_count": len(new_jobs),
                                "job_ids": [j.get("id") for j in new_jobs[:10]],
                            },
                            delivered_via=[],
                        )
                        db.add(notification)

                        # Send email if in delivery methods
                        if "email" in (alert.delivery_methods or []) and user.email:
                            email_sent = _send_job_alert_email(
                                user.email, alert.name, new_jobs[:10]
                            )
                            if email_sent:
                                notification.delivered_via.append("email")
                                notifications_sent += 1

                        # Update alert stats
                        alert.last_triggered = datetime.utcnow()
                        alert.last_jobs_count = len(new_jobs)
                        alert.jobs_found_total = (alert.jobs_found_total or 0) + len(
                            new_jobs
                        )

                        db.add(alert)

                alerts_processed += 1

            except Exception as e:
                logger.error(f"Error processing alert {alert.id}: {e}")
                continue

        db.commit()

        return {
            "status": "completed",
            "frequency": frequency,
            "alerts_processed": alerts_processed,
            "notifications_sent": notifications_sent,
            "processed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Job alert processing failed: {str(e)}")
        raise
    finally:
        db.close()


def _format_job_alert_message(jobs: List[Dict], alert_name: str) -> str:
    """Format job alert message for notification"""
    if not jobs:
        return f"No new jobs found for '{alert_name}'"

    message = f"New opportunities matching your '{alert_name}' alert:\n\n"

    for i, job in enumerate(jobs[:5], 1):
        title = job.get("title", "Unknown Title")
        company = job.get("organization", "Unknown Company")
        location = job.get("location", "")

        message += f"{i}. {title}\n"
        message += f"   🏢 {company}"
        if location:
            message += f" | 📍 {location}"
        message += "\n"

    if len(jobs) > 5:
        message += f"\n...and {len(jobs) - 5} more opportunities!"

    return message


def _send_job_alert_email(to_email: str, alert_name: str, jobs: List[Dict]) -> bool:
    """Send job alert email digest"""
    if not jobs:
        return False

    subject = f"🎯 {len(jobs)} new jobs match your '{alert_name}' alert"

    body = "Hi there,\n\n"
    body += f"Great news! We found {len(jobs)} new job(s) matching your '{alert_name}' job alert.\n\n"
    body += "Here are the top matches:\n\n"

    for i, job in enumerate(jobs[:10], 1):
        title = job.get("title", "Unknown Title")
        company = job.get("organization", "Unknown Company")
        location = job.get("location", "")
        url = job.get("url", "")

        body += f"{i}. {title}\n"
        body += f"   Company: {company}\n"
        if location:
            body += f"   Location: {location}\n"
        if url:
            body += f"   Apply: {url}\n"
        body += "\n"

    body += "\n---\n"
    body += "You're receiving this email because you set up a job alert on NextStep.\n"
    body += "To manage your alerts, visit your account settings.\n"

    return send_email(to_email, subject, body)
