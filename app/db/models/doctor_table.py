# public/app/db/models/doctor_table.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .db_base_model import DbBaseModel

if TYPE_CHECKING:
    from .schedules import Schedule
    from .appointment_table import Appointment


class Doctor(DbBaseModel):
    __tablename__ = "doctors"

    doctor_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=DbBaseModel.generate_uuid,
    )

    doctor_code: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        default=DbBaseModel.generate_short_code,
        unique=True,
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False)

    specialty: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # later link to Specialty table

    contact_info: Mapped[str] = mapped_column(Text, nullable=False)

    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule", back_populates="doctor"
    )

    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="doctor"
    )


__all__ = ["Doctor"]
