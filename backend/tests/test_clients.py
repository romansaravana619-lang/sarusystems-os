from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.clients.router import (
    _validate_agreement_transition,
    _validate_client_transition,
    _validate_owner,
)
from app.clients.schemas import AgreementCreate, ClientCreate, ClientUpdate


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


def test_agreement_defaults_to_draft() -> None:
    payload = AgreementCreate(title="Service Agreement")
    assert payload.status == "draft"


def test_agreement_lifecycle_rejects_terminal_reopen() -> None:
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
