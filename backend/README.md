# SaruSystems OS — Backend

FastAPI backend for the SaruSystems OS founder operating system.

## Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Pydantic Settings
- Argon2 password hashing

## Local development

1. Create a virtual environment.
2. Install the package with `pip install -e '.[dev]'`.
3. Copy `.env.example` to `.env` and configure secrets/database access.
4. Start PostgreSQL.
5. Run `uvicorn app.main:app --reload`.

Health endpoints:

- `GET /health`
- `GET /ready`
