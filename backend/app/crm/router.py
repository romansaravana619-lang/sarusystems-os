from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.crm.schemas import (
    COMMUNICATION_CHANNELS,
    ContactCreate, ContactResponse, CommunicationCreate, CommunicationResponse,
    FollowUpCreate, FollowUpResponse, FollowUpUpdate, OpportunityCreate, OpportunityResponse,
    OpportunityUpdate, ProspectCreate, ProspectResponse, ProspectUpdate,
    OPPORTUNITY_STAGES, PROSPECT_STATUSES, FOLLOW_UP_STATUSES,
)
from app.shared.models import AuditLog, CommunicationActivity, Contact, CRMFollowUp, Opportunity, Prospect, User

router = APIRouter(prefix="/crm", tags=["crm"])
PROSPECT_TRANSITIONS = {"new": {"contacted", "qualified", "lost", "nurture"}, "contacted": {"qualified", "discovery", "lost", "nurture"}, "qualified": {"discovery", "proposal", "lost", "nurture"}, "discovery": {"proposal", "lost", "nurture"}, "proposal": {"won", "lost", "nurture"}, "won": set(), "lost": {"nurture", "new"}, "nurture": {"new", "contacted", "qualified", "lost"}}
OPPORTUNITY_TRANSITIONS = {"qualification": {"discovery", "lost"}, "discovery": {"requirement_captured", "lost"}, "requirement_captured": {"proposal", "lost"}, "proposal": {"negotiation", "won", "lost"}, "negotiation": {"won", "lost", "proposal"}, "won": set(), "lost": {"qualification"}}


def _validate_owner(db: Session, company_id: UUID, owner_user_id: UUID | None) -> None:
    if owner_user_id is None: return
    owner = db.scalar(select(User).where(User.id == owner_user_id, User.company_id == company_id))
    if owner is None or not owner.is_active: raise HTTPException(status_code=400, detail="Owner must be an active user in the company.")


def _validate_transition(current: str, target: str, transitions: dict[str, set[str]], valid_values: set[str], label: str) -> None:
    if target not in valid_values: raise HTTPException(status_code=400, detail=f"Invalid {label}.")
    if target == current: return
    if target not in transitions.get(current, set()): raise HTTPException(status_code=409, detail=f"Invalid {label} transition: {current} -> {target}.")


def _validate_record_link(db: Session, company_id: UUID, prospect_id: UUID | None, contact_id: UUID | None) -> None:
    if prospect_id is None and contact_id is None: raise HTTPException(status_code=400, detail="A prospect or contact is required.")
    if prospect_id is not None:
        prospect = db.get(Prospect, prospect_id)
        if prospect is None or prospect.company_id != company_id: raise HTTPException(status_code=400, detail="Prospect must belong to the company.")
    if contact_id is not None:
        contact = db.get(Contact, contact_id)
        if contact is None or contact.company_id != company_id: raise HTTPException(status_code=400, detail="Contact must belong to the company.")


@router.get("/prospects", response_model=list[ProspectResponse])
def list_prospects(current_user: User = Depends(require_permission("crm.prospects.view")), db: Session = Depends(get_db)) -> list[Prospect]:
    return list(db.scalars(select(Prospect).where(Prospect.company_id == current_user.company_id).order_by(Prospect.lead_score.desc(), Prospect.name)).all())

@router.post("/prospects", response_model=ProspectResponse, status_code=status.HTTP_201_CREATED)
def create_prospect(payload: ProspectCreate, current_user: User = Depends(require_permission("crm.prospects.create")), db: Session = Depends(get_db)) -> Prospect:
    _validate_owner(db, current_user.company_id, payload.owner_user_id)
    prospect = Prospect(company_id=current_user.company_id, **payload.model_dump())
    db.add(prospect); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="prospect.create", entity_type="Prospect", entity_id=str(prospect.id)))
    db.commit(); db.refresh(prospect); return prospect

