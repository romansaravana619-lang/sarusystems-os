# Audit 8 — AI ↔ Existing OS API Integration

## Status

**COMPLETE — findings recorded; no implementation fixes applied in this audit phase.**

## Objective

Verify that the AI Company Assistant actually connects to the existing SaruSystems OS domain APIs, rather than only defining abstract tool contracts, and that AI execution preserves the approved architecture: AI UI → orchestrator/context/intent → approved tools → existing OS APIs → RBAC → business rules → database/workflow → audit → response.

## Evidence reviewed

- `backend/app/ai_assistant/registry.py`
- `backend/app/ai_assistant/orchestrator.py`
- `backend/app/ai_assistant/rbac.py`
- `backend/app/ai_assistant/safety.py`
- `backend/app/ai_assistant/audit.py`
- `backend/app/main.py`
- `backend/tests/test_ai_testing.py`

## Positive findings

1. The AI registry defines explicit read/write tools with required permissions, allowed entities, validation rules, business-rule requirements, failure behavior, and audit event metadata.
2. AI RBAC uses the authenticated OS user's existing permission graph and company scope rather than granting AI-specific privileges.
3. AI write safety requires explicit confirmation and binds confirmation to request, tool, and payload hashes.
4. AI audit events are written through the existing OS `AuditLog` model and include company/request/tool/permission/business-rule/confirmation/execution context.
5. The orchestrator explicitly documents that it must not receive a database session or write directly to the database.

## Findings

### F1 — HIGH: Approved AI tools are not wired to concrete OS API handlers

`AIToolDefinition` supports an optional `handler`, but the approved read and write tool definitions are created without handlers. `AIOrchestrator.execute_read()` therefore requires a handler to be supplied externally and raises when the registered tool has no execution handler.

There is no reviewed adapter/handler layer that maps the approved AI tools to the existing domain API/service functions. This means the registry currently describes intended capabilities rather than providing a complete execution path through the real OS APIs.

**Impact:** The AI Assistant cannot be considered end-to-end integrated with the existing OS business modules. This is the primary Audit 8 finding.

### F2 — HIGH: AI Assistant is not exposed through the main FastAPI application

`backend/app/main.py` registers the OS domain routers, but no AI Assistant router is included. The AI package is imported as a domain foundation but there is no production API entry point shown in the reviewed main application for Founder AI requests.

**Impact:** There is no verified HTTP/UI → AI orchestrator → existing OS API execution path in the current application.

### F3 — HIGH: Existing AI scenario tests are contract-level, not real OS API integration tests

`backend/tests/test_ai_testing.py` validates response contracts and failure behavior using constructed `AIResponseContract` objects. The scenarios do not invoke real CRM, Sales, Projects, Finance, Tasks, Calendar, Communication, Notification, or other OS API/service endpoints through the AI orchestrator.

**Impact:** CI can prove the AI contracts behave correctly while still passing if actual AI-to-domain API wiring is absent or broken.

### F4 — MEDIUM: Write-tool execution boundary is incomplete in the orchestrator

The orchestrator provides `preview_write()` and `execute_read()`, but no corresponding concrete write execution method that combines safety confirmation, RBAC, business-rule enforcement, domain API invocation, audit recording, and response construction. The safety policy exists separately, but the reviewed integration does not demonstrate that the full sequence is invoked by a real OS request path.

**Impact:** The approved safety architecture exists as reusable components, but the complete production execution path is not yet verified.

### F5 — MEDIUM: No verified provider-neutral request entry point was found

The AI package contains contracts, registry, orchestration, RBAC, safety, business-rule, audit, global-search, and response components, but no reviewed request adapter/controller was found that accepts a Founder request, resolves intent, selects a registered tool, authorizes it, calls the existing domain API, and returns the response contract.

**Impact:** The architecture foundation is strong, but integration remains incomplete at the application boundary.

## Architecture compliance conclusion

The reviewed AI components respect the intended **no direct database write** boundary. However, the audit could not verify the required **approved tools → existing OS APIs** and **Founder request → orchestrator → domain execution** links in the running application.

## Audit conclusion

**Audit 8 is COMPLETE.**

Primary findings are F1/F2/F3: the current AI implementation is a strong architecture/safety foundation, but the repository does not yet demonstrate a real end-to-end integration of AI tools with the existing OS APIs or an application request endpoint.

Per the approved workflow, **no implementation fixes are created in Audit 8**. Findings will be carried forward to the consolidated fixes phase after Audits 1–11 are completed.
