import os
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file (assuming it's in the project root)
# The current file is at backend/app/core/config.py
# Root is three levels up
env_path = os.path.join(os.path.dirname(__file__), "../../../.env")
load_dotenv(env_path)


class Settings(BaseModel):
    # App Configuration
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))

    # Domain settings
    DOMAIN: str = os.getenv("DOMAIN", "nextstep.co.ke")
    API_DOMAIN: str = os.getenv("API_DOMAIN", "api.nextstep.co.ke")
    WEBSITE_URL: str = os.getenv("WEBSITE_URL", "https://nextstep.co.ke")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.nextstep.co.ke")

    # CORS
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "https://nextstep.co.ke,https://www.nextstep.co.ke,https://api.nextstep.co.ke",
    )

    # Database
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "career_lmi")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))

    @property
    def DATABASE_URL(self) -> str:
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Authentication & Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    # Browser auth cookies (optional; API still supports Bearer tokens).
    AUTH_COOKIE_ACCESS_NAME: str = os.getenv(
        "AUTH_COOKIE_ACCESS_NAME", "nextstep_access"
    )
    AUTH_COOKIE_REFRESH_NAME: str = os.getenv(
        "AUTH_COOKIE_REFRESH_NAME", "nextstep_refresh"
    )
    # Leave blank to avoid host-mismatch in local/test environments.
    AUTH_COOKIE_DOMAIN: str = os.getenv("AUTH_COOKIE_DOMAIN", "")
    AUTH_COOKIE_PATH: str = os.getenv("AUTH_COOKIE_PATH", "/")
    AUTH_COOKIE_SAMESITE: str = os.getenv("AUTH_COOKIE_SAMESITE", "lax")
    AUTH_COOKIE_SECURE: bool = (
        os.getenv(
            "AUTH_COOKIE_SECURE",
            "true"
            if os.getenv("WEBSITE_URL", "http://localhost").startswith("https")
            else "false",
        ).lower()
        == "true"
    )
    ADMIN_EMAILS: str = os.getenv("ADMIN_EMAILS", "")
    ADMIN_API_KEY: Optional[str] = os.getenv(
        "ADMIN_API_KEY"
    )  # For server-to-server admin access
    ADMIN_CONVERSION_ALERT_THRESHOLD: float = float(
        os.getenv("ADMIN_CONVERSION_ALERT_THRESHOLD", "5.0")
    )
    ADMIN_CONVERSION_ALERT_COOLDOWN_HOURS: int = int(
        os.getenv("ADMIN_CONVERSION_ALERT_COOLDOWN_HOURS", "6")
    )
    ADMIN_CONVERSION_ALERT_IN_APP_ENABLED: bool = (
        os.getenv("ADMIN_CONVERSION_ALERT_IN_APP_ENABLED", "true").lower()
        == "true"
    )
    ADMIN_CONVERSION_ALERT_EMAIL_ENABLED: bool = (
        os.getenv("ADMIN_CONVERSION_ALERT_EMAIL_ENABLED", "true").lower()
        == "true"
    )
    ADMIN_CONVERSION_ALERT_WHATSAPP_ENABLED: bool = (
        os.getenv("ADMIN_CONVERSION_ALERT_WHATSAPP_ENABLED", "true").lower()
        == "true"
    )

    # AI & ML Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    # Embeddings
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))

    # Skill Extraction
    SKILL_EXTRACTOR_MODE: str = os.getenv("SKILL_EXTRACTOR_MODE", "skillner")
    SKILLNER_DATA_DIR: str = os.getenv("SKILLNER_DATA_DIR", "")

    # Twilio/WhatsApp
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")
    TWILIO_VALIDATE_WEBHOOK_SIGNATURE: bool = (
        os.getenv("TWILIO_VALIDATE_WEBHOOK_SIGNATURE", "true").lower() == "true"
    )
    # If set, use this exact URL for signature validation; otherwise use request.url.
    TWILIO_WEBHOOK_URL: str = os.getenv("TWILIO_WEBHOOK_URL", "")

    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "true").lower() == "true"
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@nextstep.co.ke")

    # Password reset
    PASSWORD_RESET_URL: str = os.getenv(
        "PASSWORD_RESET_URL",
        f"{os.getenv('WEBSITE_URL', 'http://localhost:5173')}/reset.html",
    )
    PASSWORD_RESET_EXPIRE_MINUTES: int = int(
        os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "30")
    )

    # Google OAuth (auth)
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")

    # Payment Integration
    MPESA_CONSUMER_KEY: Optional[str] = os.getenv("MPESA_CONSUMER_KEY")
    MPESA_CONSUMER_SECRET: Optional[str] = os.getenv("MPESA_CONSUMER_SECRET")
    MPESA_SHORTCODE: Optional[str] = os.getenv("MPESA_SHORTCODE")
    MPESA_PASSKEY: Optional[str] = os.getenv("MPESA_PASSKEY")
    MPESA_CALLBACK_URL: Optional[str] = os.getenv("MPESA_CALLBACK_URL")
    MPESA_WEBHOOK_SECRET: Optional[str] = os.getenv(
        "MPESA_WEBHOOK_SECRET", os.getenv("MPESA_PASSKEY", "")
    )

    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Redis Configuration (for caching and background tasks)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Background Tasks
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
    )

    # File Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB

    # Monitoring & Logging
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Timezone
    TZ: str = os.getenv("TZ", "Africa/Nairobi")

    # Feature Flags
    ENABLE_REAL_TIME_NOTIFICATIONS: bool = (
        os.getenv("ENABLE_REAL_TIME_NOTIFICATIONS", "true").lower() == "true"
    )
    ENABLE_AI_RECOMMENDATIONS: bool = (
        os.getenv("ENABLE_AI_RECOMMENDATIONS", "true").lower() == "true"
    )
    ENABLE_COMPANY_REVIEWS: bool = (
        os.getenv("ENABLE_COMPANY_REVIEWS", "true").lower() == "true"
    )
    ENABLE_SKILL_ASSESSMENTS: bool = (
        os.getenv("ENABLE_SKILL_ASSESSMENTS", "true").lower() == "true"
    )

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Next_KE Career Platform"
    VERSION: str = "2.0.0"
    DESCRIPTION: str = "Advanced Career Search and Advisory Platform for Kenya"

    # Subscription Plans
    BASIC_PLAN_FEATURES: List[str] = [
        "job_search",
        "basic_insights",
        "whatsapp_notifications",
        "career_path_suggestions",
    ]
    PROFESSIONAL_PLAN_FEATURES: List[str] = [
        "ai_cv_optimization",
        "personalized_cover_letters",
        "advanced_career_coaching",
        "priority_job_alerts",
        "salary_negotiation_tips",
        "skill_assessments",
    ]
    ENTERPRISE_PLAN_FEATURES: List[str] = [
        "one_on_one_coaching",
        "interview_preparation",
        "linkedin_optimization",
        "direct_recruiter_connections",
        "custom_job_alerts",
        "company_insights",
    ]

    # LinkedIn Integration
    LINKEDIN_CLIENT_ID: Optional[str] = os.getenv("LINKEDIN_CLIENT_ID")
    LINKEDIN_CLIENT_SECRET: Optional[str] = os.getenv("LINKEDIN_CLIENT_SECRET")

    # Google Calendar Integration
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")

    # Microsoft Calendar Integration
    MICROSOFT_CLIENT_ID: Optional[str] = os.getenv("MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET: Optional[str] = os.getenv("MICROSOFT_CLIENT_SECRET")

    # Integration Feature Flags
    ENABLE_LINKEDIN_INTEGRATION: bool = (
        os.getenv("ENABLE_LINKEDIN_INTEGRATION", "true").lower() == "true"
    )
    ENABLE_CALENDAR_INTEGRATION: bool = (
        os.getenv("ENABLE_CALENDAR_INTEGRATION", "true").lower() == "true"
    )
    ENABLE_ATS_INTEGRATION: bool = (
        os.getenv("ENABLE_ATS_INTEGRATION", "true").lower() == "true"
    )


settings = Settings()
