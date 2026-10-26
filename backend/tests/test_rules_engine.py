from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.rules.schemas import RuleCreate, RuleEvaluateRequest, SOPCreate


def test_sop_requires_steps_before_activation_is_enforced_by_api_contract():
    sop = SOPCreate(sop_key="SOP-001", name="Project Development", steps=[])
    assert sop.status == "draft"
    assert sop.is_enforced is True


def test_business_rule_schema_captures_conditions_actions_roles_and_enforcement():
    rule = RuleCreate(
        rule_key="RULE-001",
        name="Approval before development",
        trigger_event="before_action",
        applies_to="project",
        required_conditions={"status": "requirements_approved"},
        required_actions=["start_development"],
        prohibited_actions=["start_without_approval"],
        allowed_roles=["Founder"],
        enforcement_mode="block",
    )
    assert rule.required_conditions["status"] == "requirements_approved"
    assert "start_development" in rule.required_actions
    assert rule.enforcement_mode == "block"


def test_rule_rejects_invalid_enforcement_mode():
    with pytest.raises(ValidationError):
        RuleCreate(rule_key="RULE-002", name="Bad", trigger_event="event", applies_to="project", enforcement_mode="reject")


def test_evaluation_request_accepts_context_and_actor_scope():
    user_id = uuid4()
    request = RuleEvaluateRequest(
        trigger_event="before_action",
        applies_to="project",
        action="start_development",
        context={"status": "requirements_approved"},
        user_id=user_id,
        role_names=["Founder"],
    )
    assert request.user_id == user_id
    assert request.context["status"] == "requirements_approved"