@router.patch("/prospects/{prospect_id}", response_model=ProspectResponse)
def update_prospect(prospect_id: UUID, payload: ProspectUpdate, current_user: User = Depends(require_permission("crm.prospects.edit")), db: Session = Depends(get_db)) -> Prospect:
    prospect = db.get(Prospect, prospect_id)
    if prospect is None or prospect.company_id != current_user.company_id: raise HTTPException(status_code=404, detail="Prospect not found.")
    values = payload.model_dump(exclude_unset=True)
    if "status" in values: _validate_transition(prospect.status, values["status"], PROSPECT_TRANSITIONS, PROSPECT_STATUSES, "prospect status")
    if "owner_user_id" in values: _validate_owner(db, current_user.company_id, values["owner_user_id"])
    for key, value in values.items(): setattr(prospect, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="prospect.update", entity_type="Prospect", entity_id=str(prospect.id)))
    db.commit(); db.refresh(prospect); return prospect

@router.post("/prospects/{prospect_id}/convert", response_model=ContactResponse)
def convert_prospect(prospect_id: UUID, current_user: User = Depends(require_permission("crm.prospects.convert")), db: Session = Depends(get_db)) -> Contact:
    prospect = db.get(Prospect, prospect_id)
    if prospect is None or prospect.company_id != current_user.company_id: raise HTTPException(status_code=404, detail="Prospect not found.")
    existing = db.scalar(select(Contact).where(Contact.prospect_id == prospect.id))
    if existing is not None: return existing
    if prospect.status not in {"qualified", "discovery", "proposal"}: raise HTTPException(status_code=409, detail="Prospect must be qualified before conversion to a contact.")
    contact = Contact(company_id=prospect.company_id, prospect_id=prospect.id, name=prospect.name, company_name=prospect.company_name, email=prospect.email, phone=prospect.phone, notes=prospect.notes)
    db.add(contact); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="prospect.convert", entity_type="Prospect", entity_id=str(prospect.id), details=f"Converted to Contact {contact.id}"))
    db.commit(); db.refresh(contact); return contact

@router.get("/contacts", response_model=list[ContactResponse])
def list_contacts(current_user: User = Depends(require_permission("crm.contacts.view")), db: Session = Depends(get_db)) -> list[Contact]:
    return list(db.scalars(select(Contact).where(Contact.company_id == current_user.company_id).order_by(Contact.name)).all())

@router.post("/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(payload: ContactCreate, current_user: User = Depends(require_permission("crm.contacts.create")), db: Session = Depends(get_db)) -> Contact:
    contact = Contact(company_id=current_user.company_id, **payload.model_dump()); db.add(contact); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="contact.create", entity_type="Contact", entity_id=str(contact.id))); db.commit(); db.refresh(contact); return contact

@router.get("/opportunities", response_model=list[OpportunityResponse])
def list_opportunities(current_user: User = Depends(require_permission("crm.opportunities.view")), db: Session = Depends(get_db)) -> list[Opportunity]:
    return list(db.scalars(select(Opportunity).where(Opportunity.company_id == current_user.company_id).order_by(Opportunity.created_at.desc())).all())

@router.post("/opportunities", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
def create_opportunity(payload: OpportunityCreate, current_user: User = Depends(require_permission("crm.opportunities.create")), db: Session = Depends(get_db)) -> Opportunity:
    if payload.stage not in OPPORTUNITY_STAGES: raise HTTPException(status_code=400, detail="Invalid opportunity stage.")
    contact = db.get(Contact, payload.contact_id)
    if contact is None or contact.company_id != current_user.company_id: raise HTTPException(status_code=400, detail="Contact must belong to the company.")
    _validate_owner(db, current_user.company_id, payload.owner_user_id)
    opportunity = Opportunity(company_id=current_user.company_id, **payload.model_dump()); db.add(opportunity); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="opportunity.create", entity_type="Opportunity", entity_id=str(opportunity.id))); db.commit(); db.refresh(opportunity); return opportunity

@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
def update_opportunity(opportunity_id: UUID, payload: OpportunityUpdate, current_user: User = Depends(require_permission("crm.opportunities.edit")), db: Session = Depends(get_db)) -> Opportunity:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None or opportunity.company_id != current_user.company_id: raise HTTPException(status_code=404, detail="Opportunity not found.")
    values = payload.model_dump(exclude_unset=True)
    if "stage" in values: _validate_transition(opportunity.stage, values["stage"], OPPORTUNITY_TRANSITIONS, OPPORTUNITY_STAGES, "opportunity stage")
    if "owner_user_id" in values: _validate_owner(db, current_user.company_id, values["owner_user_id"])
    for key, value in values.items(): setattr(opportunity, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="opportunity.update", entity_type="Opportunity", entity_id=str(opportunity.id))); db.commit(); db.refresh(opportunity); return opportunity

