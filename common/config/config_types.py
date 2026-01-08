# public/common/config/config_types.py
"""Configuration type definitions."""
from enum import Enum
import logging


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


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_production(self) -> bool:
        """Check if production environment."""
        return self == Environment.PRODUCTION

    def __str__(self) -> str:
        return self.value


__all__ = ["EnvLogLevel", "Environment"]
