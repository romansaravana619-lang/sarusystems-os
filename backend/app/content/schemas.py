from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTENT_TYPES = {"post", "carousel", "reel", "video", "story", "article", "blog", "email", "case_study", "graphic", "other"}
IDEA_STATUSES = {"idea", "approved", "in_production", "converted", "rejected", "archived"}
PRIORITIES = {"low", "medium", "high", "urgent"}
ASSET_STATUSES = {"draft", "in_review", "revision", "approved", "archived"}
PRODUCTION_STATUSES = {"planned", "in_progress", "review", "revision", "completed", "cancelled"}
PUBLICATION_STATUSES = {"planned", "scheduled", "published", "failed", "cancelled"}
PLATFORMS = {"instagram", "facebook", "linkedin", "youtube", "website", "whatsapp", "email", "other"}

class IdeaCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = None
    content_type: str
    pillar: str | None = None
    audience: str | None = None
    objective: str | None = None
    priority: str = "medium"
    status: str = "idea"
    owner_user_id: UUID | None = None
    @field_validator("content_type")
    @classmethod
    def valid_type(cls, v):
        if v not in CONTENT_TYPES: raise ValueError("Invalid content type")
        return v
    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v not in PRIORITIES: raise ValueError("Invalid priority")
        return v
    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in IDEA_STATUSES: raise ValueError("Invalid idea status")
        return v

class IdeaUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = None
    content_type: str | None = None
    pillar: str | None = None
    audience: str | None = None
    objective: str | None = None
    priority: str | None = None
    status: str | None = None
    owner_user_id: UUID | None = None

class IdeaResponse(IdeaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime

class AssetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    idea_id: UUID | None = None
    asset_type: str
    file_url: str | None = None
    caption: str | None = None
    copy_text: str | None = None
    version: int = Field(default=1, ge=1)
    status: str = "draft"
    owner_user_id: UUID | None = None
    @field_validator("asset_type")
    @classmethod
    def valid_type(cls, v):
        if v not in CONTENT_TYPES: raise ValueError("Invalid asset type")
        return v
    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in ASSET_STATUSES: raise ValueError("Invalid asset status")
        return v

class AssetUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    file_url: str | None = None
    caption: str | None = None
    copy_text: str | None = None
    version: int | None = Field(default=None, ge=1)
    status: str | None = None
    owner_user_id: UUID | None = None

class AssetResponse(AssetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime

class ProductionCreate(BaseModel):
    idea_id: UUID | None = None
    asset_id: UUID | None = None
    producer_user_id: UUID | None = None
    status: str = "planned"
    brief: str | None = None
    due_at: datetime | None = None
    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in PRODUCTION_STATUSES: raise ValueError("Invalid production status")
        return v

class ProductionUpdate(BaseModel):
    asset_id: UUID | None = None
    producer_user_id: UUID | None = None
    status: str | None = None
    brief: str | None = None
    due_at: datetime | None = None

class ProductionResponse(ProductionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    started_at: datetime | None
    completed_at: datetime | None
    revision_count: int
    created_at: datetime
    updated_at: datetime

class PublicationCreate(BaseModel):
    asset_id: UUID
    platform: str
    status: str = "planned"
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    external_reference: str | None = None
    notes: str | None = None
    @field_validator("platform")
    @classmethod
    def valid_platform(cls, v):
        if v not in PLATFORMS: raise ValueError("Invalid publication platform")
        return v
    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in PUBLICATION_STATUSES: raise ValueError("Invalid publication status")
        return v

class PublicationUpdate(BaseModel):
    status: str | None = None
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    external_reference: str | None = None
    notes: str | None = None

class PublicationResponse(PublicationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime

class ContentDashboardResponse(BaseModel):
    ideas: int
    approved_ideas: int
    in_production_ideas: int
    assets: int
    assets_in_review: int
    approved_assets: int
    active_production: int
    revision_production: int
    scheduled_publications: int
    published_publications: int
    overdue_production: int
    by_content_type: dict[str, int]
    by_asset_status: dict[str, int]
    by_platform: dict[str, int]
    recent_publications: list[PublicationResponse]
