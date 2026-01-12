# public/common/config/logging_config.py
from dataclasses import dataclass
from .env_config import require_env
from .config_types import EnvLogLevel, EnvLogBackends
from common.api_error import ConfigurationError

_default_log_level_env_key = "LOG_LEVEL"
_default_log_backend_env_key = "LOG_BACKEND"


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""

    log_level: EnvLogLevel
    log_backend: EnvLogBackends

    @property
    def level_value(self) -> str:
        """Get string value of log level."""
        return self.log_level.value

    @property
    def level_int(self) -> int:
        """Get numeric log level."""
        return self.log_level.level


def load_logging_config(
    log_level_env_key: str = _default_log_level_env_key,
    log_backend_env_key: str = _default_log_backend_env_key,
) -> LoggingConfig:
    """
    Load logging configuration from environment.

    Args:
        log_level_env_key: Environment variable name
        log_backend_env_key: Environment variable name

    Returns:
        LoggingConfig instance

    Raises:
        ConfigurationError: If LOG_LEVEL is missing or invalid
    """
    try:
        log_level_val = require_env(log_level_env_key).upper()
        log_backend_val = require_env(log_backend_env_key).lower()

        return LoggingConfig(
            log_level=EnvLogLevel(log_level_val),
            log_backend=EnvLogBackends(log_backend_val),
        )

    except ValueError as exc:
        valid_levels = ", ".join(level.value for level in EnvLogLevel)
        valid_backends = ", ".join(backend.value for backend in EnvLogBackends)

        raise ConfigurationError(
            f"Invalid logging configuration. "
            f"{log_level_env_key} must be one of [{valid_levels}], "
            f"{log_backend_env_key} must be one of [{valid_backends}]"
        ) from exc


__all__ = [
    "_default_log_level_env_key",
    "LoggingConfig",
    "load_logging_config",
]
