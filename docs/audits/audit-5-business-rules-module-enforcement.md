# Audit 5 — Business Rules ↔ Module Enforcement

## Scope
- Verify the 4.16 Business Rules Engine boundary against module workflows.
- Verify company isolation and RBAC at rule evaluation.
- Verify blocking semantics and non-blocking warnings.
- Verify audit coverage for rule decisions.
- Distinguish configurable business rules from module-local invariants.

## Findings

### Finding A — Module-local invariants vs configurable business rules
**Status: Accepted / No defect**

Finance and Project modules contain deterministic local validations for invariants such as valid status transitions, approved requirements/scope, project completion prerequisites, payment amount limits, and required relationship references. These are mandatory domain invariants and do not replace the 4.16 configurable rules engine. The 4.16 engine remains the explicit configurable policy boundary and the AI layer already delegates to it. No parallel rules engine was introduced.

No architecture redesign was made for this item.

### Finding B — Rule evaluation decisions were not audit-recorded
**Severity: Medium**
**Status: Fixed**

The `/rules-engine/evaluate` endpoint evaluated active enforced rules and returned allow/block decisions, but the evaluation decision itself was not persisted in the OS audit trail.

### Fix
- Rule evaluations now create a `business_rule.evaluate` audit event.
- Audit details capture trigger event, target scope, action, final allowed state, blocked rule IDs, and evaluation count.
- The audit record is committed before the evaluation response is returned.
- Company scope and existing RBAC remain unchanged.
- Added focused regression tests for allowed and blocked evaluation audit coverage.

## Verification gate
CI GREEN → exact-head audit → PR merge → final Audit 5 verification → Notion checkpoint.
