# public/main.py
from fastapi import FastAPI
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Union, Annotated
import os

app_title = os.getenv("APP_TITLE") or "DBO"
app_version = os.getenv("APP_VERSION") or "0.1.0"

app = FastAPI(title=app_title or "DB0")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Current system health status")
    timestamp: datetime = Field(..., description="Server time in ISO 8601 format")
    version: str = Field(..., description="Application version")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message describing the failure")
    timestamp: datetime = Field(..., description="Server time when the error occurred")


@app.get(
    "/health",
    response_model=Union[HealthCheckResponse, ErrorResponse],
    responses={
        200: {"description": "System is healthy", "model": HealthCheckResponse},
        503: {"description": "System is unhealthy", "model": ErrorResponse},
    },
)
def check_health() -> Annotated[Union[HealthCheckResponse, ErrorResponse], "API response"]:
    try:
        if not app_version:
            return ErrorResponse(
                error="version not found",
                timestamp=datetime.now(),
            )

        return HealthCheckResponse(status="Healthy", timestamp=datetime.now(), version=app_version)
    except Exception as e:
        return ErrorResponse(
            error=f"Unexpected error: {str(e)}",
            timestamp=datetime.now(),
        )
