# Audit 2 — Backend API & Module Integration Findings

## Confirmed finding A — Project/client integration lookup defect

`backend/app/projects/router.py` currently starts project creation with `db.get(Client, opportunity.id)` and only then falls back to `select(Client).where(Client.opportunity_id == opportunity.id)`.

The first lookup treats an Opportunity UUID as a Client primary key. This is the wrong relationship key and can select an unrelated Client if UUID values ever collide. The authoritative relationship is `Client.opportunity_id == Opportunity.id`.

Required fix: remove the primary-key lookup and resolve the converted client directly through its `opportunity_id` relationship, with company isolation preserved.

## Confirmed finding B — AI tool permission identifiers do not match domain API permissions

`backend/app/ai_assistant/registry.py` declares abstract permission codes such as `task.view`, `crm.view`, `sales.view`, `project.view`, `finance.view`, `freelancer.view`, `calendar.view`, `notification.view`, and `communication.view`.

The actual domain routers enforce different permission codes, for example `tasks.view`, `crm.pipeline.view`, `sales.pipeline.view`, `projects.view`, `finance.dashboard.view` / `finance.transactions.view`, and module-specific permissions.

Because `AIToolRBACPolicy` compares the registry's `required_permission` directly against the authenticated user's permission codes, an otherwise authorized user can be denied by the AI layer before the domain API is reached.

Required fix: align AI tool authorization metadata with the existing domain permission vocabulary without creating a parallel privilege system.

## Audit conclusion

Audit 2 cannot be closed until findings A and B are fixed, regression-tested, CI-verified, and merged to `main`.

No architecture redesign is required.
