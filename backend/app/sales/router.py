from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.crm.router import OPPORTUNITY_TRANSITIONS
from app.crm.schemas import OPPORTUNITY_STAGES
from app.sales.models import DealOutcome, Discovery, Negotiation, Proposal, Quotation, Requirement
from app.sales.schemas import (DealOutcomeCreate, DealResponse, DiscoveryCreate, DiscoveryResponse, NegotiationCreate, NegotiationResponse, NegotiationUpdate, ProposalCreate, ProposalResponse, ProposalUpdate, QuotationCreate, QuotationResponse, QuotationUpdate, RequirementCreate, RequirementResponse, SalesDashboardResponse)
from app.shared.models import AuditLog, Opportunity, User

router = APIRouter(prefix="/sales", tags=["sales"])
PROPOSAL_STATUSES={"draft","internal_review","ready_to_send","sent","viewed","negotiation","accepted","rejected","expired"}
PROPOSAL_TRANSITIONS={"draft":{"internal_review"},"internal_review":{"draft","ready_to_send"},"ready_to_send":{"internal_review","sent"},"sent":{"viewed","negotiation","accepted","rejected","expired"},"viewed":{"negotiation","accepted","rejected","expired"},"negotiation":{"accepted","rejected","expired"},"accepted":set(),"rejected":set(),"expired":set()}
QUOTATION_STATUSES={"draft","sent","accepted","rejected","expired"}
QUOTATION_TRANSITIONS={"draft":{"sent"},"sent":{"accepted","rejected","expired"},"accepted":set(),"rejected":set(),"expired":set()}
NEGOTIATION_STATUSES={"open","won","lost","closed"}
LOST_REASONS={"price","budget","timing","competitor","scope_mismatch","no_response","not_a_fit","other"}

def _opportunity(db, company_id, opportunity_id):
    opportunity=db.get(Opportunity,opportunity_id)
    if opportunity is None or opportunity.company_id!=company_id: raise HTTPException(404,"Opportunity not found.")
    return opportunity

def _move_opportunity(db, opportunity, target):
    if target not in OPPORTUNITY_STAGES or target==opportunity.stage: return
    if target not in OPPORTUNITY_TRANSITIONS.get(opportunity.stage,set()): raise HTTPException(409,f"Invalid opportunity stage transition: {opportunity.stage} -> {target}.")
    opportunity.stage=target

def _proposal_transition(current,target):
    if target not in PROPOSAL_STATUSES: raise HTTPException(400,"Invalid proposal status.")
    if target!=current and target not in PROPOSAL_TRANSITIONS.get(current,set()): raise HTTPException(409,f"Invalid proposal status transition: {current} -> {target}.")
def _quotation_transition(current,target):
    if target not in QUOTATION_STATUSES: raise HTTPException(400,"Invalid quotation status.")
    if target!=current and target not in QUOTATION_TRANSITIONS.get(current,set()): raise HTTPException(409,f"Invalid quotation status transition: {current} -> {target}.")

def _audit(db,user,action,entity,entity_id,details=None): db.add(AuditLog(actor_user_id=user.id,action=action,entity_type=entity,entity_id=str(entity_id),details=details))

@router.get("/dashboard",response_model=SalesDashboardResponse)
def dashboard(current_user:User=Depends(require_permission("sales.dashboard.view")),db:Session=Depends(get_db)):
    opps=list(db.scalars(select(Opportunity).where(Opportunity.company_id==current_user.company_id)).all())
    discoveries=db.scalars(select(Discovery).join(Opportunity,Discovery.opportunity_id==Opportunity.id).where(Opportunity.company_id==current_user.company_id)).all()
    requirements=db.scalars(select(Requirement).join(Opportunity,Requirement.opportunity_id==Opportunity.id).where(Opportunity.company_id==current_user.company_id)).all()
    proposals=db.scalars(select(Proposal).join(Opportunity,Proposal.opportunity_id==Opportunity.id).where(Opportunity.company_id==current_user.company_id)).all()
    quotations=db.scalars(select(Quotation).join(Opportunity,Quotation.opportunity_id==Opportunity.id).where(Opportunity.company_id==current_user.company_id)).all()
    negotiations=db.scalars(select(Negotiation).join(Opportunity,Negotiation.opportunity_id==Opportunity.id).where(Opportunity.company_id==current_user.company_id)).all()
    outcomes=db.scalars(select(DealOutcome).join(Opportunity,DealOutcome.opportunity_id==Opportunity.id).where(Opportunity.company_id==current_user.company_id)).all()
    open_opps=[o for o in opps if o.stage not in {"won","lost"}]
    won=[o for o in opps if o.stage=="won"]; lost=[o for o in opps if o.stage=="lost"]
    by_stage={stage:sum(1 for o in opps if o.stage==stage) for stage in OPPORTUNITY_STAGES}
    by_reason={reason:sum(1 for x in outcomes if x.outcome=="lost" and x.lost_reason==reason) for reason in LOST_REASONS}
    total=len(opps); conversion=round((len(won)/total)*100,2) if total else 0
    return SalesDashboardResponse(total_opportunities=total,open_opportunities=len(open_opps),pipeline_value=float(sum((o.estimated_value or 0) for o in open_opps)),discovery_count=len(discoveries),requirement_count=len(requirements),proposal_count=len(proposals),quotation_count=len(quotations),negotiation_count=len(negotiations),won_count=len(won),won_value=float(sum((o.estimated_value or 0) for o in won)),lost_count=len(lost),lost_value=float(sum((o.estimated_value or 0) for o in lost)),conversion_rate=conversion,by_stage=by_stage,by_lost_reason=by_reason)

