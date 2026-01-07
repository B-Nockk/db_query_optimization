# public/logging/logger.py
from typing import Any
import structlog
from .structlog_config import log


class AppLogger:
    """Centralized logger with Rich formatting"""

    def __init__(self, name: str = "app"):
        self.logger = structlog.get_logger(name)

    def debug(self, msg: str, **kwargs: Any) -> None:
        self.logger.debug(msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        self.logger.info(msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self.logger.warning(msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self.logger.error(msg, **kwargs)

    def critical(self, msg: str, **kwargs: Any) -> None:
        self.logger.critical(msg, **kwargs)


# Convenience instance
logger = AppLogger()

__all__ = ["logger", "AppLogger", "log"]
