from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from ..db.database import get_db
from ..db.models import User, Organization, JobApplication
from ..db.integration_models import (
    LinkedInProfile, CalendarIntegration, CalendarEvent, 
    ATSIntegration, ATSJobSync, ATSApplicationSync, IntegrationActivityLog
)
from ..services.auth_service import get_current_user
from ..services.linkedin_service import linkedin_service
from ..services.calendar_service import calendar_service
from ..services.ats_service import ats_service
from ..core.config import settings
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class LinkedInAuthResponse(BaseModel):
    authorization_url: str
    state: str

class CalendarAuthResponse(BaseModel):
    authorization_url: str
    provider: str
    state: str

class ATSIntegrationRequest(BaseModel):
    ats_provider: str
    credentials: Dict[str, Any]
    settings: Optional[Dict[str, Any]] = None

class CalendarEventRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    location: Optional[str] = ""
    start_time: datetime
    end_time: datetime
    timezone: str = "Africa/Nairobi"
    meeting_url: Optional[str] = None
    meeting_platform: Optional[str] = None
    attendees: List[str] = []
    reminder_times: List[int] = [15, 60]

# LinkedIn Integration Routes
@router.get("/linkedin/auth", response_model=LinkedInAuthResponse)
async def linkedin_auth_url(
    current_user: User = Depends(get_current_user)
):
    """Get LinkedIn OAuth authorization URL"""
    try:
        if not settings.ENABLE_LINKEDIN_INTEGRATION:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="LinkedIn integration is disabled"
            )
        
        state = str(uuid.uuid4())
        authorization_url = linkedin_service.get_authorization_url(state)
        
        return LinkedInAuthResponse(
            authorization_url=authorization_url,
            state=state
        )
    except Exception as e:
        logger.error(f"Error generating LinkedIn auth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )

@router.get("/linkedin/callback")
async def linkedin_callback(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Handle LinkedIn OAuth callback"""
    try:
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LinkedIn authorization failed: {error}"
            )
        
        # Exchange code for token
        token_data = await linkedin_service.exchange_code_for_token(code, state)
        
        # Get profile data
        profile_data = await linkedin_service.get_profile_data(token_data['access_token'])
        
        # Create or update LinkedIn profile
        linkedin_profile = await linkedin_service.create_or_update_linkedin_profile(
            db, current_user.id, token_data, profile_data
        )
        
        # Sync profile data to user profile
        await linkedin_service.sync_profile_to_user_profile(
            db, current_user.id, linkedin_profile
        )
        
        # Redirect to frontend success page
        return RedirectResponse(
            url=f"{settings.WEBSITE_URL}/dashboard/integrations?linkedin=success"
        )
        
    except Exception as e:
        logger.error(f"Error in LinkedIn callback: {str(e)}")
        return RedirectResponse(
            url=f"{settings.WEBSITE_URL}/dashboard/integrations?linkedin=error&message={str(e)}"
        )

@router.get("/linkedin/profile")
async def get_linkedin_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's LinkedIn profile integration"""
    try:
        result = await db.execute(
            select(LinkedInProfile).where(LinkedInProfile.user_id == current_user.id)
        )
        linkedin_profile = result.scalar_one_or_none()
        
        if not linkedin_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LinkedIn profile not found"
            )
        
        return {
            "id": linkedin_profile.id,
            "linkedin_id": linkedin_profile.linkedin_id,
            "profile_url": linkedin_profile.profile_url,
            "headline": linkedin_profile.headline,
            "location": linkedin_profile.location,
            "industry": linkedin_profile.industry,
            "sync_status": linkedin_profile.sync_status,
            "last_synced": linkedin_profile.last_synced,
            "auto_sync_enabled": linkedin_profile.auto_sync_enabled,
            "sync_frequency": linkedin_profile.sync_frequency,
            "privacy_settings": {
                "sync_profile_picture": linkedin_profile.sync_profile_picture,
                "sync_experience": linkedin_profile.sync_experience,
                "sync_education": linkedin_profile.sync_education,
                "sync_skills": linkedin_profile.sync_skills
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting LinkedIn profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get LinkedIn profile"
        )

@router.post("/linkedin/sync")
async def sync_linkedin_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually sync LinkedIn profile"""
    try:
        result = await db.execute(
            select(LinkedInProfile).where(LinkedInProfile.user_id == current_user.id)
        )
        linkedin_profile = result.scalar_one_or_none()
        
        if not linkedin_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LinkedIn profile not found"
            )
        
        # Check if token needs refresh
        if linkedin_profile.token_expires_at and linkedin_profile.token_expires_at <= datetime.utcnow():
            if not await linkedin_service.refresh_access_token(db, linkedin_profile):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to refresh LinkedIn access token"
                )
        
        # Fetch updated profile data
        profile_data = await linkedin_service.get_profile_data(linkedin_profile.access_token)
        
        # Update profile
        updated_profile = await linkedin_service.create_or_update_linkedin_profile(
            db, current_user.id, {'access_token': linkedin_profile.access_token}, profile_data
        )
        
        # Sync to user profile
        await linkedin_service.sync_profile_to_user_profile(
            db, current_user.id, updated_profile
        )
        
        return {"message": "LinkedIn profile synced successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing LinkedIn profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync LinkedIn profile"
        )

@router.delete("/linkedin")
async def disconnect_linkedin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect LinkedIn integration"""
    try:
        result = await db.execute(
            select(LinkedInProfile).where(LinkedInProfile.user_id == current_user.id)
        )
        linkedin_profile = result.scalar_one_or_none()
        
        if not linkedin_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LinkedIn profile not found"
            )
        
        await db.delete(linkedin_profile)
        await db.commit()
        
        return {"message": "LinkedIn integration disconnected successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting LinkedIn: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect LinkedIn integration"
        )

# Calendar Integration Routes
@router.get("/calendar/auth/{provider}", response_model=CalendarAuthResponse)
async def calendar_auth_url(
    provider: str,
    current_user: User = Depends(get_current_user)
):
    """Get calendar OAuth authorization URL"""
    try:
        if not settings.ENABLE_CALENDAR_INTEGRATION:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Calendar integration is disabled"
            )
        
        if provider not in ['google', 'microsoft']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported calendar provider"
            )
        
        state = str(uuid.uuid4())
        
        if provider == 'google':
            authorization_url = calendar_service.get_google_authorization_url(state)
        else:  # microsoft
            authorization_url = calendar_service.get_microsoft_authorization_url(state)
        
        return CalendarAuthResponse(
            authorization_url=authorization_url,
            provider=provider,
            state=state
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating calendar auth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )

