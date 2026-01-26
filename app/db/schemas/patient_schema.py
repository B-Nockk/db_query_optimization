# public/app/db/schemas/patient_schema.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime, timedelta
from typing import Optional, List
from uuid import UUID


class PatientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    date_of_birth: date
    gender: Optional[str] = Field(None, max_length=10)
    contact_info: str = Field(..., max_length=200)
    medical_history: Optional[str] = Field(None, max_length=500)


class PatientCreate(PatientBase):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def seed_records(
        cls,
        template: dict,
        records: int,
        start_index: int = 0,
        date_interval: int = 0,
        gender_cycle: list[str] = ["Male", "Female"],
    ) -> List["PatientCreate"]:
        result = []
        base_date = template.get("date_of_birth", date.today())
        genders = gender_cycle
        for i in range(start_index, start_index + records):
            record = cls(
                name=f"{template['name']}_{i}",
                date_of_birth=base_date - timedelta(days=(i * date_interval)),
                gender=genders[i % len(genders)],
                contact_info=f"{template['contact_info']} #{i}",
                medical_history=template.get("medical_history"),
            )
            result.append(record)
        return result


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
