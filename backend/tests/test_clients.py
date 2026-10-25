from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.clients.router import _validate_agreement_transition, _validate_client_transition, _validate_owner
from app.clients.schemas import (
    AGREEMENT_STATUSES,
    CLIENT_RELATION_TYPES,
    HEALTH_STATUSES,
    ONBOARDING_ITEM_STATUSES,
    AgreementCreate,
    ClientContactCreate,
    ClientCreate,
    ClientDocumentCreate,
    ClientHealthUpdate,
    ClientRelationCreate,
    ClientUpdate,
    OnboardingItemCreate,
    OnboardingItemUpdate,
)


def test_client_conversion_requires_opportunity() -> None:
    payload = ClientCreate(opportunity_id=uuid4())
    assert payload.opportunity_id is not None


def test_client_status_validation_values_are_explicit() -> None:
    assert ClientUpdate(status="onboarding").status == "onboarding"
    assert ClientUpdate(status="active").status == "active"


def test_client_lifecycle_allows_expected_progression() -> None:
    _validate_client_transition("onboarding", "active")
    _validate_client_transition("active", "at_risk")
    _validate_client_transition("at_risk", "inactive")
    _validate_client_transition("inactive", "archived")


def test_client_lifecycle_rejects_invalid_jump_and_reactivation() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_client_transition("onboarding", "at_risk")
    assert exc_info.value.status_code == 409
    with pytest.raises(HTTPException) as exc_info:
        _validate_client_transition("archived", "active")
    assert exc_info.value.status_code == 409


def test_agreement_defaults_to_draft_and_terminal_reopen_is_blocked() -> None:
    payload = AgreementCreate(title="Service Agreement")
    assert payload.status == "draft"
    _validate_agreement_transition("draft", "sent")
    _validate_agreement_transition("sent", "signed")
    with pytest.raises(HTTPException) as exc_info:
        _validate_agreement_transition("signed", "draft")
    assert exc_info.value.status_code == 409


def test_client_owner_validation_rejects_inactive_user() -> None:
    class FakeDb:
        def scalar(self, _statement):
            return type("UserStub", (), {"is_active": False})()

    with pytest.raises(HTTPException) as exc_info:
        _validate_owner(FakeDb(), uuid4(), uuid4())
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Owner must be an active user in the company."


def test_client_ecosystem_vocabularies_are_explicit() -> None:
    assert AGREEMENT_STATUSES == {"draft", "sent", "signed", "expired", "cancelled"}
    assert HEALTH_STATUSES == {"healthy", "watch", "at_risk", "critical"}
    assert ONBOARDING_ITEM_STATUSES == {"pending", "in_progress", "completed", "skipped"}
    assert CLIENT_RELATION_TYPES == {"project", "payment", "communication", "support"}


def test_client_health_payload_is_bounded() -> None:
    assert ClientHealthUpdate(health_status="healthy", health_score=100).health_score == 100
    with pytest.raises(ValueError):
        ClientHealthUpdate(health_status="healthy", health_score=101)


def test_client_workspace_payloads_validate() -> None:
    contact = ClientContactCreate(name="Owner", is_primary=True)
    document = ClientDocumentCreate(title="Signed agreement", document_type="agreement")
    relation = ClientRelationCreate(relation_type="communication", related_entity_id=uuid4(), label="WhatsApp")
    assert contact.is_primary is True
    assert document.status == "active"
    assert relation.relation_type == "communication"


def test_onboarding_item_defaults_to_required_pending() -> None:
    create = OnboardingItemCreate(title="Collect signed agreement")
    update = OnboardingItemUpdate(status="completed")
    assert create.required is True
    assert update.status == "completed"