@router.get("/opportunities/{opportunity_id}/discoveries",response_model=list[DiscoveryResponse])
def list_discoveries(opportunity_id:UUID,current_user:User=Depends(require_permission("sales.discovery.view")),db:Session=Depends(get_db)): _opportunity(db,current_user.company_id,opportunity_id); return list(db.scalars(select(Discovery).where(Discovery.opportunity_id==opportunity_id).order_by(Discovery.created_at.desc())).all())
@router.post("/opportunities/{opportunity_id}/discoveries",response_model=DiscoveryResponse,status_code=201)
def create_discovery(opportunity_id:UUID,payload:DiscoveryCreate,current_user:User=Depends(require_permission("sales.discovery.create")),db:Session=Depends(get_db)):
    opportunity=_opportunity(db,current_user.company_id,opportunity_id)
    if opportunity.stage!="discovery": _move_opportunity(db,opportunity,"discovery")
    record=Discovery(opportunity_id=opportunity.id,created_by_user_id=current_user.id,**payload.model_dump()); db.add(record); db.flush(); _audit(db,current_user,"discovery.create","Discovery",record.id); db.commit(); db.refresh(record); return record
@router.get("/opportunities/{opportunity_id}/requirements",response_model=list[RequirementResponse])
def list_requirements(opportunity_id:UUID,current_user:User=Depends(require_permission("sales.requirements.view")),db:Session=Depends(get_db)): _opportunity(db,current_user.company_id,opportunity_id); return list(db.scalars(select(Requirement).where(Requirement.opportunity_id==opportunity_id).order_by(Requirement.created_at.desc())).all())
@router.post("/opportunities/{opportunity_id}/requirements",response_model=RequirementResponse,status_code=201)
def create_requirement(opportunity_id:UUID,payload:RequirementCreate,current_user:User=Depends(require_permission("sales.requirements.create")),db:Session=Depends(get_db)):
    opportunity=_opportunity(db,current_user.company_id,opportunity_id)
    if opportunity.stage not in {"discovery","requirement_captured"}: raise HTTPException(409,"Requirements can only be captured after discovery.")
    if opportunity.stage=="discovery": _move_opportunity(db,opportunity,"requirement_captured")
    record=Requirement(opportunity_id=opportunity.id,created_by_user_id=current_user.id,approved=False,**payload.model_dump()); db.add(record); db.flush(); _audit(db,current_user,"requirement.create","Requirement",record.id); db.commit(); db.refresh(record); return record
@router.post("/requirements/{requirement_id}/approve",response_model=RequirementResponse)
def approve_requirement(requirement_id:UUID,current_user:User=Depends(require_permission("sales.requirements.approve")),db:Session=Depends(get_db)):
    record=db.get(Requirement,requirement_id)
    if record is None: raise HTTPException(404,"Requirement not found.")
    opportunity=_opportunity(db,current_user.company_id,record.opportunity_id)
    if record.approved: return record
    record.approved=True; record.approved_by_user_id=current_user.id; record.approved_at=datetime.now(timezone.utc); _audit(db,current_user,"requirement.approve","Requirement",record.id,f"Opportunity {opportunity.id}"); db.commit(); db.refresh(record); return record
