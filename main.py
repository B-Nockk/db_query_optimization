# main.py
from fastapi import FastAPI, HTTPException, Request
from datetime import datetime
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from common.config import initialize_config, get_config, is_configured, Environment
from common.logger import get_app_logger
from common.logger.logger_middleware import RequestLoggingMiddleware
from common.api_error import ConfigurationError, AppError
from typing import Any
from app.db import DbManager
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse

load_dotenv()
try:
    initialize_config()
except ConfigurationError as e:
    # Can't use logger yet, but that's OK - this is a fatal startup error
    print(f"FATAL: Configuration error:\n{e}")
    import sys

    sys.exit(1)

config = get_config()
logger = get_app_logger(
    name=__name__,
    track_timing=True,
    persist=True,
)

app_title = config.app_title
app_version = config.app_version


@asynccontextmanager
async def lifespan(app: FastAPI):
    _db_config = config.database
    if not _db_config:
        raise RuntimeError("Database configuration required")

    logger.info(f"{_db_config}")

    db_manager = DbManager.from_config(
        _db_config,
    )
    await db_manager.verify_connection()

    # Ensure migrations are up-to-date (fail fast if not)
    try:
        await db_manager.verify_migrations_current()
        logger.info("✓ All migrations applied")
    except RuntimeError as e:
        logger.error(f"❌ Migration check failed: {e}")
        logger.error("Run 'python scripts/migrate.py' or 'alembic upgrade head'")
        raise

    # Add to state
    app.state.db_manager = db_manager

    yield
    logger.info("shutting down")
    await db_manager.dispose()


app = FastAPI(
    title=app_title,
    version=app_version,
    description=f"Running in {config.environment} environment",
    lifespan=lifespan,
)
app.add_middleware(
    RequestLoggingMiddleware,
    expose_performance_headers=config.environment.lower()
    != Environment.PRODUCTION.value.lower(),
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):

    logger.error(
        f"Domain Error: {exc.code}",
        path=request.url.path,
        error_code=exc.code,
        message=exc.message,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "timestamp": datetime.now().isoformat(),
        },
    )


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Current system health status")
    timestamp: datetime = Field(..., description="Server time in ISO 8601 format")
    version: str = Field(..., description="Application version")
    logging_configured: bool = Field(..., description="Logging configuration status")
    log_level: str = Field(..., description="Application log level")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message describing the failure")
    timestamp: datetime = Field(..., description="Server time when the error occurred")


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    responses={
        200: {"description": "System is healthy", "model": HealthCheckResponse},
        503: {"description": "System is unhealthy", "model": ErrorResponse},
        500: {"description": "Unexpected server error", "model": ErrorResponse},
    },
)
def check_health() -> HealthCheckResponse:
    try:
        if not app_version:
            logger.error("Version not found", endpoint="/health", app_title=app_title)
            err = ErrorResponse(
                error="version not found",
                timestamp=datetime.now(),
            )
            raise HTTPException(
                status_code=503,
                detail=err.model_dump(mode="json"),
            )

        logger.info("Health check passed", version=app_version, endpoint="/health")
        return HealthCheckResponse(
            status="Healthy",
            timestamp=datetime.now(),
            version=app_version,
            logging_configured=is_configured(),
            log_level=get_config().logging.level_value,
        )
    except HTTPException:
        raise
    except Exception as e:
        # exc_info=True will show full traceback with Rich formatting
        logger.critical("Unexpected error in health check", exc_info=True, error=str(e))
        err = ErrorResponse(
            error=f"Unexpected error: {str(e)}",
            timestamp=datetime.now(),
        )
        raise HTTPException(
            status_code=500,
            detail=err.model_dump(mode="json"),
        )


@app.get("/metrics")
async def metrics() -> dict[str, Any]:
    """Get logging performance metrics."""
    from common.logger.persistence import get_persistence_metrics
    from common.logger.log_backends import get_all_metrics

    return {
        "logger": logger.get_timing_stats(),
        "persistence": get_persistence_metrics(),
        "backends": get_all_metrics(),
    }


__all__ = ["app", "config"]
