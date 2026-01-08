# public/main.py
from fastapi import FastAPI, HTTPException
from datetime import datetime
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from common.config import initialize_config, get_config, is_configured
from common.logger import get_app_logger
from common.api_error import ConfigurationError


load_dotenv()
try:
    initialize_config()
except ConfigurationError as e:
    # Can't use logger yet, but that's OK - this is a fatal startup error
    print(f"FATAL: Configuration error:\n{e}")
    import sys

    sys.exit(1)

config = get_config()
logger = get_app_logger(__name__)

app_title = config.app_title
app_version = config.app_version

app = FastAPI(
    title=app_title,
    version=app_version,
    description=f"Running in {config.environment} environment",
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=config.environment != "production",
        log_level=config.logging.level_value.lower(),
    )
