from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

PLATFORMS = {"linkedin", "instagram", "facebook", "x"}
STATUSES = {"draft", "ready", "scheduled", "published"}
TRANSITIONS = {"draft": {"ready"}, "ready": {"draft", "scheduled"}, "scheduled": {"ready", "published"}, "published": set()}

class SocialPostCreate(BaseModel):
    platform: str
    post_id: str = Field(min_length=1, max_length=120)
    post_title: str | None = Field(default=None, max_length=240)
    post_content: str | None = None
    alt_text: str | None = None
    creative_url: str | None = None
    external_link: str | None = None
    status: str = "draft"
    post_date: datetime | None = None
    notes: str | None = None
    @field_validator("platform")
    @classmethod
    def valid_platform(cls, v):
        if v not in PLATFORMS: raise ValueError("Invalid social platform")
        return v
    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in STATUSES: raise ValueError("Invalid social post status")
        return v

class SocialPostUpdate(BaseModel):
    post_title: str | None = Field(default=None, max_length=240)
    post_content: str | None = None
    alt_text: str | None = None
    creative_url: str | None = None
    external_link: str | None = None
    status: str | None = None
    post_date: datetime | None = None
    notes: str | None = None
    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v is not None and v not in STATUSES: raise ValueError("Invalid social post status")
        return v

class SocialPostResponse(SocialPostCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime

class SocialDashboard(BaseModel):
    total_posts: int
    drafts: int
    ready: int
    scheduled: int
    published: int
    by_platform: dict[str, int]
    recent_posts: list[SocialPostResponse]
