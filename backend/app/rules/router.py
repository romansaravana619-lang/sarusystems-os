import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.rules.models import BusinessRule, SOPDefinition
from app.rules.schemas import RuleCreate, RuleEvaluateRequest, RuleEvaluateResponse, RuleEvaluation, RuleResponse, RuleUpdate, SOPCreate, SOPResponse, SOPUpdate
from app.shared.models import AuditLog, User

router = APIRouter(prefix="/rules-engine", tags=["sop-business-rules"])


def _sop(db: Session, company_id: UUID, item_id: UUID) -> SOPDefinition:
    obj = db.scalar(select(SOPDefinition).where(SOPDefinition.id == item_id, SOPDefinition.company_id == company_id))
    if obj is None:
        raise HTTPException(404, "SOP not found.")
    return obj


def _rule(db: Session, company_id: UUID, item_id: UUID) -> BusinessRule:
    obj = db.scalar(select(BusinessRule).where(BusinessRule.id == item_id, BusinessRule.company_id == company_id))
    if obj is None:
        raise HTTPException(404, "Business rule not found.")
    return obj


def _user_check(db: Session, company_id: UUID, user_id: UUID | None) -> None:
    if user_id is not None and db.scalar(select(User.id).where(User.id == user_id, User.company_id == company_id, User.is_active.is_(True))) is None:
        raise HTTPException(400, "Referenced user must be an active user in this company.")


def _audit(db: Session, actor: User, action: str, entity_type: str, entity_id: UUID, details: str | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type=entity_type, entity_id=str(entity_id), details=details))


def _json_details(value: object) -> str:
    return json.dumps(value, default=str)[:4000]


def _rule_values(values: dict) -> dict:
    if "allowed_user_ids" in values:
        values["allowed_user_ids"] = [str(value) for value in values["allowed_user_ids"]]
    return values


@router.get("/dashboard")
def dashboard(current_user: User = Depends(require_permission("rules_engine.dashboard.view")), db: Session = Depends(get_db)):
    base_sop = SOPDefinition.company_id == current_user.company_id
    base_rule = BusinessRule.company_id == current_user.company_id
    return {"sops": db.scalar(select(func.count(SOPDefinition.id)).where(base_sop)) or 0, "active_sops": db.scalar(select(func.count(SOPDefinition.id)).where(base_sop, SOPDefinition.status == "active")) or 0, "rules": db.scalar(select(func.count(BusinessRule.id)).where(base_rule)) or 0, "active_rules": db.scalar(select(func.count(BusinessRule.id)).where(base_rule, BusinessRule.status == "active")) or 0, "enforced_rules": db.scalar(select(func.count(BusinessRule.id)).where(base_rule, BusinessRule.is_enforced.is_(True), BusinessRule.status == "active")) or 0}


@router.get("/sops", response_model=list[SOPResponse])
def list_sops(status_filter: str | None = Query(default=None, alias="status"), current_user: User = Depends(require_permission("rules_engine.sops.view")), db: Session = Depends(get_db)):
    query = select(SOPDefinition).where(SOPDefinition.company_id == current_user.company_id)
    if status_filter:
        query = query.where(SOPDefinition.status == status_filter)
    return list(db.scalars(query.order_by(SOPDefinition.updated_at.desc())).all())


@router.post("/sops", response_model=SOPResponse, status_code=status.HTTP_201_CREATED)
def create_sop(payload: SOPCreate, current_user: User = Depends(require_permission("rules_engine.sops.create")), db: Session = Depends(get_db)):
    _user_check(db, current_user.company_id, payload.owner_user_id)
    if db.scalar(select(SOPDefinition.id).where(SOPDefinition.company_id == current_user.company_id, SOPDefinition.sop_key == payload.sop_key)):
        raise HTTPException(409, "SOP key already exists.")
    obj = SOPDefinition(company_id=current_user.company_id, **payload.model_dump())
    db.add(obj); db.flush(); _audit(db, current_user, "sop.create", "SOPDefinition", obj.id, obj.sop_key); db.commit(); db.refresh(obj)
    return obj


@router.patch("/sops/{sop_id}", response_model=SOPResponse)
def update_sop(sop_id: UUID, payload: SOPUpdate, current_user: User = Depends(require_permission("rules_engine.sops.edit")), db: Session = Depends(get_db)):
    obj = _sop(db, current_user.company_id, sop_id)
    values = payload.model_dump(exclude_unset=True)
    _user_check(db, current_user.company_id, values.get("owner_user_id", obj.owner_user_id))
    if values.get("status") == "active" and not obj.steps and not values.get("steps"):
        raise HTTPException(409, "An SOP must define at least one step before activation.")
    for key, value in values.items(): setattr(obj, key, value)
    _audit(db, current_user, "sop.update", "SOPDefinition", obj.id); db.commit(); db.refresh(obj)
    return obj


