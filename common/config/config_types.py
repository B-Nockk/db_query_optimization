# public/common/config/config_types.py
"""Configuration type definitions."""

from enum import Enum
import logging


class EnvBool(str, Enum):
    TRUE = "true"
    FALSE = "false"

    def __str__(self) -> str:
        """Return string value for easy printing."""
        return self.value


class EnvLogLevel(str, Enum):
    """
    Supported log levels.

    Inherits from str so enum values serialize naturally to JSON/strings
    without custom serialization logic.

    Examples:
        >>> EnvLogLevel.INFO
        <EnvLogLevel.INFO: 'INFO'>
        >>> str(EnvLogLevel.INFO)
        'INFO'
        >>> EnvLogLevel.INFO.value
        'INFO'
        >>> json.dumps({"level": EnvLogLevel.INFO})  # Works automatically!
        '{"level": "INFO"}'
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @property
    def level(self) -> int:
        """Get numeric logging level for stdlib logging module."""
        return getattr(logging, self.value)

    def __str__(self) -> str:
        """Return string value for easy printing."""
        return self.value


class EnvLogBackends(str, Enum):
    FILE = "file"
    DATA_DOG = "datadog"

    def __str__(self) -> str:
        """Return string value for easy printing."""
        return self.value


class EnvMetricBackend(str, Enum):
    PROMETHEUS = "prometheus"
    DATADOG = "datadog"

    def __str__(self) -> str:
        return self.value


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_production(self) -> bool:
        """Check if production environment."""
        return self == Environment.PRODUCTION

    @property
    def is_staging(self) -> bool:
        """Check if staging environment."""
        return self == Environment.STAGING

    @property
    def is_development(self) -> bool:
        """Check if development environment."""
        return self == Environment.DEVELOPMENT

    def __str__(self) -> str:
        return self.value


class DbDriver(str, Enum):
    """Supported database drivers."""

    ASYNCPG = "asyncpg"
    PSYCOPG = "psycopg"
    AIOSQLITE = "aiosqlite"


class SslMode(str, Enum):
    """PostgreSQL SSL modes."""

    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"
    VERIFY_CA = "verify-ca"
    VERIFY_FULL = "verify-full"


__all__ = [
    "EnvBool",
    "EnvLogLevel",
    "Environment",
    "EnvLogBackends",
    "EnvMetricBackend",
    "DbDriver",
    "SslMode",
]
