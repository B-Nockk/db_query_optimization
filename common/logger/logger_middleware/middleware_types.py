# common/logger/logger_middleware/middleware_types.py
"""
Type definitions for request logging middleware.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, computed_field
from common.config import require_env


class PerformanceBreakdown(BaseModel):
    """Breakdown of where time was spent during the request."""

    total_ms: float
    app_logic_ms: float
    db_session_total_ms: float
    sql_execution_total_ms: float
    query_count: int = Field(0, description="Number of SQL queries executed")  # <-- NEW

    # Showcase efficiency
    def _calculate_db_overhead(self) -> float:
        """Calculate DB overhead."""
        return round(
            self.db_session_total_ms - self.sql_execution_total_ms,
            2,
        )

    @property
    # @computed_field
    def db_overhead_ms(self) -> float:
        """Time spent in DB session management (pooling, commits) NOT executing SQL."""
        return self._calculate_db_overhead()


class RequestMetadata(BaseModel):
    """
    Core request metadata - always captured.
    """

    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    path: str = Field(..., description="Request path without query params")
    status_code: int = Field(..., ge=100, le=599, description="HTTP status code")
    duration_ms: float = Field(
        ..., ge=0, description="Request duration in milliseconds"
    )

    model_config = {"frozen": True}

    @computed_field
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
    content_length: Optional[int] = Field(
        None, ge=0, description="Response size in bytes"
    )

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
    performance: Optional[PerformanceBreakdown] = None  # <-- NEW FIELD

    model_config = {"frozen": True}

    # @property
    @computed_field
    def is_slow(self) -> bool:
        """Flag slow requests (>1 second)."""
        return self.metadata.duration_ms > 1000

    # @property
    @computed_field
    def is_error(self) -> bool:
        """Flag error responses (5xx)."""
        return self.metadata.status_code >= 500

    @computed_field
    def optimization_warnings(self) -> list[str]:
        """
        Smart warnings that account for both absolute time and percentages.

        Key insight: On fast requests (<50ms), high DB percentage is normal and healthy.
        Only warn when there's actual optimization potential.
        """
        warns: list[str] = []
        if not self.performance:
            return warns

        slow_query_threshold: float = float(require_env("SLOW_QUERY_THRESHOLD"))
        total_time = float(self.metadata.duration_ms)
        db_time = float(self.performance.db_session_total_ms)
        sql_time = float(self.performance.sql_execution_total_ms)
        db_overhead = float(self.performance.db_overhead_ms)
        query_count = int(self.performance.query_count)

        # ============================================
        # 1. N+1 QUERY DETECTION (Most Important!)
        # ============================================
        # High query count often indicates N+1 problem
        # This is THE most common performance killer
        if query_count > 10:
            warns.append(
                f"🚨 N+1_QUERY_SUSPECTED: {query_count} queries "
                f"(likely missing eager loading)"
            )
        elif query_count > 5:
            warns.append(
                f"⚠️ HIGH_QUERY_COUNT: {query_count} queries "
                f"(consider using selectinload/joinedload)"
            )

        # ============================================
        # 2. ABSOLUTE TIME THRESHOLDS
        # ============================================
        # These matter regardless of percentages

        # Slow SQL execution (actual query time)
        if sql_time > slow_query_threshold:  # 500ms is concerning
            warns.append(
                f"🐌 SLOW_SQL: Query execution took {sql_time:.0f}ms "
                f"(needs indexing or query optimization)"
            )
        elif sql_time > 100:  # 100ms is worth investigating
            warns.append(
                f"⏱️ MODERATE_SQL: Query took {sql_time:.0f}ms "
                f"(check indexes and EXPLAIN plan)"
            )

        # High DB overhead (connection/transaction management)
        # Only warn if it's both HIGH and SLOW
        if db_overhead > (slow_query_threshold / 2) and db_overhead > (
            total_time * 0.3
        ):
            warns.append(
                f"🔌 HIGH_CONNECTION_OVERHEAD: {db_overhead:.0f}ms "
                f"in connection management (check pool settings)"
            )

        # ============================================
        # 3. PERCENTAGE-BASED (Only for slow requests)
        # ============================================
        # For requests >50ms, check if DB is dominating
        # Below 50ms, high DB% is expected and healthy
        if total_time > 50:
            db_percentage = (db_time / total_time) * 100

            # DB taking >80% of a slow request
            if db_percentage > 80 and total_time > 200:
                warns.append(
                    f"📊 DB_DOMINATED_REQUEST: {db_percentage:.0f}% "
                    f"of {total_time:.0f}ms spent in DB "
                    f"({query_count} queries)"
                )

        # ============================================
        # 4. EFFICIENCY INDICATORS (Positive signals)
        # ============================================
        # Add context when things are actually good
        if not warns and total_time < 20 and query_count <= 2:
            # Don't add this as a "warning" - maybe log it separately
            # or return in a different field like "optimization_notes"
            pass

        return warns

    # BONUS: Add a separate computed field for positive signals
    @computed_field
    def performance_notes(self) -> list[str]:
        """
        Positive performance indicators (not warnings).
        Use this to highlight well-optimized requests.
        """
        notes: list[str] = []
        if not self.performance:
            return notes

        total_time = self.metadata.duration_ms
        query_count = self.performance.query_count
        sql_time = self.performance.sql_execution_total_ms

        # Fast and efficient
        if total_time < 20 and query_count <= 2:
            notes.append(
                f"✨ OPTIMAL: {total_time:.1f}ms with {query_count} "
                f"{'query' if query_count == 1 else 'queries'}"
            )

        # Good SQL performance
        if sql_time < 10 and query_count > 0:
            notes.append(f"⚡ FAST_SQL: Queries executed in {sql_time:.1f}ms")

        # Efficient batching (multiple queries but still fast)
        if query_count >= 5 and total_time < 50:
            notes.append(
                f"🎯 EFFICIENT_BATCH: {query_count} queries in {total_time:.1f}ms"
            )

        return notes


__all__ = [
    "RequestMetadata",
    "RequestDetails",
    "RequestLogEntry",
    "PerformanceBreakdown",
]
