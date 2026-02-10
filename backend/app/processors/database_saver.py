"""
Database saver for processed job data
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..db.models import JobPost, Organization, Location, TitleNorm, Skill, JobSkill
from ..db.database import SessionLocal

logger = logging.getLogger(__name__)


class JobDatabaseSaver:
    """
    Saves processed job data to the database
    """

    def __init__(self):
        pass

    def save_job_data(self, cleaned_data: Dict) -> Optional[int]:
        """
        Save cleaned job data to database

        Args:
            cleaned_data: Cleaned and normalized job data

        Returns:
            Job post ID if successful, None otherwise
        """
        db = SessionLocal()
        try:
            if cleaned_data.get("skip_reason"):
                logger.info(
                    f"Skipping job due to {cleaned_data['skip_reason']}: {cleaned_data.get('title_raw')}"
                )
                return None
            # Get or create organization
            org_id = self._get_or_create_organization(
                db, cleaned_data.get("company_name", "")
            )

            # Get or create location
            location_id = self._get_or_create_location(db, cleaned_data)

            # Get or create title normalization
            title_norm_id = self._get_or_create_title_norm(db, cleaned_data)

            # Create job post
            job_post = JobPost(
                source=cleaned_data.get("source", ""),
                url=cleaned_data.get("url", ""),
                source_url=cleaned_data.get("source_url")
                or cleaned_data.get("url", ""),
                application_url=cleaned_data.get("application_url")
                or cleaned_data.get("url", ""),
                first_seen=cleaned_data.get("extracted_at", datetime.utcnow()),
                last_seen=cleaned_data.get("extracted_at", datetime.utcnow()),
                org_id=org_id,
                title_raw=cleaned_data.get("title_raw", ""),
                title_norm_id=title_norm_id,
                location_id=location_id,
                tenure=cleaned_data.get("employment_type"),
                salary_min=cleaned_data.get("salary_min"),
                salary_max=cleaned_data.get("salary_max"),
                currency=cleaned_data.get("currency"),
                seniority=cleaned_data.get("seniority"),
                description_raw=cleaned_data.get("description_raw"),
                requirements_raw=cleaned_data.get("requirements_raw"),
                education=cleaned_data.get("education"),
                attachment_flag=False,  # Default
            )

            # Check if job post already exists (by URL)
            existing_job = (
                db.query(JobPost).filter(JobPost.url == cleaned_data.get("url")).first()
            )
            if existing_job:
                # Update last_seen timestamp
                existing_job.last_seen = cleaned_data.get(
                    "extracted_at", datetime.utcnow()
                )

                # Update structured fields if we have better data
                if org_id and not existing_job.org_id:
                    existing_job.org_id = org_id
                if location_id and not existing_job.location_id:
                    existing_job.location_id = location_id
                if title_norm_id and not existing_job.title_norm_id:
                    existing_job.title_norm_id = title_norm_id
                if (
                    cleaned_data.get("description_raw")
                    and not existing_job.description_raw
                ):
                    existing_job.description_raw = cleaned_data.get("description_raw")
                if (
                    cleaned_data.get("requirements_raw")
                    and not existing_job.requirements_raw
                ):
                    existing_job.requirements_raw = cleaned_data.get("requirements_raw")
                if cleaned_data.get("salary_min") and not existing_job.salary_min:
                    existing_job.salary_min = cleaned_data.get("salary_min")
                if cleaned_data.get("salary_max") and not existing_job.salary_max:
                    existing_job.salary_max = cleaned_data.get("salary_max")
                if cleaned_data.get("currency") and not existing_job.currency:
                    existing_job.currency = cleaned_data.get("currency")
                if cleaned_data.get("employment_type") and not existing_job.tenure:
                    existing_job.tenure = cleaned_data.get("employment_type")
                if cleaned_data.get("seniority") and not existing_job.seniority:
                    existing_job.seniority = cleaned_data.get("seniority")
                if cleaned_data.get("education") and not existing_job.education:
                    existing_job.education = cleaned_data.get("education")

                db.commit()
                logger.info(f"Updated existing job post: {existing_job.id}")

                # Update skills
                self._update_job_skills(
                    db, existing_job.id, cleaned_data.get("skills", [])
                )

                return existing_job.id

            # Add new job post
            db.add(job_post)
            db.flush()  # Get the ID

            # Add skills
            self._add_job_skills(db, job_post.id, cleaned_data.get("skills", []))

            db.commit()
            logger.info(f"Saved new job post: {job_post.id}")
            return job_post.id

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error saving job data: {e}")
            return None
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving job data: {e}")
            return None
        finally:
            db.close()

    def _get_or_create_organization(
        self, db: Session, company_name: str
    ) -> Optional[int]:
        """Get or create organization record"""
        if not company_name:
            return None

        # Check if organization exists
        org = db.query(Organization).filter(Organization.name == company_name).first()
        if org:
            return org.id

        # Create new organization
        try:
            new_org = Organization(
                name=company_name,
                sector=None,  # Will be populated later
                ats=None,  # Will be populated later
                verified=False,
            )
            db.add(new_org)
            db.flush()
            return new_org.id
        except IntegrityError:
            db.rollback()
            # Try to get existing one (race condition)
            org = (
                db.query(Organization).filter(Organization.name == company_name).first()
            )
            return org.id if org else None

    def _get_or_create_location(self, db: Session, cleaned_data: Dict) -> Optional[int]:
        """Get or create location record"""
        country = cleaned_data.get("country")
        region = cleaned_data.get("region")
        city = cleaned_data.get("city")
        raw_location = cleaned_data.get("location_raw", "")

        if not any([country, region, city, raw_location]):
            return None

        # Check if location exists
        location = (
            db.query(Location)
            .filter(
                Location.country == country,
                Location.region == region,
                Location.city == city,
                Location.raw == raw_location,
            )
            .first()
        )

        if location:
            return location.id

        # Create new location
        try:
            new_location = Location(
                country=country, region=region, city=city, raw=raw_location
            )
            db.add(new_location)
            db.flush()
            return new_location.id
        except IntegrityError:
            db.rollback()
            # Try to get existing one (race condition)
            location = (
                db.query(Location)
                .filter(
                    Location.country == country,
                    Location.region == region,
                    Location.city == city,
                    Location.raw == raw_location,
                )
                .first()
            )
            return location.id if location else None

    def _get_or_create_title_norm(
        self, db: Session, cleaned_data: Dict
    ) -> Optional[int]:
        """Get or create title normalization record"""
        title_family = cleaned_data.get("title_family")
        title_canonical = cleaned_data.get("title_canonical")

        if not title_family or not title_canonical:
            return None

        # Check if title norm exists
        title_norm = (
            db.query(TitleNorm)
            .filter(
                TitleNorm.family == title_family,
                TitleNorm.canonical_title == title_canonical,
            )
            .first()
        )

        if title_norm:
            return title_norm.id

        # Create new title norm
        try:
            new_title_norm = TitleNorm(
                family=title_family,
                canonical_title=title_canonical,
                aliases={},  # Will be populated later
            )
            db.add(new_title_norm)
            db.flush()
            return new_title_norm.id
        except IntegrityError:
            db.rollback()
            # Try to get existing one (race condition)
            title_norm = (
                db.query(TitleNorm)
                .filter(
                    TitleNorm.family == title_family,
                    TitleNorm.canonical_title == title_canonical,
                )
                .first()
            )
            return title_norm.id if title_norm else None

    def _get_or_create_skill(self, db: Session, skill_name: str) -> Optional[int]:
        """Get or create skill record"""
        if not skill_name:
            return None

        # Check if skill exists
        skill = db.query(Skill).filter(Skill.name == skill_name).first()
        if skill:
            return skill.id

        # Create new skill
        try:
            new_skill = Skill(
                name=skill_name,
                taxonomy_ref=None,  # Will be populated later
                aliases={},  # Will be populated later
            )
            db.add(new_skill)
            db.flush()
            return new_skill.id
        except IntegrityError:
            db.rollback()
            # Try to get existing one (race condition)
            skill = db.query(Skill).filter(Skill.name == skill_name).first()
            return skill.id if skill else None

    def _add_job_skills(self, db: Session, job_post_id: int, skills: List[str]):
        """Add skills for a job post"""
        for skill_name in skills:
            skill_id = self._get_or_create_skill(db, skill_name)
            if skill_id:
                try:
                    job_skill = JobSkill(
                        job_post_id=job_post_id,
                        skill_id=skill_id,
                        confidence=0.8,  # Default confidence for extracted skills
                    )
                    db.add(job_skill)
                except IntegrityError:
                    # Skill already exists for this job
                    continue

    def _update_job_skills(self, db: Session, job_post_id: int, skills: List[str]):
        """Update skills for an existing job post"""
        # Remove existing skills
        db.query(JobSkill).filter(JobSkill.job_post_id == job_post_id).delete()

        # Add new skills
        self._add_job_skills(db, job_post_id, skills)

    def save_batch_job_data(self, cleaned_data_list: List[Dict]) -> List[Optional[int]]:
        """
        Save multiple job records in batch

        Args:
            cleaned_data_list: List of cleaned job data dictionaries

        Returns:
            List of job post IDs (None for failed saves)
        """
        results = []

        for cleaned_data in cleaned_data_list:
            try:
                job_id = self.save_job_data(cleaned_data)
                results.append(job_id)
            except Exception as e:
                logger.error(f"Error saving job data in batch: {e}")
                results.append(None)

        return results

    def get_job_stats(self) -> Dict:
        """Get statistics about saved jobs"""
        db = SessionLocal()
        try:
            total_jobs = db.query(JobPost).count()
            total_orgs = db.query(Organization).count()
            total_locations = db.query(Location).count()
            total_skills = db.query(Skill).count()

            # Jobs by source
            jobs_by_source = {}
            sources = db.query(JobPost.source).distinct().all()
            for (source,) in sources:
                count = db.query(JobPost).filter(JobPost.source == source).count()
                jobs_by_source[source] = count

            # Recent jobs (last 7 days)
            from datetime import timedelta

            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_jobs = (
                db.query(JobPost).filter(JobPost.first_seen >= week_ago).count()
            )

            return {
                "total_jobs": total_jobs,
                "total_organizations": total_orgs,
                "total_locations": total_locations,
                "total_skills": total_skills,
                "jobs_by_source": jobs_by_source,
                "recent_jobs_7_days": recent_jobs,
                "last_updated": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"Error getting job stats: {e}")
            return {}
        finally:
            db.close()
