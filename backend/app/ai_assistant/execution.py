"""Audited execution boundary for meaningful AI write actions.

The orchestrator delegates here; this adapter owns the request-scoped database
session and persists outcomes through the existing OS AuditLog model. A separate
session factory is required so failed-action audit events survive request rollback.
"""

from dataclasses import replace
from typing import Any, Callable, Protocol
from uuid import UUID

from .audit import AIAuditEvent, AIAuditRecorder, AuditSession


class FailureAuditSession(AuditSession, Protocol):
    """Independent transaction used to retain audit evidence after action rollback."""

    def commit(self) -> None: ...

    def close(self) -> None: ...


class AIAuditedActionExecutor:
    """Execute one approved domain action and persist its audit outcome."""

    def __init__(
        self,
        db: AuditSession,
        *,
        failure_audit_session_factory: Callable[[], FailureAuditSession],
        recorder: AIAuditRecorder | None = None,
    ) -> None:
        self._db = db
        self._failure_audit_session_factory = failure_audit_session_factory
        self._recorder = recorder or AIAuditRecorder()

    def execute(
        self,
        event: AIAuditEvent,
        handler: Callable[..., Any],
        **handler_kwargs: Any,
    ) -> Any:
        """Run a domain handler, recording success or a sanitized failure.

        Successful action and audit writes share the caller's transaction. Failure
        evidence is written and committed through a separate session so a caller
        rollback cannot erase it. Failure details contain only the exception class,
        never a message that may contain user data or provider secrets.
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
            failure_db = None
            try:
                failure_db = self._failure_audit_session_factory()
                self._recorder.record(failure_db, failure_event)
                failure_db.commit()
            except Exception as audit_error:  # noqa: BLE001 - preserve the original action failure
                error.add_note(
                    "The AI action failed and its independent audit event could not be committed: "
                    f"{type(audit_error).__name__}"
                )
            finally:
                if failure_db is not None:
                    try:
                        failure_db.close()
                    except Exception as close_error:  # noqa: BLE001 - preserve the original action failure
                        error.add_note(
                            "The independent failure-audit session could not be closed: "
                            f"{type(close_error).__name__}"
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
