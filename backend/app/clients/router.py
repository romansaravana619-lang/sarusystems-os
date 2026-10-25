from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.clients.models import Agreement, Client, ClientContact, ClientDocument, ClientOnboardingItem, ClientRelation
from app.clients.schemas import (
    AGREEMENT_STATUSES, CLIENT_RELATION_TYPES, CLIENT_STATUSES, HEALTH_STATUSES, ONBOARDING_ITEM_STATUSES,
    AgreementCreate, AgreementResponse, ClientContactCreate, ClientContactResponse, ClientCreate, ClientDocumentCreate,
    ClientDocumentResponse, ClientHealthUpdate, ClientRelationCreate, ClientRelationResponse, ClientResponse,
    ClientUpdate, ClientWorkspaceResponse, OnboardingItemCreate, OnboardingItemResponse, OnboardingItemUpdate,
)
from app.core.database import get_db
from app.shared.models import AuditLog, Contact, Opportunity, User

router = APIRouter(prefix="/clients", tags=["clients"])

CLIENT_STATUS_TRANSITIONS = {
    "onboarding": {"active", "inactive", "archived"},
    "active": {"at_risk", "inactive", "archived"},
    "at_risk": {"active", "inactive", "archived"},
    "inactive": {"active", "archived"},
    "archived": set(),
}
AGREEMENT_STATUS_TRANSITIONS = {
    "draft": {"sent", "cancelled"}, "sent": {"signed", "expired", "cancelled"},
    "signed": set(), "expired": set(), "cancelled": set(),
}


def _client(db: Session, company_id: UUID, client_id: UUID) -> Client:
    client = db.get(Client, client_id)
    if client is None or client.company_id != company_id:
        raise HTTPException(status_code=404, detail="Client not found.")
    return client


def _agreement(db: Session, company_id: UUID, agreement_id: UUID) -> Agreement:
    agreement = db.get(Agreement, agreement_id)
    if agreement is None:
        raise HTTPException(status_code=404, detail="Agreement not found.")
    _client(db, company_id, agreement.client_id)
    return agreement


def _validate_owner(db: Session, company_id: UUID, owner_user_id: UUID | None) -> None:
    if owner_user_id is None:
        return
    owner = db.scalar(select(User).where(User.id == owner_user_id, User.company_id == company_id))
    if owner is None or not owner.is_active:
        raise HTTPException(status_code=400, detail="Owner must be an active user in the company.")


def _validate_client_transition(current: str, target: str) -> None:
    if target not in CLIENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid client status.")
    if current != target and target not in CLIENT_STATUS_TRANSITIONS.get(current, set()):
        raise HTTPException(status_code=409, detail=f"Invalid client status transition: {current} -> {target}.")


def _validate_agreement_transition(current: str, target: str) -> None:
    if target not in AGREEMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid agreement status.")
    if current != target and target not in AGREEMENT_STATUS_TRANSITIONS.get(current, set()):
        raise HTTPException(status_code=409, detail=f"Invalid agreement status transition: {current} -> {target}.")


@router.get("", response_model=list[ClientResponse])
def list_clients(current_user: User = Depends(require_permission("clients.view")), db: Session = Depends(get_db)) -> list[Client]:
    return list(db.scalars(select(Client).where(Client.company_id == current_user.company_id).order_by(Client.name)).all())


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, current_user: User = Depends(require_permission("clients.create")), db: Session = Depends(get_db)) -> Client:
    opportunity = db.get(Opportunity, payload.opportunity_id)
    if opportunity is None or opportunity.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    if opportunity.stage != "won":
        raise HTTPException(status_code=409, detail="Only won opportunities can be converted to clients.")
    if db.scalar(select(Client).where(Client.opportunity_id == opportunity.id)) is not None:
        raise HTTPException(status_code=409, detail="This opportunity has already been converted to a client.")
    contact = db.get(Contact, opportunity.contact_id)
    if contact is None or contact.company_id != current_user.company_id:
        raise HTTPException(status_code=409, detail="Opportunity contact is not available for client conversion.")
    _validate_owner(db, current_user.company_id, payload.owner_user_id)
    client = Client(
        company_id=opportunity.company_id, opportunity_id=opportunity.id, source_contact_id=contact.id,
        code="PENDING", name=contact.name, company_name=contact.company_name, email=str(contact.email) if contact.email else None,
        phone=contact.phone, status="onboarding", owner_user_id=payload.owner_user_id, notes=payload.notes,
    )
    db.add(client); db.flush(); client.code = f"CL-{client.id.hex[:8].upper()}"
    db.add(AuditLog(actor_user_id=current_user.id, action="client.convert", entity_type="Client", entity_id=str(client.id), details=f"Converted Opportunity {opportunity.id}"))
    db.commit(); db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: UUID, current_user: User = Depends(require_permission("clients.view")), db: Session = Depends(get_db)) -> Client:
    return _client(db, current_user.company_id, client_id)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(client_id: UUID, payload: ClientUpdate, current_user: User = Depends(require_permission("clients.edit")), db: Session = Depends(get_db)) -> Client:
    client = _client(db, current_user.company_id, client_id)
    values = payload.model_dump(exclude_unset=True)
    if "status" in values: _validate_client_transition(client.status, values["status"])
    if "owner_user_id" in values: _validate_owner(db, current_user.company_id, values["owner_user_id"])
    for key, value in values.items(): setattr(client, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="client.update", entity_type="Client", entity_id=str(client.id)))
    db.commit(); db.refresh(client)
    return client


