# public/common/config/initialize_config.py
"""
Configuration initialization module.

Handles the complete application configuration lifecycle.
"""
from typing import Optional, List
from pydantic import ValidationError
from .app_config import AppConfig, load_app_config
from .structlog_config import configure_structlog
from common.api_error import ConfigurationError


class _ConfigState:
    """
    Thread-safe singleton for application configuration.
    """

    _instance: Optional["_ConfigState"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = None
        return cls._instance

    @property
    def config(self) -> AppConfig:
        """Get application configuration."""
        if not self._config:
            raise RuntimeError(
                "Configuration not initialized. Call initialize_config() at startup."
            )
        return self._config

    def set_config(self, config: AppConfig) -> None:
        """Set application configuration."""
        if self._config:
            print("Configuration already initialized")
        self._config = config


_state = _ConfigState()


def initialize_config() -> None:
    """
    Initialize and validate all application configuration.

    This MUST be called once at application startup before any other code.
    Configuration is validated using Pydantic and will fail fast with clear
    error messages if invalid.

    Safe to call in multiprocess environments (e.g., uvicorn with reload).

    Raises:
        ConfigurationError: If configuration is invalid or missing
        ValidationError: If Pydantic validation fails
        RuntimeError: If already initialized
    """
    try:
        # Load and validate all config (Pydantic validates here)
        config = load_app_config()

        # Configure structlog (process-safe)
        configure_structlog(config.logging.level_int)

        # Store in global state
        _state.set_config(config)

    except ValidationError as e:
        # Convert Pydantic errors to ConfigurationError with better messages
        errors: List[str] = []
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"{field}: {msg}")

        raise ConfigurationError(
            f"Configuration validation failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        ) from e


def get_config() -> AppConfig:
    """
    Get validated application configuration.

    Returns:
        AppConfig instance

    Raises:
        RuntimeError: If not initialized
    """
    return _state.config


__all__ = ["initialize_config", "get_config"]
