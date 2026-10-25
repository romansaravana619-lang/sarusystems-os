from fastapi import FastAPI

from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.roles.router import router as roles_router
from app.users.router import router as users_router


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Founder operating system for Saru Systems.",
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(audit_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str]:
    return {"status": "ready"}
