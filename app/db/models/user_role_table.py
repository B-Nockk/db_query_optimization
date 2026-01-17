# public/app/db/models/user_role_table.py
from typing import Any, Optional
from sqlalchemy import String, JSON, ForeignKey
from .db_base_model import DbBaseModel
from sqlalchemy.orm import Mapped, mapped_column, relationship


class UserRole(DbBaseModel):
    __tablename__ = "user_roles"

    role_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=DbBaseModel.generate_uuid,
    )

    # Business Key: Stable string for code logic (e.g., 'ADMIN_FULL', 'DOC_STAFF')
    role_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
    )

    role_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Role Hierarchy: Self-referential Foreign Key
    parent_role_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("user_roles.role_id"),
        nullable=True,
    )

    permissions: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Relationship for hierarchy traversal
    sub_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="parent_role",
    )
    parent_role: Mapped[Optional["UserRole"]] = relationship(
        "UserRole",
        remote_side=[role_id],
        back_populates="sub_roles",
    )


__all__ = ["UserRole"]
