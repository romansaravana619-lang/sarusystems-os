from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.products.models import Product, ProductFeature, ProductIssue, ProductRelease, ProductRequirement, ProductRoadmapItem, ProductVersion, ProductDocument
from app.products.router import (
    ISSUE_TRANSITIONS,
    PRODUCT_TRANSITIONS,
    RELEASE_TRANSITIONS,
    ROADMAP_TRANSITIONS,
    VERSION_TRANSITIONS,
    _validate_owner_id,
    _validate_related_task,
)
from app.products.schemas import (
    PRODUCT_TYPES,
    PRODUCT_STATUSES,
    ROADMAP_STATUSES,
    FEATURE_STATUSES,
    REQUIREMENT_STATUSES,
    ISSUE_STATUSES,
    VERSION_STATUSES,
    RELEASE_STATUSES,
    DOCUMENT_STATUSES,
    ProductCreate,
    RoadmapItemCreate,
    FeatureCreate,
    RequirementCreate,
    IssueCreate,
    VersionCreate,
    ReleaseCreate,
    DocumentCreate,
)


def test_product_schema_and_lifecycle_values():
    product = ProductCreate(code="SS-POS-001", name="Saru POS", product_type="internal", lifecycle_status="active")
    assert product.code == "SS-POS-001"
    assert {"internal", "client", "saas"} == PRODUCT_TYPES
    assert "active" in PRODUCT_STATUSES
    assert PRODUCT_TRANSITIONS["archived"] == set()
    with pytest.raises(ValidationError):
        ProductCreate(code="SS", name="Broken", product_type="unknown")
    with pytest.raises(ValidationError):
        ProductCreate(code="SS", name="Broken", lifecycle_status="live")
    with pytest.raises(ValidationError):
        ProductCreate(code="SS-2", name="Bad Product", lifecycle_status="retired")


def test_roadmap_lifecycle_has_terminal_done_and_cancelled_states():
    assert ROADMAP_TRANSITIONS["backlog"] == {"planned", "cancelled"}
    assert "done" in ROADMAP_STATUSES
    assert ROADMAP_TRANSITIONS["done"] == set()


def test_feature_requirement_issue_and_release_workflows_are_explicit():
    assert "in_review" in FEATURE_STATUSES
    assert {"draft", "in_review", "approved", "implemented"} <= REQUIREMENT_STATUSES
    assert ISSUE_TRANSITIONS["fixed"] == {"retest", "in_progress"}
    assert ISSUE_TRANSITIONS["retest"] == {"verified", "reopened", "in_progress"}
    assert VERSION_TRANSITIONS["ready"] == {"released", "testing", "withdrawn"}
    assert RELEASE_TRANSITIONS["ready_for_approval"] == {"released", "in_preparation", "cancelled"}
    assert "approved" in DOCUMENT_STATUSES


def test_product_related_schemas_reject_invalid_select_values():
    with pytest.raises(ValidationError):
        RoadmapItemCreate(title="Roadmap", category="sales")
    with pytest.raises(ValidationError):
        FeatureCreate(code="F-1", title="Feature", status="done")
    with pytest.raises(ValidationError):
        IssueCreate(issue_key="B-1", title="Bug", severity="blocker")
    with pytest.raises(ValidationError):
        VersionCreate(version="v1.1", status="shipped")
    # Document approval is enforced through the approval endpoint, not schema validation.
    assert DocumentCreate(title="Doc", status="approved").status == "approved"


def test_product_models_cover_all_required_module_entities():
    assert Product.__tablename__ == "products"
    assert ProductRoadmapItem.__tablename__ == "product_roadmap_items"
    assert ProductFeature.__tablename__ == "product_features"
    assert ProductRequirement.__tablename__ == "product_requirements"
    assert ProductIssue.__tablename__ == "product_issues"
    assert ProductVersion.__tablename__ == "product_versions"
    assert ProductRelease.__tablename__ == "product_releases"
    assert ProductDocument.__tablename__ == "product_documents"


def test_owner_must_belong_to_same_company():
    company_id = uuid4()
    class DB:
        def scalar(self, statement):
            return None
    with pytest.raises(HTTPException) as error:
        _validate_owner_id(DB(), company_id, uuid4())
    assert error.value.status_code == 400


def test_related_task_must_be_company_scoped_and_cannot_have_conflicting_product_link():
    company_id, product_id = uuid4(), uuid4()
    foreign_task_id = uuid4()
    class DB:
        def scalar(self, statement):
            return None
    with pytest.raises(HTTPException) as error:
        _validate_related_task(DB(), company_id, product_id, foreign_task_id)
    assert error.value.status_code == 400

    linked_task = SimpleNamespace(company_id=company_id, id=uuid4(), project_id=None, product_id=uuid4())
    class LinkedDB:
        def scalar(self, statement):
            return linked_task
    with pytest.raises(HTTPException) as error:
        _validate_related_task(LinkedDB(), company_id, product_id, linked_task.id)
    assert error.value.status_code == 409
