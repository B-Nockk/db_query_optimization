# public/app/db/models/user_role_schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from uuid import UUID


class UserRoleBase(BaseModel):
    role_code: str = Field(..., min_length=2, max_length=20, pattern=r"^[A-Z0-9_]+$")
    role_name: str = Field(..., min_length=2, max_length=50)
    permissions: dict[str, Any] = Field(default_factory=dict)
    parent_role_id: Optional[UUID] = None


class UserRoleCreate(UserRoleBase):
    pass


class UserRoleResponse(UserRoleBase):
    model_config = ConfigDict(from_attributes=True)

    role_id: UUID
    # Note: Recursive nesting of sub_roles is optional based on UI needs
