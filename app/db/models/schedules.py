# public/app/db/models/schedules.py
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey, Enum as sqlalchemy_enum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .db_base_model import DbBaseModel


class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class Schedule(DbBaseModel):
    __tablename__ = "schedules"

    schedule_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=DbBaseModel.generate_uuid,
    )
    doctor_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("doctors.doctor_id"),
        nullable=False,
    )
    day_of_week: Mapped[DayOfWeek] = mapped_column(
        sqlalchemy_enum(DayOfWeek, name="day_of_week"),
        nullable=False,
    )  # e.g., "Monday"
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
