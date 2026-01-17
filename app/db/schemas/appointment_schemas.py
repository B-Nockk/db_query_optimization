from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from ..models import AppointmentStatus
from .patient_schema import PatientResponse
from .doctor_schema import DoctorResponse
from uuid import UUID


class AppointmentBase(BaseModel):
    # Base fields common to all stages
    appointment_date: datetime = Field(..., description="Scheduled UTC date and time")
    notes: Optional[str] = Field(None, max_length=1000)


class AppointmentCreate(AppointmentBase):
    # Required to link the appointment on creation
    patient_id: UUID = Field(..., description="550e8400-e29b-41d4-a716-446655440000")
    doctor_id: UUID = Field(..., description="6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class AppointmentUpdate(BaseModel):
    # Used for rescheduling or updating status/notes
    appointment_date: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    status: AppointmentStatus
    patient_id: UUID
    doctor_id: UUID
    created_at: datetime

    # To get names, use nested related Response schemas:
    patient: PatientResponse
    doctor: DoctorResponse
