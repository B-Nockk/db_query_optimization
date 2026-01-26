# public/app/db/schemas/doctor_schema.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class DoctorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    specialty: Optional[str] = Field(None, max_length=50)
    contact_info: str = Field(..., max_length=200)


class DoctorCreate(DoctorBase):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def seed_records(
        cls,
        template: dict,
        records: int,
        start_index: int = 0,
    ) -> List["DoctorCreate"]:
        result = []
        for i in range(start_index, start_index + records):
            record = cls(
                name=f"{template['name']}_{i}",
                specialty=template.get("specialty"),
                contact_info=f"{template['contact_info']} #{i}",
            )
            result.append(record)
        return result


class DoctorResponse(DoctorBase):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: UUID
    doctor_code: str
    created_at: datetime
