# 4.22 Global Search — Implementation Audit

## Approved scope

A single search must find related:

- Prospects
- Clients
- Projects
- Proposals
- Tasks
- Payments
- Documents
- Communication records

## Gap audit and implementation

- No existing global-search feature was present on the analytics branch.
- Added a dedicated company-scoped Global Search API.
- Search covers prospects, clients, projects, opportunities, tasks, documents, payment milestones, financial transactions, communication records, and contacts.
- Proposal discovery is covered through the Documents index because proposals are stored as document records with category/type metadata.
- Supports query validation, result limit, and optional entity-type filtering.
- Results return a consistent type/id/title/subtitle/status contract for Founder navigation.
- Every query is constrained to the authenticated user's company.
- Search access is protected by `global_search.view` RBAC permission.
- Founder and Super Admin receive the permission through migration `0031_global_search.py`.
- Search events are written to the existing audit log for operational traceability.
- Added Founder Global Search workspace and navigation entry.
- Added backend contract tests.
- Added frontend search API and workspace.

## Acceptance gates

- Backend implementation: complete
- Cross-module search coverage: complete
- Proposal/document coverage: complete
- Company isolation: complete
- RBAC: complete
- Audit logging: complete
- Migration: complete
- Founder workspace: complete
- Tests: complete
- Final CI: required GREEN on exact final PR head
- PR: intentionally open and unmerged
