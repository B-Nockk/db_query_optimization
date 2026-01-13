# public/common/config/structlog_config.py
"""
Structlog configuration module.
Must be configured once at application startup via configure_structlog().
"""
import sys
import os
import threading
from typing import Optional
import structlog
from rich.traceback import install as install_rich_traceback

# Install Rich tracebacks once
install_rich_traceback(show_locals=True, width=None, extra_lines=3)


class _StructlogState:
    """
    Thread-safe, process-safe singleton for structlog configuration state.

    This prevents race conditions during initialization and handles
    multiprocess scenarios (like uvicorn reload).
    """

    _instance: Optional["_StructlogState"] = None
    _lock = threading.Lock()

    # Declare instance attributes with their types
    _initialized: bool
    _log_level: Optional[int]
    _process_id: Optional[int]

    def __new__(cls) -> "_StructlogState":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-check locking
                    instance = super().__new__(cls)
                    instance._initialized = False
                    instance._log_level = None
                    instance._process_id = None  # Track which process configured
                    cls._instance = instance
        return cls._instance

    @property
    def is_configured(self) -> bool:
        """Check if configured in the CURRENT process."""
        current_pid = os.getpid()
        # If we're in a different process than the one that configured, we're not configured
        return self._initialized and self._process_id == current_pid

    @property
    def log_level(self) -> Optional[int]:
        return self._log_level

    def mark_configured(self, log_level: int) -> None:
        """Mark structlog as configured with given level in this process."""
        with self._lock:
            current_pid = os.getpid()

            # If we're in the same process and already configured, that's an error
            if self._initialized and self._process_id == current_pid:
                if self._log_level == log_level:
                    # Idempotent - same config in same process is OK
                    return
                raise RuntimeError(
                    f"structlog already configured in this process. "
                    f"Current level: {self._log_level}, attempted: {log_level}"
                )

            # New process or first configuration
            self._log_level = log_level
            self._process_id = current_pid
            self._initialized = True

    def reset(self) -> None:
        """Reset state. FOR TESTING ONLY."""
        with self._lock:
            self._initialized = False
            self._log_level = None
            self._process_id = None


_state = _StructlogState()


def configure_structlog(log_level: int) -> None:
    """
    Configure structlog with the specified log level.

    Safe to call in multiprocess environments (e.g., uvicorn with reload).
    Each process will configure structlog independently.

    Args:
        log_level: Numeric logging level (e.g., logging.INFO)

    Raises:
        RuntimeError: If already configured in the same process with different level
    """
    # Check if already configured in THIS process
    if _state.is_configured:
        # Idempotent - allow reconfiguration with same level
        if _state.log_level == log_level:
            return
        raise RuntimeError(
            f"structlog already configured in this process. "
            f"Current level: {_state.log_level}, attempted: {log_level}"
        )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,  # type: ignore[list-item]
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(
                    show_locals=False,
                    width=None,
                    suppress=["starlette", "uvicorn", "fastapi"],
                ),
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    _state.mark_configured(log_level)


def get_logger(name: str = "app") -> structlog.BoundLogger:
    """
    Get a structlog logger instance.

    Args:
        name: Logger name

    Returns:
        Configured structlog logger

    Raises:
        RuntimeError: If structlog hasn't been configured yet in this process
    """
    if not _state.is_configured:
        raise RuntimeError(
            "structlog not configured. "
            "Call configure_structlog() at application startup."
        )
    return structlog.get_logger(name)


def is_configured() -> bool:
    """Check if structlog has been configured in this process."""
    return _state.is_configured


__all__ = [
    "configure_structlog",
    "get_logger",
    "is_configured",
]
