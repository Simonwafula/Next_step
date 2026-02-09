from typing import Dict, Any
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Form,
    Query,
    Request,
    Response,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import httpx
import uuid

from ..db.database import get_db
from ..services.auth_service import (
    auth_service,
    get_current_user,
    is_admin_user,
)
from ..db.models import User, UserProfile
from ..core.config import settings
from ..core.rate_limiter import rate_limit
from ..services.email_service import send_password_reset_email

router = APIRouter()


# Pydantic models for request/response
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    whatsapp_number: str | None = None


class UserResponse(BaseModel):
    id: int
    uuid: str
    email: str
    full_name: str
    phone: str | None = None
    whatsapp_number: str | None = None
    is_active: bool
    is_verified: bool
    subscription_tier: str
    created_at: str
    last_login: str = None
    is_admin: bool = False


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse


class ProfileUpdate(BaseModel):
    current_role: str = None
    experience_level: str = None
    education: str = None
    skills: Dict[str, float] = None
    career_goals: str = None
    preferred_locations: list = None
    salary_expectations: Dict[str, Any] = None
    linkedin_url: str = None
    portfolio_url: str = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class GoogleAuthUrlResponse(BaseModel):
    authorization_url: str


def _cookie_domain() -> str | None:
    domain = settings.AUTH_COOKIE_DOMAIN.strip()
    return domain or None


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    common = {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "path": settings.AUTH_COOKIE_PATH,
        "domain": _cookie_domain(),
    }
    response.set_cookie(
        key=settings.AUTH_COOKIE_ACCESS_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,
    )
    response.set_cookie(
        key=settings.AUTH_COOKIE_REFRESH_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **common,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.AUTH_COOKIE_ACCESS_NAME,
        path=settings.AUTH_COOKIE_PATH,
        domain=_cookie_domain(),
    )
    response.delete_cookie(
        key=settings.AUTH_COOKIE_REFRESH_NAME,
        path=settings.AUTH_COOKIE_PATH,
        domain=_cookie_domain(),
    )


def build_token_response(db: Session, user: User) -> Dict[str, Any]:
    access_token = auth_service.create_access_token(
        data={"sub": user.id, "email": user.email}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": user.id, "email": user.email}
    )
    auth_service.update_last_login(db, user)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": UserResponse(
            id=user.id,
            uuid=user.uuid,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            whatsapp_number=user.whatsapp_number,
            is_active=user.is_active,
            is_verified=user.is_verified,
            subscription_tier=user.subscription_tier,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
            is_admin=is_admin_user(user),
        ),
    }


