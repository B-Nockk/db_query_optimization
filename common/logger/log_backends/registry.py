# public/common/logger/log_backends/registry.py
"""
Backend registry for managing multiple log persistence backends.

Configure via LOG_BACKENDS environment variable:
    LOG_BACKENDS=file              # File only (default)
    LOG_BACKENDS=file,datadog      # Multiple backends
    LOG_BACKENDS=datadog           # Datadog only
"""

from typing import Any, Dict, List, Type
from common.config import require_env
from .base import LogBackend
from .file_backend import FileBackend


# Registry of available backend classes
_BACKEND_REGISTRY: Dict[str, Type[LogBackend]] = {
    "file": FileBackend,
}

# Active backend instances
_active_backends: List[LogBackend] = []
_backends_initialized = False


def register_backend(name: str, backend_class: Type[LogBackend]) -> None:
    """
    Register a custom backend class.

    Args:
        name: Backend identifier (e.g., 'datadog', 'prometheus')
        backend_class: Backend class that extends LogBackend

    Example:
        >>> register_backend('datadog', DatadogBackend)
    """
    _BACKEND_REGISTRY[name] = backend_class


def _initialize_backends() -> None:
    """Initialize backends based on LOG_BACKENDS environment variable."""
    global _backends_initialized, _active_backends

    if _backends_initialized:
        return

    # Get backend list from environment (default to 'file')
    backends_str = require_env("LOG_BACKENDS")
    backend_names = [name.strip() for name in backends_str.split(",")]

    for backend_name in backend_names:
        if backend_name not in _BACKEND_REGISTRY:
            import sys

            print(
                f"Warning: Unknown backend '{backend_name}'. "
                f"Available: {', '.join(_BACKEND_REGISTRY.keys())}",
                file=sys.stderr,
            )
            continue

        try:
            backend_class = _BACKEND_REGISTRY[backend_name]
            backend_instance = backend_class()
            _active_backends.append(backend_instance)
            print(f"Initialized log backend: {backend_name}")
        except Exception as e:
            import sys

            print(
                f"Failed to initialize backend '{backend_name}': {e}", file=sys.stderr
            )

    if not _active_backends:
        # Fallback to file backend if none initialized
        print("No backends initialized, falling back to file backend")
        _active_backends.append(FileBackend())

    _backends_initialized = True


def get_active_backends() -> List[LogBackend]:
    """
    Get list of active backend instances.

    Returns:
        List of initialized LogBackend instances
    """
    if not _backends_initialized:
        _initialize_backends()

    return _active_backends


def shutdown_all_backends(timeout: float = 5.0) -> None:
    """
    Shutdown all active backends gracefully.

    Args:
        timeout: Maximum time to wait for each backend shutdown
    """
    for backend in _active_backends:
        try:
            backend.shutdown(timeout)
        except Exception as e:
            import sys

            print(f"Error shutting down backend '{backend.name}': {e}", file=sys.stderr)


def get_all_metrics() -> Dict[str, Any]:
    """
    Get metrics from all active backends.

    Returns:
        Dictionary mapping backend names to their metrics
    """
    return {backend.name: backend.get_metrics() for backend in get_active_backends()}


__all__ = [
    "register_backend",
    "get_active_backends",
    "shutdown_all_backends",
    "get_all_metrics",
]