@router.patch("/{client_id}/health", response_model=ClientResponse)
def update_health(client_id: UUID, payload: ClientHealthUpdate, current_user: User = Depends(require_permission("clients.health")), db: Session = Depends(get_db)) -> Client:
    client = _client(db, current_user.company_id, client_id)
    if payload.health_status not in HEALTH_STATUSES: raise HTTPException(status_code=400, detail="Invalid health status.")
    client.health_status = payload.health_status; client.health_score = payload.health_score; client.health_reason = payload.health_reason
    client.last_health_reviewed_at = datetime.now(timezone.utc); client.next_health_review_at = payload.next_health_review_at
    db.add(AuditLog(actor_user_id=current_user.id, action="client.health.update", entity_type="Client", entity_id=str(client.id), details=payload.health_status))
    db.commit(); db.refresh(client)
    return client


@router.post("/{client_id}/onboarding/start", response_model=ClientResponse)
def start_onboarding(client_id: UUID, current_user: User = Depends(require_permission("clients.onboarding")), db: Session = Depends(get_db)) -> Client:
    client = _client(db, current_user.company_id, client_id)
    if client.status != "onboarding": raise HTTPException(status_code=409, detail="Onboarding can only be started for an onboarding client.")
    if client.onboarding_started_at is None:
        client.onboarding_started_at = datetime.now(timezone.utc)
        db.add(AuditLog(actor_user_id=current_user.id, action="client.onboarding.start", entity_type="Client", entity_id=str(client.id)))
        db.commit(); db.refresh(client)
    return client


@router.post("/{client_id}/onboarding/complete", response_model=ClientResponse)
def complete_onboarding(client_id: UUID, current_user: User = Depends(require_permission("clients.onboarding")), db: Session = Depends(get_db)) -> Client:
    client = _client(db, current_user.company_id, client_id)
    if client.status != "onboarding": raise HTTPException(status_code=409, detail="Only onboarding clients can complete onboarding.")
    required_remaining = db.scalar(select(func.count(ClientOnboardingItem.id)).where(ClientOnboardingItem.client_id == client.id, ClientOnboardingItem.required.is_(True), ClientOnboardingItem.status.not_in(["completed", "skipped"]))) or 0
    if required_remaining: raise HTTPException(status_code=409, detail="Required onboarding items are not complete.")
    client.onboarding_completed_at = datetime.now(timezone.utc); client.status = "active"
    db.add(AuditLog(actor_user_id=current_user.id, action="client.onboarding.complete", entity_type="Client", entity_id=str(client.id)))
    db.commit(); db.refresh(client)
    return client


@router.get("/{client_id}/workspace", response_model=ClientWorkspaceResponse)
def get_workspace(client_id: UUID, current_user: User = Depends(require_permission("clients.view")), db: Session = Depends(get_db)) -> ClientWorkspaceResponse:
    client = _client(db, current_user.company_id, client_id)
    contacts = list(db.scalars(select(ClientContact).where(ClientContact.client_id == client.id).order_by(ClientContact.is_primary.desc(), ClientContact.name)).all())
    agreements = list(db.scalars(select(Agreement).where(Agreement.client_id == client.id).order_by(Agreement.created_at.desc())).all())
    onboarding = list(db.scalars(select(ClientOnboardingItem).where(ClientOnboardingItem.client_id == client.id).order_by(ClientOnboardingItem.created_at)).all())
    documents = list(db.scalars(select(ClientDocument).where(ClientDocument.client_id == client.id).order_by(ClientDocument.created_at.desc())).all())
    relations = list(db.scalars(select(ClientRelation).where(ClientRelation.client_id == client.id).order_by(ClientRelation.occurred_at.desc().nullslast(), ClientRelation.created_at.desc())).all())
    remaining = sum(1 for item in onboarding if item.required and item.status not in {"completed", "skipped"})
    return ClientWorkspaceResponse(client=client, contacts=contacts, agreements=agreements, onboarding_items=onboarding, documents=documents, relations=relations, onboarding_required_remaining=remaining)


