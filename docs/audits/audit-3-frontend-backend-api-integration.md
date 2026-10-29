# Audit 3 — Frontend ↔ Backend API Integration Audit

Status: IN PROGRESS
Branch: `audit/3-frontend-backend-api-integration`
Base: `main` @ `dcdd12548477c6668fd8bbb56cae5b8002227549`

## Scope

1. Frontend API client architecture and base URL consistency
2. Frontend endpoint paths vs backend route paths
3. Authentication/token propagation
4. Request payload and response-shape alignment
5. Error and empty-state handling
6. Frontend permission gating vs backend authorization
7. Cross-module API integration
8. Deployment/CORS integration assumptions
9. Regression-test coverage for API clients
10. Build/runtime integration risks

## Initial Findings

### Finding A — Multiple feature API clients bypass the shared API base URL

The canonical `frontend/src/services/api.ts` correctly resolves `VITE_API_BASE_URL` with a localhost development fallback. However, several feature-level API clients call `fetch(path, ...)` directly with relative paths, including Finance, Calendar, Notifications, and Analytics.

This creates two API transport conventions in the same frontend. In a separately hosted frontend/backend deployment, these relative requests target the frontend origin instead of the configured backend origin and can fail even when `VITE_API_BASE_URL` is correctly configured.

Confirmed examples:
- `frontend/src/features/finance/financeApi.ts`
- `frontend/src/features/calendar/calendarApi.ts`
- `frontend/src/features/notifications/notificationsApi.ts`
- `frontend/src/features/analytics/analyticsApi.ts`

Required fix: centralize request/base-URL handling and migrate feature clients to the same transport convention without changing backend architecture.

### Finding B — Backend CORS policy is development-origin-only

`backend/app/main.py` currently permits only `http://localhost:5173` and `http://127.0.0.1:5173`.

The frontend already supports a configurable `VITE_API_BASE_URL`, which implies frontend/backend separation is supported at configuration level. A deployed frontend origin therefore requires corresponding backend CORS configuration; otherwise browser API calls are blocked by CORS.

Required fix: make allowed frontend origins configuration-driven, preserving safe local defaults and avoiding wildcard credentials behavior.

### Finding C — Authenticated API error handling is inconsistent across clients

The shared client in `frontend/src/services/api.ts` normalizes structured API errors and handles `204` responses. Several feature clients implement independent request wrappers that simply throw `response.text()` and do not share the same response/error contract.

This can produce inconsistent user-facing errors and makes authentication/authorization failure handling harder to centralize.

Required fix: use one shared frontend API transport/error contract across feature clients.

## Audit Principle

Do not redesign the OS architecture. Fix only confirmed frontend/backend integration defects, add focused regression coverage, run CI GREEN, perform exact-head verification, merge through PR, and then record the Audit 3 Notion checkpoint.
