# public/common/config/app_config.py
"""
Complete application configuration with validation.
Database configuration with SSL support and future-proofing.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator, SecretStr
from .config_types import EnvLogLevel, DbDriver, SslMode, Environment
from .env_config import require_env, get_env
from .logging_config import LoggingConfig
from pathlib import Path


class DatabaseConfig(BaseModel):
    """
    Database configuration with SSL/TLS support.

    Supports both simple (dev) and secure (prod) configurations.
    """

    # Basic connection
    host: str = Field(..., min_length=1)
    port: int = Field(..., gt=0, le=65535)
    name: str = Field(..., min_length=1, description="Database name")
    slow_query_threshold: float = Field(
        ..., description="Threshold for a query to be considered slow"
    )
    # Authentication (keep separate from URL for security)
    username: Optional[str] = Field(default=None, min_length=1)
    password: Optional[SecretStr] = Field(default=None)  # Pydantic hides this in logs

    # Connection pooling
    pool_size: int = Field(..., ge=1, le=100)
    max_overflow: int = Field(..., ge=0, le=100)
    pool_timeout: int = Field(..., ge=1, le=300)
    pool_recycle: int = Field(..., ge=300)  # Min 5 minutes

    # SSL/TLS Configuration
    ssl_mode: Optional[SslMode] = Field(default=None)
    ssl_cert_path: Optional[Path] = Field(default=None)
    ssl_key_path: Optional[Path] = Field(default=None)
    ssl_ca_path: Optional[Path] = Field(default=None)

    # Driver configuration
    driver: DbDriver = Field(...)

    model_config = {"frozen": True}

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate database host."""
        # Allow localhost/127.0.0.1 for development
        if v in ["localhost", "127.0.0.1", "::1"]:
            return v

        # For production, could add additional validation:
        # - Check for internal IP ranges
        # - Verify against allowlist
        # - Require FQDN format

        return v

    @field_validator("ssl_cert_path", "ssl_key_path", "ssl_ca_path")
    @classmethod
    def validate_ssl_paths(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate SSL certificate paths exist."""
        if v is not None and not v.exists():
            raise ValueError(f"SSL file not found: {v}")
        return v

    def get_connection_url(self, include_password: bool = False) -> str:
        """
        Build SQLAlchemy connection URL.

        Args:
            include_password: If True, include password in URL (use for actual connections)
                            If False, mask it (use for logging)

        Returns:
            Database URL string
        """
        if self.username:
            if include_password and self.password:
                password = self.password.get_secret_value()
                auth = f"{self.username}:{password}"
            else:
                auth = f"{self.username}:****"
            url = f"postgresql+{self.driver.value}://{auth}@{self.host}:{self.port}/{self.name}"
        else:
            url = (
                f"postgresql+{self.driver.value}://{self.host}:{self.port}/{self.name}"
            )

        return url

    def requires_ssl(self) -> bool:
        """Check if SSL is required based on configuration."""
        return self.ssl_mode in [
            SslMode.REQUIRE,
            SslMode.VERIFY_CA,
            SslMode.VERIFY_FULL,
        ]

    def to_dict_safe(self) -> dict[str, Any]:
        """Convert to dict with sensitive data masked (safe for logging)."""
        data = self.model_dump()
        if data.get("password"):
            data["password"] = "****"
        return data


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


def load_database_config(environment: Environment) -> Optional[DatabaseConfig]:
    """
    Load database configuration from environment.

    Args:
        environment: Environment enum to determine required vs optional fields

    Environment variables:
    Required:
    - DB_HOST: Database host
    - DB_PORT: Database port
    - DB_NAME: Database name
    - DB_POOL_SIZE: Connection pool size
    - DB_MAX_OVERFLOW: Max overflow connections
    - DB_POOL_TIMEOUT: Pool timeout in seconds
    - DB_POOL_RECYCLE: Pool recycle time in seconds
    - DB_DRIVER: Database driver (asyncpg, psycopg, aiosqlite)

    Optional (dev) / Required (prod):
    - DB_USER: Database username
    - DB_PASSWORD: Database password
    - DB_SSL_MODE: SSL mode

    Optional:
    - DB_SSL_CERT: Path to client certificate
    - DB_SSL_KEY: Path to client key
    - DB_SSL_CA: Path to CA certificate
    """

    # Check if database is configured at all
    host = get_env("DB_HOST")
    if not host:
        return None

    # Required fields (no defaults!)
    port_str = require_env("DB_PORT")
    name = require_env("DB_NAME")
    pool_size_str = require_env("DB_POOL_SIZE")
    max_overflow_str = require_env("DB_MAX_OVERFLOW")
    pool_timeout_str = require_env("DB_POOL_TIMEOUT")
    pool_recycle_str = require_env("DB_POOL_RECYCLE")
    driver_str = require_env("DB_DRIVER")
    slow_query_threshold = float(require_env("SLOW_QUERY_THRESHOLD"))

    # Validate driver enum
    try:
        driver = DbDriver(driver_str)
    except ValueError:
        valid_drivers = [d.value for d in DbDriver]
        raise ValueError(
            f"Invalid DB_DRIVER: {driver_str}. Must be one of: {valid_drivers}"
        )

    username: Optional[str] = None
    password_str: Optional[str] = None
    ssl_mode_str: Optional[str] = None

    # Environment-dependent fields
    if environment.is_production:
        # Production: credentials are REQUIRED
        username = require_env("DB_USER")
        password_str = require_env("DB_PASSWORD")
        ssl_mode_str = require_env("DB_SSL_MODE")
    else:
        # Development: credentials are optional
        username = get_env("DB_USER")
        password_str = get_env("DB_PASSWORD")
        ssl_mode_str = get_env("DB_SSL_MODE")

    # Parse SSL mode if provided
    ssl_mode: Optional[SslMode] = None
    if ssl_mode_str:
        try:
            ssl_mode = SslMode(ssl_mode_str)
        except ValueError:
            valid_modes = [m.value for m in SslMode]
            raise ValueError(
                f"Invalid DB_SSL_MODE: {ssl_mode_str}. Must be one of: {valid_modes}"
            )

    # Parse password to SecretStr if provided
    password: Optional[SecretStr] = None
    if password_str:
        password = SecretStr(password_str)

    # Build SSL paths if provided
    ssl_cert_path: Optional[Path] = None
    ssl_key_path: Optional[Path] = None
    ssl_ca_path: Optional[Path] = None

    ssl_cert = get_env("DB_SSL_CERT")
    if ssl_cert:
        ssl_cert_path = Path(ssl_cert)

    ssl_key = get_env("DB_SSL_KEY")
    if ssl_key:
        ssl_key_path = Path(ssl_key)

    ssl_ca = get_env("DB_SSL_CA")
    if ssl_ca:
        ssl_ca_path = Path(ssl_ca)

    return DatabaseConfig(
        host=host,
        port=int(port_str),
        name=name,
        username=username,
        password=password,
        pool_size=int(pool_size_str),
        max_overflow=int(max_overflow_str),
        pool_timeout=int(pool_timeout_str),
        pool_recycle=int(pool_recycle_str),
        ssl_mode=ssl_mode,
        ssl_cert_path=ssl_cert_path,
        ssl_key_path=ssl_key_path,
        ssl_ca_path=ssl_ca_path,
        driver=driver,
        slow_query_threshold=slow_query_threshold,
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

    env_str = require_env("ENVIRONMENT")

    try:
        environment = Environment(env_str)
    except ValueError:
        valid_envs = [e.value for e in Environment]
        raise ValueError(
            f"Invalid ENVIRONMENT: {env_str}. Must be one of: {valid_envs}"
        )

    return AppConfig(
        app_title=require_env("APP_TITLE"),
        app_version=require_env("APP_VERSION"),
        environment=require_env("ENVIRONMENT"),
        logging=load_logging_config(),
        database=load_database_config(environment),
    )


__all__ = [
    "AppConfig",
    "DatabaseConfig",
    "ApiConfig",
    "load_app_config",
]
