from uuid import uuid4

import pytest

from app.ai_assistant.audit import AIAuditContext, AIAuditPolicy


class Sink:
    def __init__(self):
        self.contexts = []

    def record(self, context):
        self.contexts.append(context)
        return type("Record", (), {"audit_reference": f"audit:{context.request_id}", "context": context})()


def test_ai_audit_captures_required_context_without_provider_data():
    sink = Sink()
    request_id = uuid4()
    user_id = uuid4()
    company_id = uuid4()
    target_id = uuid4()
    context = AIAuditContext(
        user_id=user_id,
        company_id=company_id,
        request_id=request_id,
        user_request="Create a follow-up task",
        normalized_intent="create_followup",
        tool_name="create_followup",
        target_entity_type="prospect",
        target_entity_id=target_id,
        input_metadata={"priority": "high"},
        permission_decision="allowed",
        business_rule_decision="allowed",
        confirmation_state="confirmed",
        execution_result="success",
        resulting_record_ids=(uuid4(),),
    )
    result = AIAuditPolicy(sink).record(context)
    assert result.audit_reference == f"audit:{request_id}"
    assert sink.contexts == [context]


def test_ai_audit_requires_request_intent_and_tool():
    sink = Sink()
    base = dict(user_id=uuid4(), company_id=uuid4(), request_id=uuid4())
    with pytest.raises(ValueError):
        AIAuditPolicy(sink).record(AIAuditContext(**base, user_request=" ", normalized_intent="x", tool_name="x"))
    with pytest.raises(ValueError):
        AIAuditPolicy(sink).record(AIAuditContext(**base, user_request="x", normalized_intent=" ", tool_name="x"))
    with pytest.raises(ValueError):
        AIAuditPolicy(sink).record(AIAuditContext(**base, user_request="x", normalized_intent="x", tool_name=" "))


def test_ai_audit_requires_target_type_for_target_id():
    sink = Sink()
    context = AIAuditContext(
        user_id=uuid4(),
        company_id=uuid4(),
        request_id=uuid4(),
        user_request="Open record",
        normalized_intent="open_record",
        tool_name="global_search",
        target_entity_id=uuid4(),
    )
    with pytest.raises(ValueError):
        AIAuditPolicy(sink).record(context)
