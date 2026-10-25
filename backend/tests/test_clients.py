from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.clients.router import _validate_owner
from app.clients.schemas import AgreementCreate, ClientCreate, ClientUpdate


def test_client_conversion_requires_opportunity() -> None:
    payload = ClientCreate(opportunity_id=uuid4())
    assert payload.opportunity_id is not None


def test_client_status_validation_values_are_explicit() -> None:
    assert ClientUpdate(status="onboarding").status == "onboarding"
    assert ClientUpdate(status="active").status == "active"


def test_agreement_defaults_to_draft() -> None:
    payload = AgreementCreate(title="Service Agreement")
    assert payload.status == "draft"


def test_client_owner_validation_rejects_inactive_user() -> None:
    class FakeDb:
        def scalar(self, _statement):
            return type("UserStub", (), {"is_active": False})()

    with pytest.raises(HTTPException) as exc_info:
        _validate_owner(FakeDb(), uuid4(), uuid4())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Owner must be an active user in the company."
