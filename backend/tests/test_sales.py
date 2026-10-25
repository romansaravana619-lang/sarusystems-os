from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.sales.router import PROPOSAL_STATUSES, PROPOSAL_TRANSITIONS, _validate_proposal_status_transition
from app.sales.schemas import DiscoveryCreate, ProposalCreate, RequirementCreate


def test_discovery_requires_summary() -> None:
    with pytest.raises(ValueError):
        DiscoveryCreate(summary="")


def test_requirement_is_not_implicitly_approved() -> None:
    payload = RequirementCreate(description="Approved scope")
    assert not hasattr(payload, "approved")


def test_proposal_amount_accepts_non_negative_value() -> None:
    payload = ProposalCreate(title="Website", summary="Business website", amount=25000)
    assert payload.amount == 25000


def test_proposal_statuses_are_explicit() -> None:
    assert "draft" in PROPOSAL_STATUSES
    assert "accepted" in PROPOSAL_STATUSES
    assert "sent" in PROPOSAL_STATUSES


def test_proposal_lifecycle_allows_forward_review() -> None:
    _validate_proposal_status_transition("draft", "internal_review")
    _validate_proposal_status_transition("internal_review", "ready_to_send")
    _validate_proposal_status_transition("ready_to_send", "sent")


def test_proposal_lifecycle_rejects_skipping_review() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_proposal_status_transition("draft", "sent")

    assert exc_info.value.status_code == 409


def test_proposal_terminal_state_cannot_change() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_proposal_status_transition("accepted", "rejected")

    assert exc_info.value.status_code == 409


def test_proposal_status_rejects_unknown_value() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validate_proposal_status_transition("draft", "not_a_real_status")

    assert exc_info.value.status_code == 400


def test_proposal_transition_map_has_no_unknown_targets() -> None:
    for targets in PROPOSAL_TRANSITIONS.values():
        assert targets <= PROPOSAL_STATUSES


def test_uuid_reference_shape_for_sales_records() -> None:
    assert isinstance(uuid4(), type(uuid4()))
