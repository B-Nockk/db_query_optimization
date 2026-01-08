# public/common/config/app_config.py
"""
Complete application configuration with validation.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from .config_types import EnvLogLevel
from .env_config import require_env, get_env
from .logging_config import LoggingConfig


class DatabaseConfig(BaseModel):
    """
    Database configuration with validation.
    """

    host: str = Field(..., min_length=1)
    port: int = Field(..., gt=0, le=65535)
    name: str = Field(..., min_length=1)
    pool_size: int = Field(default=10, ge=1, le=100)

    model_config = {"frozen": True}

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """
        Validate database host.
        """
        if v.startswith("localhost") or v.startswith("127.0.0.1"):
            return v
        # TODO:: production host validation will go here
        return v


class ApiConfig(BaseModel):
    """
    API configuration with validation.
    """

    timeout: int = Field(..., gt=0, le=300, description="Request timeout in seconds")
    max_retries: int = Field(..., ge=0, le=10)
    rate_limit: int = Field(..., gt=0)

    model_config = {"frozen": True}


class AppConfig(BaseModel):
    """
    Complete application configuration.

    All configuration is loaded from environment variables and validated
    at startup. Invalid configuration will fail fast with clear error messages.
    """

    app_title: str = Field(..., min_length=1)
    app_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")  # Semantic versioning
    environment: str = Field(..., pattern="^(development|staging|production)$")

    logging: LoggingConfig
    database: Optional[DatabaseConfig] = None
    api: Optional[ApiConfig] = None

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_production_settings(self) -> "AppConfig":
        """
        Validate production-specific requirements.
        """
        if self.environment == "production":
            # In production, require certain configs
            if self.database is None:
                raise ValueError("Database config required in production")
            if self.logging.log_level == EnvLogLevel.DEBUG:
                raise ValueError("DEBUG log level not allowed in production")
        return self


def load_database_config() -> Optional[DatabaseConfig]:
    """
    Load database configuration if present.
    """
    host = get_env("DB_HOST")
    if not host:
        return None

    return DatabaseConfig(
        host=host,
        port=int(require_env("DB_PORT")),
        name=require_env("DB_NAME"),
        pool_size=int(require_env("DB_POOL_SIZE")),
    )


def load_app_config() -> AppConfig:
    """
    Load complete application configuration.

    Returns:
        Validated AppConfig instance

    Raises:
        ValidationError: If configuration is invalid
        ConfigurationError: If required env vars are missing
    """
    from .logging_config import load_logging_config

    return AppConfig(
        app_title=require_env("APP_TITLE"),
        app_version=require_env("APP_VERSION"),
        environment=require_env("ENVIRONMENT"),
        logging=load_logging_config(),
        database=load_database_config(),
    )


__all__ = [
    "AppConfig",
    "DatabaseConfig",
    "ApiConfig",
    "load_app_config",
]
