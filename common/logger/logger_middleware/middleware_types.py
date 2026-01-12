# public/common/logger/logger_middleware/middleware_types.py
"""
Type definitions for request logging middleware.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, computed_field


class RequestMetadata(BaseModel):
    """
    Core request metadata - always captured.
    """

    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    path: str = Field(..., description="Request path without query params")
    status_code: int = Field(..., ge=100, le=599, description="HTTP status code")
    duration_ms: float = Field(..., ge=0, description="Request duration in milliseconds")

    model_config = {"frozen": True}

    @computed_field
    @property
    def duration_seconds(self) -> float:
        """Duration in seconds for easier reading."""
        return round(self.duration_ms / 1000, 3)


class RequestDetails(BaseModel):
    """
    Extended request details - optional, configurable.
    """

    # Client info
    client_host: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User-Agent header")

    # Request info
    query_params: Optional[Dict[str, Any]] = Field(None, description="Query parameters")
    path_params: Optional[Dict[str, Any]] = Field(None, description="Path parameters")
    request_id: Optional[str] = Field(None, description="Unique request ID")

    # Response info
    content_length: Optional[int] = Field(None, ge=0, description="Response size in bytes")

    # Timing breakdown (for advanced profiling)
    time_to_first_byte: Optional[float] = Field(None, ge=0, description="TTFB in ms")

    model_config = {"frozen": True}


class RequestLogEntry(BaseModel):
    """
    Complete request log entry combining metadata and optional details.

    Use this for structured logging - it serializes cleanly to JSON.
    """

    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: RequestMetadata
    details: Optional[RequestDetails] = None

    model_config = {"frozen": True}

    @computed_field
    @property
    def is_slow(self) -> bool:
        """Flag slow requests (>1 second)."""
        return self.metadata.duration_ms > 1000

    @computed_field
    @property
    def is_error(self) -> bool:
        """Flag error responses (5xx)."""
        return self.metadata.status_code >= 500


__all__ = [
    "RequestMetadata",
    "RequestDetails",
    "RequestLogEntry",
]
