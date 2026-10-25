from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from itertools import pairwise

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.crm.router import OPPORTUNITY_TRANSITIONS, PROSPECT_TRANSITIONS, _validate_owner, _validate_record_link, _validate_transition
from app.crm.schemas import CommunicationCreate, CRMDashboardResponse, FollowUpCreate, OpportunityCreate, ProspectCreate, ProspectUpdate


def test_prospect_create_accepts_operational_outreach_fields() -> None:
    payload = ProspectCreate(name="Anitha Makeup Artist", company_name="Anitha Makeup Artist", email="hello@example.com", source="instagram", industry="Beauty", location="Coimbatore", website="https://example.com", preferred_channel="Instagram", outreach_channel="Instagram", problem_observed="No enquiry flow", potential_service="Professional Website Development", discovery_angle="Improve enquiry conversion", why_selected="Strong local fit", lead_score=82, qualification_level="HOT", next_action="Call prospect", next_action_at=datetime.now(timezone.utc))
    assert payload.lead_score == 82
    assert payload.qualification_level == "HOT"
    assert payload.outreach_channel == "Instagram"
    assert payload.problem_observed == "No enquiry flow"
    assert payload.status == "new"


def test_prospect_status_matches_approved_lifecycle() -> None:
    statuses = ["new", "contacted", "responded", "discovery_scheduled", "discovery_completed", "proposal_sent", "negotiation", "won", "lost", "on_hold"]
    for status in statuses:
        assert ProspectCreate(name="Lead", status=status).status == status
    with pytest.raises(ValidationError): ProspectCreate(name="Lead", status="qualified")


def test_prospect_score_and_qualification_are_bounded() -> None:
    with pytest.raises(ValidationError): ProspectCreate(name="Lead", lead_score=101)
    with pytest.raises(ValidationError): ProspectCreate(name="Lead", qualification_level="INVALID")
    with pytest.raises(ValidationError): ProspectUpdate(qualification_level="INVALID")


def test_prospect_update_accepts_canonical_status() -> None:
    assert ProspectUpdate(status="discovery_scheduled").status == "discovery_scheduled"


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


def test_prospect_lifecycle_follows_approved_sequence() -> None:
    sequence = ["new", "contacted", "responded", "discovery_scheduled", "discovery_completed", "proposal_sent", "negotiation", "won"]
    for current, target in pairwise(sequence):
        _validate_transition(current, target, PROSPECT_TRANSITIONS, {"new", "contacted", "responded", "discovery_scheduled", "discovery_completed", "proposal_sent", "negotiation", "won", "lost", "on_hold"}, "prospect status")


def test_prospect_lifecycle_rejects_invalid_bypass() -> None:
    with pytest.raises(HTTPException) as exc_info: _validate_transition("new", "proposal_sent", PROSPECT_TRANSITIONS, {"new", "contacted", "responded", "proposal_sent"}, "prospect status")
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


def test_dashboard_contract_covers_founder_operating_metrics() -> None:
    payload = CRMDashboardResponse(total_prospects=10, active_prospects=8, qualified_leads=3, outreach_sent=7, replies=2, positive_replies=1, follow_ups_open=4, follow_ups_overdue=1, discovery_calls=2, proposals=1, negotiations=1, won_opportunities=1, pipeline_value=125000, won_value=50000, by_prospect_status={"responded": 4}, by_source={"Google Maps": 5}, by_outreach_channel={"WhatsApp": 4}, by_opportunity_stage={"proposal": 1})
    assert payload.outreach_sent == 7
    assert payload.by_outreach_channel["WhatsApp"] == 4
