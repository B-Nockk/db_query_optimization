# public/app/db/models/appointment_table.py
from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey, Text, Enum as sqlalchemy_Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .db_base_model import DbBaseModel


# 1. Define a standard Python Enum
class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"  # Booked, but not yet time
    CHECKED_IN = "checked_in"  # Patient arrived at clinic
    IN_PROGRESS = "in_progress"  # Patient is with the doctor (clinical encounter)
    COMPLETED = "completed"  # Appointment finished
    CANCELLED = "cancelled"  # Patient/Doctor cancelled
    NO_SHOW = "no_show"  # Appointment time passed without arrival


if TYPE_CHECKING:
    from .patient_table import Patient
    from .doctor_table import Doctor


class Appointment(DbBaseModel):
    __tablename__ = "appointments"

    appointment_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=DbBaseModel.generate_uuid,
    )

    patient_id: Mapped[str] = mapped_column(
        ForeignKey(
            "patients.patient_id"
        ),  # mapped_column handles ForeignKey just like Column did
        nullable=False,
    )

    doctor_id: Mapped[str] = mapped_column(
        ForeignKey("doctors.doctor_id"),
        nullable=False,
    )

    appointment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    status: Mapped[AppointmentStatus] = mapped_column(
        sqlalchemy_Enum(AppointmentStatus, name="appointment_status"),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Mapped[str | None] handles nullable

    # Relationships don't need mapped_column, they use relationship()
    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments")


__all__ = ["Appointment"]