@router.get("/{client_id}/contacts", response_model=list[ClientContactResponse])
def list_client_contacts(client_id: UUID, current_user: User = Depends(require_permission("clients.view")), db: Session = Depends(get_db)) -> list[ClientContact]:
    _client(db, current_user.company_id, client_id)
    return list(db.scalars(select(ClientContact).where(ClientContact.client_id == client_id).order_by(ClientContact.is_primary.desc(), ClientContact.name)).all())


@router.post("/{client_id}/contacts", response_model=ClientContactResponse, status_code=status.HTTP_201_CREATED)
def create_client_contact(client_id: UUID, payload: ClientContactCreate, current_user: User = Depends(require_permission("clients.edit")), db: Session = Depends(get_db)) -> ClientContact:
    client = _client(db, current_user.company_id, client_id)
    if payload.is_primary:
        for contact in db.scalars(select(ClientContact).where(ClientContact.client_id == client.id, ClientContact.is_primary.is_(True))).all(): contact.is_primary = False
    contact = ClientContact(client_id=client.id, **payload.model_dump()); db.add(contact); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="client.contact.create", entity_type="ClientContact", entity_id=str(contact.id), details=f"Client {client.id}"))
    db.commit(); db.refresh(contact); return contact


@router.patch("/contacts/{contact_id}", response_model=ClientContactResponse)
def update_client_contact(contact_id: UUID, payload: ClientContactCreate, current_user: User = Depends(require_permission("clients.edit")), db: Session = Depends(get_db)) -> ClientContact:
    contact = db.get(ClientContact, contact_id)
    if contact is None: raise HTTPException(status_code=404, detail="Client contact not found.")
    client = _client(db, current_user.company_id, contact.client_id)
    if payload.is_primary:
        for item in db.scalars(select(ClientContact).where(ClientContact.client_id == client.id, ClientContact.is_primary.is_(True), ClientContact.id != contact.id)).all(): item.is_primary = False
    for key, value in payload.model_dump().items(): setattr(contact, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="client.contact.update", entity_type="ClientContact", entity_id=str(contact.id)))
    db.commit(); db.refresh(contact); return contact


@router.get("/{client_id}/agreements", response_model=list[AgreementResponse])
def list_agreements(client_id: UUID, current_user: User = Depends(require_permission("clients.view")), db: Session = Depends(get_db)) -> list[Agreement]:
    _client(db, current_user.company_id, client_id)
    return list(db.scalars(select(Agreement).where(Agreement.client_id == client_id).order_by(Agreement.created_at.desc())).all())


@router.post("/{client_id}/agreements", response_model=AgreementResponse, status_code=status.HTTP_201_CREATED)
def create_agreement(client_id: UUID, payload: AgreementCreate, current_user: User = Depends(require_permission("clients.edit")), db: Session = Depends(get_db)) -> Agreement:
    client = _client(db, current_user.company_id, client_id)
    if payload.status not in AGREEMENT_STATUSES: raise HTTPException(status_code=400, detail="Invalid agreement status.")
    agreement = Agreement(client_id=client.id, **payload.model_dump()); db.add(agreement); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="client.agreement.create", entity_type="Agreement", entity_id=str(agreement.id), details=f"Client {client.id}"))
    db.commit(); db.refresh(agreement); return agreement


@router.patch("/agreements/{agreement_id}", response_model=AgreementResponse)
def update_agreement(agreement_id: UUID, payload: AgreementCreate, current_user: User = Depends(require_permission("clients.edit")), db: Session = Depends(get_db)) -> Agreement:
    agreement = _agreement(db, current_user.company_id, agreement_id)
    _validate_agreement_transition(agreement.status, payload.status)
    agreement.title = payload.title; agreement.status = payload.status; agreement.document_id = payload.document_id; agreement.notes = payload.notes
    db.add(AuditLog(actor_user_id=current_user.id, action="client.agreement.update", entity_type="Agreement", entity_id=str(agreement.id), details=f"Status {payload.status}"))
    db.commit(); db.refresh(agreement); return agreement


