"""Configuration for coordinator service."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Find the .env file relative to the project root.
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Coordinator service settings."""

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    # Server
    coordinator_host: str = "0.0.0.0"
    coordinator_port: int = 8000

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    room_ttl_seconds: int = 3600

    # Enclave service
    enclave_service_url: str = "http://localhost:8001"

    # Environment
    environment: str = "development"


settings = Settings()
