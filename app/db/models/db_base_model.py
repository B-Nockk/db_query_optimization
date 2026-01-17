# public/app/db/db_base_model.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime
from datetime import datetime, timezone
from uuid import uuid4


class DbBaseModel(DeclarativeBase):
    __abstract__ = True  # prevents SQLAlchemy from creating a table for this base

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(tz=timezone.utc),  # always UTC
        nullable=False,
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(tz=timezone.utc),
        onupdate=datetime.now(tz=timezone.utc),  # auto-update on row change
        nullable=False,
    )

    @staticmethod
    def generate_uuid():
        return str(uuid4())

    @staticmethod
    def generate_short_code():
        # Generate UUIDv4
        full_uuid = uuid4()
        # Convert to integer and take modulo to fit 10 digits
        short_code = str(full_uuid.int % 10**10).zfill(10)
        return short_code


__all__ = ["DbBaseModel"]
