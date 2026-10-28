# Architecture

## V1 architecture

`Responsive Web App → API/Application Layer → Domain/Workflow Layer → Data Layer → Integration Layer`

V1 uses a modular monolith to keep deployment and operational complexity low while preserving clear domain boundaries.

## Core rules

- Central authentication and authorization
- Record-level access checks
- Audit critical mutations
- PostgreSQL in production
- Object storage for binary files
- External integrations do not become the source of truth for core records
