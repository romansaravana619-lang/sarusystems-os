from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.crm.router import OPPORTUNITY_TRANSITIONS, PROSPECT_TRANSITIONS, _validate_owner, _validate_record_link, _validate_transition
from app.crm.schemas import CommunicationCreate, FollowUpCreate, OpportunityCreate, ProspectCreate, ProspectUpdate


def test_prospect_create_accepts_lead_intelligence_fields() -> None:
    payload = ProspectCreate(name="Anitha Makeup Artist", company_name="Anitha Makeup Artist", email="hello@example.com", source="instagram", industry="Beauty", lead_score=82, qualification_level="HOT", next_action="Call prospect", next_action_at=datetime.now(timezone.utc))
    assert payload.lead_score == 82
    assert payload.qualification_level == "HOT"
    assert payload.industry == "Beauty"


def test_prospect_score_and_qualification_are_bounded() -> None:
    with pytest.raises(ValidationError): ProspectCreate(name="Lead", lead_score=101)
    with pytest.raises(ValidationError): ProspectCreate(name="Lead", qualification_level="INVALID")
    with pytest.raises(ValidationError): ProspectUpdate(qualification_level="INVALID")


def test_prospect_update_accepts_status_for_router_validation() -> None:
    assert ProspectUpdate(status="qualified").status == "qualified"


def test_opportunity_defaults_to_qualification() -> None:
    payload = OpportunityCreate(contact_id=uuid4(), name="Website project")
    assert payload.stage == "qualification"
    assert payload.estimated_value is None


def test_owner_validation_rejects_user_outside_company() -> None:
    class FakeDb:
        def scalar(self, _statement): return None
    with pytest.raises(HTTPException) as exc_info: _validate_owner(FakeDb(), uuid4(), uuid4())
    assert exc_info.value.status_code == 400


def test_owner_validation_rejects_inactive_user() -> None:
    class FakeDb:
        def scalar(self, _statement): return SimpleNamespace(is_active=False)
    with pytest.raises(HTTPException): _validate_owner(FakeDb(), uuid4(), uuid4())


def test_prospect_lifecycle_allows_forward_transition() -> None:
    _validate_transition("new", "contacted", PROSPECT_TRANSITIONS, {"new", "contacted"}, "prospect status")


def test_prospect_lifecycle_rejects_invalid_transition() -> None:
    with pytest.raises(HTTPException) as exc_info: _validate_transition("new", "proposal", PROSPECT_TRANSITIONS, {"new", "contacted", "proposal"}, "prospect status")
    assert exc_info.value.status_code == 409


def test_terminal_won_prospect_cannot_move_forward() -> None:
    with pytest.raises(HTTPException) as exc_info: _validate_transition("won", "lost", PROSPECT_TRANSITIONS, {"won", "lost"}, "prospect status")
    assert exc_info.value.status_code == 409


def test_opportunity_lifecycle_requires_requirement_before_proposal() -> None:
    with pytest.raises(HTTPException) as exc_info: _validate_transition("discovery", "proposal", OPPORTUNITY_TRANSITIONS, {"discovery", "proposal"}, "opportunity stage")
    assert exc_info.value.status_code == 409


def test_opportunity_lifecycle_allows_requirement_to_proposal() -> None:
    _validate_transition("requirement_captured", "proposal", OPPORTUNITY_TRANSITIONS, {"requirement_captured", "proposal"}, "opportunity stage")


def test_communication_requires_prospect_or_contact() -> None:
    class FakeDb:
        def get(self, _model, _id): return None
    with pytest.raises(HTTPException) as exc_info: _validate_record_link(FakeDb(), uuid4(), None, None)
    assert exc_info.value.status_code == 400
    with pytest.raises(ValidationError): CommunicationCreate(channel="whatsapp", summary="")


def test_follow_up_requires_owner_and_due_date() -> None:
    payload = FollowUpCreate(prospect_id=uuid4(), owner_user_id=uuid4(), title="Follow up", due_at=datetime.now(timezone.utc))
    assert payload.title == "Follow up"
    with pytest.raises(ValidationError): FollowUpCreate(prospect_id=uuid4(), title="Missing owner", due_at=datetime.now(timezone.utc))
