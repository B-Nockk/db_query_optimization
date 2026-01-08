# public/common/config/logging_config.py
from dataclasses import dataclass
from .env_config import require_env  # Not get_env!
from .config_types import EnvLogLevel
from common.api_error import ConfigurationError

_default_log_level_env_key = "LOG_LEVEL"


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""

    log_level: EnvLogLevel

    @property
    def level_value(self) -> str:
        """Get string value of log level."""
        return self.log_level.value

    @property
    def level_int(self) -> int:
        """Get numeric log level."""
        return self.log_level.level


def load_logging_config(env_key: str = _default_log_level_env_key) -> LoggingConfig:
    """
    Load logging configuration from environment.

    Args:
        env_key: Environment variable name

    Returns:
        LoggingConfig instance

    Raises:
        ConfigurationError: If LOG_LEVEL is missing or invalid
    """
    env_val = require_env(env_key).upper()

    try:
        return LoggingConfig(log_level=EnvLogLevel(env_val))
    except ValueError as exc:
        valid_levels = ", ".join(level.value for level in EnvLogLevel)
        raise ConfigurationError(f"Invalid {env_key}='{env_val}'. Must be one of: {valid_levels}") from exc


__all__ = [
    "_default_log_level_env_key",
    "LoggingConfig",
    "load_logging_config",
]
