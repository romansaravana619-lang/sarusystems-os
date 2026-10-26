from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

PRODUCT_TYPES = {"internal", "client", "saas"}
PRODUCT_STATUSES = {"discovery", "planned", "active", "maintenance", "deprecated", "archived"}
ROADMAP_CATEGORIES = {"feature", "requirement", "bug", "technical_debt", "research"}
ROADMAP_STATUSES = {"backlog", "planned", "in_progress", "blocked", "done", "deferred", "cancelled"}
FEATURE_STATUSES = {"proposed", "planned", "in_progress", "in_review", "released", "deferred", "cancelled"}
PRIORITIES = {"critical", "high", "medium", "low"}
REQUIREMENT_TYPES = {"functional", "non_functional", "security", "performance", "accessibility", "integration"}
REQUIREMENT_STATUSES = {"draft", "in_review", "approved", "implemented", "rejected", "deprecated"}
ISSUE_STATUSES = {"open", "assigned", "in_progress", "fixed", "retest", "verified", "reopened", "closed"}
ISSUE_SEVERITIES = {"critical", "high", "medium", "low"}
RETEST_RESULTS = {"passed", "failed", "partially_passed"}
VERSION_STATUSES = {"planned", "in_development", "testing", "ready", "released", "withdrawn"}
RELEASE_STATUSES = {"planned", "in_preparation", "ready_for_approval", "released", "rolled_back", "cancelled"}
DOCUMENT_TYPES = {"product_overview", "requirements", "architecture", "api", "user_guide", "runbook", "release_notes", "qa", "other"}
DOCUMENT_STATUSES = {"draft", "in_review", "approved", "archived"}
DOCUMENT_VISIBILITY = {"internal", "client", "public"}


def _validate_select(field_name, allowed):
    @field_validator(field_name)
    @classmethod
    def validate(cls, value):
        if value is not None and value not in allowed:
            raise ValueError(f"Invalid {field_name.replace('_', ' ')}.")
        return value
    return validate


class ProductCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=2, max_length=200)
    summary: str | None = None
    product_type: str = "internal"
    lifecycle_status: str = "discovery"
    current_version: str | None = Field(default=None, max_length=80)
    repository_url: str | None = None
    documentation_url: str | None = None
    demo_url: str | None = None
    owner_user_id: UUID | None = None
    notes: str | None = None

    @field_validator("product_type")
    @classmethod
    def valid_type(cls, v):
        if v not in PRODUCT_TYPES: raise ValueError("Invalid product type.")
        return v

    @field_validator("lifecycle_status")
    @classmethod
    def valid_status(cls, v):
        if v not in PRODUCT_STATUSES: raise ValueError("Invalid product lifecycle status.")
        return v


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    summary: str | None = None
    product_type: str | None = None
    lifecycle_status: str | None = None
    current_version: str | None = Field(default=None, max_length=80)
    repository_url: str | None = None
    documentation_url: str | None = None
    demo_url: str | None = None
    owner_user_id: UUID | None = None
    notes: str | None = None

    @field_validator("product_type")
    @classmethod
    def valid_type(cls, v):
        if v is not None and v not in PRODUCT_TYPES: raise ValueError("Invalid product type.")
        return v

    @field_validator("lifecycle_status")
    @classmethod
    def valid_status(cls, v):
        if v is not None and v not in PRODUCT_STATUSES: raise ValueError("Invalid product lifecycle status.")
        return v


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    code: str
    name: str
    summary: str | None
    product_type: str
    lifecycle_status: str
    current_version: str | None
    repository_url: str | None
    documentation_url: str | None
    demo_url: str | None
    owner_user_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RoadmapItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    description: str | None = None
    category: str = "feature"
    status: str = "backlog"
    priority: str = "medium"
    target_version_id: UUID | None = None
    target_date: datetime | None = None
    owner_user_id: UUID | None = None
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in ROADMAP_CATEGORIES: raise ValueError("Invalid roadmap category.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in ROADMAP_STATUSES: raise ValueError("Invalid roadmap status.")
        return v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v not in PRIORITIES: raise ValueError("Invalid priority.")
        return v


class RoadmapItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    description: str | None = None
    category: str | None = None
    status: str | None = None
    priority: str | None = None
    target_version_id: UUID | None = None
    target_date: datetime | None = None
    owner_user_id: UUID | None = None
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v is not None and v not in ROADMAP_CATEGORIES: raise ValueError("Invalid roadmap category.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v is not None and v not in ROADMAP_STATUSES: raise ValueError("Invalid roadmap status.")
        return v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v is not None and v not in PRIORITIES: raise ValueError("Invalid priority.")
        return v


class RoadmapItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    product_id: UUID
    title: str
    description: str | None
    category: str
    status: str
    priority: str
    target_version_id: UUID | None
    target_date: datetime | None
    owner_user_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class FeatureCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=240)
    description: str | None = None
    roadmap_item_id: UUID | None = None
    acceptance_criteria: str | None = None
    status: str = "proposed"
    priority: str = "medium"
    owner_user_id: UUID | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in FEATURE_STATUSES: raise ValueError("Invalid feature status.")
        return v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v not in PRIORITIES: raise ValueError("Invalid priority.")
        return v


class FeatureUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    description: str | None = None
    roadmap_item_id: UUID | None = None
    acceptance_criteria: str | None = None
    status: str | None = None
    priority: str | None = None
    owner_user_id: UUID | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v is not None and v not in FEATURE_STATUSES: raise ValueError("Invalid feature status.")
        return v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v is not None and v not in PRIORITIES: raise ValueError("Invalid priority.")
        return v


class FeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    product_id: UUID
    roadmap_item_id: UUID | None
    code: str
    title: str
    description: str | None
    acceptance_criteria: str | None
    status: str
    priority: str
    owner_user_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RequirementCreate(BaseModel):
    requirement_key: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=240)
    statement: str = Field(min_length=2)
    feature_id: UUID | None = None
    acceptance_criteria: str | None = None
    requirement_type: str = "functional"
    priority: str = "medium"
    status: str = "draft"
    notes: str | None = None

    @field_validator("requirement_type")
    @classmethod
    def valid_type(cls, v):
        if v not in REQUIREMENT_TYPES: raise ValueError("Invalid requirement type.")
        return v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v not in PRIORITIES: raise ValueError("Invalid priority.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in REQUIREMENT_STATUSES: raise ValueError("Invalid requirement status.")
        return v


class RequirementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    statement: str | None = Field(default=None, min_length=2)
    feature_id: UUID | None = None
    acceptance_criteria: str | None = None
    requirement_type: str | None = None
    priority: str | None = None
    status: str | None = None
    notes: str | None = None

    @field_validator("requirement_type")
    @classmethod
    def valid_type(cls, v):
        if v is not None and v not in REQUIREMENT_TYPES: raise ValueError("Invalid requirement type.")
        return v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v is not None and v not in PRIORITIES: raise ValueError("Invalid priority.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v is not None and v not in REQUIREMENT_STATUSES: raise ValueError("Invalid requirement status.")
        return v


class RequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    product_id: UUID
    feature_id: UUID | None
    requirement_key: str
    title: str
    statement: str
    acceptance_criteria: str | None
    requirement_type: str
    priority: str
    status: str
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class IssueCreate(BaseModel):
    issue_key: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=240)
    description: str | None = None
    feature_id: UUID | None = None
    requirement_id: UUID | None = None
    task_id: UUID | None = None
    expected_result: str | None = None
    actual_result: str | None = None
    reproduction_steps: str | None = None
    severity: str = "medium"
    priority: str = "medium"
    status: str = "open"
    assigned_user_id: UUID | None = None
    fix_date: datetime | None = None
    retest_result: str | None = None
    founder_notes: str | None = None
    resolution: str | None = None

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, v):
        if v not in ISSUE_SEVERITIES: raise ValueError("Invalid severity.")
        return v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v not in PRIORITIES: raise ValueError("Invalid priority.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in ISSUE_STATUSES: raise ValueError("Invalid issue status.")
        return v

    @field_validator("retest_result")
    @classmethod
    def valid_retest(cls, v):
        if v is not None and v not in RETEST_RESULTS: raise ValueError("Invalid retest result.")
        return v


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    description: str | None = None
    feature_id: UUID | None = None
    requirement_id: UUID | None = None
    task_id: UUID | None = None
    expected_result: str | None = None
    actual_result: str | None = None
    reproduction_steps: str | None = None
    severity: str | None = None
    priority: str | None = None
    status: str | None = None
    assigned_user_id: UUID | None = None
    fix_date: datetime | None = None
    retest_result: str | None = None
    founder_notes: str | None = None
    resolution: str | None = None

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, v):
        if v is not None and v not in ISSUE_SEVERITIES: raise ValueError("Invalid severity.")
        return v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        if v is not None and v not in PRIORITIES: raise ValueError("Invalid priority.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v is not None and v not in ISSUE_STATUSES: raise ValueError("Invalid issue status.")
        return v

    @field_validator("retest_result")
    @classmethod
    def valid_retest(cls, v):
        if v is not None and v not in RETEST_RESULTS: raise ValueError("Invalid retest result.")
        return v


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    product_id: UUID
    feature_id: UUID | None
    requirement_id: UUID | None
    task_id: UUID | None
    issue_key: str
    title: str
    description: str | None
    expected_result: str | None
    actual_result: str | None
    reproduction_steps: str | None
    severity: str
    priority: str
    status: str
    assigned_user_id: UUID | None
    fix_date: datetime | None
    retest_result: str | None
    founder_notes: str | None
    resolution: str | None
    created_at: datetime
    updated_at: datetime


class VersionCreate(BaseModel):
    version: str = Field(min_length=1, max_length=80)
    name: str | None = None
    status: str = "planned"
    target_release_at: datetime | None = None
    changelog: str | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in VERSION_STATUSES: raise ValueError("Invalid version status.")
        return v


class VersionUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    target_release_at: datetime | None = None
    changelog: str | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v is not None and v not in VERSION_STATUSES: raise ValueError("Invalid version status.")
        return v


class VersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    product_id: UUID
    version: str
    name: str | None
    status: str
    target_release_at: datetime | None
    released_at: datetime | None
    changelog: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ReleaseCreate(BaseModel):
    release_key: str = Field(min_length=2, max_length=100)
    title: str = Field(min_length=2, max_length=240)
    version_id: UUID
    status: str = "planned"
    release_notes: str | None = None
    deployment_url: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in RELEASE_STATUSES: raise ValueError("Invalid release status.")
        return v


class ReleaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    status: str | None = None
    release_notes: str | None = None
    deployment_url: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v is not None and v not in RELEASE_STATUSES: raise ValueError("Invalid release status.")
        return v


class ReleaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    product_id: UUID
    version_id: UUID
    release_key: str
    title: str
    status: str
    release_notes: str | None
    deployment_url: str | None
    released_at: datetime | None
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DocumentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    document_type: str = "technical"
    document_url: str | None = None
    content: str | None = None
    feature_id: UUID | None = None
    version_id: UUID | None = None
    status: str = "draft"
    visibility: str = "internal"
    owner_user_id: UUID | None = None
    notes: str | None = None

    @field_validator("document_type")
    @classmethod
    def valid_type(cls, v):
        if v not in DOCUMENT_TYPES | {"technical"}: raise ValueError("Invalid document type.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in DOCUMENT_STATUSES: raise ValueError("Invalid document status.")
        return v

    @field_validator("visibility")
    @classmethod
    def valid_visibility(cls, v):
        if v not in DOCUMENT_VISIBILITY: raise ValueError("Invalid document visibility.")
        return v


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    document_type: str | None = None
    document_url: str | None = None
    content: str | None = None
    feature_id: UUID | None = None
    version_id: UUID | None = None
    status: str | None = None
    visibility: str | None = None
    owner_user_id: UUID | None = None
    notes: str | None = None

    @field_validator("document_type")
    @classmethod
    def valid_type(cls, v):
        if v is not None and v not in DOCUMENT_TYPES | {"technical"}: raise ValueError("Invalid document type.")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v is not None and v not in DOCUMENT_STATUSES: raise ValueError("Invalid document status.")
        return v

    @field_validator("visibility")
    @classmethod
    def valid_visibility(cls, v):
        if v is not None and v not in DOCUMENT_VISIBILITY: raise ValueError("Invalid document visibility.")
        return v


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    product_id: UUID
    feature_id: UUID | None
    version_id: UUID | None
    title: str
    document_type: str
    document_url: str | None
    content: str | None
    status: str
    visibility: str
    owner_user_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ProductDashboardResponse(BaseModel):
    total_products: int
    active_products: int
    roadmap_items: int
    open_issues: int
    in_progress_features: int
    released_versions: int
    planned_releases: int
    recent_products: list[ProductResponse]
