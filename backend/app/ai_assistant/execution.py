"""Audited execution boundary for meaningful AI write actions.

The orchestrator delegates here; this adapter owns the request-scoped database
session and persists the result through the existing OS AuditLog model.
"""

from dataclasses import replace
from typing import Any, Callable
from uuid import UUID

from .audit import AIAuditEvent, AIAuditRecorder, AuditSession


class AIAuditedActionExecutor:
    """Execute one approved domain action and persist its audit outcome."""

    def __init__(self, db: AuditSession, recorder: AIAuditRecorder | None = None) -> None:
        self._db = db
        self._recorder = recorder or AIAuditRecorder()

    def execute(
        self,
        event: AIAuditEvent,
        handler: Callable[..., Any],
        **handler_kwargs: Any,
    ) -> Any:
        """Run a domain handler, recording success or a sanitized failure.

        The caller owns the surrounding transaction and must commit/rollback it.
        Failure details deliberately contain only the exception class, never its
        message, which may contain user data or provider secrets.
        """
        if event.read_only:
            raise ValueError("Meaningful write execution cannot use a read-only audit event")

        try:
            result = handler(**handler_kwargs)
        except Exception as error:
            failure_event = replace(
                event,
                execution_result="failed",
                failure_error=type(error).__name__,
                resulting_record_ids=(),
            )
            try:
                self._recorder.record(self._db, failure_event)
            except Exception as audit_error:
                error.add_note(
                    "The AI action failed and its audit event could not be flushed: "
                    f"{type(audit_error).__name__}"
                )
            raise

        success_event = replace(
            event,
            execution_result="success",
            failure_error=None,
            resulting_record_ids=self._resulting_record_ids(result),
        )
        self._recorder.record(self._db, success_event)
        return result

    @staticmethod
    def _resulting_record_ids(result: Any) -> tuple[UUID, ...]:
        """Extract explicit record identifiers without serializing full results."""
        if isinstance(result, dict):
            candidates = result.get("resulting_record_ids")
            if candidates is None:
                candidates = [result.get("record_id", result.get("id"))]
        else:
            candidates = getattr(result, "resulting_record_ids", None)
            if candidates is None:
                candidates = [getattr(result, "id", None)]

        if isinstance(candidates, (str, UUID)):
            candidates = [candidates]
        return tuple(
            value if isinstance(value, UUID) else UUID(str(value))
            for value in (candidates or ())
            if value is not None
        )
