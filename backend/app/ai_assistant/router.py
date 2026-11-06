"""Authenticated API adapter for the provider-neutral AI Assistant runtime.

This first runtime slice exposes registered read capabilities only. It deliberately
does not pretend to provide natural-language model inference or enable writes.
"""

from dataclasses import replace
from datetime import date, datetime, time, timezone
from threading import Lock
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_permission
from app.analytics.router import dashboard as analytics_dashboard
from app.calendar.router import list_events
from app.clients.router import get_workspace as get_client_workspace
from app.command_center.router import get_command_center
from app.communication.router import list_activities
from app.crm.router import create_follow_up_record, crm_pipeline, list_follow_ups, list_opportunities
from app.finance.router import dashboard as finance_dashboard, list_milestones
from app.freelancers.router import workspace as freelancer_workspace
from app.notifications.router import list_notifications
from app.projects.router import list_projects, workspace as project_workspace
from app.sales.router import pipeline as sales_pipeline
from app.core.database import SessionLocal, get_db
from app.global_search.router import search as global_search
from app.shared.models import User
from app.tasks.router import create_task_record, list_tasks
from app.tasks.schemas import TaskCreate, TaskResponse
from app.crm.schemas import FollowUpCreate, FollowUpResponse
from app.rules.router import evaluate_rules
from app.rules.schemas import RuleEvaluateRequest

from .audit import AIAuditEvent, AIAuditRecorder
from .business_rules import AIBusinessRuleRequest, AIBusinessRulesPolicy
from .execution import AIAuditedActionExecutor
from .contracts import AIActionKind, AIRequest, AIRecordReference, AIResponse, AIResponseType
from .orchestrator import AIOrchestrator
from .rbac import AIToolRBACPolicy
from .read_write import AIReadWritePolicy
from .registry import get_default_ai_tool_registry
from .safety import AISafetyPolicy, AIWritePreview, canonical_payload_hash

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])
WRITE_REGISTRY = get_default_ai_tool_registry()
WRITE_SAFETY_POLICY = AISafetyPolicy(WRITE_REGISTRY)
PENDING_WRITE_PREVIEWS: dict[UUID, tuple[AIRequest, AIWritePreview, UUID, UUID, datetime]] = {}
PENDING_WRITE_LOCK = Lock()

DOMAIN_PERMISSIONS = {
    "get_today_attention": "command_center.view",
    "get_tasks": "tasks.view",
    "get_followups": "crm.followups.view",
    "get_sales_pipeline": "sales.pipeline.view",
    "get_prospect_followups": "crm.pipeline.view",
    "get_proposals": "sales.pipeline.view",
    "get_project_milestones": "projects.view",
    "get_client_summary": "clients.view",
    "get_project_summary": "projects.view",
    "get_opportunity_summary": "crm.opportunities.view",
    "get_project_risks": "projects.view",
    "get_opportunities": "crm.opportunities.view",
    "get_projects": "projects.view",
    "get_unpaid_payments": "finance.milestones.view",
    "get_financial_summary": "finance.dashboard.view",
    "get_freelancer_workload": "freelancers.view",
    "get_calendar_events": "calendar.events.view",
    "get_notifications": "notifications.view",
    "get_communication_history": "communication.activities.view",
    "get_analytics_summary": "analytics.dashboard.view",
    "global_search": "global_search.view",
}

