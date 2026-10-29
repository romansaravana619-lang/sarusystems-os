# Audit 11 — Production Readiness Findings

**Status:** COMPLETE — findings recorded; no implementation fixes in this audit.

## Scope

Review the current `main` implementation for production-readiness assumptions across runtime configuration, secrets, database/deployment configuration, frontend/backend build and dependency management, CI, health/readiness checks, CORS, migrations, security boundaries, error handling, observability, and deployment assumptions.

This audit is intentionally findings-only. Per the frozen audit workflow, implementation fixes are deferred until Audits 1–11 are complete and then handled as separate feature branches/PRs.

## Evidence reviewed

- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/pyproject.toml`
- `frontend/package.json`
- `infra/docker/docker-compose.yml`
- `.github/workflows/ci.yml`
- Existing Audit 1–10 findings and regression verification

## Positive findings

- Production/non-development environments reject the default JWT secret unless an explicit secret is configured.
- CORS is environment-configurable rather than permanently hard-coded to one frontend host.
- Backend and frontend have automated CI verification for tests/builds and Ruff checks.
- `/health` and `/ready` endpoints exist.
- Backend dependency ranges are bounded by major versions rather than completely unbounded.
- Core OS already has company isolation, RBAC, audit logging, and migration infrastructure from earlier audits.

## Findings

### F1 — HIGH — Database deployment configuration is development-grade

`infra/docker/docker-compose.yml` contains fixed database credentials (`sarusystems` / `sarusystems`) and publishes PostgreSQL directly on host port `5432`. This is suitable for local development but is not an acceptable production deployment posture without environment-secret injection, restricted network exposure, and production database controls.

### F2 — HIGH — No production application container/deployment definition was found

The repository contains a PostgreSQL Compose service, but no reviewed backend/frontend Dockerfile or complete production application deployment definition was found. The repository therefore does not currently provide a reproducible production runtime topology for the full OS.

### F3 — HIGH — Dependency installation is not reproducibly locked

Backend dependencies use version ranges in `pyproject.toml`, while CI installs the editable package directly. Frontend dependencies are declared as `latest` in `package.json`, and CI uses `npm install`. This allows dependency versions to drift between builds and makes production artifacts non-reproducible.

### F4 — MEDIUM — CI is validation-only, not a production release gate

CI verifies backend tests/Ruff and frontend build, but there is no reviewed production image build, deployment validation, migration execution gate, smoke test against a deployed environment, or release artifact promotion flow.

### F5 — MEDIUM — Readiness endpoint is not a real dependency readiness check

`/ready` returns `{"status": "ready"}` without checking database connectivity or other critical runtime dependencies. A deployment orchestrator could therefore receive a ready response while the application cannot actually reach its database.

### F6 — MEDIUM — Default runtime configuration remains development-oriented

The configuration defaults to `environment="development"`, localhost database connectivity, development CORS origins, and the development secret. The secret is protected for non-development environments, but a production deployment still requires explicit configuration of all runtime settings and should fail closed for other unsafe defaults.

### F7 — MEDIUM — No production observability/operational policy is defined in the reviewed repository

No complete reviewed configuration was found for structured application logging, metrics, tracing, centralized error monitoring, alerting, log retention, or operational SLO/incident handling. Existing audit logging is a business audit mechanism, not a replacement for infrastructure/application observability.

### F8 — MEDIUM — Backup/recovery and database lifecycle policy are not represented

The repository defines a persistent Postgres volume for local Compose usage, but no production backup schedule, restore verification, retention policy, disaster-recovery procedure, or database migration rollback/recovery policy was found in the reviewed production configuration.

### F9 — LOW/MEDIUM — Frontend linting is not part of CI

`frontend/package.json` defines an ESLint script, but the CI workflow runs `npm install` and `npm run build` only. Frontend lint therefore is not currently a CI gate.

### F10 — LOW — CI mutates the checked-out tree during verification

The backend CI runs `ruff check --fix .` before running `ruff check .`. A verification pipeline should generally be non-mutating and should fail on formatting/lint defects rather than changing files during the check.

## Production-readiness verdict

**NOT PRODUCTION READY YET.**

The core application has a strong internal foundation and the approved 4.14–4.23 scope is implemented, but production deployment requires a dedicated hardening/productization pass. The highest-priority items are production deployment topology, secret/database configuration, reproducible dependency locking, real readiness checks, and operational observability/backup/recovery controls.

## Deferred implementation phase

No fixes are implemented as part of Audit 11. The consolidated findings from Audits 1–11 must now be reviewed together. After that review, each approved fix group must be implemented on its own feature branch and PR, with tests/CI and final cross-audit verification before merge.
