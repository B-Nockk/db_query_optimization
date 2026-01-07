# public/main.py
from fastapi import FastAPI, HTTPException
from datetime import datetime
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
from common.logger import logger

load_dotenv()

app_title = os.getenv("APP_TITLE")
app_version = os.getenv("APP_VERSION")

app = FastAPI(title=app_title or "App title missing")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Current system health status")
    timestamp: datetime = Field(..., description="Server time in ISO 8601 format")
    version: str = Field(..., description="Application version")


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
