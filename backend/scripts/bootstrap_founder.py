import os

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.shared.models import Company, Permission, Role, User

PERMISSIONS = {
    "command_center.view": "View the Founder Command Center",
    "company.view": "View company core",
    "company.edit": "Edit company profile and brand information",
    "company.departments.manage": "Manage company departments",
    "company.goals.manage": "Manage company goals",
    "company.policies.manage": "Manage company policies",
    "company.rules.manage": "Manage operating rules",
    "users.view": "View company users",
    "users.create": "Create company users",
    "users.edit": "Edit company users",
    "roles.view": "View roles",
    "roles.create": "Create roles",
    "roles.edit": "Edit roles",
    "permissions.view": "View permissions",
    "permissions.create": "Create permissions",
    "roles.permissions.manage": "Manage role permissions",
    "audit.view": "View audit history",
    "crm.prospects.view": "View CRM prospects",
    "crm.prospects.create": "Create CRM prospects",
    "crm.prospects.edit": "Edit CRM prospects",
    "crm.prospects.convert": "Convert CRM prospects to contacts",
    "crm.contacts.view": "View CRM contacts",
    "crm.contacts.create": "Create CRM contacts",
    "crm.opportunities.view": "View CRM opportunities",
    "crm.opportunities.create": "Create CRM opportunities",
    "crm.opportunities.edit": "Edit CRM opportunities",
    "sales.discovery.view": "View opportunity discoveries",
    "sales.discovery.create": "Create opportunity discoveries",
    "sales.requirements.view": "View opportunity requirements",
    "sales.requirements.create": "Create opportunity requirements",
    "sales.requirements.approve": "Approve captured sales requirements",
    "sales.proposals.view": "View sales proposals",
    "sales.proposals.create": "Create sales proposals",
    "sales.proposals.edit": "Edit sales proposals",
    "sales.deal.decide": "Mark sales deals won or lost",
    "clients.view": "View company clients",
    "clients.create": "Convert won opportunities into clients",
    "clients.edit": "Edit clients and client records",
    "clients.onboarding": "Manage client onboarding",
    "clients.health": "Review and update client health",
    "clients.documents": "Manage client document metadata",
    "services.view": "View service catalog",
    "services.create": "Create services",
    "services.edit": "Edit services, requirements and deliverables",
    "tasks.view": "View company tasks",
    "tasks.create": "Create company tasks",
    "tasks.edit": "Edit task details and lifecycle",
    "tasks.assign": "Assign tasks to active company users",
    "tasks.complete": "Complete tasks",
}


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    company_name = os.getenv("FOUNDER_COMPANY_NAME", "Saru Systems")
    company_code = os.getenv("FOUNDER_COMPANY_CODE", "SARU")
    founder_email = required_env("FOUNDER_EMAIL")
    founder_name = os.getenv("FOUNDER_NAME", "Founder")
    founder_password = required_env("FOUNDER_PASSWORD")

    with SessionLocal.begin() as db:
        company = db.scalar(select(Company).where(Company.code == company_code))
        if company is None:
            company = Company(name=company_name, code=company_code)
            db.add(company)
            db.flush()
        permissions: list[Permission] = []
        for code, description in PERMISSIONS.items():
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, description=description)
                db.add(permission)
                db.flush()
            permissions.append(permission)
        role = db.scalar(select(Role).where(Role.name == "Founder / Super Admin"))
        if role is None:
            role = Role(name="Founder / Super Admin", description="Full V1 founder control")
            db.add(role)
            db.flush()
        role.permissions = permissions
        founder = db.scalar(select(User).where(User.email == founder_email))
        if founder is None:
            founder = User(company_id=company.id, email=founder_email, full_name=founder_name, password_hash=hash_password(founder_password), roles=[role])
            db.add(founder)
        else:
            founder.company_id = company.id
            founder.full_name = founder_name
            founder.roles = [role]
            founder.is_active = True
    print(f"Founder bootstrap completed for {founder_email}.")


if __name__ == "__main__":
    main()
