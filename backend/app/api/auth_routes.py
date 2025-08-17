from datetime import timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from ..db.database import get_db
from ..services.auth_service import auth_service, get_current_user, get_current_user_optional
from ..db.models import User, UserProfile
from ..core.config import settings

router = APIRouter()

# Pydantic models for request/response
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str = None
    whatsapp_number: str = None

class UserResponse(BaseModel):
    id: int
    uuid: str
    email: str
    full_name: str
    phone: str = None
    whatsapp_number: str = None
    is_active: bool
    is_verified: bool
    subscription_tier: str
    created_at: str
    last_login: str = None

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

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        # Create user
        user = auth_service.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            phone=user_data.phone,
            whatsapp_number=user_data.whatsapp_number
        )
        
        # Create tokens
        access_token = auth_service.create_access_token(
            data={"sub": user.id, "email": user.email}
        )
        refresh_token = auth_service.create_refresh_token(
            data={"sub": user.id, "email": user.email}
        )
        
        # Update last login
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
                last_login=user.last_login.isoformat() if user.last_login else None
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login user with email and password."""
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = auth_service.create_access_token(
        data={"sub": user.id, "email": user.email}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": user.id, "email": user.email}
    )
    
    # Update last login
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
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Form(...),
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    try:
        payload = auth_service.verify_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        user = auth_service.get_user_by_id(db, user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        new_access_token = auth_service.create_access_token(
            data={"sub": user.id, "email": user.email}
        )
        new_refresh_token = auth_service.create_refresh_token(
            data={"sub": user.id, "email": user.email}
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
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
                last_login=user.last_login.isoformat() if user.last_login else None
            )
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

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
        last_login=current_user.last_login.isoformat() if current_user.last_login else None
    )

@router.get("/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get user profile information."""
    profile = current_user.profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
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
        "updated_at": profile.updated_at.isoformat()
    }

@router.put("/profile")
async def update_user_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information."""
    profile = current_user.profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
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
        "profile_completeness": profile.profile_completeness
    }

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should discard tokens)."""
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
