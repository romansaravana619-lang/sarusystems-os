# SaruSystems OS

Founder operating system for Saru Systems.

## Product principle

> If a business activity happens inside Saru Systems, the OS should manage it, track it, connect it, automate it, or provide the information required to operate it.

## V1 goal

Build a secure, founder-first operating console covering the core company flow:

**Marketing → Prospect → CRM → Sales → Proposal → Client → Project → Tasks → Payment → Completion → Growth**

## V1 foundation

- Authentication
- Users, roles and permissions
- Company core
- Audit log
- Notifications
- CRM
- Sales
- Client management
- Tasks
- Communication/activity history
- Foundational global search

## Repository

```text
sarusystems-os/
├── backend/      # FastAPI + SQLAlchemy + Alembic
├── frontend/     # React + TypeScript + Vite
├── docs/         # Architecture and engineering documentation
└── infra/        # Local/deployment infrastructure
```

## Current development stage

**Phase A — Foundation**

Repository bootstrap is underway on `feature/foundation`. Authentication, authorization, database migrations, audit services, and the first vertical slice will be implemented incrementally with tests.

## Engineering principles

- Modular monolith for V1
- REST-first API
- PostgreSQL as production source of truth
- RBAC + record scope + workflow conditions
- Audit-first critical mutations
- UTC internally
- No silent hard deletes for business records
- Critical workflows require automated tests before trusted automation