READ_HANDLERS = frozenset({
    "get_today_attention", "get_tasks", "get_followups", "get_sales_pipeline",
    "get_prospect_followups", "get_proposals", "get_opportunities", "get_projects",
    "get_project_milestones", "get_client_summary", "get_project_summary",
    "get_opportunity_summary", "get_project_risks",
    "get_unpaid_payments", "get_financial_summary", "get_freelancer_workload",
    "get_calendar_events", "get_notifications", "get_communication_history",
    "get_analytics_summary", "global_search",
})


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
    try:
        AIReadWritePolicy(registry).validate_request(tool, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if tool_name == "global_search":
        query = payload.get("query")
        if not isinstance(query, str) or not 2 <= len(query.strip()) <= 120:
            raise HTTPException(status_code=422, detail="Search query must contain 2-120 characters.")
        entity_types = payload.get("entity_types", [])
        if not isinstance(entity_types, list) or len(entity_types) > 1:
            raise HTTPException(status_code=422, detail="Select at most one entity type per search.")
        if entity_types and (
            not isinstance(entity_types[0], str)
            or not entity_types[0].replace("_", "").isalnum()
            or entity_types[0].lower() != entity_types[0]
        ):
            raise HTTPException(status_code=422, detail="Invalid entity type.")
    else:
        for field_name, field_schema in tool.input_schema.get("properties", {}).items():
            if field_schema.get("format") == "uuid" and field_name in payload:
                try:
                    UUID(str(payload[field_name]))
                except (TypeError, ValueError) as exc:
                    raise HTTPException(status_code=422, detail=f"{field_name} must be a valid UUID.") from exc

    if tool_name == "get_tasks":
        if "status" in payload and not isinstance(payload["status"], str):
            raise HTTPException(status_code=422, detail="Task status must be text.")
        if "due_before" in payload:
            try:
                value = payload["due_before"]
                if not isinstance(value, str):
                    raise TypeError("due_before must be text")
                if "T" not in value and " " not in value:
                    date.fromisoformat(value)
                else:
                    datetime.fromisoformat(value)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail="due_before must be an ISO date or datetime.") from exc


def _read_handler(tool_name: str, payload: dict[str, Any], current_user: User, db: Session):
    registry = get_default_ai_tool_registry()
    tool = registry.require(tool_name)
    permission = DOMAIN_PERMISSIONS.get(tool_name, tool.required_permission)
    if permission:
        require_permission(permission)(current_user)

    if tool_name == "global_search":
        result = global_search(
            q=payload["query"].strip(),
            entity_type=(payload.get("entity_types") or [None])[0],
            current_user=current_user,
            db=db,
        )
        return result["results"]
    if tool_name == "get_tasks":
        tasks = list_tasks(current_user=current_user, db=db)
        if "status" in payload:
            tasks = [task for task in tasks if task.status == payload["status"]]
        if "due_before" in payload:
            value = payload["due_before"]
            if "T" not in value and " " not in value:
                boundary = datetime.combine(date.fromisoformat(value), time.max, tzinfo=timezone.utc)
            else:
                boundary = datetime.fromisoformat(value)
            if boundary.tzinfo is None:
                boundary = boundary.replace(tzinfo=timezone.utc)
            tasks = [task for task in tasks if task.due_at is not None and task.due_at <= boundary]
        return [_serialize_task(task) for task in tasks]
    if tool_name == "get_today_attention":
        return get_command_center(current_user=current_user, db=db).model_dump(mode="json")
    if tool_name == "get_followups":
        return [item.model_dump(mode="json") for item in list_follow_ups(current_user=current_user, db=db)]
    if tool_name == "get_sales_pipeline":
        return [item.model_dump(mode="json") for item in sales_pipeline(current_user=current_user, db=db)]
    if tool_name == "get_prospect_followups":
        prospects = crm_pipeline(current_user=current_user, db=db)["prospects"]
        now = datetime.now(timezone.utc)
        due = []
        for prospect in prospects:
            value = prospect.get("next_action_at")
            if not value:
                continue
            due_at = datetime.fromisoformat(value) if isinstance(value, str) else value
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            if due_at <= now:
                due.append(prospect)
        return due
    if tool_name == "get_proposals":
        return [
            item.model_dump(mode="json")
            for item in sales_pipeline(current_user=current_user, db=db)
            if item.proposal_status is not None
        ]
    if tool_name == "get_opportunities":
        return [item.model_dump(mode="json") for item in list_opportunities(current_user=current_user, db=db)]
    if tool_name == "get_projects":
        return [item.model_dump(mode="json") for item in list_projects(current_user=current_user, db=db)]
    if tool_name == "get_project_milestones":
        from app.projects.router import list_milestones as list_project_milestones

        return [
            item.model_dump(mode="json")
            for item in list_project_milestones(
                project_id=UUID(payload["project_id"]),
                current_user=current_user,
                db=db,
            )
        ]
    if tool_name == "get_client_summary":
        return get_client_workspace(
            client_id=UUID(payload["client_id"]),
            current_user=current_user,
            db=db,
        ).model_dump(mode="json")
    if tool_name == "get_project_summary":
        return project_workspace(
            project_id=UUID(payload["project_id"]),
            current_user=current_user,
            db=db,
        ).model_dump(mode="json")
    if tool_name == "get_opportunity_summary":
        opportunity_id = UUID(payload["opportunity_id"])
        opportunities = list_opportunities(current_user=current_user, db=db)
        match = next((item for item in opportunities if item.id == opportunity_id), None)
        if match is None:
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        return match.model_dump(mode="json")
    if tool_name == "get_project_risks":
        projects = list_projects(current_user=current_user, db=db)
        workspaces = [
            project_workspace(project_id=item.id, current_user=current_user, db=db)
            for item in projects[:100]
        ]
        return [
            risk.model_dump(mode="json")
            for workspace in workspaces
            for risk in workspace.risks
            if risk.status == "open"
        ]
    if tool_name == "get_unpaid_payments":
        milestones = list_milestones(current_user=current_user, db=db)
        return [item.model_dump(mode="json") for item in milestones if item.status != "paid"]
    if tool_name == "get_financial_summary":
        return finance_dashboard(current_user=current_user, db=db).model_dump(mode="json")
    if tool_name == "get_freelancer_workload":
        return freelancer_workspace(current_user=current_user, db=db).model_dump(mode="json")
    if tool_name == "get_calendar_events":
        return [item.model_dump(mode="json") for item in list_events(current_user=current_user, db=db, limit=100)]
    if tool_name == "get_notifications":
        return [item.model_dump(mode="json") for item in list_notifications(current_user=current_user, db=db, unread_only=True, limit=100)]
    if tool_name == "get_communication_history":
        return [item.model_dump(mode="json") for item in list_activities(current_user=current_user, db=db, limit=50)]
    if tool_name == "get_analytics_summary":
        return analytics_dashboard(current_user=current_user, db=db)
    raise HTTPException(status_code=501, detail="This registered AI read capability is not connected to an OS API yet.")


