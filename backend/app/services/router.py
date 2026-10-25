from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.services.models import Service, ServiceDeliverable, ServiceRequirement
from app.services.schemas import (
    PRICING_MODELS,
    ServiceCreate,
    ServiceItemCreate,
    ServiceItemResponse,
    ServiceItemUpdate,
    ServiceResponse,
    ServiceUpdate,
)
from app.shared.models import AuditLog, User

router = APIRouter(prefix="/services", tags=["services"])


def _service(db: Session, company_id: UUID, service_id: UUID) -> Service:
    service = db.get(Service, service_id)
    if service is None or service.company_id != company_id:
        raise HTTPException(status_code=404, detail="Service not found.")
    return service


def _validate_pricing(model: str) -> None:
    if model not in PRICING_MODELS:
        raise HTTPException(status_code=400, detail="Invalid pricing model.")


def _validate_currency(currency: str) -> None:
    if len(currency) != 3 or not currency.isalpha() or currency.upper() != currency:
        raise HTTPException(status_code=400, detail="Currency must be a 3-letter uppercase code.")


def _validate_item_payload(payload: ServiceItemCreate | ServiceItemUpdate) -> None:
    values = payload.model_dump(exclude_unset=True)
    if "sort_order" in values and values["sort_order"] < 0:
        raise HTTPException(status_code=400, detail="Sort order cannot be negative.")


@router.get("", response_model=list[ServiceResponse])
def list_services(current_user: User = Depends(require_permission("services.view")), db: Session = Depends(get_db)) -> list[Service]:
    return list(db.scalars(select(Service).where(Service.company_id == current_user.company_id).order_by(Service.name)).all())


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(payload: ServiceCreate, current_user: User = Depends(require_permission("services.create")), db: Session = Depends(get_db)) -> Service:
    _validate_pricing(payload.pricing_model)
    _validate_currency(payload.currency)
    if db.scalar(select(Service).where(Service.company_id == current_user.company_id, Service.code == payload.code)):
        raise HTTPException(status_code=409, detail="Service code already exists.")
    service = Service(company_id=current_user.company_id, **payload.model_dump())
    db.add(service)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="service.create", entity_type="Service", entity_id=str(service.id), details=service.code))
    db.commit()
    db.refresh(service)
    return service


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: UUID, current_user: User = Depends(require_permission("services.view")), db: Session = Depends(get_db)) -> Service:
    return _service(db, current_user.company_id, service_id)


@router.patch("/{service_id}", response_model=ServiceResponse)
def update_service(service_id: UUID, payload: ServiceUpdate, current_user: User = Depends(require_permission("services.edit")), db: Session = Depends(get_db)) -> Service:
    service = _service(db, current_user.company_id, service_id)
    changes = payload.model_dump(exclude_unset=True)
    if "pricing_model" in changes:
        _validate_pricing(changes["pricing_model"])
    if "currency" in changes:
        _validate_currency(changes["currency"])
    for key, value in changes.items():
        setattr(service, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="service.update", entity_type="Service", entity_id=str(service.id), details=",".join(changes)))
    db.commit()
    db.refresh(service)
    return service


@router.get("/{service_id}/requirements", response_model=list[ServiceItemResponse])
def list_requirements(service_id: UUID, current_user: User = Depends(require_permission("services.view")), db: Session = Depends(get_db)) -> list[ServiceRequirement]:
    _service(db, current_user.company_id, service_id)
    return list(db.scalars(select(ServiceRequirement).where(ServiceRequirement.service_id == service_id).order_by(ServiceRequirement.sort_order, ServiceRequirement.name)).all())


@router.post("/{service_id}/requirements", response_model=ServiceItemResponse, status_code=status.HTTP_201_CREATED)
def create_requirement(service_id: UUID, payload: ServiceItemCreate, current_user: User = Depends(require_permission("services.edit")), db: Session = Depends(get_db)) -> ServiceRequirement:
    _service(db, current_user.company_id, service_id)
    _validate_item_payload(payload)
    item = ServiceRequirement(service_id=service_id, **payload.model_dump())
    db.add(item)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="service.requirement.create", entity_type="ServiceRequirement", entity_id=str(item.id), details=str(service_id)))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{service_id}/requirements/{item_id}", response_model=ServiceItemResponse)
def update_requirement(service_id: UUID, item_id: UUID, payload: ServiceItemUpdate, current_user: User = Depends(require_permission("services.edit")), db: Session = Depends(get_db)) -> ServiceRequirement:
    _service(db, current_user.company_id, service_id)
    _validate_item_payload(payload)
    item = db.get(ServiceRequirement, item_id)
    if item is None or item.service_id != service_id:
        raise HTTPException(status_code=404, detail="Service requirement not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="service.requirement.update", entity_type="ServiceRequirement", entity_id=str(item.id), details=str(service_id)))
    db.commit()
    db.refresh(item)
    return item


@router.get("/{service_id}/deliverables", response_model=list[ServiceItemResponse])
def list_deliverables(service_id: UUID, current_user: User = Depends(require_permission("services.view")), db: Session = Depends(get_db)) -> list[ServiceDeliverable]:
    _service(db, current_user.company_id, service_id)
    return list(db.scalars(select(ServiceDeliverable).where(ServiceDeliverable.service_id == service_id).order_by(ServiceDeliverable.sort_order, ServiceDeliverable.name)).all())


@router.post("/{service_id}/deliverables", response_model=ServiceItemResponse, status_code=status.HTTP_201_CREATED)
def create_deliverable(service_id: UUID, payload: ServiceItemCreate, current_user: User = Depends(require_permission("services.edit")), db: Session = Depends(get_db)) -> ServiceDeliverable:
    _service(db, current_user.company_id, service_id)
    _validate_item_payload(payload)
    item = ServiceDeliverable(service_id=service_id, **payload.model_dump())
    db.add(item)
    db.flush()
    db.add(AuditLog(actor_user_id=current_user.id, action="service.deliverable.create", entity_type="ServiceDeliverable", entity_id=str(item.id), details=str(service_id)))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{service_id}/deliverables/{item_id}", response_model=ServiceItemResponse)
def update_deliverable(service_id: UUID, item_id: UUID, payload: ServiceItemUpdate, current_user: User = Depends(require_permission("services.edit")), db: Session = Depends(get_db)) -> ServiceDeliverable:
    _service(db, current_user.company_id, service_id)
    _validate_item_payload(payload)
    item = db.get(ServiceDeliverable, item_id)
    if item is None or item.service_id != service_id:
        raise HTTPException(status_code=404, detail="Service deliverable not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.add(AuditLog(actor_user_id=current_user.id, action="service.deliverable.update", entity_type="ServiceDeliverable", entity_id=str(item.id), details=str(service_id)))
    db.commit()
    db.refresh(item)
    return item
