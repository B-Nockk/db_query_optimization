# public/common/logger/log_backends/base.py
"""Base classes for log persistence backends."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class LogBackend(ABC):
    """
    Abstract base class for log persistence backends.

    Each backend must implement write() method to handle log entries.
    Backends can be file-based, cloud-based (Datadog), metrics (Prometheus), etc.
    """

    def __init__(self, **config: Any):
        """
        Initialize backend with configuration.

        Args:
            **config: Backend-specific configuration options
        """
        self.config = config

    @abstractmethod
    def write(self, log_entry: Dict[str, Any]) -> bool:
        """
        Write a log entry to this backend.

        Args:
            log_entry: Dictionary containing log data with at minimum:
                - message: str
                - timestamp: str (ISO format)
                - level: str
                Optional fields depend on backend needs.

        Returns:
            True if write succeeded, False otherwise
        """
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance/health metrics for this backend.

        Returns:
            Dictionary with backend-specific metrics
        """
        pass

    def shutdown(self, timeout: float = 5.0) -> None:
        """
        Gracefully shutdown the backend.

        Args:
            timeout: Maximum time to wait for shutdown (seconds)
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for identification."""
        pass


__all__ = ["LogBackend"]
