from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.crm.schemas import OPPORTUNITY_STAGES
from app.crm.router import OPPORTUNITY_TRANSITIONS
from app.sales.models import DealOutcome, Discovery, Proposal, Requirement
from app.sales.schemas import (
    DealOutcomeCreate,
    DealResponse,
    DiscoveryCreate,
    DiscoveryResponse,
    ProposalCreate,
    ProposalResponse,
    ProposalUpdate,
    RequirementCreate,
    RequirementResponse,
)
from app.shared.models import AuditLog, Opportunity, User

router = APIRouter(prefix="/sales", tags=["sales"])

PROPOSAL_STATUSES = {"draft", "internal_review", "ready_to_send", "sent", "viewed", "negotiation", "accepted", "rejected", "expired"}


def _opportunity(db: Session, company_id: UUID, opportunity_id: UUID) -> Opportunity:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None or opportunity.company_id != company_id:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    return opportunity


def _move_opportunity(db: Session, opportunity: Opportunity, target: str) -> None:
    if target not in OPPORTUNITY_STAGES or target == opportunity.stage:
        return
    if target not in OPPORTUNITY_TRANSITIONS.get(opportunity.stage, set()):
        raise HTTPException(status_code=409, detail=f"Invalid opportunity stage transition: {opportunity.stage} -> {target}.")
    opportunity.stage = target


@router.get("/opportunities/{opportunity_id}/discoveries", response_model=list[DiscoveryResponse])
def list_discoveries(opportunity_id: UUID, current_user: User = Depends(require_permission("sales.discovery.view")), db: Session = Depends(get_db)) -> list[Discovery]:
    _opportunity(db, current_user.company_id, opportunity_id)
    return list(db.scalars(select(Discovery).where(Discovery.opportunity_id == opportunity_id).order_by(Discovery.created_at.desc())).all())


@router.post("/opportunities/{opportunity_id}/discoveries", response_model=DiscoveryResponse, status_code=status.HTTP_201_CREATED)
def create_discovery(opportunity_id: UUID, payload: DiscoveryCreate, current_user: User = Depends(require_permission("sales.discovery.create")), db: Session = Depends(get_db)) -> Discovery:
    opportunity = _opportunity(db, current_user.company_id, opportunity_id)
    if opportunity.stage != "discovery":
        _move_opportunity(db, opportunity, "discovery")
    discovery = Discovery(opportunity_id=opportunity.id, created_by_user_id=current_user.id, **payload.model_dump())
    db.add(discovery)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="discovery.create", entity_type="Discovery", entity_id=str(discovery.id)))
    db.commit()
    db.refresh(discovery)
    return discovery


@router.get("/opportunities/{opportunity_id}/requirements", response_model=list[RequirementResponse])
def list_requirements(opportunity_id: UUID, current_user: User = Depends(require_permission("sales.requirements.view")), db: Session = Depends(get_db)) -> list[Requirement]:
    _opportunity(db, current_user.company_id, opportunity_id)
    return list(db.scalars(select(Requirement).where(Requirement.opportunity_id == opportunity_id).order_by(Requirement.created_at.desc())).all())


