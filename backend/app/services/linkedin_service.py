import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from linkedin_api import Linkedin
import httpx
from requests_oauthlib import OAuth2Session

from ..core.config import settings
from ..db.database import get_db
from ..db.models import User, UserProfile
from ..db.integration_models import LinkedInProfile, IntegrationActivityLog
import logging

logger = logging.getLogger(__name__)


class LinkedInService:
    def __init__(self):
        self.client_id = settings.LINKEDIN_CLIENT_ID
        self.client_secret = settings.LINKEDIN_CLIENT_SECRET
        self.redirect_uri = (
            f"{settings.API_BASE_URL}/api/v1/integrations/linkedin/callback"
        )
        self.scope = [
            "r_liteprofile",
            "r_emailaddress",
            "w_member_social",
            "r_basicprofile",
            "r_fullprofile",
        ]

    def get_authorization_url(self, state: str = None) -> str:
        """Generate LinkedIn OAuth authorization URL"""
        oauth = OAuth2Session(
            self.client_id,
            scope=self.scope,
            redirect_uri=self.redirect_uri,
            state=state,
        )
        authorization_url, state = oauth.authorization_url(
            "https://www.linkedin.com/oauth/v2/authorization"
        )
        return authorization_url

    async def exchange_code_for_token(
        self, code: str, state: str = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        try:
            oauth = OAuth2Session(
                self.client_id, redirect_uri=self.redirect_uri, state=state
            )

            token = oauth.fetch_token(
                "https://www.linkedin.com/oauth/v2/accessToken",
                code=code,
                client_secret=self.client_secret,
            )

            return token
        except Exception as e:
            logger.error(f"Error exchanging LinkedIn code for token: {str(e)}")
            raise

    async def get_profile_data(self, access_token: str) -> Dict[str, Any]:
        """Fetch user profile data from LinkedIn API"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                # Get basic profile
                profile_response = await client.get(
                    "https://api.linkedin.com/v2/people/~", headers=headers
                )
                profile_data = profile_response.json()

                # Get email address
                email_response = await client.get(
                    "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                    headers=headers,
                )
                email_data = email_response.json()

                # Get positions (experience)
                positions_response = await client.get(
                    "https://api.linkedin.com/v2/positions?q=members&projection=(elements*(*,company~(name,industry,logo)))",
                    headers=headers,
                )
                positions_data = positions_response.json()

                # Get education
                education_response = await client.get(
                    "https://api.linkedin.com/v2/educations?q=members&projection=(elements*(*,school~(name,logo)))",
                    headers=headers,
                )
                education_data = education_response.json()

                # Get skills
                skills_response = await client.get(
                    "https://api.linkedin.com/v2/skills?q=members&projection=(elements*(name,standardizedSkillUrn))",
                    headers=headers,
                )
                skills_data = skills_response.json()

                return {
                    "profile": profile_data,
                    "email": email_data,
                    "positions": positions_data,
                    "education": education_data,
                    "skills": skills_data,
                }

        except Exception as e:
            logger.error(f"Error fetching LinkedIn profile data: {str(e)}")
            raise

    async def create_or_update_linkedin_profile(
        self,
        db: AsyncSession,
        user_id: int,
        token_data: Dict[str, Any],
        profile_data: Dict[str, Any],
    ) -> LinkedInProfile:
        """Create or update LinkedIn profile integration"""
        try:
            # Check if profile already exists
            result = await db.execute(
                select(LinkedInProfile).where(LinkedInProfile.user_id == user_id)
            )
            linkedin_profile = result.scalar_one_or_none()

            # Extract profile information
            profile_info = profile_data.get("profile", {})
            email_info = profile_data.get("email", {})
            positions_info = profile_data.get("positions", {})
            education_info = profile_data.get("education", {})
            skills_info = profile_data.get("skills", {})

            # Process profile data
            linkedin_id = profile_info.get("id", "")
            headline = (
                profile_info.get("headline", {}).get("localized", {}).get("en_US", "")
            )
            summary = (
                profile_info.get("summary", {}).get("localized", {}).get("en_US", "")
            )

            # Process location
            location_data = profile_info.get("location", {})
            location = f"{location_data.get('country', {}).get('localized', {}).get('en_US', '')}, {location_data.get('region', {}).get('localized', {}).get('en_US', '')}"

            # Process industry
            industry = (
                profile_info.get("industry", {}).get("localized", {}).get("en_US", "")
            )

            # Process profile picture
            profile_picture_url = None
            if "profilePicture" in profile_info:
                display_image = profile_info["profilePicture"].get("displayImage~", {})
                if "elements" in display_image and display_image["elements"]:
                    profile_picture_url = (
                        display_image["elements"][0]
                        .get("identifiers", [{}])[0]
                        .get("identifier", "")
                    )

            # Process experience
            experience = []
            if "elements" in positions_info:
                for position in positions_info["elements"]:
                    company_info = position.get("company~", {})
                    exp_item = {
                        "title": position.get("title", {})
                        .get("localized", {})
                        .get("en_US", ""),
                        "company": company_info.get("name", {})
                        .get("localized", {})
                        .get("en_US", ""),
                        "industry": company_info.get("industry", {})
                        .get("localized", {})
                        .get("en_US", ""),
                        "description": position.get("description", {})
                        .get("localized", {})
                        .get("en_US", ""),
                        "start_date": self._parse_linkedin_date(
                            position.get("dateRange", {}).get("start", {})
                        ),
                        "end_date": self._parse_linkedin_date(
                            position.get("dateRange", {}).get("end", {})
                        ),
                        "current": not position.get("dateRange", {}).get("end"),
                    }
                    experience.append(exp_item)

            # Process education
            education = []
            if "elements" in education_info:
                for edu in education_info["elements"]:
                    school_info = edu.get("school~", {})
                    edu_item = {
                        "school": school_info.get("name", {})
                        .get("localized", {})
                        .get("en_US", ""),
                        "degree": edu.get("degreeName", {})
                        .get("localized", {})
                        .get("en_US", ""),
                        "field": edu.get("fieldOfStudy", {})
                        .get("localized", {})
                        .get("en_US", ""),
                        "start_date": self._parse_linkedin_date(
                            edu.get("dateRange", {}).get("start", {})
                        ),
                        "end_date": self._parse_linkedin_date(
                            edu.get("dateRange", {}).get("end", {})
                        ),
                    }
                    education.append(edu_item)

            # Process skills
            skills = []
            if "elements" in skills_info:
                for skill in skills_info["elements"]:
                    skills.append(
                        {
                            "name": skill.get("name", {})
                            .get("localized", {})
                            .get("en_US", ""),
                            "standardized_skill_urn": skill.get(
                                "standardizedSkillUrn", ""
                            ),
                        }
                    )

            # Calculate token expiry
            expires_in = token_data.get("expires_in", 3600)
            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            if linkedin_profile:
                # Update existing profile
                linkedin_profile.access_token = token_data.get("access_token")
                linkedin_profile.refresh_token = token_data.get("refresh_token")
                linkedin_profile.token_expires_at = token_expires_at
                linkedin_profile.headline = headline
                linkedin_profile.summary = summary
                linkedin_profile.location = location
                linkedin_profile.industry = industry
                linkedin_profile.profile_picture_url = profile_picture_url
                linkedin_profile.experience = experience
                linkedin_profile.education = education
                linkedin_profile.skills = skills
                linkedin_profile.last_synced = datetime.utcnow()
                linkedin_profile.sync_status = "active"
                linkedin_profile.updated_at = datetime.utcnow()
            else:
                # Create new profile
                linkedin_profile = LinkedInProfile(
                    user_id=user_id,
                    linkedin_id=linkedin_id,
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_expires_at=token_expires_at,
                    profile_url=f"https://www.linkedin.com/in/{linkedin_id}",
                    headline=headline,
                    summary=summary,
                    location=location,
                    industry=industry,
                    profile_picture_url=profile_picture_url,
                    experience=experience,
                    education=education,
                    skills=skills,
                    last_synced=datetime.utcnow(),
                    sync_status="active",
                )
                db.add(linkedin_profile)

            await db.commit()
            await db.refresh(linkedin_profile)

            # Log activity
            await self._log_activity(
                db,
                user_id,
                linkedin_profile.id,
                "profile_sync",
                "LinkedIn profile synchronized successfully",
                {"skills_count": len(skills), "experience_count": len(experience)},
            )

            return linkedin_profile

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating/updating LinkedIn profile: {str(e)}")
            raise

    async def sync_profile_to_user_profile(
        self, db: AsyncSession, user_id: int, linkedin_profile: LinkedInProfile
    ):
        """Sync LinkedIn data to user profile"""
        try:
            # Get user profile
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            user_profile = result.scalar_one_or_none()

            if not user_profile:
                return

            # Update user profile with LinkedIn data
            if linkedin_profile.sync_experience and linkedin_profile.experience:
                # Update current role from most recent experience
                current_experience = next(
                    (
                        exp
                        for exp in linkedin_profile.experience
                        if exp.get("current", False)
                    ),
                    linkedin_profile.experience[0]
                    if linkedin_profile.experience
                    else None,
                )
                if current_experience:
                    user_profile.current_role = current_experience.get("title", "")

            # Update skills
            if linkedin_profile.sync_skills and linkedin_profile.skills:
                existing_skills = user_profile.skills or {}
                for skill in linkedin_profile.skills:
                    skill_name = skill.get("name", "").lower()
                    if skill_name:
                        existing_skills[skill_name] = existing_skills.get(
                            skill_name, 0.8
                        )  # Default confidence
                user_profile.skills = existing_skills

            # Update education
            if linkedin_profile.sync_education and linkedin_profile.education:
                education_text = []
                for edu in linkedin_profile.education:
                    edu_str = f"{edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('school', '')}"
                    education_text.append(edu_str.strip())
                user_profile.education = "; ".join(education_text)

            # Update LinkedIn URL
            user_profile.linkedin_url = linkedin_profile.profile_url

            # Update profile completeness
            user_profile.profile_completeness = self._calculate_profile_completeness(
                user_profile
            )
            user_profile.updated_at = datetime.utcnow()

            await db.commit()

            # Log activity
            await self._log_activity(
                db,
                user_id,
                linkedin_profile.id,
                "profile_update",
                "User profile updated with LinkedIn data",
                {"completeness": user_profile.profile_completeness},
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Error syncing LinkedIn profile to user profile: {str(e)}")
            raise

    async def refresh_access_token(
        self, db: AsyncSession, linkedin_profile: LinkedInProfile
    ) -> bool:
        """Refresh LinkedIn access token"""
        try:
            if not linkedin_profile.refresh_token:
                return False

            data = {
                "grant_type": "refresh_token",
                "refresh_token": linkedin_profile.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken", data=data
                )

                if response.status_code == 200:
                    token_data = response.json()

                    # Update tokens
                    linkedin_profile.access_token = token_data.get("access_token")
                    if "refresh_token" in token_data:
                        linkedin_profile.refresh_token = token_data.get("refresh_token")

                    expires_in = token_data.get("expires_in", 3600)
                    linkedin_profile.token_expires_at = datetime.utcnow() + timedelta(
                        seconds=expires_in
                    )
                    linkedin_profile.updated_at = datetime.utcnow()

                    await db.commit()
                    return True
                else:
                    logger.error(f"Failed to refresh LinkedIn token: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error refreshing LinkedIn access token: {str(e)}")
            return False

    async def sync_linkedin_profiles(self, db: AsyncSession):
        """Background task to sync all active LinkedIn profiles"""
        try:
            # Get all active LinkedIn profiles that need syncing
            result = await db.execute(
                select(LinkedInProfile).where(
                    LinkedInProfile.sync_status == "active",
                    LinkedInProfile.auto_sync_enabled == True,
                )
            )
            profiles = result.scalars().all()

            for profile in profiles:
                try:
                    # Check if sync is needed based on frequency
                    if not self._should_sync(profile):
                        continue

                    # Check if token needs refresh
                    if (
                        profile.token_expires_at
                        and profile.token_expires_at <= datetime.utcnow()
                    ):
                        if not await self.refresh_access_token(db, profile):
                            profile.sync_status = "error"
                            profile.sync_errors = {
                                "error": "Failed to refresh access token"
                            }
                            continue

                    # Fetch updated profile data
                    profile_data = await self.get_profile_data(profile.access_token)

                    # Update profile with new data
                    await self.create_or_update_linkedin_profile(
                        db,
                        profile.user_id,
                        {"access_token": profile.access_token},
                        profile_data,
                    )

                    # Sync to user profile
                    await self.sync_profile_to_user_profile(
                        db, profile.user_id, profile
                    )

                except Exception as e:
                    logger.error(
                        f"Error syncing LinkedIn profile {profile.id}: {str(e)}"
                    )
                    profile.sync_status = "error"
                    profile.sync_errors = {"error": str(e)}
                    await db.commit()

        except Exception as e:
            logger.error(f"Error in LinkedIn sync background task: {str(e)}")

    def _parse_linkedin_date(self, date_obj: Dict) -> Optional[str]:
        """Parse LinkedIn date object to string"""
        if not date_obj:
            return None

        year = date_obj.get("year")
        month = date_obj.get("month", 1)

        if year:
            return f"{year}-{month:02d}-01"
        return None

    def _should_sync(self, profile: LinkedInProfile) -> bool:
        """Check if profile should be synced based on frequency"""
        if not profile.last_synced:
            return True

        now = datetime.utcnow()
        time_diff = now - profile.last_synced

        if profile.sync_frequency == "daily":
            return time_diff >= timedelta(days=1)
        elif profile.sync_frequency == "weekly":
            return time_diff >= timedelta(weeks=1)
        elif profile.sync_frequency == "monthly":
            return time_diff >= timedelta(days=30)

        return False

    def _calculate_profile_completeness(self, user_profile: UserProfile) -> float:
        """Calculate profile completeness score"""
        score = 0.0
        total_fields = 8

        if user_profile.current_role:
            score += 1
        if user_profile.experience_level:
            score += 1
        if user_profile.education:
            score += 1
        if user_profile.skills:
            score += 1
        if user_profile.career_goals:
            score += 1
        if user_profile.preferred_locations:
            score += 1
        if user_profile.linkedin_url:
            score += 1
        if user_profile.salary_expectations:
            score += 1

        return (score / total_fields) * 100

    async def _log_activity(
        self,
        db: AsyncSession,
        user_id: int,
        integration_id: int,
        activity_type: str,
        description: str,
        data: Dict = None,
    ):
        """Log integration activity"""
        try:
            log_entry = IntegrationActivityLog(
                user_id=user_id,
                integration_type="linkedin",
                integration_id=integration_id,
                activity_type=activity_type,
                activity_description=description,
                activity_data=data or {},
                status="success",
            )
            db.add(log_entry)
            await db.commit()
        except Exception as e:
            logger.error(f"Error logging LinkedIn activity: {str(e)}")


# Create service instance
linkedin_service = LinkedInService()