@router.get("/calendar/callback")
async def calendar_callback(
    provider: str = Query(...),
    code: str = Query(...),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Handle calendar OAuth callback"""
    try:
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Calendar authorization failed: {error}"
            )
        
        # Exchange code for token
        if provider == 'google':
            token_data = await calendar_service.exchange_google_code_for_token(code, state)
            user_data = await calendar_service.get_google_user_info(token_data['access_token'])
        elif provider == 'microsoft':
            token_data = await calendar_service.exchange_microsoft_code_for_token(code)
            user_data = await calendar_service.get_microsoft_user_info(token_data['access_token'])
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported calendar provider"
            )
        
        # Create or update calendar integration
        calendar_integration = await calendar_service.create_or_update_calendar_integration(
            db, current_user.id, provider, token_data, user_data
        )
        
        # Redirect to frontend success page
        return RedirectResponse(
            url=f"{settings.WEBSITE_URL}/dashboard/integrations?calendar=success&provider={provider}"
        )
        
    except Exception as e:
        logger.error(f"Error in calendar callback: {str(e)}")
        return RedirectResponse(
            url=f"{settings.WEBSITE_URL}/dashboard/integrations?calendar=error&message={str(e)}"
        )

@router.get("/calendar/integrations")
async def get_calendar_integrations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's calendar integrations"""
    try:
        result = await db.execute(
            select(CalendarIntegration).where(CalendarIntegration.user_id == current_user.id)
        )
        integrations = result.scalars().all()
        
        return [
            {
                "id": integration.id,
                "provider": integration.provider,
                "email": integration.email,
                "is_active": integration.is_active,
                "sync_status": integration.sync_status,
                "last_synced": integration.last_synced,
                "settings": {
                    "auto_schedule_interviews": integration.auto_schedule_interviews,
                    "send_reminders": integration.send_reminders,
                    "sync_job_deadlines": integration.sync_job_deadlines
                }
            }
            for integration in integrations
        ]
        
    except Exception as e:
        logger.error(f"Error getting calendar integrations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get calendar integrations"
        )

@router.post("/calendar/events")
async def create_calendar_event(
    event_request: CalendarEventRequest,
    job_application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a calendar event for an interview"""
    try:
        # Verify job application belongs to user
        job_application = await db.get(JobApplication, job_application_id)
        if not job_application or job_application.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job application not found"
            )
        
        # Create calendar event
        event_details = event_request.dict()
        calendar_event = await calendar_service.create_interview_event(
            db, current_user.id, job_application_id, event_details
        )
        
        if not calendar_event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create calendar event. Please check your calendar integration."
            )
        
        return {
            "id": calendar_event.id,
            "external_event_id": calendar_event.external_event_id,
            "title": calendar_event.title,
            "start_time": calendar_event.start_time,
            "end_time": calendar_event.end_time,
            "status": calendar_event.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating calendar event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create calendar event"
        )

# ATS Integration Routes (for organizations)
@router.post("/ats")
async def create_ats_integration(
    request: ATSIntegrationRequest,
    organization_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create ATS integration for an organization"""
    try:
        if not settings.ENABLE_ATS_INTEGRATION:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ATS integration is disabled"
            )
        
        # Verify organization exists (you might want to add authorization check here)
        organization = await db.get(Organization, organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Create ATS integration
        ats_integration = await ats_service.create_ats_integration(
            db, organization_id, request.ats_provider, request.credentials, request.settings
        )
        
        return {
            "id": ats_integration.id,
            "ats_provider": ats_integration.ats_provider,
            "sync_status": ats_integration.sync_status,
            "is_active": ats_integration.is_active,
            "created_at": ats_integration.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ATS integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ATS integration"
        )

@router.get("/ats/{organization_id}")
async def get_ats_integrations(
    organization_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get ATS integrations for an organization"""
    try:
        result = await db.execute(
            select(ATSIntegration).where(ATSIntegration.organization_id == organization_id)
        )
        integrations = result.scalars().all()
        
        return [
            {
                "id": integration.id,
                "ats_provider": integration.ats_provider,
                "sync_status": integration.sync_status,
                "is_active": integration.is_active,
                "last_synced": integration.last_synced,
                "jobs_synced_count": integration.jobs_synced_count,
                "settings": {
                    "sync_jobs": integration.sync_jobs,
                    "sync_applications": integration.sync_applications,
                    "sync_candidates": integration.sync_candidates
                }
            }
            for integration in integrations
        ]
        
    except Exception as e:
        logger.error(f"Error getting ATS integrations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ATS integrations"
        )

@router.post("/ats/{integration_id}/sync")
async def sync_ats_jobs(
    integration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually sync jobs from ATS"""
    try:
        ats_integration = await db.get(ATSIntegration, integration_id)
        if not ats_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ATS integration not found"
            )
        
        # Sync jobs
        result = await ats_service.sync_jobs_from_ats(db, ats_integration)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing ATS jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync ATS jobs"
        )

# Integration Activity Logs
@router.get("/activity")
async def get_integration_activity(
    integration_type: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get integration activity logs for the user"""
    try:
        query = select(IntegrationActivityLog).where(
            IntegrationActivityLog.user_id == current_user.id
        )
        
        if integration_type:
            query = query.where(IntegrationActivityLog.integration_type == integration_type)
        
        query = query.order_by(IntegrationActivityLog.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        activities = result.scalars().all()
        
        return [
            {
                "id": activity.id,
                "integration_type": activity.integration_type,
                "activity_type": activity.activity_type,
                "activity_description": activity.activity_description,
                "status": activity.status,
                "created_at": activity.created_at,
                "activity_data": activity.activity_data
            }
            for activity in activities
        ]
        
    except Exception as e:
        logger.error(f"Error getting integration activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get integration activity"
        )
