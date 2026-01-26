from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select
import uuid
import secrets

from ..db.models import User, UserProfile
from ..db.database import get_db
from ..core.config import settings


def _password_schemes():
    try:
        import bcrypt as _bcrypt  # noqa: F401

        if not getattr(_bcrypt, "__about__", None):
            raise RuntimeError("bcrypt metadata unavailable")
        return ["bcrypt", "pbkdf2_sha256"]
    except Exception:
        return ["pbkdf2_sha256"]


# Password hashing
pwd_context = CryptContext(schemes=_password_schemes(), deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
PASSWORD_RESET_EXPIRE_MINUTES = settings.PASSWORD_RESET_EXPIRE_MINUTES

# Security scheme
# auto_error=False allows get_current_user_optional to work for unauthenticated users
security = HTTPBearer(auto_error=False)


class AuthService:
    def __init__(self):
        self.pwd_context = pwd_context

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return self.pwd_context.hash(password)

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if "sub" in to_encode:
            to_encode["sub"] = str(to_encode["sub"])
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        if "sub" in to_encode:
            to_encode["sub"] = str(to_encode["sub"])
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def create_password_reset_token(self, user: User) -> str:
        """Create a password reset token."""
        expire = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)
        to_encode = {
            "sub": str(user.id),
            "email": user.email,
            "type": "password_reset",
            "exp": expire,
        }
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

    def verify_password_reset_token(self, token: str) -> Dict[str, Any]:
        """Verify password reset token."""
        payload = self.verify_token(token)
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid reset token",
            )
        return payload

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        return db.execute(stmt).scalar_one_or_none()

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    def authenticate_user(
        self, db: Session, email: str, password: str
    ) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = self.get_user_by_email(db, email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_user(
        self,
        db: Session,
        email: str,
        password: str,
        full_name: str,
        phone: Optional[str] = None,
        whatsapp_number: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        # Check if user already exists
        if self.get_user_by_email(db, email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create user
        hashed_password = self.get_password_hash(password)
        user = User(
            uuid=str(uuid.uuid4()),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            phone=phone,
            whatsapp_number=whatsapp_number or phone,
            is_active=True,
            is_verified=False,
            subscription_tier="basic",
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # Create user profile
        profile = UserProfile(
            user_id=user.id,
            profile_completeness=self._calculate_initial_completeness(user),
            job_alert_preferences={
                "enabled": True,
                "frequency": "daily",
                "methods": ["email"],
            },
            notification_preferences={
                "job_alerts": True,
                "career_advice": True,
                "marketing": False,
            },
            privacy_settings={
                "profile_public": False,
                "show_salary_expectations": False,
            },
        )

        db.add(profile)
        db.commit()
        db.refresh(profile)

        return user

    def _calculate_initial_completeness(self, user: User) -> float:
        """Calculate initial profile completeness."""
        completeness = 0.0
        total_fields = 8

        if user.full_name:
            completeness += 1
        if user.email:
            completeness += 1
        if user.phone:
            completeness += 1

        # Other fields will be added when profile is updated
        return (completeness / total_fields) * 100

    def update_last_login(self, db: Session, user: User):
        """Update user's last login timestamp."""
        user.last_login = datetime.utcnow()
        db.commit()

    def set_user_password(self, db: Session, user: User, new_password: str):
        """Update user password."""
        user.hashed_password = self.get_password_hash(new_password)
        db.commit()


# Global auth service instance
auth_service = AuthService()


def is_admin_user(user: User) -> bool:
    admin_emails = {
        email.strip().lower()
        for email in settings.ADMIN_EMAILS.split(",")
        if email.strip()
    }
    if not admin_emails:
        return False
    return user.email.lower() in admin_emails


# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = auth_service.verify_token(token)

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    return user


# Optional dependency for routes that work with or without authentication
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# Dependency to check subscription tier
def require_subscription(required_tier: str = "professional"):
    """Dependency to check if user has required subscription tier."""

    async def check_subscription(
        current_user: User = Depends(get_current_user),
    ) -> User:
        tier_hierarchy = {"basic": 0, "professional": 1, "enterprise": 2}

        user_tier_level = tier_hierarchy.get(current_user.subscription_tier, 0)
        required_tier_level = tier_hierarchy.get(required_tier, 1)

        if user_tier_level < required_tier_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires {required_tier} subscription",
            )

        # Check if subscription is still valid
        if (
            current_user.subscription_expires
            and current_user.subscription_expires < datetime.utcnow()
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Subscription has expired"
            )

        return current_user

    return check_subscription


# Dependency to enforce admin access
def require_admin():
    async def check_admin(current_user: User = Depends(get_current_user)) -> User:
        if not is_admin_user(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return current_user

    return check_admin


# API Key authentication for server-to-server or script access
def verify_api_key(api_key: str) -> bool:
    """
    Verify API key against configured admin API key.
    Uses constant-time comparison to prevent timing attacks.
    """
    configured_key = getattr(settings, "ADMIN_API_KEY", None)
    if not configured_key:
        return False

    # Use constant-time comparison
    return secrets.compare_digest(api_key, configured_key)


async def get_api_key_user(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Authenticate via API key header for admin access.
    Returns a synthetic admin user for API key auth.
    """
    if not x_api_key:
        return None

    if not verify_api_key(x_api_key):
        return None

    # Return synthetic admin user for API key auth
    # This avoids needing a real user account for scripts
    class APIKeyUser:
        id = 0
        uuid = "api-key-admin"
        email = "api-admin@system.local"
        full_name = "API Key Admin"
        is_active = True
        is_verified = True
        subscription_tier = "enterprise"
        subscription_expires = None

    return APIKeyUser()


def require_admin_or_api_key():
    """
    Dependency that allows either JWT admin auth or API key auth.
    Useful for admin endpoints that need to be accessible by both
    logged-in admins and automated scripts.
    """

    async def check_auth(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
        db: Session = Depends(get_db),
    ):
        # Try API key auth first
        if x_api_key:
            if verify_api_key(x_api_key):

                class APIKeyUser:
                    id = 0
                    uuid = "api-key-admin"
                    email = "api-admin@system.local"
                    full_name = "API Key Admin"
                    is_active = True
                    is_verified = True
                    subscription_tier = "enterprise"
                    subscription_expires = None

                return APIKeyUser()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
            )

        # Fall back to JWT auth
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required (Bearer token or X-API-Key header)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await get_current_user(credentials, db)
        if not is_admin_user(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
            )
        return user

    return check_auth
