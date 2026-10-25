from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.clients.models import Agreement, Client, ClientContact
from app.clients.schemas import (
    AGREEMENT_STATUSES,
    CLIENT_STATUSES,
    AgreementCreate,
    AgreementResponse,
    ClientContactCreate,
    ClientContactResponse,
    ClientCreate,
    ClientResponse,
    ClientUpdate,
)
from app.core.database import get_db
from app.shared.models import AuditLog, Contact, Opportunity, User

router = APIRouter(prefix="/clients", tags=["clients"])


def _client(db: Session, company_id: UUID, client_id: UUID) -> Client:
    client = db.get(Client, client_id)
    if client is None or client.company_id != company_id:
        raise HTTPException(status_code=404, detail="Client not found.")
    return client


def _validate_owner(db: Session, company_id: UUID, owner_user_id: UUID | None) -> None:
    if owner_user_id is None:
        return
    owner = db.scalar(select(User).where(User.id == owner_user_id, User.company_id == company_id))
    if owner is None or not owner.is_active:
        raise HTTPException(status_code=400, detail="Owner must be an active user in the company.")


@router.get("", response_model=list[ClientResponse])
def list_clients(
    current_user: User = Depends(require_permission("clients.view")),
    db: Session = Depends(get_db),
) -> list[Client]:
    return list(db.scalars(select(Client).where(Client.company_id == current_user.company_id).order_by(Client.name)).all())


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    current_user: User = Depends(require_permission("clients.create")),
    db: Session = Depends(get_db),
) -> Client:
    opportunity = db.get(Opportunity, payload.opportunity_id)
    if opportunity is None or opportunity.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    if opportunity.stage != "won":
        raise HTTPException(status_code=409, detail="Only won opportunities can be converted to clients.")

    existing = db.scalar(select(Client).where(Client.opportunity_id == opportunity.id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="This opportunity has already been converted to a client.")

    contact = db.get(Contact, opportunity.contact_id)
    if contact is None or contact.company_id != current_user.company_id:
        raise HTTPException(status_code=409, detail="Opportunity contact is not available for client conversion.")

    _validate_owner(db, current_user.company_id, payload.owner_user_id)
    client = Client(
        company_id=opportunity.company_id,
        opportunity_id=opportunity.id,
        source_contact_id=contact.id,
        code="PENDING",
        name=contact.name,
        company_name=contact.company_name,
        email=str(contact.email) if contact.email else None,
        phone=contact.phone,
        status="onboarding",
        owner_user_id=payload.owner_user_id,
        notes=payload.notes,
    )
    db.add(client)
    db.flush()
    client.code = f"CL-{client.id.hex[:8].upper()}"
    db.add(AuditLog(actor_user_id=current_user.id, action="client.convert", entity_type="Client", entity_id=str(client.id), details=f"Converted Opportunity {opportunity.id}"))
    db.commit()
    db.refresh(client)
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    current_user: User = Depends(require_permission("clients.edit")),
    db: Session = Depends(get_db),
) -> Client:
    client = _client(db, current_user.company_id, client_id)
    values = payload.model_dump(exclude_unset=True)
    if "status" in values:
        target = values["status"]
        if target not in CLIENT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid client status.")
        if client.status == "archived" and target != "archived":
            raise HTTPException(status_code=409, detail="Archived clients cannot be reactivated.")
    if "owner_user_id" in values:
        _validate_owner(db, current_user.company_id, values["owner_user_id"])
    for key, value in values.items():
        setattr(client, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="client.update", entity_type="Client", entity_id=str(client.id)))
    db.commit()
    db.refresh(client)
    return client


@router.post("/{client_id}/onboarding/start", response_model=ClientResponse)
def start_onboarding(
    client_id: UUID,
    current_user: User = Depends(require_permission("clients.onboarding")),
    db: Session = Depends(get_db),
) -> Client:
    client = _client(db, current_user.company_id, client_id)
    if client.status == "archived":
        raise HTTPException(status_code=409, detail="Archived clients cannot start onboarding.")
    if client.onboarding_started_at is None:
        client.onboarding_started_at = datetime.now(timezone.utc)
        db.add(AuditLog(actor_user_id=current_user.id, action="client.onboarding.start", entity_type="Client", entity_id=str(client.id)))
        db.commit()
        db.refresh(client)
    return client


@router.get("/{client_id}/contacts", response_model=list[ClientContactResponse])
def list_client_contacts(
    client_id: UUID,
    current_user: User = Depends(require_permission("clients.view")),
    db: Session = Depends(get_db),
) -> list[ClientContact]:
    _client(db, current_user.company_id, client_id)
    return list(db.scalars(select(ClientContact).where(ClientContact.client_id == client_id).order_by(ClientContact.name)).all())


@router.post("/{client_id}/contacts", response_model=ClientContactResponse, status_code=status.HTTP_201_CREATED)
def create_client_contact(
    client_id: UUID,
    payload: ClientContactCreate,
    current_user: User = Depends(require_permission("clients.edit")),
    db: Session = Depends(get_db),
) -> ClientContact:
    client = _client(db, current_user.company_id, client_id)
    contact = ClientContact(client_id=client.id, **payload.model_dump())
    db.add(contact)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="client.contact.create", entity_type="ClientContact", entity_id=str(contact.id), details=f"Client {client.id}"))
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/{client_id}/agreements", response_model=list[AgreementResponse])
def list_agreements(
    client_id: UUID,
    current_user: User = Depends(require_permission("clients.view")),
    db: Session = Depends(get_db),
) -> list[Agreement]:
    _client(db, current_user.company_id, client_id)
    return list(db.scalars(select(Agreement).where(Agreement.client_id == client_id).order_by(Agreement.created_at.desc())).all())


@router.post("/{client_id}/agreements", response_model=AgreementResponse, status_code=status.HTTP_201_CREATED)
def create_agreement(
    client_id: UUID,
    payload: AgreementCreate,
    current_user: User = Depends(require_permission("clients.edit")),
    db: Session = Depends(get_db),
) -> Agreement:
    client = _client(db, current_user.company_id, client_id)
    if payload.status not in AGREEMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid agreement status.")
    agreement = Agreement(client_id=client.id, **payload.model_dump())
    db.add(agreement)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="client.agreement.create", entity_type="Agreement", entity_id=str(agreement.id), details=f"Client {client.id}"))
    db.commit()
    db.refresh(agreement)
    return agreement
