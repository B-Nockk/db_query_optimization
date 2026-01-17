# public/app/db/patient_table.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String, Date
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .db_base_model import DbBaseModel

if TYPE_CHECKING:
    from .appointment_table import Appointment


class Patient(DbBaseModel):
    __tablename__ = "patients"
    patient_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=DbBaseModel.generate_uuid,
    )

    patient_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True,
        default=DbBaseModel.generate_short_code,
    )

    # Patient details
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    date_of_birth: Mapped[Date] = mapped_column(
        Date,
        nullable=False,
    )

    gender: Mapped[str] = mapped_column(
        String(10),
    )

    contact_info: Mapped[str] = mapped_column(
        String(200),
    )

    medical_history: Mapped[str] = mapped_column(
        String(500),
    )

    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="patient"
    )


__all__ = ["Patient"]