@router.post("/register", response_model=Token)
@rate_limit(max_requests=5, window_seconds=60)  # 5 registrations per minute per IP
async def register(
    request: Request,
    response: Response,
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """Register a new user."""
    try:
        # Create user
        user = auth_service.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            phone=user_data.phone,
            whatsapp_number=user_data.whatsapp_number,
        )

        payload = build_token_response(db, user)
        _set_auth_cookies(response, payload["access_token"], payload["refresh_token"])
        return payload

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=Token)
@rate_limit(max_requests=10, window_seconds=60)  # 10 login attempts per minute per IP
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login user with email and password."""
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = build_token_response(db, user)
    _set_auth_cookies(response, payload["access_token"], payload["refresh_token"])
    return payload


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Refresh access token using refresh token."""
    try:
        token = refresh_token or request.cookies.get(settings.AUTH_COOKIE_REFRESH_NAME)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
            )
        payload = auth_service.verify_token(token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        user_id = payload.get("sub")
        user = auth_service.get_user_by_id(db, user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        next_payload = build_token_response(db, user)
        _set_auth_cookies(
            response, next_payload["access_token"], next_payload["refresh_token"]
        )
        return next_payload

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@router.post("/forgot-password")
@rate_limit(max_requests=3, window_seconds=60)  # 3 reset requests per minute per IP
async def forgot_password(
    request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)
):
    """Request a password reset email."""
    user = auth_service.get_user_by_email(db, payload.email)
    token = None
    if user:
        token = auth_service.create_password_reset_token(user)
        reset_url = f"{settings.PASSWORD_RESET_URL}?token={token}"
        send_password_reset_email(
            payload.email, reset_url, settings.PASSWORD_RESET_EXPIRE_MINUTES
        )

    response = {"message": "If the email exists, reset instructions were sent."}
    if settings.APP_ENV == "dev" and token:
        response["reset_token"] = token
    return response


@router.post("/reset-password")
async def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset password using a valid reset token."""
    token_payload = auth_service.verify_password_reset_token(payload.token)
    try:
        user_id = int(token_payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid reset token"
        )
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    auth_service.set_user_password(db, user, payload.new_password)
    return {"message": "Password updated successfully"}


@router.get("/google/url", response_model=GoogleAuthUrlResponse)
async def google_auth_url(
    redirect_uri: str | None = Query(None),
    state: str | None = Query(None),
):
    """Get Google OAuth authorization URL."""
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured",
        )

    redirect = redirect_uri or settings.GOOGLE_OAUTH_REDIRECT_URI
    if not redirect:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="redirect_uri required"
        )

    params = {
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state

    query = httpx.QueryParams(params)
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
    return GoogleAuthUrlResponse(authorization_url=url)


@router.get("/google/callback", response_model=Token)
async def google_callback(
    response: Response,
    code: str = Query(...),
    redirect_uri: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Exchange Google OAuth code for tokens and sign in the user."""
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured",
        )

    redirect = redirect_uri or settings.GOOGLE_OAUTH_REDIRECT_URI
    if not redirect:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="redirect_uri required"
        )

    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect,
            },
        )
        if token_resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google token exchange failed",
            )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token missing"
            )

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google userinfo failed",
            )
        userinfo = userinfo_resp.json()

    email = userinfo.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account missing email",
        )

    user = auth_service.get_user_by_email(db, email)
    if not user:
        full_name = userinfo.get("name") or email.split("@")[0]
        random_password = uuid.uuid4().hex
        user = auth_service.create_user(
            db, email=email, password=random_password, full_name=full_name
        )
        user.is_verified = True
        db.commit()
        db.refresh(user)
    elif not user.is_verified:
        user.is_verified = True
        db.commit()

    payload = build_token_response(db, user)
    # Google OAuth is typically used by browsers; set cookies too.
    _set_auth_cookies(response, payload["access_token"], payload["refresh_token"])
    return payload


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        uuid=current_user.uuid,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        whatsapp_number=current_user.whatsapp_number,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        subscription_tier=current_user.subscription_tier,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat()
        if current_user.last_login
        else None,
        is_admin=is_admin_user(current_user),
    )


@router.get("/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get user profile information."""
    profile = current_user.profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    return {
        "current_role": profile.current_role,
        "experience_level": profile.experience_level,
        "education": profile.education,
        "skills": profile.skills,
        "career_goals": profile.career_goals,
        "preferred_locations": profile.preferred_locations,
        "salary_expectations": profile.salary_expectations,
        "linkedin_url": profile.linkedin_url,
        "portfolio_url": profile.portfolio_url,
        "profile_completeness": profile.profile_completeness,
        "job_alert_preferences": profile.job_alert_preferences,
        "notification_preferences": profile.notification_preferences,
        "updated_at": profile.updated_at.isoformat(),
    }


@router.put("/profile")
async def update_user_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user profile information."""
    profile = current_user.profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    # Update profile fields
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(profile, field):
            setattr(profile, field, value)

    # Recalculate profile completeness
    profile.profile_completeness = calculate_profile_completeness(current_user, profile)

    db.commit()
    db.refresh(profile)

    return {
        "message": "Profile updated successfully",
        "profile_completeness": profile.profile_completeness,
    }


@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user)):
    """Logout user (client should discard tokens)."""
    _clear_auth_cookies(response)
    return {"message": "Successfully logged out"}


def calculate_profile_completeness(user: User, profile: UserProfile) -> float:
    """Calculate profile completeness percentage."""
    total_fields = 10
    completed_fields = 0

    # Basic user info
    if user.full_name:
        completed_fields += 1
    if user.email:
        completed_fields += 1
    if user.phone:
        completed_fields += 1

    # Profile info
    if profile.current_role:
        completed_fields += 1
    if profile.experience_level:
        completed_fields += 1
    if profile.education:
        completed_fields += 1
    if profile.skills:
        completed_fields += 1
    if profile.career_goals:
        completed_fields += 1
    if profile.preferred_locations:
        completed_fields += 1
    if profile.salary_expectations:
        completed_fields += 1

    return (completed_fields / total_fields) * 100
