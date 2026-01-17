from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from ..models import DayOfWeek
from uuid import UUID


class ScheduleBase(BaseModel):
    day_of_week: DayOfWeek
    start_time: datetime = Field(..., description="UTC Start time")
    end_time: datetime = Field(..., description="UTC End time")


class ScheduleCreate(ScheduleBase):
    doctor_id: UUID = Field(..., description="The UUID of the doctor")


class ScheduleUpdate(BaseModel):
    day_of_week: Optional[DayOfWeek] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ScheduleResponse(ScheduleBase):
    model_config = ConfigDict(from_attributes=True)

    schedule_id: UUID
    doctor_id: UUID
