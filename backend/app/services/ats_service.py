import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import base64

from ..core.config import settings
from ..db.models import JobPost, JobApplication, User
from ..db.integration_models import (
    ATSIntegration,
    ATSJobSync,
    ATSApplicationSync,
    IntegrationActivityLog,
)
import logging

logger = logging.getLogger(__name__)


class ATSService:
    def __init__(self):
        self.supported_ats = {
            "greenhouse": {
                "base_url": "https://harvest-api.greenhouse.io/v1/",
                "auth_type": "basic",
                "webhook_events": [
                    "job.created",
                    "job.updated",
                    "application.created",
                    "application.updated",
                ],
            },
            "lever": {
                "base_url": "https://api.lever.co/v1/",
                "auth_type": "basic",
                "webhook_events": [
                    "posting.created",
                    "posting.updated",
                    "application.created",
                    "application.updated",
                ],
            },
            "workday": {
                "base_url": "https://wd2-impl-services1.workday.com/",
                "auth_type": "oauth",
                "webhook_events": [
                    "job.created",
                    "job.updated",
                    "candidate.created",
                    "candidate.updated",
                ],
            },
            "bamboohr": {
                "base_url": "https://api.bamboohr.com/api/gateway.php/",
                "auth_type": "basic",
                "webhook_events": ["job.created", "job.updated", "application.created"],
            },
        }

    async def create_ats_integration(
        self,
        db: AsyncSession,
        organization_id: int,
        ats_provider: str,
        credentials: Dict[str, Any],
        settings_data: Dict[str, Any] = None,
    ) -> ATSIntegration:
        """Create a new ATS integration"""
        try:
            if ats_provider not in self.supported_ats:
                raise ValueError(f"Unsupported ATS provider: {ats_provider}")

            # Test connection first
            connection_test = await self._test_ats_connection(ats_provider, credentials)
            if not connection_test["success"]:
                raise Exception(
                    f"ATS connection test failed: {connection_test['error']}"
                )

            # Check if integration already exists
            result = await db.execute(
                select(ATSIntegration).where(
                    ATSIntegration.organization_id == organization_id,
                    ATSIntegration.ats_provider == ats_provider,
                )
            )
            existing_integration = result.scalar_one_or_none()

            if existing_integration:
                # Update existing integration
                ats_integration = existing_integration
                ats_integration.api_key = credentials.get("api_key")
                ats_integration.api_secret = credentials.get("api_secret")
                ats_integration.access_token = credentials.get("access_token")
                ats_integration.refresh_token = credentials.get("refresh_token")
                ats_integration.ats_instance_url = credentials.get("instance_url", "")
                ats_integration.ats_company_id = credentials.get("company_id")
                ats_integration.is_active = True
                ats_integration.sync_status = "active"
                ats_integration.updated_at = datetime.utcnow()
            else:
                # Create new integration
                ats_integration = ATSIntegration(
                    organization_id=organization_id,
                    ats_provider=ats_provider,
                    ats_instance_url=credentials.get("instance_url", ""),
                    ats_company_id=credentials.get("company_id"),
                    api_key=credentials.get("api_key"),
                    api_secret=credentials.get("api_secret"),
                    access_token=credentials.get("access_token"),
                    refresh_token=credentials.get("refresh_token"),
                    is_active=True,
                    sync_status="active",
                )
                db.add(ats_integration)

            # Apply settings if provided
            if settings_data:
                ats_integration.sync_jobs = settings_data.get("sync_jobs", True)
                ats_integration.sync_applications = settings_data.get(
                    "sync_applications", True
                )
                ats_integration.sync_candidates = settings_data.get(
                    "sync_candidates", False
                )
                ats_integration.webhook_events = settings_data.get(
                    "webhook_events", self.supported_ats[ats_provider]["webhook_events"]
                )

            await db.commit()
            await db.refresh(ats_integration)

            # Set up webhook if supported
            if credentials.get("setup_webhook", False):
                await self._setup_webhook(db, ats_integration)

            # Log activity
            await self._log_activity(
                db,
                None,
                organization_id,
                ats_integration.id,
                "integration_created",
                f"{ats_provider.title()} ATS integration created",
                {"provider": ats_provider, "company_id": credentials.get("company_id")},
            )

            return ats_integration

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating ATS integration: {str(e)}")
            raise

    async def _test_ats_connection(
        self, ats_provider: str, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test connection to ATS provider"""
        try:
            if ats_provider == "greenhouse":
                return await self._test_greenhouse_connection(credentials)
            elif ats_provider == "lever":
                return await self._test_lever_connection(credentials)
            elif ats_provider == "workday":
                return await self._test_workday_connection(credentials)
            elif ats_provider == "bamboohr":
                return await self._test_bamboohr_connection(credentials)
            else:
                return {"success": False, "error": "Unsupported ATS provider"}

        except Exception as e:
            logger.error(f"Error testing ATS connection: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _test_greenhouse_connection(
        self, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test Greenhouse API connection"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return {"success": False, "error": "API key is required"}

            # Encode API key for basic auth
            auth_string = base64.b64encode(f"{api_key}:".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://harvest-api.greenhouse.io/v1/users", headers=headers
                )

                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {
                        "success": False,
                        "error": f"API test failed: {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_lever_connection(
        self, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test Lever API connection"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return {"success": False, "error": "API key is required"}

            # Encode API key for basic auth
            auth_string = base64.b64encode(f"{api_key}:".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.lever.co/v1/users", headers=headers
                )

                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {
                        "success": False,
                        "error": f"API test failed: {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_workday_connection(
        self, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test Workday API connection"""
        try:
            # Workday uses OAuth, so we need access token
            access_token = credentials.get("access_token")
            instance_url = credentials.get("instance_url")

            if not access_token or not instance_url:
                return {
                    "success": False,
                    "error": "Access token and instance URL are required",
                }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{instance_url}/ccx/api/v1/workers", headers=headers
                )

                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {
                        "success": False,
                        "error": f"API test failed: {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_bamboohr_connection(
        self, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test BambooHR API connection"""
        try:
            api_key = credentials.get("api_key")
            company_id = credentials.get("company_id")

            if not api_key or not company_id:
                return {
                    "success": False,
                    "error": "API key and company ID are required",
                }

            # Encode API key for basic auth
            auth_string = base64.b64encode(f"{api_key}:x".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.bamboohr.com/api/gateway.php/{company_id}/v1/employees/directory",
                    headers=headers,
                )

                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {
                        "success": False,
                        "error": f"API test failed: {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def sync_jobs_from_ats(
        self, db: AsyncSession, ats_integration: ATSIntegration
    ) -> Dict[str, Any]:
        """Sync jobs from ATS to our platform"""
        try:
            if not ats_integration.sync_jobs:
                return {"success": False, "error": "Job sync is disabled"}

            # Get jobs from ATS based on provider
            if ats_integration.ats_provider == "greenhouse":
                jobs_data = await self._get_greenhouse_jobs(ats_integration)
            elif ats_integration.ats_provider == "lever":
                jobs_data = await self._get_lever_jobs(ats_integration)
            elif ats_integration.ats_provider == "workday":
                jobs_data = await self._get_workday_jobs(ats_integration)
            elif ats_integration.ats_provider == "bamboohr":
                jobs_data = await self._get_bamboohr_jobs(ats_integration)
            else:
                return {"success": False, "error": "Unsupported ATS provider"}

            if not jobs_data["success"]:
                return jobs_data

            # Process and save jobs
            jobs_processed = 0
            jobs_created = 0
            jobs_updated = 0

            for job_data in jobs_data["jobs"]:
                try:
                    result = await self._process_ats_job(db, ats_integration, job_data)
                    jobs_processed += 1
                    if result["created"]:
                        jobs_created += 1
                    else:
                        jobs_updated += 1

                except Exception as e:
                    logger.error(
                        f"Error processing job {job_data.get('id', 'unknown')}: {str(e)}"
                    )

            # Update sync status
            ats_integration.last_synced = datetime.utcnow()
            ats_integration.jobs_synced_count = jobs_processed
            ats_integration.sync_status = "active"
            await db.commit()

            # Log activity
            await self._log_activity(
                db,
                None,
                ats_integration.organization_id,
                ats_integration.id,
                "jobs_synced",
                f"Synced {jobs_processed} jobs from {ats_integration.ats_provider}",
                {
                    "jobs_processed": jobs_processed,
                    "jobs_created": jobs_created,
                    "jobs_updated": jobs_updated,
                },
            )

            return {
                "success": True,
                "jobs_processed": jobs_processed,
                "jobs_created": jobs_created,
                "jobs_updated": jobs_updated,
            }

        except Exception as e:
            logger.error(f"Error syncing jobs from ATS: {str(e)}")
            ats_integration.sync_status = "error"
            ats_integration.sync_errors = {"error": str(e)}
            await db.commit()
            return {"success": False, "error": str(e)}

    async def _get_greenhouse_jobs(
        self, ats_integration: ATSIntegration
    ) -> Dict[str, Any]:
        """Get jobs from Greenhouse API"""
        try:
            auth_string = base64.b64encode(
                f"{ats_integration.api_key}:".encode()
            ).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://harvest-api.greenhouse.io/v1/jobs", headers=headers
                )

                if response.status_code == 200:
                    jobs = response.json()
                    return {"success": True, "jobs": jobs}
                else:
                    return {
                        "success": False,
                        "error": f"Failed to fetch jobs: {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_lever_jobs(self, ats_integration: ATSIntegration) -> Dict[str, Any]:
        """Get jobs from Lever API"""
        try:
            auth_string = base64.b64encode(
                f"{ats_integration.api_key}:".encode()
            ).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.lever.co/v1/postings", headers=headers
                )

                if response.status_code == 200:
                    jobs = response.json()
                    return {"success": True, "jobs": jobs.get("data", [])}
                else:
                    return {
                        "success": False,
                        "error": f"Failed to fetch jobs: {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_workday_jobs(
        self, ats_integration: ATSIntegration
    ) -> Dict[str, Any]:
        """Get jobs from Workday API"""
        try:
            headers = {
                "Authorization": f"Bearer {ats_integration.access_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{ats_integration.ats_instance_url}/ccx/api/v1/jobs",
                    headers=headers,
                )

                if response.status_code == 200:
                    jobs = response.json()
                    return {"success": True, "jobs": jobs.get("data", [])}
                else:
                    return {
                        "success": False,
                        "error": f"Failed to fetch jobs: {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_bamboohr_jobs(
        self, ats_integration: ATSIntegration
    ) -> Dict[str, Any]:
        """Get jobs from BambooHR API"""
        try:
            auth_string = base64.b64encode(
                f"{ats_integration.api_key}:x".encode()
            ).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.bamboohr.com/api/gateway.php/{ats_integration.ats_company_id}/v1/applicant_tracking/jobs",
                    headers=headers,
                )

                if response.status_code == 200:
                    jobs = response.json()
                    return {"success": True, "jobs": jobs.get("jobs", [])}
                else:
                    return {
                        "success": False,
                        "error": f"Failed to fetch jobs: {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _process_ats_job(
        self,
        db: AsyncSession,
        ats_integration: ATSIntegration,
        job_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process and save a job from ATS"""
        try:
            # Extract job information based on ATS provider
            if ats_integration.ats_provider == "greenhouse":
                job_info = self._extract_greenhouse_job_info(job_data)
            elif ats_integration.ats_provider == "lever":
                job_info = self._extract_lever_job_info(job_data)
            elif ats_integration.ats_provider == "workday":
                job_info = self._extract_workday_job_info(job_data)
            elif ats_integration.ats_provider == "bamboohr":
                job_info = self._extract_bamboohr_job_info(job_data)
            else:
                return {"success": False, "error": "Unsupported ATS provider"}

            # Check if job already exists
            result = await db.execute(
                select(ATSJobSync).where(
                    ATSJobSync.ats_integration_id == ats_integration.id,
                    ATSJobSync.ats_job_id == job_info["ats_job_id"],
                )
            )
            existing_sync = result.scalar_one_or_none()

            created = False
            if existing_sync:
                # Update existing job
                job_post = await db.get(JobPost, existing_sync.job_post_id)
                if job_post:
                    self._update_job_post_from_ats(job_post, job_info)
                    existing_sync.last_synced = datetime.utcnow()
                    existing_sync.ats_status = job_info.get("status", "open")
                    existing_sync.ats_metadata = job_info.get("metadata", {})
            else:
                # Create new job post
                job_post = self._create_job_post_from_ats(ats_integration, job_info)
                db.add(job_post)
                await db.flush()  # Get the job_post.id

                # Create ATS sync record
                ats_job_sync = ATSJobSync(
                    ats_integration_id=ats_integration.id,
                    job_post_id=job_post.id,
                    ats_job_id=job_info["ats_job_id"],
                    ats_job_url=job_info.get("job_url"),
                    ats_status=job_info.get("status", "open"),
                    ats_metadata=job_info.get("metadata", {}),
                    hiring_manager=job_info.get("hiring_manager"),
                    department=job_info.get("department"),
                    job_code=job_info.get("job_code"),
                )
                db.add(ats_job_sync)
                created = True

            await db.commit()
            return {"success": True, "created": created}

        except Exception as e:
            await db.rollback()
            logger.error(f"Error processing ATS job: {str(e)}")
            return {"success": False, "error": str(e)}

    def _extract_greenhouse_job_info(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract job information from Greenhouse job data"""
        return {
            "ats_job_id": str(job_data.get("id", "")),
            "title": job_data.get("name", ""),
            "description": job_data.get("notes", ""),
            "requirements": "",  # Greenhouse doesn't have separate requirements field
            "location": self._extract_greenhouse_location(job_data.get("offices", [])),
            "department": job_data.get("departments", [{}])[0].get("name", "")
            if job_data.get("departments")
            else "",
            "status": "open" if job_data.get("status") == "open" else "closed",
            "job_url": job_data.get("absolute_url", ""),
            "metadata": {
                "requisition_id": job_data.get("requisition_id"),
                "created_at": job_data.get("created_at"),
                "updated_at": job_data.get("updated_at"),
                "confidential": job_data.get("confidential", False),
            },
        }

    def _extract_lever_job_info(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract job information from Lever job data"""
        return {
            "ats_job_id": str(job_data.get("id", "")),
            "title": job_data.get("text", ""),
            "description": job_data.get("content", {}).get("description", ""),
            "requirements": job_data.get("content", {}).get("requirements", ""),
            "location": job_data.get("categories", {}).get("location", ""),
            "department": job_data.get("categories", {}).get("department", ""),
            "status": "open" if job_data.get("state") == "published" else "closed",
            "job_url": job_data.get("hostedUrl", ""),
            "metadata": {
                "created_at": job_data.get("createdAt"),
                "updated_at": job_data.get("updatedAt"),
                "commitment": job_data.get("categories", {}).get("commitment"),
                "team": job_data.get("categories", {}).get("team"),
            },
        }

    def _extract_workday_job_info(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract job information from Workday job data"""
        return {
            "ats_job_id": str(job_data.get("id", "")),
            "title": job_data.get("title", ""),
            "description": job_data.get("jobDescription", ""),
            "requirements": job_data.get("qualifications", ""),
            "location": job_data.get("primaryLocation", {}).get("address", ""),
            "department": job_data.get("supervisoryOrganization", ""),
            "status": "open"
            if job_data.get("jobPostingStatus") == "Active"
            else "closed",
            "job_url": job_data.get("externalUrl", ""),
            "metadata": {
                "job_family": job_data.get("jobFamily"),
                "job_profile": job_data.get("jobProfile"),
                "time_type": job_data.get("timeType"),
                "worker_type": job_data.get("workerType"),
            },
        }

    def _extract_bamboohr_job_info(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract job information from BambooHR job data"""
        return {
            "ats_job_id": str(job_data.get("id", "")),
            "title": job_data.get("jobTitle", ""),
            "description": job_data.get("description", ""),
            "requirements": job_data.get("requirements", ""),
            "location": job_data.get("location", ""),
            "department": job_data.get("department", ""),
            "status": "open" if job_data.get("status") == "Open" else "closed",
            "job_url": job_data.get("applicationUrl", ""),
            "metadata": {
                "employment_type": job_data.get("employmentType"),
                "experience_level": job_data.get("experienceLevel"),
                "salary_range": job_data.get("salaryRange"),
            },
        }

    def _extract_greenhouse_location(self, offices: List[Dict]) -> str:
        """Extract location from Greenhouse offices data"""
        if not offices:
            return ""

        locations = []
        for office in offices:
            location_parts = []
            if office.get("name"):
                location_parts.append(office["name"])
            if office.get("location", {}).get("name"):
                location_parts.append(office["location"]["name"])

            if location_parts:
                locations.append(", ".join(location_parts))

        return "; ".join(locations)

    def _create_job_post_from_ats(
        self, ats_integration: ATSIntegration, job_info: Dict[str, Any]
    ) -> JobPost:
        """Create a new JobPost from ATS job information"""
        return JobPost(
            source=f"ats_{ats_integration.ats_provider}",
            url=job_info.get("job_url", ""),
            org_id=ats_integration.organization_id,
            title_raw=job_info.get("title", ""),
            description_raw=job_info.get("description", ""),
            requirements_raw=job_info.get("requirements", ""),
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )

    def _update_job_post_from_ats(self, job_post: JobPost, job_info: Dict[str, Any]):
        """Update existing JobPost with ATS job information"""
        job_post.title_raw = job_info.get("title", job_post.title_raw)
        job_post.description_raw = job_info.get("description", job_post.description_raw)
        job_post.requirements_raw = job_info.get(
            "requirements", job_post.requirements_raw
        )
        job_post.last_seen = datetime.utcnow()

    async def submit_application_to_ats(
        self,
        db: AsyncSession,
        job_application: JobApplication,
        ats_integration: ATSIntegration,
    ) -> Dict[str, Any]:
        """Submit job application to ATS"""
        try:
            if not ats_integration.sync_applications:
                return {"success": False, "error": "Application sync is disabled"}

            # Get user and job information
            user = await db.get(User, job_application.user_id)
            job_post = await db.get(JobPost, job_application.job_post_id)

            if not user or not job_post:
                return {"success": False, "error": "User or job not found"}

            # Get ATS job sync record
            result = await db.execute(
                select(ATSJobSync).where(
                    ATSJobSync.ats_integration_id == ats_integration.id,
                    ATSJobSync.job_post_id == job_post.id,
                )
            )
            ats_job_sync = result.scalar_one_or_none()

            if not ats_job_sync:
                return {"success": False, "error": "Job not synced with ATS"}

            # Submit application based on ATS provider
            if ats_integration.ats_provider == "greenhouse":
                result = await self._submit_greenhouse_application(
                    ats_integration, ats_job_sync, user, job_application
                )
            elif ats_integration.ats_provider == "lever":
                result = await self._submit_lever_application(
                    ats_integration, ats_job_sync, user, job_application
                )
            else:
                return {
                    "success": False,
                    "error": "Application submission not supported for this ATS",
                }

            if result["success"]:
                # Create ATS application sync record
                ats_app_sync = ATSApplicationSync(
                    ats_integration_id=ats_integration.id,
                    job_application_id=job_application.id,
                    ats_application_id=result["ats_application_id"],
                    ats_candidate_id=result.get("ats_candidate_id"),
                    ats_status=result.get("status", "submitted"),
                    submitted_to_ats=True,
                    ats_submission_date=datetime.utcnow(),
                    ats_metadata=result.get("metadata", {}),
                )
                db.add(ats_app_sync)

                # Update job application status
                job_application.status = "submitted"
                job_application.application_source = (
                    f"ats_{ats_integration.ats_provider}"
                )

                await db.commit()

                # Log activity
                await self._log_activity(
                    db,
                    user.id,
                    ats_integration.organization_id,
                    ats_integration.id,
                    "application_submitted",
                    "Application submitted to ATS",
                    {"ats_application_id": result["ats_application_id"]},
                )

            return result

        except Exception as e:
            await db.rollback()
            logger.error(f"Error submitting application to ATS: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _submit_greenhouse_application(
        self,
        ats_integration: ATSIntegration,
        ats_job_sync: ATSJobSync,
        user: User,
        job_application: JobApplication,
    ) -> Dict[str, Any]:
        """Submit application to Greenhouse"""
        try:
            auth_string = base64.b64encode(
                f"{ats_integration.api_key}:".encode()
            ).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json",
            }

            # Prepare application data
            application_data = {
                "first_name": user.full_name.split()[0] if user.full_name else "",
                "last_name": " ".join(user.full_name.split()[1:])
                if user.full_name and len(user.full_name.split()) > 1
                else "",
                "email": user.email,
                "phone": user.phone or "",
                "resume_text": job_application.cover_letter or "",
                "job_id": int(ats_job_sync.ats_job_id),
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://harvest-api.greenhouse.io/v1/candidates",
                    headers=headers,
                    json=application_data,
                )

                if response.status_code == 201:
                    candidate_data = response.json()
                    return {
                        "success": True,
                        "ats_application_id": str(candidate_data.get("id", "")),
                        "ats_candidate_id": str(candidate_data.get("id", "")),
                        "status": "submitted",
                        "metadata": candidate_data,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Greenhouse submission failed: {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _submit_lever_application(
        self,
        ats_integration: ATSIntegration,
        ats_job_sync: ATSJobSync,
        user: User,
        job_application: JobApplication,
    ) -> Dict[str, Any]:
        """Submit application to Lever"""
        try:
            auth_string = base64.b64encode(
                f"{ats_integration.api_key}:".encode()
            ).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json",
            }

            # Prepare application data
            application_data = {
                "name": user.full_name or "",
                "email": user.email,
                "phone": user.phone or "",
                "resume": job_application.cover_letter or "",
                "postingId": ats_job_sync.ats_job_id,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.lever.co/v1/candidates",
                    headers=headers,
                    json=application_data,
                )

                if response.status_code == 200:
                    candidate_data = response.json()
                    return {
                        "success": True,
                        "ats_application_id": str(candidate_data.get("id", "")),
                        "ats_candidate_id": str(candidate_data.get("id", "")),
                        "status": "submitted",
                        "metadata": candidate_data,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Lever submission failed: {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _setup_webhook(self, db: AsyncSession, ats_integration: ATSIntegration):
        """Set up webhook for ATS integration"""
        try:
            webhook_url = f"{settings.API_BASE_URL}/api/v1/integrations/ats/webhook/{ats_integration.id}"

            if ats_integration.ats_provider == "greenhouse":
                await self._setup_greenhouse_webhook(ats_integration, webhook_url)
            elif ats_integration.ats_provider == "lever":
                await self._setup_lever_webhook(ats_integration, webhook_url)

            # Update integration with webhook URL
            ats_integration.webhook_url = webhook_url
            await db.commit()

        except Exception as e:
            logger.error(f"Error setting up ATS webhook: {str(e)}")

    async def _setup_greenhouse_webhook(
        self, ats_integration: ATSIntegration, webhook_url: str
    ):
        """Set up Greenhouse webhook"""
        # Greenhouse webhooks are typically set up through their UI
        # This is a placeholder for webhook setup logic
        pass

    async def _setup_lever_webhook(
        self, ats_integration: ATSIntegration, webhook_url: str
    ):
        """Set up Lever webhook"""
        # Lever webhooks are typically set up through their UI
        # This is a placeholder for webhook setup logic
        pass

    async def sync_all_ats_integrations(self, db: AsyncSession):
        """Background task to sync all active ATS integrations"""
        try:
            # Get all active ATS integrations
            result = await db.execute(
                select(ATSIntegration).where(
                    ATSIntegration.is_active.is_(True),
                    ATSIntegration.sync_status == "active",
                )
            )
            integrations = result.scalars().all()

            for integration in integrations:
                try:
                    # Sync jobs from ATS
                    if integration.sync_jobs:
                        await self.sync_jobs_from_ats(db, integration)

                    # Add delay between syncs to avoid rate limiting
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(
                        f"Error syncing ATS integration {integration.id}: {str(e)}"
                    )
                    integration.sync_status = "error"
                    integration.sync_errors = {"error": str(e)}
                    await db.commit()

        except Exception as e:
            logger.error(f"Error in ATS sync background task: {str(e)}")

    async def _log_activity(
        self,
        db: AsyncSession,
        user_id: Optional[int],
        organization_id: Optional[int],
        integration_id: int,
        activity_type: str,
        description: str,
        data: Dict = None,
    ):
        """Log integration activity"""
        try:
            log_entry = IntegrationActivityLog(
                user_id=user_id,
                organization_id=organization_id,
                integration_type="ats",
                integration_id=integration_id,
                activity_type=activity_type,
                activity_description=description,
                activity_data=data or {},
                status="success",
            )
            db.add(log_entry)
            await db.commit()
        except Exception as e:
            logger.error(f"Error logging ATS activity: {str(e)}")


# Create service instance
ats_service = ATSService()