@router.get("/tools")
def list_ai_read_tools(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    registry = get_default_ai_tool_registry()
    policy = AIToolRBACPolicy()
    available = []
    for tool in registry.list(AIActionKind.READ):
        if tool.name not in READ_HANDLERS:
            continue
        effective_tool = replace(
            tool,
            required_permission=DOMAIN_PERMISSIONS.get(tool.name, tool.required_permission),
        )
        decision = policy.authorize_user(effective_tool, current_user)
        if decision.allowed:
            available.append({
                "name": tool.name,
                "purpose": tool.purpose,
                "input_schema": tool.input_schema,
            })
    write_available = []
    for tool in registry.list(AIActionKind.WRITE):
        if tool.name not in {"create_task", "create_followup"}:
            continue
        effective_tool = replace(
            tool,
            required_permission=DOMAIN_PERMISSIONS.get(tool.name, tool.required_permission),
        )
        decision = policy.authorize_user(effective_tool, current_user)
        if decision.allowed and "rules_engine.evaluate" in policy.permission_codes_from_user(current_user):
            write_available.append({
                "name": tool.name,
                "purpose": tool.purpose,
                "input_schema": tool.input_schema,
                "requires_confirmation": tool.requires_confirmation,
            })
    return {"tools": available, "write_tools": write_available, "provider_connected": False}


@router.post("/read", response_model=AIResponse)
def execute_ai_read(
    invocation: AIReadInvocation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIResponse:
    request = AIRequest(message=invocation.message, context=invocation.input)
    registry = get_default_ai_tool_registry()
    tool = registry.get(invocation.tool_name)
    if tool is None or tool.action_kind != AIActionKind.READ:
        raise HTTPException(status_code=404, detail="Registered read capability not found.")
    if tool.name not in READ_HANDLERS:
        raise HTTPException(status_code=501, detail="This registered AI read capability is not connected to an OS API yet.")

    effective_tool = replace(
        tool,
        required_permission=DOMAIN_PERMISSIONS.get(tool.name, tool.required_permission),
    )
    decision = AIToolRBACPolicy().authorize_user(effective_tool, current_user)
    if not decision.allowed:
        return AIResponse(
            request_id=request.request_id,
            intent=tool.name,
            response_type=AIResponseType.BLOCKED,
            summary="You do not have permission to access this information.",
            error_code="permission_denied",
        )

    _validate_read_input(tool.name, invocation.input)
    orchestrator = AIOrchestrator(registry)
    result = orchestrator.execute_read(
        request,
        tool.name,
        handler=lambda request, context: _read_handler(tool.name, context, current_user, db),
    )

    records = []
    items = [result] if isinstance(result, dict) else list(result)
    for item in items:
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
    summary = f"Found {len(items)} result(s)."
    return AIResponse(
        request_id=request.request_id,
        intent=tool.name,
        response_type=AIResponseType.ANSWER,
        summary=summary,
        data={"items": items},
        records=records,
        audit_reference=audit_reference,
    )


class AIWriteInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=4000)
    tool_name: str = Field(min_length=1, max_length=100)
    input: dict[str, Any] = Field(default_factory=dict)


class AIWriteConfirmation(AIWriteInvocation):
    preview_id: UUID


class _ExistingRulesEngineEvaluator:
    def __init__(self, current_user: User, db: Session) -> None:
        self.current_user = current_user
        self.db = db

    def evaluate(self, request: AIBusinessRuleRequest):
        require_permission("rules_engine.evaluate")(self.current_user)
        return evaluate_rules(
            RuleEvaluateRequest(
                trigger_event=request.trigger_event,
                applies_to=request.applies_to,
                action=request.action,
                context=request.context,
                user_id=request.user_id,
                role_names=list(request.role_names),
            ),
            current_user=self.current_user,
            db=self.db,
        )


@router.post("/write/preview", response_model=AIResponse)
def preview_ai_write(
    invocation: AIWriteInvocation,
    current_user: User = Depends(get_current_user),
) -> AIResponse:
    tool = WRITE_REGISTRY.get(invocation.tool_name)
    if tool is None or tool.action_kind != AIActionKind.WRITE:
        raise HTTPException(status_code=404, detail="Registered write capability not found.")
    if tool.name != "create_task":
        raise HTTPException(status_code=501, detail="This write capability is not enabled for execution yet.")

    effective_tool = replace(
        tool,
        required_permission=DOMAIN_PERMISSIONS.get(tool.name, tool.required_permission),
    )
    decision = AIToolRBACPolicy().authorize_user(effective_tool, current_user)
    if not decision.allowed:
        return AIResponse(
            request_id=UUID(int=0),
            intent=tool.name,
            response_type=AIResponseType.BLOCKED,
            summary="You do not have permission to create this record.",
            error_code="permission_denied",
        )

    try:
        AIReadWritePolicy(WRITE_REGISTRY).validate_request(tool, invocation.input)
        if tool.name == "create_task":
            preview_payload = TaskCreate.model_validate(invocation.input).model_dump(mode="json")
            action_label = "Create task"
        else:
            target_field = "prospect_id" if invocation.input["target_type"] == "prospect" else "contact_id"
            followup_input = {
                target_field: UUID(invocation.input["target_id"]),
                "owner_user_id": current_user.id,
                "title": invocation.input["title"],
                "due_at": invocation.input["due_at"],
                "notes": invocation.input.get("notes"),
            }
            preview_payload = FollowUpCreate.model_validate(followup_input).model_dump(mode="json")
            action_label = "Create CRM follow-up"
        request = AIRequest(message=invocation.message, context=invocation.input)
        preview = WRITE_SAFETY_POLICY.preview_write(request, tool.name, invocation.input)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="The task details are invalid. Review the required fields and try again.") from exc

    with PENDING_WRITE_LOCK:
        now = datetime.now(timezone.utc)
        expired = [
            preview_id
            for preview_id, pending in PENDING_WRITE_PREVIEWS.items()
            if now - pending[4] >= WRITE_SAFETY_POLICY.ttl
        ]
        for preview_id in expired:
            PENDING_WRITE_PREVIEWS.pop(preview_id, None)
        while len(PENDING_WRITE_PREVIEWS) >= 500:
            PENDING_WRITE_PREVIEWS.pop(next(iter(PENDING_WRITE_PREVIEWS)))
        PENDING_WRITE_PREVIEWS[preview.preview_id] = (
            request,
            preview,
            current_user.id,
            current_user.company_id,
            now,
        )

    return AIResponse(
        request_id=request.request_id,
        intent=tool.name,
        response_type=AIResponseType.ACTION_PREVIEW,
        summary=preview.summary,
        data={
            "preview_id": str(preview.preview_id),
            "action": action_label,
            "payload": preview_payload,
        },
        actions_available=["confirm_create_task"],
        confirmation_required=True,
        warnings=list(preview.warnings),
    )