@router.get("/{client_id}/onboarding/items", response_model=list[OnboardingItemResponse])
def list_onboarding_items(client_id: UUID, current_user: User = Depends(require_permission("clients.view")), db: Session = Depends(get_db)) -> list[ClientOnboardingItem]:
    _client(db, current_user.company_id, client_id)
    return list(db.scalars(select(ClientOnboardingItem).where(ClientOnboardingItem.client_id == client_id).order_by(ClientOnboardingItem.created_at)).all())


@router.post("/{client_id}/onboarding/items", response_model=OnboardingItemResponse, status_code=status.HTTP_201_CREATED)
def create_onboarding_item(client_id: UUID, payload: OnboardingItemCreate, current_user: User = Depends(require_permission("clients.onboarding")), db: Session = Depends(get_db)) -> ClientOnboardingItem:
    client = _client(db, current_user.company_id, client_id)
    item = ClientOnboardingItem(client_id=client.id, **payload.model_dump()); db.add(item); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="client.onboarding.item.create", entity_type="ClientOnboardingItem", entity_id=str(item.id)))
    db.commit(); db.refresh(item); return item


@router.patch("/{client_id}/onboarding/items/{item_id}", response_model=OnboardingItemResponse)
def update_onboarding_item(client_id: UUID, item_id: UUID, payload: OnboardingItemUpdate, current_user: User = Depends(require_permission("clients.onboarding")), db: Session = Depends(get_db)) -> ClientOnboardingItem:
    client = _client(db, current_user.company_id, client_id); item = db.get(ClientOnboardingItem, item_id)
    if item is None or item.client_id != client.id: raise HTTPException(status_code=404, detail="Onboarding item not found.")
    values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in ONBOARDING_ITEM_STATUSES: raise HTTPException(status_code=400, detail="Invalid onboarding item status.")
    for key, value in values.items(): setattr(item, key, value)
    if item.status == "completed": item.completed_at = datetime.now(timezone.utc)
    elif "status" in values: item.completed_at = None
    db.add(AuditLog(actor_user_id=current_user.id, action="client.onboarding.item.update", entity_type="ClientOnboardingItem", entity_id=str(item.id), details=item.status))
    db.commit(); db.refresh(item); return item


@router.get("/{client_id}/documents", response_model=list[ClientDocumentResponse])
def list_documents(client_id: UUID, current_user: User = Depends(require_permission("clients.view")), db: Session = Depends(get_db)) -> list[ClientDocument]:
    _client(db, current_user.company_id, client_id)
    return list(db.scalars(select(ClientDocument).where(ClientDocument.client_id == client_id).order_by(ClientDocument.created_at.desc())).all())


@router.post("/{client_id}/documents", response_model=ClientDocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(client_id: UUID, payload: ClientDocumentCreate, current_user: User = Depends(require_permission("clients.documents")), db: Session = Depends(get_db)) -> ClientDocument:
    client = _client(db, current_user.company_id, client_id)
    document = ClientDocument(client_id=client.id, **payload.model_dump()); db.add(document); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="client.document.create", entity_type="ClientDocument", entity_id=str(document.id)))
    db.commit(); db.refresh(document); return document


@router.get("/{client_id}/relations", response_model=list[ClientRelationResponse])
def list_relations(client_id: UUID, current_user: User = Depends(require_permission("clients.view")), db: Session = Depends(get_db)) -> list[ClientRelation]:
    _client(db, current_user.company_id, client_id)
    return list(db.scalars(select(ClientRelation).where(ClientRelation.client_id == client_id).order_by(ClientRelation.created_at.desc())).all())


@router.post("/{client_id}/relations", response_model=ClientRelationResponse, status_code=status.HTTP_201_CREATED)
def create_relation(client_id: UUID, payload: ClientRelationCreate, current_user: User = Depends(require_permission("clients.edit")), db: Session = Depends(get_db)) -> ClientRelation:
    client = _client(db, current_user.company_id, client_id)
    if payload.relation_type not in CLIENT_RELATION_TYPES: raise HTTPException(status_code=400, detail="Invalid client relation type.")
    relation = ClientRelation(client_id=client.id, **payload.model_dump()); db.add(relation); db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="client.relation.create", entity_type="ClientRelation", entity_id=str(relation.id), details=payload.relation_type))
    db.commit(); db.refresh(relation); return relation
