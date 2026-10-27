from app.ai_assistant.contracts import AIActionKind
from app.ai_assistant.use_cases import (
    APPROVED_AI_USE_CASES,
    AIUseCaseCategory,
    get_use_case,
    list_use_cases,
)


def test_catalogue_is_unique_and_complete_enough_for_approved_4232_scope() -> None:
    keys = [item.key for item in APPROVED_AI_USE_CASES]
    assert len(keys) == len(set(keys))
    assert len(APPROVED_AI_USE_CASES) >= 40

    expected = {
        "today_attention",
        "prospect_followups",
        "sales_pipeline",
        "project_risks",
        "unpaid_client_payments",
        "global_search",
        "create_followup_task",
        "schedule_followup",
        "record_activity",
        "update_allowed_task_field",
        "recommend_next_best_action",
        "founder_daily_briefing",
    }
    assert expected.issubset(keys)


def test_read_and_write_use_cases_are_separated() -> None:
    reads = list_use_cases(AIActionKind.READ)
    writes = list_use_cases(AIActionKind.WRITE)

    assert reads
    assert writes
    assert all(item.action_kind is AIActionKind.READ for item in reads)
    assert all(item.action_kind is AIActionKind.WRITE for item in writes)
    assert all(not item.confirmation_required for item in reads)
    assert all(item.confirmation_required for item in writes)


def test_future_intelligence_is_advisory_only() -> None:
    intelligence = [
        item for item in APPROVED_AI_USE_CASES if item.category is AIUseCaseCategory.INTELLIGENCE
    ]
    assert intelligence
    assert all(item.advisory_only for item in intelligence)
    assert all(item.action_kind is AIActionKind.READ for item in intelligence)


def test_use_case_lookup_is_allow_list_only() -> None:
    assert get_use_case("sales_pipeline") is not None
    assert get_use_case("not-approved") is None
