from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.clients.router import router as clients_router
from app.command_center.router import router as command_center_router
from app.company.router import router as company_router
from app.core.config import settings
from app.crm.router import router as crm_router
from app.freelancers.router import router as freelancers_router
from app.freelancers.workflow_router import router as freelancer_workflow_router
from app.freelancer_work.router import router as freelancer_work_router
from app.marketing.router import router as marketing_router
from app.content.router import router as content_router
from app.social_media.router import router as social_media_router
from app.projects.router import router as projects_router
from app.roles.router import router as roles_router
from app.sales.router import router as sales_router
from app.services.router import router as services_router
from app.tasks.router import router as tasks_router
from app.users.router import router as users_router

app = FastAPI(title=settings.app_name, version=settings.app_version, description="Founder operating system for Saru Systems.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])
app.include_router(auth_router); app.include_router(users_router); app.include_router(roles_router); app.include_router(audit_router); app.include_router(command_center_router); app.include_router(company_router); app.include_router(crm_router); app.include_router(sales_router); app.include_router(clients_router); app.include_router(services_router); app.include_router(projects_router); app.include_router(tasks_router); app.include_router(freelancer_work_router); app.include_router(freelancer_workflow_router); app.include_router(freelancers_router); app.include_router(marketing_router); app.include_router(content_router); app.include_router(social_media_router)
@app.get("/health", tags=["system"])
def health() -> dict[str, str]: return {"status": "ok"}
@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str]: return {"status": "ready"}
