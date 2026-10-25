from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CommandCenterUserSummary(BaseModel):
    id: UUID
    full_name: str
    email: str
    is_active: bool
    roles: list[str]


class CommandCenterAuditItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    details: str | None
    created_at: datetime


class CommandCenterResponse(BaseModel):
    user: CommandCenterUserSummary
    attention: dict[str, int]
    counts: dict[str, int]
    recent_activity: list[CommandCenterAuditItem]
