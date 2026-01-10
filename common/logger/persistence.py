# public/common/logger/persistence.py
"""
Non-blocking log persistence with pluggable backends.

This module handles writing logs without blocking the main application.
Uses a background thread with a queue to ensure <5ms latency for log calls.

Supports multiple backends via LOG_BACKENDS environment variable:
    LOG_BACKENDS=file              # File only (default)
    LOG_BACKENDS=file,datadog      # Multiple backends
"""

import queue
import threading
import time
from typing import Any, Dict, Optional
from .log_backends import get_active_backends


class LogPersistenceHandler:
    """
    Handles non-blocking log persistence to multiple backends.

    Uses a background thread and queue to ensure log calls return immediately.
    Supports pluggable backends (file, datadog, prometheus, etc).
    """

    _instance: Optional["LogPersistenceHandler"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "LogPersistenceHandler":
        """Singleton pattern to ensure single queue/thread."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initialize the persistence handler (called once due to singleton)."""
        if self._initialized:
            return

        self._queue: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=10000)
        self._shutdown_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Metrics
        self._total_logs = 0
        self._failed_logs = 0
        self._total_write_time = 0.0

        self._initialized = True
        self._start_worker()

    def _start_worker(self) -> None:
        """Start the background worker thread."""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return

        self._worker_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="LogPersistenceWorker",
        )
        self._worker_thread.start()

    def _process_queue(self) -> None:
        """Background worker that processes the log queue."""
        while not self._shutdown_event.is_set():
            batch: list[Dict[str, Any]] = []
            try:
                try:
                    # Block for first item with timeout
                    item = self._queue.get(timeout=0.5)
                    batch.append(item)

                    # Grab any additional items without blocking
                    while len(batch) < 100:  # Max batch size
                        try:
                            batch.append(self._queue.get_nowait())
                        except queue.Empty:
                            break

                except queue.Empty:
                    continue

                # Write batch to all backends
                self._write_batch(batch)

                # Mark all items as done
                for _ in batch:
                    self._queue.task_done()

            except Exception as e:
                import sys

                print(f"LogPersistenceWorker error: {e}", file=sys.stderr)
                self._failed_logs += len(batch) if batch else 1

    def _write_batch(self, batch: list[Dict[str, Any]]) -> None:
        """Write a batch of log entries to all active backends."""
        if not batch:
            return

        start_time = time.perf_counter()

        try:
            log_backends = get_active_backends()

            # Write to each backend
            for backend in log_backends:
                for entry in batch:
                    try:
                        backend.write(entry)
                    except Exception as e:
                        import sys

                        print(f"Backend '{backend.name}' write failed: {e}", file=sys.stderr)

            self._total_logs += len(batch)

        except Exception as e:
            import sys

            print(f"Failed to write log batch: {e}", file=sys.stderr)
            self._failed_logs += len(batch)
        finally:
            elapsed = time.perf_counter() - start_time
            self._total_write_time += elapsed

    def enqueue_log(self, log_entry: Dict[str, Any]) -> bool:
        """
        Add a log entry to the persistence queue (non-blocking).

        Args:
            log_entry: Dictionary containing log data.

        Returns:
            True if enqueued successfully, False if queue is full.
        """
        try:
            # Non-blocking put with immediate return
            self._queue.put_nowait(log_entry)
            return True
        except queue.Full:
            import sys

            print("Log queue full, dropping log entry", file=sys.stderr)
            self._failed_logs += 1
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        avg_write_time = self._total_write_time / self._total_logs if self._total_logs > 0 else 0

        return {
            "total_logs": self._total_logs,
            "failed_logs": self._failed_logs,
            "queue_size": self._queue.qsize(),
            "avg_write_time_ms": avg_write_time * 1000,
            "worker_alive": (self._worker_thread.is_alive() if self._worker_thread else False),
        }

    def shutdown(self, timeout: float = 5.0) -> None:
        """
        Gracefully shutdown the persistence handler.

        Args:
            timeout: Maximum time to wait for queue to drain (seconds).
        """
        print("Shutting down log persistence handler...")
        self._shutdown_event.set()

        # Wait for queue to drain
        try:
            self._queue.join()
        except Exception:
            pass

        # Wait for worker thread
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

        print(f"Log persistence shutdown complete. Metrics: {self.get_metrics()}")


# Global singleton instance
_persistence_handler = LogPersistenceHandler()


def persist_log(log_entry: Dict[str, Any]) -> bool:
    """
    Persist a log entry to all active backends (non-blocking).

    This is the main entry point for log persistence. It enqueues the log
    for background processing and returns immediately.

    Args:
        log_entry: Dictionary containing log data

    Returns:
        True if successfully enqueued, False otherwise
    """
    return _persistence_handler.enqueue_log(log_entry)


def get_persistence_metrics() -> Dict[str, Any]:
    """Get performance metrics from the persistence handler."""
    return _persistence_handler.get_metrics()


def shutdown_persistence(timeout: float = 5.0) -> None:
    """Shutdown persistence handler gracefully."""
    _persistence_handler.shutdown(timeout)


__all__ = [
    "persist_log",
    "get_persistence_metrics",
    "shutdown_persistence",
    "LogPersistenceHandler",
]