@router.get("/opportunities/{opportunity_id}/proposals",response_model=list[ProposalResponse])
def list_proposals(opportunity_id:UUID,current_user:User=Depends(require_permission("sales.proposals.view")),db:Session=Depends(get_db)): _opportunity(db,current_user.company_id,opportunity_id); return list(db.scalars(select(Proposal).where(Proposal.opportunity_id==opportunity_id).order_by(Proposal.created_at.desc())).all())
@router.post("/opportunities/{opportunity_id}/proposals",response_model=ProposalResponse,status_code=201)
def create_proposal(opportunity_id:UUID,payload:ProposalCreate,current_user:User=Depends(require_permission("sales.proposals.create")),db:Session=Depends(get_db)):
    opportunity=_opportunity(db,current_user.company_id,opportunity_id); requirements=list(db.scalars(select(Requirement).where(Requirement.opportunity_id==opportunity.id)).all())
    if opportunity.stage!="requirement_captured" or not requirements or not all(x.approved for x in requirements): raise HTTPException(409,"All requirements must be captured and approved before proposal creation.")
    record=Proposal(opportunity_id=opportunity.id,created_by_user_id=current_user.id,**payload.model_dump()); _move_opportunity(db,opportunity,"proposal"); db.add(record); db.flush(); _audit(db,current_user,"proposal.create","Proposal",record.id); db.commit(); db.refresh(record); return record
@router.patch("/proposals/{proposal_id}",response_model=ProposalResponse)
def update_proposal(proposal_id:UUID,payload:ProposalUpdate,current_user:User=Depends(require_permission("sales.proposals.edit")),db:Session=Depends(get_db)):
    record=db.get(Proposal,proposal_id)
    if record is None: raise HTTPException(404,"Proposal not found.")
    opportunity=_opportunity(db,current_user.company_id,record.opportunity_id); values=payload.model_dump(exclude_unset=True)
    if "status" in values: _proposal_transition(record.status,values["status"])
    for key,value in values.items(): setattr(record,key,value)
    _audit(db,current_user,"proposal.update","Proposal",record.id,f"Opportunity {opportunity.id}"); db.commit(); db.refresh(record); return record
@router.post("/proposals/{proposal_id}/send",response_model=ProposalResponse)
def send_proposal(proposal_id:UUID,current_user:User=Depends(require_permission("sales.proposals.edit")),db:Session=Depends(get_db)):
    record=db.get(Proposal,proposal_id)
    if record is None: raise HTTPException(404,"Proposal not found.")
    _opportunity(db,current_user.company_id,record.opportunity_id); _proposal_transition(record.status,"sent"); record.status="sent"; _audit(db,current_user,"proposal.send","Proposal",record.id); db.commit(); db.refresh(record); return record

@router.get("/opportunities/{opportunity_id}/quotations",response_model=list[QuotationResponse])
def list_quotations(opportunity_id:UUID,current_user:User=Depends(require_permission("sales.quotations.view")),db:Session=Depends(get_db)): _opportunity(db,current_user.company_id,opportunity_id); return list(db.scalars(select(Quotation).where(Quotation.opportunity_id==opportunity_id).order_by(Quotation.created_at.desc())).all())
@router.post("/opportunities/{opportunity_id}/quotations",response_model=QuotationResponse,status_code=201)
def create_quotation(opportunity_id:UUID,payload:QuotationCreate,current_user:User=Depends(require_permission("sales.quotations.create")),db:Session=Depends(get_db)):
    opportunity=_opportunity(db,current_user.company_id,opportunity_id)
    if opportunity.stage not in {"proposal","negotiation"}: raise HTTPException(409,"Quotation requires an active proposal or negotiation stage.")
    if payload.proposal_id is not None:
        proposal=db.get(Proposal,payload.proposal_id)
        if proposal is None or proposal.opportunity_id!=opportunity.id: raise HTTPException(400,"Proposal does not belong to this opportunity.")
    record=Quotation(opportunity_id=opportunity.id,created_by_user_id=current_user.id,total_amount=payload.subtotal+payload.tax_amount,**payload.model_dump()); db.add(record); db.flush(); _audit(db,current_user,"quotation.create","Quotation",record.id); db.commit(); db.refresh(record); return record
@router.patch("/quotations/{quotation_id}",response_model=QuotationResponse)
def update_quotation(quotation_id:UUID,payload:QuotationUpdate,current_user:User=Depends(require_permission("sales.quotations.edit")),db:Session=Depends(get_db)):
    record=db.get(Quotation,quotation_id)
    if record is None: raise HTTPException(404,"Quotation not found.")
    _opportunity(db,current_user.company_id,record.opportunity_id); values=payload.model_dump(exclude_unset=True)
    if "status" in values: _quotation_transition(record.status,values["status"])
    for key,value in values.items(): setattr(record,key,value)
    record.total_amount=float(record.subtotal or 0)+float(record.tax_amount or 0); _audit(db,current_user,"quotation.update","Quotation",record.id); db.commit(); db.refresh(record); return record

