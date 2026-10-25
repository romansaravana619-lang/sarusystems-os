from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    permission_ids: list[UUID] = Field(default_factory=list)


class PermissionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    description: str | None