@router.post("/write/confirm", response_model=AIResponse)
def confirm_ai_write(
    confirmation: AIWriteConfirmation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIResponse:
    tool = WRITE_REGISTRY.get(confirmation.tool_name)
    if tool is None or tool.name not in {"create_task", "create_followup"} or tool.action_kind != AIActionKind.WRITE:
        raise HTTPException(status_code=404, detail="Confirmed write capability not found.")

    with PENDING_WRITE_LOCK:
        pending = PENDING_WRITE_PREVIEWS.get(confirmation.preview_id)
    if pending is None:
        raise HTTPException(status_code=409, detail="This preview is no longer available. Prepare a new preview.")

    request, preview, preview_user_id, preview_company_id, preview_created_at = pending
    if datetime.now(timezone.utc) - preview_created_at >= WRITE_SAFETY_POLICY.ttl:
        with PENDING_WRITE_LOCK:
            PENDING_WRITE_PREVIEWS.pop(confirmation.preview_id, None)
        raise HTTPException(status_code=409, detail="This preview has expired. Prepare a new preview.")
    if preview_user_id != current_user.id or preview_company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="This preview belongs to a different authenticated user.")
    if (
        confirmation.message != request.message
        or confirmation.tool_name != preview.tool_name
        or canonical_payload_hash(confirmation.input) != preview.payload_hash
    ):
        raise HTTPException(status_code=409, detail="The confirmed request does not exactly match the preview. Prepare a new preview.")

    effective_tool = replace(
        tool,
        required_permission=DOMAIN_PERMISSIONS.get(tool.name, tool.required_permission),
    )
    authorization = AIToolRBACPolicy().authorize_user(effective_tool, current_user)
    if not authorization.allowed:
        return AIResponse(
            request_id=request.request_id,
            intent=tool.name,
            response_type=AIResponseType.BLOCKED,
            summary="You do not have permission to create this record.",
            error_code="permission_denied",
        )

    try:
        task_payload = TaskCreate.model_validate(confirmation.input)
        role_names = tuple(
            role.name for role in current_user.roles
            if getattr(role, "is_active", True)
        )
        rule_request = AIBusinessRuleRequest(
            trigger_event="task.create",
            applies_to="task",
            action="create_task",
            context=task_payload.model_dump(mode="json"),
            user_id=current_user.id,
            role_names=role_names,
        )
        business_decision = AIBusinessRulesPolicy().evaluate(
            rule_request,
            _ExistingRulesEngineEvaluator(current_user, db),
        )
    except HTTPException:
        db.rollback()
        return AIResponse(
            request_id=request.request_id,
            intent=tool.name,
            response_type=AIResponseType.BLOCKED,
            summary="The task cannot be created because the required authorization or business-rule check is unavailable.",
            error_code="business_rule_check_unavailable",
        )
    except (ValueError, TypeError):
        db.rollback()
        raise HTTPException(status_code=422, detail="The confirmed task details are invalid.")

    if business_decision.blocked:
        event = AIAuditEvent(
            user_id=current_user.id,
            company_id=current_user.company_id,
            request_id=request.request_id,
            user_request=request.message,
            normalized_intent=tool.use_case_key or tool.name,
            tool_name=tool.name,
            target_entity_type="task",
            action_metadata={"task": task_payload.model_dump(mode="json")},
            action_payload_hash=preview.payload_hash,
            permission_decision="allowed",
            business_rule_decision=business_decision.reason_code,
            confirmation_state="confirmed",
            execution_result="blocked",
            read_only=False,
        )
        audit_reference = AIAuditRecorder().record(db, event)
        db.commit()
        with PENDING_WRITE_LOCK:
            PENDING_WRITE_PREVIEWS.pop(confirmation.preview_id, None)
        return AIResponse(
            request_id=request.request_id,
            intent=tool.name,
            response_type=AIResponseType.BLOCKED,
            summary="The task creation was blocked by an active Saru Systems business rule.",
            error_code="business_rule_blocked",
            warnings=list(business_decision.warnings),
            audit_reference=audit_reference,
        )

    try:
        ticket = WRITE_SAFETY_POLICY.issue_confirmation(preview)
        audit_event = AIAuditEvent(
            user_id=current_user.id,
            company_id=current_user.company_id,
            request_id=request.request_id,
            user_request=request.message,
            normalized_intent=tool.use_case_key or tool.name,
            tool_name=tool.name,
            target_entity_type="task",
            action_metadata={"task": task_payload.model_dump(mode="json")},
            action_payload_hash=preview.payload_hash,
            permission_decision="allowed",
            business_rule_decision=business_decision.reason_code,
            confirmation_state="confirmation_validated",
            read_only=False,
        )
        executor = AIAuditedActionExecutor(
            db,
            failure_audit_session_factory=SessionLocal,
        )
        orchestrator = AIOrchestrator(
            WRITE_REGISTRY,
            action_executor=executor,
            safety_policy=WRITE_SAFETY_POLICY,
        )

        def create_task_handler(request: AIRequest, context: dict[str, Any], payload: dict[str, Any]):
            task = create_task_record(
                TaskCreate.model_validate(payload),
                current_user,
                db,
                commit=False,
            )
            return {
                "record_id": str(task.id),
                "resulting_record_ids": [str(task.id)],
                "task": TaskResponse.model_validate(task).model_dump(mode="json"),
            }

        result = orchestrator.execute_write(
            request,
            tool.name,
            confirmation.input,
            confirmation_id=ticket.confirmation_id,
            authorization_decision=authorization,
            business_rule_decision=business_decision,
            audit_event=audit_event,
            handler=create_task_handler,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001 - return a safe failure without leaking internal details
        db.rollback()
        with PENDING_WRITE_LOCK:
            PENDING_WRITE_PREVIEWS.pop(confirmation.preview_id, None)
        if isinstance(exc, PermissionError):
            return AIResponse(
                request_id=request.request_id,
                intent=tool.name,
                response_type=AIResponseType.BLOCKED,
                summary="The task was not created because its confirmation or execution authorization was rejected.",
                error_code="write_confirmation_rejected",
            )
        return AIResponse(
            request_id=request.request_id,
            intent=tool.name,
            response_type=AIResponseType.ERROR,
            summary="The task could not be created. No success is being reported.",
            error_code="task_creation_failed",
        )

    with PENDING_WRITE_LOCK:
        PENDING_WRITE_PREVIEWS.pop(confirmation.preview_id, None)
    task_data = result["task"]
    record = AIRecordReference(
        entity_type="task",
        entity_id=UUID(result["record_id"]),
        label=task_data["title"],
    )
    return AIResponse(
        request_id=request.request_id,
        intent=tool.name,
        response_type=AIResponseType.ACTION_RESULT,
        summary="The task was created successfully.",
        data={"task": task_data},
        records=[record],
        audit_reference=executor.last_audit_reference,
    )