@router.get("/opportunities/{opportunity_id}/negotiations",response_model=list[NegotiationResponse])
def list_negotiations(opportunity_id:UUID,current_user:User=Depends(require_permission("sales.negotiations.view")),db:Session=Depends(get_db)): _opportunity(db,current_user.company_id,opportunity_id); return list(db.scalars(select(Negotiation).where(Negotiation.opportunity_id==opportunity_id).order_by(Negotiation.created_at.desc())).all())
@router.post("/opportunities/{opportunity_id}/negotiations",response_model=NegotiationResponse,status_code=201)
def create_negotiation(opportunity_id:UUID,payload:NegotiationCreate,current_user:User=Depends(require_permission("sales.negotiations.create")),db:Session=Depends(get_db)):
    opportunity=_opportunity(db,current_user.company_id,opportunity_id)
    if opportunity.stage not in {"proposal","negotiation"}: raise HTTPException(409,"Negotiation can only start after proposal.")
    if opportunity.stage=="proposal": _move_opportunity(db,opportunity,"negotiation")
    if payload.proposal_id is not None:
        proposal=db.get(Proposal,payload.proposal_id)
        if proposal is None or proposal.opportunity_id!=opportunity.id: raise HTTPException(400,"Proposal does not belong to this opportunity.")
    record=Negotiation(opportunity_id=opportunity.id,created_by_user_id=current_user.id,**payload.model_dump()); db.add(record); db.flush(); _audit(db,current_user,"negotiation.create","Negotiation",record.id); db.commit(); db.refresh(record); return record
@router.patch("/negotiations/{negotiation_id}",response_model=NegotiationResponse)
def update_negotiation(negotiation_id:UUID,payload:NegotiationUpdate,current_user:User=Depends(require_permission("sales.negotiations.edit")),db:Session=Depends(get_db)):
    record=db.get(Negotiation,negotiation_id)
    if record is None: raise HTTPException(404,"Negotiation not found.")
    _opportunity(db,current_user.company_id,record.opportunity_id)
    values=payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in NEGOTIATION_STATUSES: raise HTTPException(400,"Invalid negotiation status.")
    for key,value in values.items(): setattr(record,key,value)
    _audit(db,current_user,"negotiation.update","Negotiation",record.id); db.commit(); db.refresh(record); return record

@router.post("/opportunities/{opportunity_id}/win",response_model=DealResponse)
def win_deal(opportunity_id:UUID,payload:DealOutcomeCreate,current_user:User=Depends(require_permission("sales.deal.decide")),db:Session=Depends(get_db)):
    opportunity=_opportunity(db,current_user.company_id,opportunity_id)
    if opportunity.stage=="won": raise HTTPException(409,"A won opportunity cannot be decided again.")
    proposals=list(db.scalars(select(Proposal).where(Proposal.opportunity_id==opportunity.id)).all())
    if not any(x.status=="accepted" for x in proposals): raise HTTPException(409,"An accepted proposal is required before marking the deal won.")
    _move_opportunity(db,opportunity,"won"); outcome=DealOutcome(opportunity_id=opportunity.id,outcome="won",lost_reason=None,notes=payload.notes,decided_by_user_id=current_user.id,decided_at=datetime.now(timezone.utc)); db.add(outcome); _audit(db,current_user,"deal.won","Opportunity",opportunity.id); db.commit(); db.refresh(outcome); return outcome
@router.post("/opportunities/{opportunity_id}/lose",response_model=DealResponse)
def lose_deal(opportunity_id:UUID,payload:DealOutcomeCreate,current_user:User=Depends(require_permission("sales.deal.decide")),db:Session=Depends(get_db)):
    opportunity=_opportunity(db,current_user.company_id,opportunity_id)
    if opportunity.stage=="won": raise HTTPException(409,"A won opportunity cannot be marked lost.")
    if opportunity.stage=="lost": raise HTTPException(409,"A lost opportunity cannot be decided again.")
    if payload.lost_reason not in LOST_REASONS: raise HTTPException(400,"A valid lost reason is required.")
    _move_opportunity(db,opportunity,"lost"); outcome=DealOutcome(opportunity_id=opportunity.id,outcome="lost",lost_reason=payload.lost_reason,notes=payload.notes,decided_by_user_id=current_user.id,decided_at=datetime.now(timezone.utc)); db.add(outcome); _audit(db,current_user,"deal.lost","Opportunity",opportunity.id,f"Lost reason: {payload.lost_reason}"); db.commit(); db.refresh(outcome); return outcome
