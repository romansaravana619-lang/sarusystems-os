"""AI entity resolution boundary over the existing 4.22 Global Search surface."""

from dataclasses import dataclass
from typing import Any, Callable, Mapping
from uuid import UUID


_REQUIRED_PERMISSION = "global_search.view"


@dataclass(frozen=True, slots=True)
class AISearchContext:
    """Security context inherited from the authenticated AI request."""

    user_id: UUID
    company_id: UUID
    permission_codes: frozenset[str]


@dataclass(frozen=True, slots=True)
class AISearchResult:
    """Normalized result returned by the authoritative Global Search surface."""

    entity_type: str
    record_id: UUID
    title: str
    subtitle: str | None = None
    status: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AISearchResult":
        try:
            entity_type = str(value["type"])
            record_id = UUID(str(value["id"]))
            title = str(value["title"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Global Search result has an invalid shape") from exc
        return cls(
            entity_type=entity_type,
            record_id=record_id,
            title=title,
            subtitle=value.get("subtitle"),
            status=value.get("status"),
        )


@dataclass(frozen=True, slots=True)
class AIEntityResolution:
    """Safe resolution outcome for an AI reference."""

    status: str
    query: str
    result: AISearchResult | None = None
    candidates: tuple[AISearchResult, ...] = ()
    reason_code: str | None = None

    @property
    def resolved(self) -> bool:
        return self.status == "resolved" and self.result is not None

    @property
    def needs_clarification(self) -> bool:
        return self.status == "clarification_required"


class AIGlobalSearchResolver:
    """Resolve AI entity references using the existing 4.22 search contract."""

    REQUIRED_PERMISSION = _REQUIRED_PERMISSION

    def __init__(
        self,
        search: Callable[..., Mapping[str, Any]],
        *,
        permission: str = _REQUIRED_PERMISSION,
    ) -> None:
        self._search = search
        self._permission = permission

    @staticmethod
    def _normalize_query(query: str) -> str:
        normalized = " ".join(query.split())
        if len(normalized) < 2:
            raise ValueError("Search query must contain at least 2 characters")
        if len(normalized) > 120:
            raise ValueError("Search query must not exceed 120 characters")
        return normalized

    @staticmethod
    def _validate_entity_type(entity_type: str | None) -> str | None:
        if entity_type is None:
            return None
        normalized = entity_type.strip().lower()
        if not normalized or not normalized.replace("_", "").isalnum():
            raise ValueError("Invalid entity_type")
        return normalized

    @staticmethod
    def _coerce_results(
        payload: Mapping[str, Any],
    ) -> tuple[AISearchResult, ...]:
        raw_results = payload.get("results", ())
        if not isinstance(raw_results, list):
            raise ValueError("Global Search response must contain a results list")
        return tuple(AISearchResult.from_mapping(item) for item in raw_results)

    @staticmethod
    def _exact_matches(
        results: tuple[AISearchResult, ...],
        query: str,
    ) -> tuple[AISearchResult, ...]:
        folded = query.casefold()
        return tuple(
            result for result in results if result.title.strip().casefold() == folded
        )

    def resolve(
        self,
        query: str,
        context: AISearchContext,
        *,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> AIEntityResolution:
        """Resolve a natural-language reference without bypassing Global Search."""
        if self._permission not in context.permission_codes:
            return AIEntityResolution(
                status="blocked",
                query=query,
                reason_code="permission_denied",
            )
        if limit < 1 or limit > 50:
            raise ValueError("Limit must be between 1 and 50")

        normalized_query = self._normalize_query(query)
        normalized_entity_type = self._validate_entity_type(entity_type)

        # Company/user scope is supplied explicitly and forwarded to the
        # authoritative search boundary. The resolver never changes it.
        payload = self._search(
            query=normalized_query,
            limit=limit,
            entity_type=normalized_entity_type,
            user_id=context.user_id,
            company_id=context.company_id,
        )
        results = self._coerce_results(payload)

        if not results:
            return AIEntityResolution(
                status="not_found",
                query=normalized_query,
                reason_code="no_matching_record",
            )

        exact = self._exact_matches(results, normalized_query)
        if len(exact) == 1:
            return AIEntityResolution(
                status="resolved",
                query=normalized_query,
                result=exact[0],
            )
        if len(exact) > 1:
            return AIEntityResolution(
                status="clarification_required",
                query=normalized_query,
                candidates=exact,
                reason_code="multiple_exact_matches",
            )
        if len(results) == 1:
            return AIEntityResolution(
                status="resolved",
                query=normalized_query,
                result=results[0],
            )

        return AIEntityResolution(
            status="clarification_required",
            query=normalized_query,
            candidates=results,
            reason_code="multiple_matches",
        )


def resolve_ai_entity(
    search: Callable[..., Mapping[str, Any]],
    query: str,
    context: AISearchContext,
    *,
    entity_type: str | None = None,
    limit: int = 20,
) -> AIEntityResolution:
    """Convenience entry point for AI context resolution."""
    return AIGlobalSearchResolver(search).resolve(
        query,
        context,
        entity_type=entity_type,
        limit=limit,
    )
