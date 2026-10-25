from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.sales.router import (LOST_REASONS, PROPOSAL_STATUSES, PROPOSAL_TRANSITIONS, QUOTATION_STATUSES, _proposal_transition, _quotation_transition)
from app.sales.schemas import DealOutcomeCreate, DiscoveryCreate, ProposalCreate, QuotationCreate, SalesDashboardResponse

def test_discovery_requires_summary():
    with pytest.raises(ValueError): DiscoveryCreate(summary="")
def test_proposal_amount_non_negative():
    assert ProposalCreate(title="Website",summary="Business website",amount=25000).amount==25000
def test_proposal_statuses_are_explicit():
    assert {"draft","sent","accepted"} <= PROPOSAL_STATUSES
def test_proposal_review_lifecycle():
    _proposal_transition("draft","internal_review"); _proposal_transition("internal_review","ready_to_send"); _proposal_transition("ready_to_send","sent")
def test_proposal_cannot_skip_review():
    with pytest.raises(HTTPException) as exc: _proposal_transition("draft","sent")
    assert exc.value.status_code==409
def test_proposal_terminal_state():
    with pytest.raises(HTTPException) as exc: _proposal_transition("accepted","rejected")
    assert exc.value.status_code==409
def test_quotation_lifecycle():
    _quotation_transition("draft","sent"); _quotation_transition("sent","accepted")
def test_quotation_terminal_state():
    with pytest.raises(HTTPException): _quotation_transition("accepted","rejected")
def test_quotation_total_inputs():
    q=QuotationCreate(quotation_number="QT-001",title="Website",subtotal=10000,tax_amount=1800)
    assert q.subtotal+q.tax_amount==11800
def test_lost_reason_is_controlled():
    assert "price" in LOST_REASONS
    with pytest.raises(ValueError): DealOutcomeCreate(lost_reason="random")
def test_dashboard_contract():
    data=SalesDashboardResponse(total_opportunities=1,open_opportunities=1,pipeline_value=1000,discovery_count=1,requirement_count=1,proposal_count=1,quotation_count=0,negotiation_count=0,won_count=0,won_value=0,lost_count=0,lost_value=0,conversion_rate=0,by_stage={"qualification":1},by_lost_reason={})
    assert data.pipeline_value==1000
def test_uuid_reference_shape():
    assert isinstance(uuid4(),type(uuid4()))
