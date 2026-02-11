"""
Application configuration
"""

from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/aifai"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Email configuration
    EMAIL_PROVIDER: str = "smtp"  # "ses" or "smtp"
    EMAIL_FROM: str = "notifications@analyticalfire.com"
    EMAIL_FROM_NAME: str = "AIFAI Platform"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    PLATFORM_URL: str = "https://analyticalfire.com"
    
    # Security alert email (direct email alerts, no SNS)
    SECURITY_ALERT_EMAIL: str = "greg@analyticalinsider.com"
    
    # Visibility: one secret for platform owner to get content sample (no moderator/auditor setup)
    VISIBILITY_SECRET: Optional[str] = None

    # Billing / revenue: enable credit economy; key to record payments (fiat/BTC/manual) and add credits
    REVENUE_ENABLED: bool = False
    BILLING_ADMIN_KEY: Optional[str] = None  # Header X-Billing-Admin-Key to record payments and add credits

    # Webhook configuration
    WEBHOOK_SECRET: str = "change-me-in-production"
    WEBHOOK_TIMEOUT: int = 10  # seconds
    WEBHOOK_MAX_RETRIES: int = 3
    WEBHOOK_RETRY_DELAY: float = 1.0  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
