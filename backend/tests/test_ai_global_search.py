from uuid import uuid4

import pytest

from app.ai_assistant.global_search import (
    AIGlobalSearchResolver,
    AISearchContext,
    AISearchResult,
    resolve_ai_entity,
)


def context(*permissions: str) -> AISearchContext:
    return AISearchContext(
        user_id=uuid4(),
        company_id=uuid4(),
        permission_codes=frozenset(permissions),
    )


def result(title: str, entity_type: str = "client") -> dict[str, str | None]:
    return {
        "type": entity_type,
        "id": str(uuid4()),
        "title": title,
        "subtitle": None,
        "status": "active",
    }


def test_exact_match_is_resolved_and_scope_is_forwarded() -> None:
    ctx = context("global_search.view")
    calls: list[dict] = []

    def search(**kwargs):
        calls.append(kwargs)
        return {"results": [result("ABC")]}

    resolved = AIGlobalSearchResolver(search).resolve(
        " ABC ", ctx, entity_type="client"
    )

    assert resolved.resolved
    assert resolved.result is not None
    assert resolved.result.title == "ABC"
    assert calls[0]["company_id"] == ctx.company_id
    assert calls[0]["user_id"] == ctx.user_id
    assert calls[0]["entity_type"] == "client"
    assert calls[0]["query"] == "ABC"


def test_single_non_exact_match_is_safely_resolved() -> None:
    ctx = context("global_search.view")
    resolved = resolve_ai_entity(
        lambda **_: {"results": [result("ABC Website")]}, "ABC", ctx
    )

    assert resolved.status == "resolved"
    assert resolved.result is not None
    assert resolved.result.title == "ABC Website"


def test_multiple_matches_require_clarification() -> None:
    ctx = context("global_search.view")
    resolved = resolve_ai_entity(
        lambda **_: {"results": [result("ABC Website"), result("ABC POS")]},
        "ABC",
        ctx,
    )

    assert resolved.needs_clarification
    assert resolved.reason_code == "multiple_matches"
    assert len(resolved.candidates) == 2


def test_multiple_exact_matches_require_clarification() -> None:
    ctx = context("global_search.view")
    resolved = resolve_ai_entity(
        lambda **_: {"results": [result("ABC"), result("ABC")]},
        "ABC",
        ctx,
    )

    assert resolved.status == "clarification_required"
    assert resolved.reason_code == "multiple_exact_matches"


def test_missing_record_is_not_guessed() -> None:
    ctx = context("global_search.view")
    resolved = resolve_ai_entity(lambda **_: {"results": []}, "Unknown", ctx)

    assert resolved.status == "not_found"
    assert resolved.result is None
    assert resolved.reason_code == "no_matching_record"


def test_permission_denied_does_not_call_search_or_expose_candidates() -> None:
    called = False

    def search(**_):
        nonlocal called
        called = True
        return {"results": [result("Secret Client")]}

    resolved = resolve_ai_entity(search, "Secret", context("task.view"))

    assert resolved.status == "blocked"
    assert resolved.reason_code == "permission_denied"
    assert resolved.result is None
    assert resolved.candidates == ()
    assert called is False


def test_invalid_query_and_limit_are_rejected_before_search() -> None:
    calls = 0

    def search(**_):
        nonlocal calls
        calls += 1
        return {"results": []}

    resolver = AIGlobalSearchResolver(search)
    ctx = context("global_search.view")

    with pytest.raises(ValueError, match="at least 2"):
        resolver.resolve("A", ctx)
    with pytest.raises(ValueError, match="between 1 and 50"):
        resolver.resolve("ABC", ctx, limit=51)

    assert calls == 0


def test_malformed_search_response_is_rejected() -> None:
    ctx = context("global_search.view")
    with pytest.raises(TypeError, match="results list"):
        resolve_ai_entity(lambda **_: {"results": {}}, "ABC", ctx)


def test_malformed_result_is_rejected() -> None:
    ctx = context("global_search.view")
    malformed = {
        "results": [{"type": "client", "id": "bad", "title": "ABC"}]
    }
    with pytest.raises(ValueError, match="invalid shape"):
        resolve_ai_entity(lambda **_: malformed, "ABC", ctx)


def test_result_contract_normalizes_uuid() -> None:
    record_id = uuid4()
    normalized = AISearchResult.from_mapping(
        {"type": "project", "id": str(record_id), "title": "POS"}
    )
    assert normalized.record_id == record_id
