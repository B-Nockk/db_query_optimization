# public/app/services/v1/patient_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Patient
from sqlalchemy import select


class PatientService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_patient_profile(self, patient_id: str):
        """
        Fetches a patient.
        Note: We use 'select' explicitly to stay in control of
        what columns are loaded (Optimization!).
        """
        query = (
            select(Patient)
            .where(Patient.patient_id == patient_id)
            .execution_options(logging_token="PatientService.get_patient_profile")
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()


__all__ = ["PatientService"]