@router.post("/opportunities/{opportunity_id}/requirements", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
def create_requirement(opportunity_id: UUID, payload: RequirementCreate, current_user: User = Depends(require_permission("sales.requirements.create")), db: Session = Depends(get_db)) -> Requirement:
    opportunity = _opportunity(db, current_user.company_id, opportunity_id)
    if opportunity.stage not in {"discovery", "requirement_captured"}:
        raise HTTPException(status_code=409, detail="Requirements can only be captured after discovery.")
    if opportunity.stage == "discovery":
        _move_opportunity(db, opportunity, "requirement_captured")
    requirement = Requirement(opportunity_id=opportunity.id, created_by_user_id=current_user.id, approved=False, **payload.model_dump(exclude={"approved"}))
    db.add(requirement)
    db.flush()
    if payload.approved:
        requirement.approved = True
        requirement.approved_by_user_id = current_user.id
        requirement.approved_at = datetime.now(timezone.utc)
    db.add(AuditLog(actor_user_id=current_user.id, action="requirement.create", entity_type="Requirement", entity_id=str(requirement.id)))
    db.commit()
    db.refresh(requirement)
    return requirement


@router.post("/opportunities/{opportunity_id}/proposals", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
def create_proposal(opportunity_id: UUID, payload: ProposalCreate, current_user: User = Depends(require_permission("sales.proposals.create")), db: Session = Depends(get_db)) -> Proposal:
    opportunity = _opportunity(db, current_user.company_id, opportunity_id)
    requirements = list(db.scalars(select(Requirement).where(Requirement.opportunity_id == opportunity.id)).all())
    if opportunity.stage != "requirement_captured" or not requirements or not all(item.approved for item in requirements):
        raise HTTPException(status_code=409, detail="All requirements must be captured and approved before proposal creation.")
    proposal = Proposal(opportunity_id=opportunity.id, created_by_user_id=current_user.id, **payload.model_dump())
    _move_opportunity(db, opportunity, "proposal")
    db.add(proposal)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="proposal.create", entity_type="Proposal", entity_id=str(proposal.id)))
    db.commit()
    db.refresh(proposal)
    return proposal


@router.patch("/proposals/{proposal_id}", response_model=ProposalResponse)
def update_proposal(proposal_id: UUID, payload: ProposalUpdate, current_user: User = Depends(require_permission("sales.proposals.edit")), db: Session = Depends(get_db)) -> Proposal:
    proposal = db.get(Proposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    opportunity = _opportunity(db, current_user.company_id, proposal.opportunity_id)
    values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in PROPOSAL_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid proposal status.")
    for key, value in values.items():
        setattr(proposal, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="proposal.update", entity_type="Proposal", entity_id=str(proposal.id), details=f"Opportunity {opportunity.id}"))
    db.commit()
    db.refresh(proposal)
    return proposal


@router.post("/opportunities/{opportunity_id}/win", response_model=DealResponse)
def win_deal(opportunity_id: UUID, payload: DealOutcomeCreate, current_user: User = Depends(require_permission("sales.deal.decide")), db: Session = Depends(get_db)) -> DealOutcome:
    opportunity = _opportunity(db, current_user.company_id, opportunity_id)
    proposals = list(db.scalars(select(Proposal).where(Proposal.opportunity_id == opportunity.id)).all())
    if not proposals or not any(proposal.status == "accepted" for proposal in proposals):
        raise HTTPException(status_code=409, detail="An accepted proposal is required before marking the deal won.")
    _move_opportunity(db, opportunity, "won")
    outcome = DealOutcome(opportunity_id=opportunity.id, outcome="won", notes=payload.notes, decided_by_user_id=current_user.id, decided_at=datetime.now(timezone.utc))
    db.add(outcome)
    db.add(AuditLog(actor_user_id=current_user.id, action="deal.won", entity_type="Opportunity", entity_id=str(opportunity.id)))
    db.commit()
    return outcome


@router.post("/opportunities/{opportunity_id}/lose", response_model=DealResponse)
def lose_deal(opportunity_id: UUID, payload: DealOutcomeCreate, current_user: User = Depends(require_permission("sales.deal.decide")), db: Session = Depends(get_db)) -> DealOutcome:
    opportunity = _opportunity(db, current_user.company_id, opportunity_id)
    if opportunity.stage == "won":
        raise HTTPException(status_code=409, detail="A won opportunity cannot be marked lost.")
    _move_opportunity(db, opportunity, "lost")
    outcome = DealOutcome(opportunity_id=opportunity.id, outcome="lost", notes=payload.notes, decided_by_user_id=current_user.id, decided_at=datetime.now(timezone.utc))
    db.add(outcome)
    db.add(AuditLog(actor_user_id=current_user.id, action="deal.lost", entity_type="Opportunity", entity_id=str(opportunity.id)))
    db.commit()
    return outcome
