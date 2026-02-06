from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow

from ..core.config import settings
from ..db.models import User
from ..db.integration_models import (
    CalendarIntegration,
    CalendarEvent,
    IntegrationActivityLog,
)
import logging

logger = logging.getLogger(__name__)


class CalendarService:
    def __init__(self):
        self.google_client_id = settings.GOOGLE_CLIENT_ID
        self.google_client_secret = settings.GOOGLE_CLIENT_SECRET
        self.microsoft_client_id = settings.MICROSOFT_CLIENT_ID
        self.microsoft_client_secret = settings.MICROSOFT_CLIENT_SECRET
        self.redirect_uri = (
            f"{settings.API_BASE_URL}/api/v1/integrations/calendar/callback"
        )

        # Google Calendar scopes
        self.google_scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
        ]

        # Microsoft Graph scopes
        self.microsoft_scopes = [
            "https://graph.microsoft.com/calendars.readwrite",
            "https://graph.microsoft.com/user.read",
        ]

    def get_google_authorization_url(self, state: str = None) -> str:
        """Generate Google Calendar OAuth authorization URL"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.google_client_id,
                    "client_secret": self.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=self.google_scopes,
        )
        flow.redirect_uri = self.redirect_uri

        authorization_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", state=state
        )
        return authorization_url

    def get_microsoft_authorization_url(self, state: str = None) -> str:
        """Generate Microsoft Calendar OAuth authorization URL"""
        params = {
            "client_id": self.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.microsoft_scopes),
            "state": state or "",
            "response_mode": "query",
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{query_string}"

    async def exchange_google_code_for_token(
        self, code: str, state: str = None
    ) -> Dict[str, Any]:
        """Exchange Google authorization code for access token"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.google_client_id,
                        "client_secret": self.google_client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri],
                    }
                },
                scopes=self.google_scopes,
                state=state,
            )
            flow.redirect_uri = self.redirect_uri

            flow.fetch_token(code=code)
            credentials = flow.credentials

            return {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_in": 3600,  # Google tokens typically expire in 1 hour
                "token_type": "Bearer",
            }

        except Exception as e:
            logger.error(f"Error exchanging Google code for token: {str(e)}")
            raise

    async def exchange_microsoft_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange Microsoft authorization code for access token"""
        try:
            data = {
                "client_id": self.microsoft_client_id,
                "client_secret": self.microsoft_client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                    data=data,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Microsoft token exchange failed: {response.text}")
                    raise Exception(f"Token exchange failed: {response.text}")

        except Exception as e:
            logger.error(f"Error exchanging Microsoft code for token: {str(e)}")
            raise

    async def get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Google user information"""
        try:
            credentials = Credentials(token=access_token)
            service = build("oauth2", "v2", credentials=credentials)
            user_info = service.userinfo().get().execute()

            # Also get calendar list
            calendar_service = build("calendar", "v3", credentials=credentials)
            calendars = calendar_service.calendarList().list().execute()

            return {"user_info": user_info, "calendars": calendars.get("items", [])}

        except Exception as e:
            logger.error(f"Error getting Google user info: {str(e)}")
            raise

    async def get_microsoft_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Microsoft user information"""
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                # Get user info
                user_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me", headers=headers
                )
                user_info = user_response.json()

                # Get calendars
                calendars_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me/calendars", headers=headers
                )
                calendars_info = calendars_response.json()

                return {
                    "user_info": user_info,
                    "calendars": calendars_info.get("value", []),
                }

        except Exception as e:
            logger.error(f"Error getting Microsoft user info: {str(e)}")
            raise

    async def create_or_update_calendar_integration(
        self,
        db: AsyncSession,
        user_id: int,
        provider: str,
        token_data: Dict[str, Any],
        user_data: Dict[str, Any],
    ) -> CalendarIntegration:
        """Create or update calendar integration"""
        try:
            # Check if integration already exists
            result = await db.execute(
                select(CalendarIntegration).where(
                    CalendarIntegration.user_id == user_id,
                    CalendarIntegration.provider == provider,
                )
            )
            calendar_integration = result.scalar_one_or_none()

            # Extract user information
            user_info = user_data.get("user_info", {})
            calendars = user_data.get("calendars", [])

            # Get primary calendar
            primary_calendar_id = None
            if provider == "google":
                primary_calendar = next(
                    (cal for cal in calendars if cal.get("primary", False)),
                    calendars[0] if calendars else None,
                )
                if primary_calendar:
                    primary_calendar_id = primary_calendar.get("id")
                provider_user_id = user_info.get("id", "")
                email = user_info.get("email", "")
            else:  # Microsoft
                primary_calendar = next(
                    (cal for cal in calendars if cal.get("isDefaultCalendar", False)),
                    calendars[0] if calendars else None,
                )
                if primary_calendar:
                    primary_calendar_id = primary_calendar.get("id")
                provider_user_id = user_info.get("id", "")
                email = user_info.get("mail") or user_info.get("userPrincipalName", "")

            # Calculate token expiry
            expires_in = token_data.get("expires_in", 3600)
            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            if calendar_integration:
                # Update existing integration
                calendar_integration.access_token = token_data.get("access_token")
                calendar_integration.refresh_token = token_data.get("refresh_token")
                calendar_integration.token_expires_at = token_expires_at
                calendar_integration.primary_calendar_id = primary_calendar_id
                calendar_integration.email = email
                calendar_integration.is_active = True
                calendar_integration.sync_status = "active"
                calendar_integration.updated_at = datetime.utcnow()
            else:
                # Create new integration
                calendar_integration = CalendarIntegration(
                    user_id=user_id,
                    provider=provider,
                    provider_user_id=provider_user_id,
                    email=email,
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_expires_at=token_expires_at,
                    primary_calendar_id=primary_calendar_id,
                    is_active=True,
                    sync_status="active",
                )
                db.add(calendar_integration)

            await db.commit()
            await db.refresh(calendar_integration)

            # Log activity
            await self._log_activity(
                db,
                user_id,
                calendar_integration.id,
                "integration_created",
                f"{provider.title()} calendar integration created",
                {"provider": provider, "email": email},
            )

            return calendar_integration

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating/updating calendar integration: {str(e)}")
            raise

    async def create_interview_event(
        self,
        db: AsyncSession,
        user_id: int,
        job_application_id: int,
        event_details: Dict[str, Any],
    ) -> Optional[CalendarEvent]:
        """Create an interview event in user's calendar"""
        try:
            # Get user's calendar integration
            result = await db.execute(
                select(CalendarIntegration).where(
                    CalendarIntegration.user_id == user_id,
                    CalendarIntegration.is_active.is_(True),
                )
            )
            calendar_integration = result.scalar_one_or_none()

            if not calendar_integration:
                logger.warning(
                    f"No active calendar integration found for user {user_id}"
                )
                return None

            # Check if token needs refresh
            if calendar_integration.token_expires_at <= datetime.utcnow():
                if not await self.refresh_access_token(db, calendar_integration):
                    logger.error(
                        f"Failed to refresh token for calendar integration {calendar_integration.id}"
                    )
                    return None

            # Create event based on provider
            if calendar_integration.provider == "google":
                external_event_id = await self._create_google_event(
                    calendar_integration, event_details
                )
            else:  # Microsoft
                external_event_id = await self._create_microsoft_event(
                    calendar_integration, event_details
                )

            if not external_event_id:
                return None

            # Create calendar event record
            calendar_event = CalendarEvent(
                calendar_integration_id=calendar_integration.id,
                user_id=user_id,
                external_event_id=external_event_id,
                title=event_details.get("title", "Interview"),
                description=event_details.get("description", ""),
                location=event_details.get("location", ""),
                start_time=event_details.get("start_time"),
                end_time=event_details.get("end_time"),
                timezone=event_details.get("timezone", "Africa/Nairobi"),
                event_type="interview",
                related_application_id=job_application_id,
                meeting_url=event_details.get("meeting_url"),
                meeting_platform=event_details.get("meeting_platform"),
                attendees=event_details.get("attendees", []),
                reminder_times=event_details.get(
                    "reminder_times", [15, 60]
                ),  # 15 min and 1 hour before
            )

            db.add(calendar_event)
            await db.commit()
            await db.refresh(calendar_event)

            # Log activity
            await self._log_activity(
                db,
                user_id,
                calendar_integration.id,
                "event_created",
                "Interview event created in calendar",
                {"event_id": external_event_id, "title": event_details.get("title")},
            )

            return calendar_event

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating interview event: {str(e)}")
            return None

    async def _create_google_event(
        self, calendar_integration: CalendarIntegration, event_details: Dict[str, Any]
    ) -> Optional[str]:
        """Create event in Google Calendar"""
        try:
            credentials = Credentials(
                token=calendar_integration.access_token,
                refresh_token=calendar_integration.refresh_token,
            )

            service = build("calendar", "v3", credentials=credentials)

            # Prepare event data
            event_data = {
                "summary": event_details.get("title", "Interview"),
                "description": event_details.get("description", ""),
                "location": event_details.get("location", ""),
                "start": {
                    "dateTime": event_details.get("start_time").isoformat(),
                    "timeZone": event_details.get("timezone", "Africa/Nairobi"),
                },
                "end": {
                    "dateTime": event_details.get("end_time").isoformat(),
                    "timeZone": event_details.get("timezone", "Africa/Nairobi"),
                },
                "attendees": [
                    {"email": attendee}
                    for attendee in event_details.get("attendees", [])
                ],
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": minutes}
                        for minutes in event_details.get("reminder_times", [15, 60])
                    ],
                },
            }

            # Add meeting URL if provided
            if event_details.get("meeting_url"):
                event_data["description"] += (
                    f"\n\nMeeting Link: {event_details.get('meeting_url')}"
                )

            # Create event
            event = (
                service.events()
                .insert(
                    calendarId=calendar_integration.primary_calendar_id or "primary",
                    body=event_data,
                )
                .execute()
            )

            return event.get("id")

        except Exception as e:
            logger.error(f"Error creating Google Calendar event: {str(e)}")
            return None

    async def _create_microsoft_event(
        self, calendar_integration: CalendarIntegration, event_details: Dict[str, Any]
    ) -> Optional[str]:
        """Create event in Microsoft Calendar"""
        try:
            headers = {
                "Authorization": f"Bearer {calendar_integration.access_token}",
                "Content-Type": "application/json",
            }

            # Prepare event data
            event_data = {
                "subject": event_details.get("title", "Interview"),
                "body": {
                    "contentType": "HTML",
                    "content": event_details.get("description", ""),
                },
                "start": {
                    "dateTime": event_details.get("start_time").isoformat(),
                    "timeZone": event_details.get("timezone", "Africa/Nairobi"),
                },
                "end": {
                    "dateTime": event_details.get("end_time").isoformat(),
                    "timeZone": event_details.get("timezone", "Africa/Nairobi"),
                },
                "location": {"displayName": event_details.get("location", "")},
                "attendees": [
                    {"emailAddress": {"address": attendee, "name": attendee}}
                    for attendee in event_details.get("attendees", [])
                ],
                "reminderMinutesBeforeStart": min(
                    event_details.get("reminder_times", [15])
                ),
            }

            # Add meeting URL if provided
            if event_details.get("meeting_url"):
                event_data["body"]["content"] += (
                    f"<br><br>Meeting Link: <a href='{event_details.get('meeting_url')}'>{event_details.get('meeting_url')}</a>"
                )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_integration.primary_calendar_id or 'calendar'}/events",
                    headers=headers,
                    json=event_data,
                )

                if response.status_code == 201:
                    event = response.json()
                    return event.get("id")
                else:
                    logger.error(f"Failed to create Microsoft event: {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error creating Microsoft Calendar event: {str(e)}")
            return None

    async def refresh_access_token(
        self, db: AsyncSession, calendar_integration: CalendarIntegration
    ) -> bool:
        """Refresh calendar access token"""
        try:
            if not calendar_integration.refresh_token:
                return False

            if calendar_integration.provider == "google":
                return await self._refresh_google_token(db, calendar_integration)
            else:  # Microsoft
                return await self._refresh_microsoft_token(db, calendar_integration)

        except Exception as e:
            logger.error(f"Error refreshing calendar access token: {str(e)}")
            return False

    async def _refresh_google_token(
        self, db: AsyncSession, calendar_integration: CalendarIntegration
    ) -> bool:
        """Refresh Google access token"""
        try:
            credentials = Credentials(
                token=calendar_integration.access_token,
                refresh_token=calendar_integration.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.google_client_id,
                client_secret=self.google_client_secret,
            )

            credentials.refresh(Request())

            # Update integration with new token
            calendar_integration.access_token = credentials.token
            calendar_integration.token_expires_at = credentials.expiry
            calendar_integration.updated_at = datetime.utcnow()

            await db.commit()
            return True

        except Exception as e:
            logger.error(f"Error refreshing Google token: {str(e)}")
            return False

    async def _refresh_microsoft_token(
        self, db: AsyncSession, calendar_integration: CalendarIntegration
    ) -> bool:
        """Refresh Microsoft access token"""
        try:
            data = {
                "client_id": self.microsoft_client_id,
                "client_secret": self.microsoft_client_secret,
                "refresh_token": calendar_integration.refresh_token,
                "grant_type": "refresh_token",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                    data=data,
                )

                if response.status_code == 200:
                    token_data = response.json()

                    # Update integration with new token
                    calendar_integration.access_token = token_data.get("access_token")
                    if "refresh_token" in token_data:
                        calendar_integration.refresh_token = token_data.get(
                            "refresh_token"
                        )

                    expires_in = token_data.get("expires_in", 3600)
                    calendar_integration.token_expires_at = (
                        datetime.utcnow() + timedelta(seconds=expires_in)
                    )
                    calendar_integration.updated_at = datetime.utcnow()

                    await db.commit()
                    return True
                else:
                    logger.error(f"Failed to refresh Microsoft token: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error refreshing Microsoft token: {str(e)}")
            return False

    async def sync_upcoming_interviews(self, db: AsyncSession):
        """Background task to sync upcoming interviews and send reminders"""
        try:
            # Get all calendar events that need reminders
            now = datetime.utcnow()
            result = await db.execute(
                select(CalendarEvent).where(
                    CalendarEvent.start_time > now,
                    CalendarEvent.start_time <= now + timedelta(hours=24),
                    CalendarEvent.reminder_sent.is_(False),
                    CalendarEvent.status == "scheduled",
                )
            )
            events = result.scalars().all()

            for event in events:
                try:
                    # Check if it's time to send reminder
                    time_until_event = event.start_time - now
                    minutes_until = time_until_event.total_seconds() / 60

                    # Check if any reminder time matches
                    for reminder_minutes in event.reminder_times:
                        if (
                            abs(minutes_until - reminder_minutes) <= 5
                        ):  # 5-minute tolerance
                            await self._send_interview_reminder(db, event)
                            break

                except Exception as e:
                    logger.error(
                        f"Error processing reminder for event {event.id}: {str(e)}"
                    )

        except Exception as e:
            logger.error(f"Error in calendar sync background task: {str(e)}")

    async def _send_interview_reminder(self, db: AsyncSession, event: CalendarEvent):
        """Send interview reminder notification"""
        try:
            # Import here to avoid circular imports
            from .notification_service import notification_service

            # Get user
            result = await db.execute(select(User).where(User.id == event.user_id))
            user = result.scalar_one_or_none()

            if not user:
                return

            # Prepare reminder message
            time_until = event.start_time - datetime.utcnow()
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)

            if hours > 0:
                time_str = f"{hours} hour{'s' if hours > 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
            else:
                time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"

            message = f"Interview Reminder: Your interview '{event.title}' is starting in {time_str}."
            if event.location:
                message += f" Location: {event.location}"
            if event.meeting_url:
                message += f" Meeting Link: {event.meeting_url}"

            # Send notification
            await notification_service.send_notification(
                db,
                user.id,
                "interview_reminder",
                "Interview Reminder",
                message,
                {"event_id": event.id, "start_time": event.start_time.isoformat()},
            )

            # Mark reminder as sent
            event.reminder_sent = True
            await db.commit()

            # Log activity
            await self._log_activity(
                db,
                user.id,
                event.calendar_integration_id,
                "reminder_sent",
                "Interview reminder sent",
                {"event_id": event.id, "title": event.title},
            )

        except Exception as e:
            logger.error(f"Error sending interview reminder: {str(e)}")

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
                integration_type="calendar",
                integration_id=integration_id,
                activity_type=activity_type,
                activity_description=description,
                activity_data=data or {},
                status="success",
            )
            db.add(log_entry)
            await db.commit()
        except Exception as e:
            logger.error(f"Error logging calendar activity: {str(e)}")


# Create service instance
calendar_service = CalendarService()
