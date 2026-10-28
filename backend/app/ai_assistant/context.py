"""Context resolution boundary for the AI Assistant.

Actual Global Search/domain API integration is implemented in 4.23.7. This boundary
prevents the orchestrator from reaching directly into database models.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResolvedEntity:
    entity_type: str
    entity_id: UUID
    label: str


class AIContextResolver(Protocol):
    def resolve(self, reference: str, *, company_id: UUID, user_id: UUID) -> list[ResolvedEntity]:
        """Resolve a user reference within the caller's company and permissions."""