@router.get("/rules", response_model=list[RuleResponse])
def list_rules(status_filter: str | None = Query(default=None, alias="status"), trigger_event: str | None = None, current_user: User = Depends(require_permission("rules_engine.rules.view")), db: Session = Depends(get_db)):
    query = select(BusinessRule).where(BusinessRule.company_id == current_user.company_id)
    if status_filter: query = query.where(BusinessRule.status == status_filter)
    if trigger_event: query = query.where(BusinessRule.trigger_event == trigger_event)
    return list(db.scalars(query.order_by(BusinessRule.priority.asc(), BusinessRule.updated_at.desc())).all())


@router.post("/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(payload: RuleCreate, current_user: User = Depends(require_permission("rules_engine.rules.create")), db: Session = Depends(get_db)):
    for user_id in [*payload.allowed_user_ids, payload.owner_user_id, payload.reviewer_user_id]: _user_check(db, current_user.company_id, user_id)
    if db.scalar(select(BusinessRule.id).where(BusinessRule.company_id == current_user.company_id, BusinessRule.rule_key == payload.rule_key)):
        raise HTTPException(409, "Business rule key already exists.")
    values = _rule_values(payload.model_dump())
    obj = BusinessRule(company_id=current_user.company_id, **values)
    db.add(obj); db.flush(); _audit(db, current_user, "business_rule.create", "BusinessRule", obj.id, obj.rule_key); db.commit(); db.refresh(obj)
    return obj


@router.patch("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(rule_id: UUID, payload: RuleUpdate, current_user: User = Depends(require_permission("rules_engine.rules.edit")), db: Session = Depends(get_db)):
    obj = _rule(db, current_user.company_id, rule_id)
    values = _rule_values(payload.model_dump(exclude_unset=True))
    for user_id in [*(values.get("allowed_user_ids") or obj.allowed_user_ids), values.get("owner_user_id", obj.owner_user_id), values.get("reviewer_user_id", obj.reviewer_user_id)]: _user_check(db, current_user.company_id, user_id)
    if values.get("status") == "active":
        conditions = values.get("required_conditions", obj.required_conditions)
        actions = values.get("required_actions", obj.required_actions)
        if not conditions and not actions:
            raise HTTPException(409, "An active business rule must define a condition or required action.")
    for key, value in values.items(): setattr(obj, key, value)
    _audit(db, current_user, "business_rule.update", "BusinessRule", obj.id); db.commit(); db.refresh(obj)
    return obj


def _matches(context: dict, expected: dict) -> bool:
    return all(context.get(key) == value for key, value in expected.items())


def _evaluate_rule(rule: BusinessRule, payload: RuleEvaluateRequest) -> RuleEvaluation:
    reasons: list[str] = []
    if not _matches(payload.context, rule.required_conditions): reasons.append("Required conditions are not satisfied.")
    if rule.prohibited_conditions and _matches(payload.context, rule.prohibited_conditions): reasons.append("Prohibited conditions are satisfied.")
    if rule.required_actions and payload.action not in rule.required_actions: reasons.append("Requested action is not an allowed required action for this rule.")
    if rule.prohibited_actions and payload.action in rule.prohibited_actions: reasons.append("Requested action is explicitly prohibited by this rule.")
    if rule.allowed_roles and not set(payload.role_names).intersection(rule.allowed_roles): reasons.append("Current user role is not allowed by this rule.")
    if rule.allowed_user_ids and (payload.user_id is None or str(payload.user_id) not in {str(x) for x in rule.allowed_user_ids}): reasons.append("Current user is not allowed by this rule.")
    passed = not reasons
    return RuleEvaluation(rule_id=rule.id, rule_key=rule.rule_key, name=rule.name, enforcement_mode=rule.enforcement_mode, passed=passed, blocked=(not passed and rule.enforcement_mode == "block"), reasons=reasons)


@router.post("/evaluate", response_model=RuleEvaluateResponse)
def evaluate_rules(payload: RuleEvaluateRequest, current_user: User = Depends(require_permission("rules_engine.evaluate")), db: Session = Depends(get_db)):
    rules = list(db.scalars(select(BusinessRule).where(BusinessRule.company_id == current_user.company_id, BusinessRule.status == "active", BusinessRule.is_enforced.is_(True), BusinessRule.trigger_event == payload.trigger_event, BusinessRule.applies_to == payload.applies_to).order_by(BusinessRule.priority.asc())).all())
    evaluations = [_evaluate_rule(rule, payload) for rule in rules]
    blocked = [item for item in evaluations if item.blocked]
    return RuleEvaluateResponse(allowed=not blocked, evaluations=evaluations)
