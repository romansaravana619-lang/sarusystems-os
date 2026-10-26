from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.clients.models import Client
from app.core.database import get_db
from app.documents.models import Document
from app.documents.schemas import CATEGORIES, STATUSES, VISIBILITIES, DocumentCreate, DocumentDashboardResponse, DocumentResponse, DocumentUpdate
from app.freelancers.models import Freelancer
from app.projects.models import Project
from app.products.models import Product
from app.shared.models import AuditLog, User

router = APIRouter(prefix="/documents", tags=["documents"])

TRANSITIONS = {
    "draft": {"in_review", "archived"},
    "in_review": {"approved", "draft", "archived"},
    "approved": {"published", "archived", "superseded"},
    "published": {"superseded", "archived"},
    "superseded": {"archived"},
    "archived": set(),
}


def _record(db: Session, company_id: UUID, document_id: UUID) -> Document:
    obj = db.scalar(select(Document).where(Document.id == document_id, Document.company_id == company_id))
    if obj is None:
        raise HTTPException(404, detail="Document not found.")
    return obj


def _audit(db: Session, actor: User, action: str, obj: Document, details: str | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type="Document", entity_id=str(obj.id), details=details))


def _validate_user(db: Session, company_id: UUID, user_id: UUID | None) -> None:
    if user_id is not None and db.scalar(select(User.id).where(User.id == user_id, User.company_id == company_id, User.is_active.is_(True))) is None:
        raise HTTPException(400, detail="Referenced user must be an active user in this company.")


def _validate_links(db: Session, company_id: UUID, values: dict) -> None:
    checks = [(Client, "client_id", "Client"), (Project, "project_id", "Project"), (Freelancer, "freelancer_id", "Freelancer"), (Product, "product_id", "Product")]
    for model, key, label in checks:
        value = values.get(key)
        if value is not None and db.scalar(select(model.id).where(model.id == value, model.company_id == company_id)) is None:
            raise HTTPException(400, detail=f"{label} must belong to this company.")
    _validate_user(db, company_id, values.get("owner_user_id"))
    _validate_user(db, company_id, values.get("reviewer_user_id"))


def _validate_values(values: dict) -> None:
    if "category" in values and values["category"] not in CATEGORIES:
        raise HTTPException(400, detail=f"Invalid document category. Allowed: {', '.join(CATEGORIES)}")
    if "status" in values and values["status"] not in STATUSES:
        raise HTTPException(400, detail=f"Invalid document status. Allowed: {', '.join(STATUSES)}")
    if "visibility" in values and values["visibility"] not in VISIBILITIES:
        raise HTTPException(400, detail=f"Invalid document visibility. Allowed: {', '.join(VISIBILITIES)}")


@router.get("/dashboard", response_model=DocumentDashboardResponse)
def dashboard(current_user: User = Depends(require_permission("documents.dashboard.view")), db: Session = Depends(get_db)):
    base = Document.company_id == current_user.company_id
    return DocumentDashboardResponse(
        total_documents=db.scalar(select(func.count(Document.id)).where(base)) or 0,
        draft_documents=db.scalar(select(func.count(Document.id)).where(base, Document.status == "draft")) or 0,
        review_documents=db.scalar(select(func.count(Document.id)).where(base, Document.status == "in_review")) or 0,
        approved_documents=db.scalar(select(func.count(Document.id)).where(base, Document.status.in_(["approved", "published"]))) or 0,
        templates=db.scalar(select(func.count(Document.id)).where(base, Document.is_template.is_(True))) or 0,
        recent_documents=list(db.scalars(select(Document).where(base).order_by(Document.updated_at.desc()).limit(8)).all()),
    )


@router.get("/search", response_model=list[DocumentResponse])
def search_documents(q: str = Query(min_length=1), current_user: User = Depends(require_permission("documents.view")), db: Session = Depends(get_db)):
    term = f"%{q.strip()}%"
    return list(db.scalars(select(Document).where(Document.company_id == current_user.company_id, or_(Document.document_key.ilike(term), Document.title.ilike(term), Document.description.ilike(term), Document.content.ilike(term), Document.tags.ilike(term), Document.category.ilike(term), Document.document_type.ilike(term))).order_by(Document.updated_at.desc()).limit(50)).all())


@router.get("", response_model=list[DocumentResponse])
def list_documents(category: str | None = None, status_filter: str | None = Query(default=None, alias="status"), template_only: bool = False, current_user: User = Depends(require_permission("documents.view")), db: Session = Depends(get_db)):
    query = select(Document).where(Document.company_id == current_user.company_id)
    if category:
        query = query.where(Document.category == category)
    if status_filter:
        query = query.where(Document.status == status_filter)
    if template_only:
        query = query.where(Document.is_template.is_(True))
    return list(db.scalars(query.order_by(Document.updated_at.desc())).all())


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(p: DocumentCreate, current_user: User = Depends(require_permission("documents.create")), db: Session = Depends(get_db)):
    values = p.model_dump()
    _validate_values(values); _validate_links(db, current_user.company_id, values)
    if db.scalar(select(Document.id).where(Document.company_id == current_user.company_id, Document.document_key == p.document_key)) is not None:
        raise HTTPException(409, detail="Document key already exists.")
    obj = Document(company_id=current_user.company_id, **values)
    db.add(obj); db.flush(); _audit(db, current_user, "document.create", obj, obj.document_key); db.commit(); db.refresh(obj)
    return obj


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, current_user: User = Depends(require_permission("documents.view")), db: Session = Depends(get_db)):
    return _record(db, current_user.company_id, document_id)


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(document_id: UUID, p: DocumentUpdate, current_user: User = Depends(require_permission("documents.edit")), db: Session = Depends(get_db)):
    obj = _record(db, current_user.company_id, document_id)
    values = p.model_dump(exclude_unset=True)
    _validate_values(values); _validate_links(db, current_user.company_id, {**{k: getattr(obj, k) for k in ["owner_user_id", "reviewer_user_id", "client_id", "project_id", "freelancer_id", "product_id"]}, **values})
    target = values.get("status", obj.status)
    if target != obj.status and target not in TRANSITIONS[obj.status]:
        raise HTTPException(409, detail=f"Invalid document status transition: {obj.status} -> {target}.")
    if "title" in values and not values["title"].strip():
        raise HTTPException(400, detail="Document title cannot be empty.")
    for key, value in values.items():
        setattr(obj, key, value)
    _audit(db, current_user, "document.update", obj); db.commit(); db.refresh(obj)
    return obj


@router.post("/{document_id}/approve", response_model=DocumentResponse)
def approve_document(document_id: UUID, current_user: User = Depends(require_permission("documents.approve")), db: Session = Depends(get_db)):
    obj = _record(db, current_user.company_id, document_id)
    if obj.status != "in_review":
        raise HTTPException(409, detail="Only documents in review can be approved.")
    obj.status = "approved"; obj.approved_by_user_id = current_user.id; obj.approved_at = datetime.now(timezone.utc)
    _audit(db, current_user, "document.approve", obj); db.commit(); db.refresh(obj)
    return obj