@router.get("/prospects/{prospect_id}/communications", response_model=list[CommunicationResponse])
def list_prospect_communications(prospect_id: UUID, current_user: User = Depends(require_permission("crm.communication.view")), db: Session = Depends(get_db)) -> list[CommunicationActivity]:
    prospect = db.get(Prospect, prospect_id)
    if prospect is None or prospect.company_id != current_user.company_id: raise HTTPException(status_code=404, detail="Prospect not found.")
    return list(db.scalars(select(CommunicationActivity).where(CommunicationActivity.company_id == current_user.company_id, CommunicationActivity.prospect_id == prospect_id).order_by(CommunicationActivity.occurred_at.desc())).all())

@router.post("/communications", response_model=CommunicationResponse, status_code=status.HTTP_201_CREATED)
def create_communication(payload: CommunicationCreate, current_user: User = Depends(require_permission("crm.communication.create")), db: Session = Depends(get_db)) -> CommunicationActivity:
    _validate_record_link(db, current_user.company_id, payload.prospect_id, payload.contact_id)
    occurred_at = payload.occurred_at or datetime.now(timezone.utc)
    activity = CommunicationActivity(company_id=current_user.company_id, actor_user_id=current_user.id, occurred_at=occurred_at, **payload.model_dump(exclude={"occurred_at"}))
    db.add(activity)
    if payload.prospect_id:
        prospect = db.get(Prospect, payload.prospect_id); prospect.last_contact_at = occurred_at
    db.flush(); db.add(AuditLog(actor_user_id=current_user.id, action="crm.communication.create", entity_type="CommunicationActivity", entity_id=str(activity.id))); db.commit(); db.refresh(activity); return activity

@router.get("/follow-ups", response_model=list[FollowUpResponse])
def list_follow_ups(current_user: User = Depends(require_permission("crm.followups.view")), db: Session = Depends(get_db)) -> list[CRMFollowUp]:
    return list(db.scalars(select(CRMFollowUp).where(CRMFollowUp.company_id == current_user.company_id).order_by(CRMFollowUp.due_at)).all())

@router.post("/follow-ups", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
def create_follow_up(payload: FollowUpCreate, current_user: User = Depends(require_permission("crm.followups.create")), db: Session = Depends(get_db)) -> CRMFollowUp:
    _validate_record_link(db, current_user.company_id, payload.prospect_id, payload.contact_id)
    _validate_owner(db, current_user.company_id, payload.owner_user_id)
    follow_up = CRMFollowUp(company_id=current_user.company_id, **payload.model_dump()); db.add(follow_up); db.flush()
    if payload.prospect_id:
        prospect = db.get(Prospect, payload.prospect_id); prospect.next_action = payload.title; prospect.next_action_at = payload.due_at
    db.add(AuditLog(actor_user_id=current_user.id, action="crm.followup.create", entity_type="CRMFollowUp", entity_id=str(follow_up.id))); db.commit(); db.refresh(follow_up); return follow_up

@router.patch("/follow-ups/{follow_up_id}", response_model=FollowUpResponse)
def update_follow_up(follow_up_id: UUID, payload: FollowUpUpdate, current_user: User = Depends(require_permission("crm.followups.edit")), db: Session = Depends(get_db)) -> CRMFollowUp:
    follow_up = db.get(CRMFollowUp, follow_up_id)
    if follow_up is None or follow_up.company_id != current_user.company_id: raise HTTPException(status_code=404, detail="Follow-up not found.")
    values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in FOLLOW_UP_STATUSES: raise HTTPException(status_code=400, detail="Invalid follow-up status.")
    for key, value in values.items(): setattr(follow_up, key, value)
    if values.get("status") == "completed": follow_up.completed_at = datetime.now(timezone.utc)
    db.add(AuditLog(actor_user_id=current_user.id, action="crm.followup.update", entity_type="CRMFollowUp", entity_id=str(follow_up.id))); db.commit(); db.refresh(follow_up); return follow_up
