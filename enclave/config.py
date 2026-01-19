"""Configuration for enclave service."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Find the .env file relative to the project root.
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Enclave service settings."""

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    # Server
    enclave_host: str = "0.0.0.0"
    enclave_port: int = 8001

    # OpenAI
    openai_api_key: str

    # Environment
    environment: str = "development"


settings = Settings()
