# Audit 7 — Audit Logging Coverage

## Status

**COMPLETE — findings recorded; no implementation fixes applied in this audit phase.**

Repository audited: `romansaravana619-lang/sarusystems-os`
Branch baseline: `main`
Audit branch: `audit/7-audit-logging-coverage`

## Objective

Verify that meaningful security, governance, business, and AI actions are represented in the existing `AuditLog` trail, that audit records are queryable by authorized users, and that audit visibility preserves company isolation.

## Existing audit foundation

- `AuditLog` exists as the shared audit entity with actor, action, entity type, entity id, details, and timestamp fields.
- The audit API exposes recent logs and entity history behind `audit.view`.
- Major business modules use explicit audit writes for important create/update/approval/payment actions.
- Authentication records successful login and logout.
- User and role/permission administration records material changes.
- Business-rule evaluation records allow/block decisions.
- The AI Assistant has a dedicated audit recorder carrying request, intent, tool, permission, business-rule, confirmation, execution, failure, and resulting-record context.

## Coverage reviewed

### Covered areas

- Authentication: successful login and logout.
- User administration: create and update.
- Role administration: role creation and permission replacement.
- Permission administration: permission creation.
- Company governance: profile, department, goal, policy, and operating-rule changes.
- Projects: project creation/update, scope changes/approval, requirement creation/approval, milestone creation/update, and related project workflow events.
- Finance: transaction creation, milestone creation, and payment recording.
- Business Rules: rule/SOP creation and update plus rule-evaluation decisions.
- AI Assistant: structured AI activity audit boundary and safety-related context.

### Findings

#### F1 — HIGH: Audit log read endpoints are not company-scoped

`backend/app/audit/router.py` queries `AuditLog` directly for both the global recent-log endpoint and entity-history endpoint. The queries do not constrain results to the authenticated user's company. `AuditLog` itself stores `actor_user_id` but does not contain a `company_id` field or an equivalent enforced tenant key.

Impact: in a multi-company deployment, a user with `audit.view` could potentially retrieve audit records belonging to another company through the audit listing endpoint, and entity history is likewise not explicitly tenant-scoped.

This is a tenant-isolation/security finding and should be treated as a priority fix after the full audit sequence reaches the fixes phase.

#### F2 — MEDIUM: Failed authentication attempts are not recorded

`backend/app/auth/router.py` records successful login and logout, but the invalid-credential path raises `401` without creating an audit record.

Impact: the audit trail cannot distinguish normal successful authentication activity from repeated failed authentication attempts, reducing security investigation visibility.

#### F3 — LOW/MEDIUM: Token refresh activity is not audited

The `/auth/refresh` endpoint issues a new token but does not record the refresh event. This leaves a gap in authentication-session activity history.

#### F4 — MEDIUM: Authorization denials are not centrally recorded

The shared `require_permission` guard returns `403` for missing permissions, but the reviewed audit design does not record denied authorization attempts. This means permission-abuse/security investigation cannot reliably reconstruct denied access attempts from the audit trail.

#### F5 — LOW: Read-only business access is intentionally sparse in audit coverage

Most module audit events are attached to material writes and governance decisions rather than ordinary reads. This is reasonable for an operational audit trail, but the current implementation does not provide a consistent distinction between ordinary reads and sensitive read/access events. No immediate architectural change is proposed; this should be considered during production-readiness review.

#### F6 — LOW: Audit record details are free-form strings in most domain modules

The shared `AuditLog.details` field is a bounded string and most domain modules write human-readable text. The AI Assistant has a structured JSON audit contract, but the broader OS does not have the same machine-readable structure across all modules. This limits consistent analytics/searching over audit events.

## Positive verification

- Material write actions in the reviewed core modules are generally accompanied by audit writes before commit.
- Business-rule evaluation decisions were explicitly added to the audit trail in the completed Business Rules enforcement work.
- AI audit recording uses the existing OS `AuditLog` model and avoids provider-specific credentials/secrets.
- Audit access itself is permission-gated through `audit.view`.

## Audit conclusion

**Audit 7 is COMPLETE.**

The audit subsystem exists and has meaningful coverage across major business operations, but the review identified security and observability gaps, with **F1 company isolation of audit reads** as the highest-priority finding.

Per the approved audit workflow, these findings are recorded now and **no implementation fix is created in Audit 7**. Fixes will be planned only after Audits 1–11 are completed.
