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
        slow_query_threshold=500,  # Flag requests >500ms
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
from .request_timer import RequestTimer
from common import request_timer_context_var
import time
import uuid

from ..logger import get_app_logger
from .middleware_types import (
    RequestMetadata,
    RequestDetails,
    RequestLogEntry,
    PerformanceBreakdown,
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request logging.

    **Why a class?**
    - Configuration: Each instance can have different settings (log_details, slow_query_threshold)
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
            slow_query_threshold=500
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
        expose_performance_headers: Optional[bool] = False,
        log_details: bool = True,
        slow_query_threshold: float = 1000.0,
        log_query_params: bool = True,
        log_client_info: bool = True,
        logger_name: Optional[str] = None,
    ):
        """
        Initialize request logging middleware.

        Args:
            app: ASGI application
            log_details: Whether to log extended details (client IP, headers, etc.)
            slow_query_threshold: Threshold for flagging slow requests
            log_query_params: Whether to include query parameters (may contain PII)
            log_client_info: Whether to log client IP and User-Agent
            logger_name: Custom logger name (defaults to module name)
        """
        super().__init__(app)
        self.log_details = log_details
        self.slow_query_threshold = slow_query_threshold
        self.log_query_params = log_query_params
        self.log_client_info = log_client_info
        self.expose_performance_headers = expose_performance_headers

        # Logger is NOT a singleton - it's a bound logger instance
        # Each middleware instance can have its own logger name
        self.logger = get_app_logger(
            name=logger_name or __name__, persist=True, track_timing=True
        )

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
        timer = RequestTimer()
        token = request_timer_context_var.set(timer)
        start_time = time.perf_counter()

        # Extract or Generate unique request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Process request
        try:
            with timer.capture("app"):
                response = await call_next(request)
        finally:
            # CAPTURE TIMINGS BEFORE RESETTING TOKEN
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Extract data from the timer object
            perf_data = PerformanceBreakdown(
                total_ms=round(duration_ms, 2),
                app_logic_ms=round(timer.timings.get("app", 0), 2),
                db_session_total_ms=round(timer.timings.get("db", 0), 2),
                sql_execution_total_ms=round(timer.timings.get("sql", 0), 2),
                query_count=int(timer.timings.get("query_count", 0)),
            )

            request_timer_context_var.reset(token)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Build the header
        timing_header = timer.format_server_timing()
        timing_header += f", total;dur={duration_ms:.2f}"

        # Add request ID to response headers for tracing
        response.headers["X-Request-ID"] = request_id

        # Timing Header if toggle is ON or Router enables it
        expose = self.expose_performance_headers or getattr(
            request.state, "expose_perf", False
        )
        if expose:
            response.headers["Server-Timing"] = timing_header

        # Build log entry
        log_entry = self._build_log_entry(
            request=request,
            response=response,
            duration_ms=duration_ms,
            request_id=request_id,
            perf_data=perf_data,
        )

        # Log with appropriate level
        self._log_request(log_entry)
        return response

    def _build_log_entry(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        request_id: str,
        perf_data: Optional[PerformanceBreakdown] = None,
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
                client_host=(
                    request.client.host
                    if self.log_client_info and request.client
                    else None
                ),
                user_agent=(
                    request.headers.get("user-agent") if self.log_client_info else None
                ),
                query_params=(
                    dict(request.query_params)
                    if self.log_query_params and request.query_params
                    else None
                ),
                path_params=request.path_params if request.path_params else None,
                content_length=int(response.headers.get("content-length", 0)) or None,
                time_to_first_byte=time_to_first_byte,  # TODO:: add later when you implement it
            )

        return RequestLogEntry(
            metadata=metadata,
            details=details,
            performance=perf_data,
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

        if log_entry.is_error:  # type: ignore[truthy-function]
            self.logger.error("Request failed with server error", **log_data)
        elif log_entry.is_slow:
            self.logger.warning(
                f"Slow request detected ({log_entry.metadata.duration_ms}ms)",
                **log_data,
            )
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


# Toggle Dependency for on the fly usage
async def enable_perf_headers(request: Request):
    """
    Dependency to flag that this request should expose performance headers.
    Requires RequestLoggingMiddleware to be active.

    Usage Examples:
        - Router level - All endpoints attached to router
            router = APIRouter(
                prefix="/users",
                tags=["router"],
                dependencies=[Depends(enable_perf_headers)]
            )

        - Specific Route level
            @router.get("/user/{id}", dependencies=[Depends(enable_perf_headers)])
    """
    request.state.expose_perf = True


__all__ = [
    "RequestLoggingMiddleware",
    "simple_request_logger",
    "enable_perf_headers",
]
