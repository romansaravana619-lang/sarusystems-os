from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.crm.router import (
    OPPORTUNITY_TRANSITIONS,
    PROSPECT_TRANSITIONS,
    _validate_owner,
    _validate_transition,
)
from app.crm.schemas import OpportunityCreate, ProspectCreate, ProspectUpdate


def test_prospect_create_accepts_core_lead_data() -> None:
    payload = ProspectCreate(
        name="Anitha Makeup Artist",
        company_name="Anitha Makeup Artist",
        email="hello@example.com",
        source="instagram",
    )

    assert payload.name == "Anitha Makeup Artist"
    assert payload.email == "hello@example.com"
    assert payload.source == "instagram"


def test_prospect_update_accepts_status_for_router_validation() -> None:
    payload = ProspectUpdate(status="qualified")
    assert payload.status == "qualified"


def test_opportunity_defaults_to_qualification() -> None:
    payload = OpportunityCreate(contact_id=uuid4(), name="Website project")
    assert payload.stage == "qualification"
    assert payload.estimated_value is None


def test_owner_validation_rejects_user_outside_company() -> None:
    class FakeDb:
        def scalar(self, _statement):
            return None

    with pytest.raises(HTTPException) as exc_info:
        _validate_owner(FakeDb(), uuid4(), uuid4())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Owner must be an active user in the company."


def test_owner_validation_rejects_inactive_user() -> None:
    class FakeDb:
        def scalar(self, _statement):
            return SimpleNamespace(is_active=False)

    with pytest.raises(HTTPException) as exc_info:
        _validate_owner(FakeDb(), uuid4(), uuid4())

    assert exc_info.value.status_code == 400


def test_prospect_lifecycle_allows_forward_transition() -> None:
    _validate_transition("new", "contacted", PROSPECT_TRANSITIONS, {"new", "contacted"}, "prospect status")


def test_prospect_lifecycle_rejects_invalid_transition() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_transition("new", "proposal", PROSPECT_TRANSITIONS, {"new", "contacted", "proposal"}, "prospect status")

    assert exc_info.value.status_code == 409


def test_terminal_won_prospect_cannot_move_forward() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_transition("won", "lost", PROSPECT_TRANSITIONS, {"won", "lost"}, "prospect status")

    assert exc_info.value.status_code == 409


def test_opportunity_lifecycle_requires_requirement_before_proposal() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_transition(
            "discovery",
            "proposal",
            OPPORTUNITY_TRANSITIONS,
            {"discovery", "proposal"},
            "opportunity stage",
        )

    assert exc_info.value.status_code == 409


def test_opportunity_lifecycle_allows_requirement_to_proposal() -> None:
    _validate_transition(
        "requirement_captured",
        "proposal",
        OPPORTUNITY_TRANSITIONS,
        {"requirement_captured", "proposal"},
        "opportunity stage",
    )
