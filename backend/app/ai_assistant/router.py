"""Authenticated API adapter for the provider-neutral AI Assistant runtime.

This first runtime slice exposes registered read capabilities only. It deliberately
does not pretend to provide natural-language model inference or enable writes.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.global_search.router import search as global_search
from app.shared.models import User
from app.tasks.router import list_tasks
from app.tasks.schemas import TaskResponse

from .audit import AIAuditEvent, AIAuditRecorder
from .contracts import AIActionKind, AIRequest, AIRecordReference, AIResponse, AIResponseType
from .orchestrator import AIOrchestrator
from .rbac import AIToolRBACPolicy
from .read_write import AIReadWritePolicy
from .registry import get_default_ai_tool_registry

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])

READ_HANDLERS = frozenset({"get_tasks", "global_search"})


class AIReadInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    tool_name: str = Field(min_length=1, max_length=100)
    input: dict[str, Any] = Field(default_factory=dict)


def _serialize_task(task: object) -> dict[str, Any]:
    return TaskResponse.model_validate(task).model_dump(mode="json")


def _validate_read_input(tool_name: str, payload: dict[str, Any]) -> None:
    registry = get_default_ai_tool_registry()
    tool = registry.require(tool_name)
    AIReadWritePolicy(registry).validate_request(tool, payload)

    if tool_name == "global_search":
        query = payload.get("query")
        if not isinstance(query, str) or not 2 <= len(query.strip()) <= 120:
            raise HTTPException(status_code=422, detail="Search query must contain 2-120 characters.")
        entity_type = payload.get("entity_type")
        if entity_type is not None and (
            not isinstance(entity_type, str)
            or not entity_type.replace("_", "").isalnum()
            or entity_type.lower() != entity_type
        ):
            raise HTTPException(status_code=422, detail="Invalid entity_type.")
    elif tool_name == "get_tasks":
        if "status" in payload and not isinstance(payload["status"], str):
            raise HTTPException(status_code=422, detail="Task status must be text.")
        if "due_before" in payload:
            try:
                datetime.fromisoformat(payload["due_before"])
            except (TypeError, ValueError) as exc:
                try:
                    date.fromisoformat(payload["due_before"])
                except (TypeError, ValueError):
                    raise HTTPException(status_code=422, detail="due_before must be an ISO date or datetime.") from exc


def _read_handler(tool_name: str, payload: dict[str, Any], current_user: User, db: Session):
    if tool_name == "global_search":
        result = global_search(
            q=payload["query"].strip(),
            entity_type=payload.get("entity_type"),
            current_user=current_user,
            db=db,
        )
        return result["results"]
    if tool_name == "get_tasks":
        tasks = list_tasks(current_user=current_user, db=db)
        if "status" in payload:
            tasks = [task for task in tasks if task.status == payload["status"]]
        if "due_before" in payload:
            boundary = datetime.fromisoformat(payload["due_before"])
            if boundary.tzinfo is None:
                boundary = boundary.replace(tzinfo=current_user.created_at.tzinfo if getattr(current_user, "created_at", None) and current_user.created_at.tzinfo else None)
            tasks = [task for task in tasks if task.due_at is not None and task.due_at <= boundary]
        return [_serialize_task(task) for task in tasks]
    raise HTTPException(status_code=501, detail="This registered AI read capability is not connected to an OS API yet.")


@router.get("/tools")
def list_ai_read_tools(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    registry = get_default_ai_tool_registry()
    policy = AIToolRBACPolicy()
    available = []
    for tool in registry.list(AIActionKind.READ):
        if tool.name not in READ_HANDLERS:
            continue
        decision = policy.authorize_user(tool, current_user)
        if decision.allowed:
            available.append({
                "name": tool.name,
                "purpose": tool.purpose,
                "input_schema": tool.input_schema,
            })
    return {"tools": available, "provider_connected": False}


@router.post("/read", response_model=AIResponse)
def execute_ai_read(
    invocation: AIReadInvocation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIResponse:
    registry = get_default_ai_tool_registry()
    tool = registry.get(invocation.tool_name)
    if tool is None or tool.action_kind != AIActionKind.READ:
        raise HTTPException(status_code=404, detail="Registered read capability not found.")
    if tool.name not in READ_HANDLERS:
        raise HTTPException(status_code=501, detail="This registered AI read capability is not connected to an OS API yet.")

    decision = AIToolRBACPolicy().authorize_user(tool, current_user)
    if not decision.allowed:
        return AIResponse(
            request_id=UUID(int=0),
            intent=tool.name,
            response_type=AIResponseType.BLOCKED,
            summary="You do not have permission to access this information.",
            error_code="permission_denied",
        )

    _validate_read_input(tool.name, invocation.input)
    request = AIRequest(message=invocation.message, context=invocation.input)
    orchestrator = AIOrchestrator(registry)
    result = orchestrator.execute_read(
        request,
        tool.name,
        handler=lambda request, context: _read_handler(tool.name, context, current_user, db),
    )

    records = []
    for item in result:
        if not isinstance(item, dict) or not item.get("id") or not item.get("type"):
            continue
        try:
            records.append(AIRecordReference(
                entity_type=str(item["type"]),
                entity_id=UUID(str(item["id"])),
                label=str(item.get("title") or item.get("name") or item["id"]),
            ))
        except (ValueError, TypeError):
            continue

    audit_reference = AIAuditRecorder().record(
        db,
        AIAuditEvent(
            user_id=current_user.id,
            company_id=current_user.company_id,
            request_id=request.request_id,
            user_request=invocation.message,
            normalized_intent=tool.use_case_key or tool.name,
            tool_name=tool.name,
            permission_decision="allowed",
            read_only=True,
        ),
    )
    db.commit()
    summary = f"Found {len(result)} result{'s' if len(result) != 1 else ''}."
    return AIResponse(
        request_id=request.request_id,
        intent=tool.name,
        response_type=AIResponseType.ANSWER,
        summary=summary,
        data={"items": result},
        records=records,
        audit_reference=audit_reference,
    )
