from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.clients.models import Client
from app.communication.models import ActivityRecord
from app.core.database import get_db
from app.documents.models import Document
from app.finance.models import FinancialTransaction, PaymentMilestone
from app.projects.models import Project
from app.shared.models import AuditLog, Contact, Opportunity, Prospect, User
from app.tasks.models import Task

router = APIRouter(prefix="/global-search", tags=["Global Search"])
PERMISSION = "global_search.view"
MAX_LIMIT = 50


def _match(*columns, q: str):
    pattern = f"%{q}%"
    return or_(*(column.ilike(pattern) for column in columns))


def _result(kind: str, record_id: UUID, title: str, subtitle: str | None = None, status: str | None = None):
    return {"type": kind, "id": str(record_id), "title": title, "subtitle": subtitle, "status": status}


@router.get("")
def search(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    entity_type: str | None = Query(default=None, pattern="^[a-z_]+$"),
    current_user: User = Depends(require_permission(PERMISSION)),
    db: Session = Depends(get_db),
):
    company_id = current_user.company_id
    requested = entity_type.lower() if entity_type else None
    results = []

    def add(kind: str, rows):
        if requested and requested != kind:
            return
        results.extend(rows)

    prospects = db.scalars(select(Prospect).where(Prospect.company_id == company_id, _match(Prospect.name, Prospect.company_name, Prospect.email, Prospect.phone, Prospect.industry, Prospect.notes, q)).limit(limit)).all()
    add("prospect", [_result("prospect", x.id, x.name, x.company_name or x.email, x.status) for x in prospects])

    clients = db.scalars(select(Client).where(Client.company_id == company_id, _match(Client.name, Client.company_name, Client.email, Client.phone, Client.industry, Client.notes, q)).limit(limit)).all()
    add("client", [_result("client", x.id, x.name, x.company_name or x.code, x.status) for x in clients])

    projects = db.scalars(select(Project).where(Project.company_id == company_id, _match(Project.name, Project.code, Project.description, Project.notes, q)).limit(limit)).all()
    add("project", [_result("project", x.id, x.name, x.code, x.status) for x in projects])

    opportunities = db.scalars(select(Opportunity).where(Opportunity.company_id == company_id, _match(Opportunity.name, Opportunity.service, Opportunity.notes, q)).limit(limit)).all()
    add("opportunity", [_result("opportunity", x.id, x.name, x.service, x.stage) for x in opportunities])

    tasks = db.scalars(select(Task).where(Task.company_id == company_id, _match(Task.title, Task.description, Task.expected_output, Task.founder_notes, Task.notes, q)).limit(limit)).all()
    add("task", [_result("task", x.id, x.title, x.expected_output, x.status) for x in tasks])

    documents = db.scalars(select(Document).where(Document.company_id == company_id, _match(Document.document_key, Document.title, Document.category, Document.document_type, Document.description, Document.content, Document.tags, Document.notes, q)).limit(limit)).all()
    add("document", [_result("document", x.id, x.title, x.document_key, x.status) for x in documents])

    payments = db.scalars(select(PaymentMilestone).where(PaymentMilestone.company_id == company_id, _match(PaymentMilestone.name, PaymentMilestone.notes, q)).limit(limit)).all()
    add("payment", [_result("payment", x.id, x.name, f"Amount {x.amount}", x.status) for x in payments])

    transactions = db.scalars(select(FinancialTransaction).where(FinancialTransaction.company_id == company_id, _match(FinancialTransaction.description, FinancialTransaction.category, FinancialTransaction.reference_type, FinancialTransaction.notes, q)).limit(limit)).all()
    add("financial_transaction", [_result("financial_transaction", x.id, x.description, x.category, x.status) for x in transactions])

    activities = db.scalars(select(ActivityRecord).where(ActivityRecord.company_id == company_id, _match(ActivityRecord.subject, ActivityRecord.summary, ActivityRecord.notes, ActivityRecord.activity_type, q)).limit(limit)).all()
    add("communication", [_result("communication", x.id, x.subject or x.activity_type, x.summary, x.direction) for x in activities])

    contacts = db.scalars(select(Contact).where(Contact.company_id == company_id, _match(Contact.name, Contact.company_name, Contact.email, Contact.phone, Contact.notes, q)).limit(limit)).all()
    add("contact", [_result("contact", x.id, x.name, x.company_name or x.email) for x in contacts])

    results = results[:limit]
    db.add(AuditLog(actor_user_id=current_user.id, action="global_search", entity_type="global_search", entity_id=None, details=f"query={q[:120]} results={len(results)}"))
    db.commit()
    return {"query": q, "count": len(results), "results": results}
