import json
from uuid import uuid4

import pytest

from app.ai_assistant.audit import AIAuditEvent, AIAuditRecorder, record_ai_audit
from app.shared.models import AuditLog


class FakeSession:
    def __init__(self) -> None:
        self.items: list[AuditLog] = []
        self.flush_count = 0

    def add(self, instance: AuditLog) -> None:
        self.items.append(instance)

    def flush(self) -> None:
        self.flush_count += 1


def make_event(**overrides):
    values = {
        "user_id": uuid4(),
        "company_id": uuid4(),
        "request_id": uuid4(),
        "user_request": "Create a follow-up task for ABC",
        "normalized_intent": "create_followup",
        "tool_name": "create_followup",
        "target_entity_type": "prospect",
        "target_entity_id": uuid4(),
        "action_metadata": {"due_at": "2026-10-29T10:00:00+00:00"},
        "permission_decision": "allowed",
        "business_rule_decision": "allowed",
        "confirmation_state": "confirmed",
        "execution_result": "success",
        "resulting_record_ids": (uuid4(),),
    }
    values.update(overrides)
    return AIAuditEvent(**values)


def test_audit_event_contains_required_trace_context_without_secrets() -> None:
    event = make_event()
    payload = json.loads(event.to_details())

    assert payload["company_id"] == str(event.company_id)
    assert payload["request_id"] == str(event.request_id)
    assert payload["user_request"] == event.user_request
    assert payload["tool_name"] == event.tool_name
    assert payload["permission_decision"] == "allowed"
    assert payload["business_rule_decision"] == "allowed"
    assert payload["confirmation_state"] == "confirmed"
    assert payload["execution_result"] == "success"
    assert "api_key" not in event.to_details().lower()
    assert "password" not in event.to_details().lower()
    assert "secret" not in event.to_details().lower()


def test_recorder_persists_ai_event_with_request_reference() -> None:
    session = FakeSession()
    event = make_event()

    reference = AIAuditRecorder().record(session, event)

    assert reference
    assert session.flush_count == 1
    assert len(session.items) == 1
    audit = session.items[0]
    assert audit.actor_user_id == event.user_id
    assert audit.action == "ai_assistant"
    assert audit.entity_type == "ai_request"
    assert audit.entity_id == str(event.request_id)
    payload = json.loads(audit.details)
    assert payload["company_id"] == str(event.company_id)
    assert payload["audit_reference"] == reference


def test_convenience_entry_point_records_same_contract() -> None:
    session = FakeSession()
    event = make_event(read_only=True, execution_result="retrieved")

    reference = record_ai_audit(session, event)

    assert reference
    payload = json.loads(session.items[0].details)
    assert payload["read_only"] is True
    assert payload["execution_result"] == "retrieved"


def test_failure_event_preserves_failure_and_target_context() -> None:
    session = FakeSession()
    event = make_event(
        permission_decision="allowed",
        business_rule_decision="allowed",
        confirmation_state="confirmed",
        execution_result="failed",
        failure_error="downstream_api_error",
    )

    record_ai_audit(session, event)
    payload = json.loads(session.items[0].details)

    assert payload["failure_error"] == "downstream_api_error"
    assert payload["target_entity_type"] == "prospect"
    assert payload["target_entity_id"] == str(event.target_entity_id)


def test_oversized_audit_metadata_is_rejected_before_persist() -> None:
    session = FakeSession()
    event = make_event(action_metadata={"large": "x" * 3900})

    with pytest.raises(ValueError, match="exceeds the AuditLog details limit"):
        record_ai_audit(session, event)

    assert session.items == []
    assert session.flush_count == 0
