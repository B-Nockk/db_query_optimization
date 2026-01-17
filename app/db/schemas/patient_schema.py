# public/app/db/schemas/patient_schema.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional
from uuid import UUID


class PatientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    date_of_birth: date
    gender: Optional[str] = Field(None, max_length=10)
    contact_info: str = Field(..., max_length=200)
    medical_history: Optional[str] = Field(None, max_length=500)


class PatientCreate(PatientBase):
    pass  # Everything in Base is required for creation


class PatientUpdate(BaseModel):
    # All fields optional for PATCH
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    contact_info: Optional[str] = None
    medical_history: Optional[str] = None


class PatientResponse(PatientBase):
    model_config = ConfigDict(
        from_attributes=True
    )  # Tells Pydantic to read SQLAlchemy objects

    patient_id: UUID
    patient_code: str
    created_at: datetime
    updated_at: datetime
