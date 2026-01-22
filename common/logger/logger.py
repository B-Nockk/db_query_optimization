# public/common/logger/logger.py
"""
Application logger with explicit initialization and optional persistence.

Usage:
    from common.logger import get_app_logger

    # Basic usage
    logger = get_app_logger()
    logger.info("Application started")

    # With persistence enabled
    logger = get_app_logger(persist=True)
    logger.info("This will be saved to disk")

    # Check performance
    print(logger.get_timing_stats())
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional
import structlog

from common.config.structlog_config import get_logger as _get_structlog_logger
from common.logger.persistence import persist_log


class TimingStats:
    """Track timing statistics for logger performance."""

    def __init__(self) -> None:
        self.total_calls = 0
        self.total_time = 0.0
        self.max_time = 0.0
        self.min_time = float("inf")

    def record(self, elapsed: float) -> None:
        """Record a timing measurement."""
        self.total_calls += 1
        self.total_time += elapsed
        self.max_time = max(self.max_time, elapsed)
        self.min_time = min(self.min_time, elapsed)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics dictionary."""
        avg = self.total_time / self.total_calls if self.total_calls > 0 else 0
        return {
            "total_calls": self.total_calls,
            "avg_time_ms": avg * 1000,
            "max_time_ms": self.max_time * 1000,
            "min_time_ms": self.min_time * 1000 if self.min_time != float("inf") else 0,
        }

    def reset(self) -> None:
        """Reset all statistics."""
        self.total_calls = 0
        self.total_time = 0.0
        self.max_time = 0.0
        self.min_time = float("inf")


class AppLogger:
    """
    Application logger wrapper with optional persistence and timing.

    Provides a type-safe interface to structlog with:
    - Non-blocking log persistence to weekly files
    - Performance timing (<5ms target)
    - Graceful degradation if persistence fails
    """

    def __init__(
        self, name: str = "app", persist: bool = False, track_timing: bool = False
    ) -> None:
        """
        Initialize application logger.

        Args:
            name: Logger name
            persist: Enable log persistence to disk
            track_timing: Enable performance timing measurements
        """
        self._name = name
        self._persist = persist
        self._track_timing = track_timing
        self._logger_instance: Optional[structlog.BoundLogger] = None
        # Fix: Don't set to None if track_timing is True
        self._timing_stats: Optional[TimingStats] = (
            TimingStats() if track_timing else None
        )

    @property
    def _logger(self) -> structlog.BoundLogger:
        """
        Lazy-load logger instance.
        This ensures structlog is configured before first use.
        """
        if self._logger_instance is None:
            self._logger_instance = _get_structlog_logger(self._name)
        return self._logger_instance

    def _log_with_persistence(self, level: str, msg: str, **kwargs: Any) -> None:
        """
        Internal method that handles logging with optional persistence and timing.

        Args:
            level: Log level (debug, info, warning, error, critical)
            msg: Log message
            **kwargs: Additional context to log
        """
        start_time = time.perf_counter() if self._track_timing else None

        try:
            # Log to structlog (console/stderr)
            log_method = getattr(self._logger, level)
            log_method(msg, **kwargs)

            # Persist to disk if enabled
            if self._persist:
                log_entry: Dict[str, Any] = {
                    "timestamp": datetime.now().isoformat(),
                    "level": level.upper(),
                    "logger": self._name,
                    "message": msg,
                    **kwargs,
                }
                persist_log(log_entry)

        finally:
            # Record timing if enabled
            # Fix: Only call record if timing_stats is not None
            if (
                self._track_timing
                and start_time is not None
                and self._timing_stats is not None
            ):
                elapsed = time.perf_counter() - start_time
                self._timing_stats.record(elapsed)

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log_with_persistence("debug", msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log_with_persistence("info", msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log_with_persistence("warning", msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log_with_persistence("error", msg, **kwargs)

    def critical(self, msg: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log_with_persistence("critical", msg, **kwargs)

    def get_timing_stats(self) -> Dict[str, Any]:
        """
        Get timing statistics for this logger.

        Returns:
            Dictionary with timing metrics or error message if timing disabled.
        """
        if self._timing_stats is None:
            return {"error": "Timing tracking not enabled"}
        return self._timing_stats.get_stats()

    def reset_timing_stats(self) -> None:
        """Reset timing statistics."""
        if self._timing_stats is not None:
            self._timing_stats.reset()


def get_app_logger(
    name: str = "app", persist: bool = False, track_timing: bool = False
) -> AppLogger:
    """
    Get application logger instance.

    Args:
        name: Logger name
        persist: Enable log persistence to weekly files
        track_timing: Enable performance timing tracking

    Returns:
        AppLogger instance

    Example:
        >>> logger = get_app_logger(persist=True, track_timing=True)
        >>> logger.info("User logged in", user_id=123)
        >>> print(logger.get_timing_stats())
        {'total_calls': 1, 'avg_time_ms': 0.234, ...}
    """
    return AppLogger(name=name, persist=persist, track_timing=track_timing)


# Convenience instance for simple usage (no persistence by default)
logger = get_app_logger()

__all__ = ["logger", "AppLogger", "get_app_logger"]
