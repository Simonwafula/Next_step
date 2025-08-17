import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    # Domain settings
    DOMAIN: str = os.getenv("DOMAIN", "nextstep.co.ke")
    API_DOMAIN: str = os.getenv("API_DOMAIN", "api.nextstep.co.ke")
    WEBSITE_URL: str = os.getenv("WEBSITE_URL", "https://nextstep.co.ke")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.nextstep.co.ke")
    # DB
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "career_lmi")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    # Embeddings
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "stub")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))
    # Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")
    # Timezone
    TZ: str = os.getenv("TZ", "Africa/Nairobi")

settings = Settings()
