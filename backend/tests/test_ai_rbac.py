from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ai_assistant import get_default_ai_tool_registry
from app.ai_assistant.rbac import AIAuthorizationContext, AIToolRBACPolicy, authorize_ai_tool


def _user(company_id, *permissions):
    return SimpleNamespace(id=uuid4(), company_id=company_id, roles=[SimpleNamespace(permissions=[SimpleNamespace(code=p) for p in permissions])])


def test_allowed_tool_uses_authenticated_user_permission():
    company_id = uuid4()
    user = _user(company_id, "sales.pipeline.view")
    tool = get_default_ai_tool_registry().require("get_sales_pipeline")
    decision = authorize_ai_tool(tool, user)
    assert decision.allowed is True
    assert decision.reason_code == "allowed"
    assert decision.company_id == company_id
    assert decision.user_id == user.id


def test_missing_permission_blocks_without_elevating_ai():
    company_id = uuid4()
    user = _user(company_id, "crm.view")
    tool = get_default_ai_tool_registry().require("get_sales_pipeline")
    decision = authorize_ai_tool(tool, user)
    assert decision.allowed is False
    assert decision.reason_code == "permission_denied"
    assert decision.required_permission == "sales.pipeline.view"


def test_cross_company_target_is_blocked_before_domain_execution():
    company_id = uuid4()
    user = _user(company_id, "global_search.view")
    tool = get_default_ai_tool_registry().require("global_search")
    decision = authorize_ai_tool(tool, user, target_company_id=uuid4())
    assert decision.allowed is False
    assert decision.reason_code == "company_scope_denied"


def test_same_company_target_is_allowed_with_permission():
    company_id = uuid4()
    user = _user(company_id, "global_search.view")
    tool = get_default_ai_tool_registry().require("global_search")
    decision = authorize_ai_tool(tool, user, target_company_id=company_id)
    assert decision.allowed is True


def test_permission_extraction_does_not_create_special_ai_privilege():
    company_id = uuid4()
    user = _user(company_id, "tasks.view")
    policy = AIToolRBACPolicy()
    codes = policy.permission_codes_from_user(user)
    assert codes == frozenset({"tasks.view"})
    assert "ai.admin" not in codes


def test_context_rejects_missing_security_identity():
    tool = get_default_ai_tool_registry().require("get_tasks")
    policy = AIToolRBACPolicy()
    with pytest.raises(ValueError, match="UUID id and company_id"):
        policy.authorize_user(tool, SimpleNamespace(id=None, company_id=None, roles=[]))


def test_context_is_explicitly_company_and_user_scoped():
    user_id = uuid4()
    company_id = uuid4()
    context = AIAuthorizationContext(user_id=user_id, company_id=company_id, permission_codes=frozenset({"tasks.view"}))
    tool = get_default_ai_tool_registry().require("get_tasks")
    decision = AIToolRBACPolicy().authorize(tool, context)
    assert decision.allowed is True
    assert decision.user_id == user_id
    assert decision.company_id == company_id
