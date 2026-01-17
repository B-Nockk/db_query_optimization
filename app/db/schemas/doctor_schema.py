# public/app/db/schemas/doctor_schema.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class DoctorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    specialty: Optional[str] = Field(None, max_length=50)
    contact_info: str = Field(..., max_length=200)


class DoctorCreate(DoctorBase):
    pass


class DoctorResponse(DoctorBase):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: UUID
    doctor_code: str
    created_at: datetime
