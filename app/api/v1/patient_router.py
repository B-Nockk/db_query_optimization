# app/api/v1/patient_router.py
from fastapi import APIRouter, Depends, status, HTTPException
from app.db.schemas import PatientResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.v1 import PatientService
from app.db import get_db

patient_router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
)


@patient_router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Get patient details",
    description="""
    Fetches full profile for a specific patient.

    **Database Impact:** - Performs a JOIN with the Records table.
    - Expected Query Count: 1
    """,
    responses={
        404: {"description": "Patient not found"},
        500: {"description": "Internal Database Error"},
    },
)
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    service = PatientService(db)

    patient = await service.get_patient_profile(patient_id)

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )

    return patient


__all__ = ["patient_router"]
