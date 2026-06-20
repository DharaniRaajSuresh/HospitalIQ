"""
WHAT THIS FILE DOES:
Loads configuration settings from the .env file (like database URL, API keys).
Uses Pydantic to validate that all required settings exist. If you need to add
a new configuration value (e.g., a new API key), you add it here.

For example: GEMINI_API_KEY, DATABASE_URL, SECRET_KEY are all defined here.

HospitalIQ Backend Configuration
Demonstrates: Encapsulation with Pydantic settings
"""

import logging
import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from .env file.
    Demonstrates: Encapsulation via Pydantic BaseSettings
    """

    # Database — must be set via .env or environment variable
    database_url: str = "sqlite:///./hospitaliq.db"
    postgres_user: str = "hospitaliq"
    postgres_password: str = ""
    postgres_db: str = "hospitaliq_db"

    # JWT — must be set via .env in production
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://127.0.0.1:8000/api/v1/auth/google/callback"

    # Gemini AI — must be set via .env to enable AI features
    gemini_api_key: str | None = None

    # CORS
    cors_origins: list[str] = ["http://localhost:8510", "http://127.0.0.1:8510", "http://localhost:8000"]

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # OpenTelemetry
    otlp_endpoint: str | None = None
    service_name: str = "hospitaliq-backend"

    # Rate limiting
    rate_limit_per_hour: int = 1000

    # App
    environment: str = "development"
    debug: bool = True
    backend_port: int = 8000
    frontend_port: int = 8501

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        case_sensitive = False
        extra = "ignore"

    def validate_gemini(self) -> bool:
        """Check if Gemini API key is set."""
        if not self.gemini_api_key or self.gemini_api_key == "your-gemini-api-key-here":
            logging.warning(
                "⚠️  GEMINI_API_KEY not set. AI features will be disabled. "
                "Set GEMINI_API_KEY in .env to enable AI assistant."
            )
            return False
        return True

    def get_db_connection_string(self) -> str:
        """Return PostgreSQL connection string."""
        return self.database_url


# Singleton instance
settings = Settings()
