# public/common/logger/logger_middleware/logger_middleware.py
"""
Production-grade request logging middleware for FastAPI.
Provides structured logging of all HTTP requests with configurable detail levels.

Usage Example:
    from fastapi import FastAPI
    from common.logger.logger_middleware import RequestLoggingMiddleware

    app = FastAPI()

    # Add middleware - FastAPI creates ONE instance for the app
    app.add_middleware(
        RequestLoggingMiddleware,
        log_details=True,  # Log extended details
        slow_threshold_ms=500,  # Flag requests >500ms
        log_query_params=False,  # Don't log query params (may contain PII)
    )

    # Or use simple functional middleware
    # from starlette.middleware.base import BaseHTTPMiddleware
    # app.middleware("http")(simple_request_logger)
"""

from typing import Callable, Awaitable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import uuid

from ..logger import get_app_logger
from .middleware_types import RequestMetadata, RequestDetails, RequestLogEntry


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request logging.

    **Why a class?**
    - Configuration: Each instance can have different settings (log_details, slow_threshold)
    - State management: Can track metrics, rate limits, sampling
    - Extensibility: Subclass for custom behavior (e.g., different logging per route)
    - Dependency injection: Easier to mock/test
    - Thread-safe: Each request gets its own execution context

    **Singleton vs Instance?**
    - Use instance (NOT singleton) - FastAPI creates one instance per app
    - Multiple apps? Each gets its own middleware instance with own config
    - Thread safety: ASGI handles concurrency, middleware should be stateless

    Usage:
        # Basic usage
        app.add_middleware(RequestLoggingMiddleware)

        # With configuration
        app.add_middleware(
            RequestLoggingMiddleware,
            log_details=True,
            slow_threshold_ms=500
        )

        # Custom subclass for specific routes
        class AuthLoggingMiddleware(RequestLoggingMiddleware):
            async def dispatch(self, request: Request, call_next):
                # Add auth-specific logging
                return await super().dispatch(request, call_next)
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        log_details: bool = True,
        slow_threshold_ms: float = 1000.0,
        log_query_params: bool = True,
        log_client_info: bool = True,
        logger_name: Optional[str] = None,
    ):
        """
        Initialize request logging middleware.

        Args:
            app: ASGI application
            log_details: Whether to log extended details (client IP, headers, etc.)
            slow_threshold_ms: Threshold for flagging slow requests
            log_query_params: Whether to include query parameters (may contain PII)
            log_client_info: Whether to log client IP and User-Agent
            logger_name: Custom logger name (defaults to module name)
        """
        super().__init__(app)
        self.log_details = log_details
        self.slow_threshold_ms = slow_threshold_ms
        self.log_query_params = log_query_params
        self.log_client_info = log_client_info

        # Logger is NOT a singleton - it's a bound logger instance
        # Each middleware instance can have its own logger name
        self.logger = get_app_logger(name=logger_name or __name__, persist=True, track_timing=True)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Process request and log metrics.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timing
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Build log entry
        log_entry = self._build_log_entry(
            request=request,
            response=response,
            duration_ms=duration_ms,
            request_id=request_id,
        )

        # Log with appropriate level
        self._log_request(log_entry)

        # Add request ID to response headers for tracing
        response.headers["X-Request-ID"] = request_id

        return response

    def _build_log_entry(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        request_id: str,
        time_to_first_byte: Optional[float] = None,
    ) -> RequestLogEntry:
        """Build structured log entry from request/response."""
        # Core metadata (always logged)
        metadata = RequestMetadata(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Optional details
        details = None
        if self.log_details:
            details = RequestDetails(
                request_id=request_id,
                client_host=request.client.host if self.log_client_info and request.client else None,
                user_agent=request.headers.get("user-agent") if self.log_client_info else None,
                query_params=dict(request.query_params) if self.log_query_params and request.query_params else None,
                path_params=request.path_params if request.path_params else None,
                content_length=int(response.headers.get("content-length", 0)) or None,
                time_to_first_byte=time_to_first_byte,  # TODO:: add later when you implement it
            )

        return RequestLogEntry(
            metadata=metadata,
            details=details,
        )

    def _log_request(
        self,
        log_entry: RequestLogEntry,
    ) -> None:
        """
        Log request with appropriate level based on status and duration.

        Strategy:
        - ERROR: 5xx responses
        - WARNING: Slow requests or 4xx errors
        - INFO: Successful requests
        """
        # Convert to dict for structured logging
        log_data = log_entry.model_dump(mode="json", exclude_none=True)

        if log_entry.is_error:
            self.logger.error("Request failed with server error", **log_data)
        elif log_entry.is_slow:
            self.logger.warning(f"Slow request detected ({log_entry.metadata.duration_ms}ms)", **log_data)
        elif log_entry.metadata.status_code >= 400:
            self.logger.warning("Request failed with client error", **log_data)
        else:
            self.logger.info("Request completed", **log_data)


# Alternative: Functional middleware for simple cases
async def simple_request_logger(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """
    Simple functional middleware for basic request logging.

    Use this if you don't need configuration or extensibility.
    For production, prefer the class-based RequestLoggingMiddleware.
    """
    logger = get_app_logger(__name__)
    start_time = time.perf_counter()

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )

    return response


__all__ = [
    "RequestLoggingMiddleware",
    "simple_request_logger",
]
