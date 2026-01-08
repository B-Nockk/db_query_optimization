# public/common/logger.py
"""
Application logger with explicit initialization.

Usage:
    from common.logger import get_app_logger

    logger = get_app_logger()
    logger.info("Application started")
"""
from typing import Any
import structlog

from common.config.structlog_config import get_logger as _get_structlog_logger


class AppLogger:
    """
    Application logger wrapper.

    Provides a type-safe interface to structlog with explicit initialization.
    """

    def __init__(self, name: str = "app"):
        self._name = name
        # Don't use Optional - we guarantee it's set via property
        self._logger_instance: structlog.BoundLogger = None  # type: ignore

    @property
    def _logger(self) -> structlog.BoundLogger:
        """
        Lazy-load logger instance.

        This ensures structlog is configured before first use.
        """
        if not self._logger_instance:
            self._logger_instance = _get_structlog_logger(self._name)
        return self._logger_instance

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._logger.debug(msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._logger.warning(msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(msg, **kwargs)

    def critical(self, msg: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._logger.critical(msg, **kwargs)


def get_app_logger(name: str = "app") -> AppLogger:
    """
    Get application logger instance.

    Args:
        name: Logger name

    Returns:
        AppLogger instance
    """
    return AppLogger(name)


# Convenience instance for simple usage
logger = get_app_logger()

__all__ = ["logger", "AppLogger", "get_app_logger"]
