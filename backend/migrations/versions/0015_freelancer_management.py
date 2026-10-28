"""Add Freelancer Management V1.

Revision ID: 0015_freelancer_management
Revises: 0014_crm_prospect_lifecycle
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_freelancer_management"
down_revision = "0014_crm_prospect_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("freelancers",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("freelancer_code", sa.String(40), nullable=False, unique=True), sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=False), sa.Column("phone", sa.String(50)), sa.Column("location", sa.String(200)),
        sa.Column("primary_role", sa.String(150)), sa.Column("department", sa.String(100)), sa.Column("experience_years", sa.Numeric(5,2)),
        sa.Column("portfolio_url", sa.String(1000)), sa.Column("resume_url", sa.String(1000)), sa.Column("bio", sa.Text()),
        sa.Column("rate_type", sa.String(30), nullable=False, server_default="project"), sa.Column("rate_amount", sa.Numeric(12,2)),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"), sa.Column("status", sa.String(40), nullable=False, server_default="prospect"),
        sa.Column("availability_status", sa.String(30), nullable=False, server_default="available"), sa.Column("source", sa.String(100)), sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_freelancers_company_id", "freelancers", ["company_id"]); op.create_index("ix_freelancers_email", "freelancers", ["email"]); op.create_index("ix_freelancers_status", "freelancers", ["status"]); op.create_index("ix_freelancers_primary_role", "freelancers", ["primary_role"])
    op.create_table("freelancer_skills", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("freelancer_id", sa.Uuid(), sa.ForeignKey("freelancers.id", ondelete="CASCADE"), nullable=False), sa.Column("skill", sa.String(120), nullable=False), sa.Column("proficiency", sa.String(30), nullable=False, server_default="intermediate"), sa.Column("years", sa.Numeric(5,2)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_freelancer_skills_freelancer_id", "freelancer_skills", ["freelancer_id"]); op.create_index("ix_freelancer_skills_skill", "freelancer_skills", ["skill"])
    op.create_table("freelancer_applications", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False), sa.Column("freelancer_id", sa.Uuid(), sa.ForeignKey("freelancers.id")), sa.Column("name", sa.String(200), nullable=False), sa.Column("email", sa.String(320), nullable=False), sa.Column("phone", sa.String(50)), sa.Column("role_applied", sa.String(150)), sa.Column("source", sa.String(100)), sa.Column("portfolio_url", sa.String(1000)), sa.Column("resume_url", sa.String(1000)), sa.Column("notes", sa.Text()), sa.Column("status", sa.String(40), nullable=False, server_default="received"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_freelancer_applications_company_id", "freelancer_applications", ["company_id"]); op.create_index("ix_freelancer_applications_email", "freelancer_applications", ["email"]); op.create_index("ix_freelancer_applications_status", "freelancer_applications", ["status"])
    op.create_table("freelancer_evaluations", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("application_id", sa.Uuid(), sa.ForeignKey("freelancer_applications.id", ondelete="CASCADE"), nullable=False), sa.Column("evaluator_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("technical_score", sa.Numeric(5,2)), sa.Column("communication_score", sa.Numeric(5,2)), sa.Column("reliability_score", sa.Numeric(5,2)), sa.Column("portfolio_score", sa.Numeric(5,2)), sa.Column("overall_score", sa.Numeric(5,2)), sa.Column("recommendation", sa.String(30), nullable=False, server_default="review"), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_freelancer_evaluations_application_id", "freelancer_evaluations", ["application_id"])
    op.create_table("freelancer_agreements", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("freelancer_id", sa.Uuid(), sa.ForeignKey("freelancers.id", ondelete="CASCADE"), nullable=False), sa.Column("agreement_type", sa.String(80), nullable=False, server_default="project_based"), sa.Column("status", sa.String(30), nullable=False, server_default="draft"), sa.Column("effective_at", sa.DateTime(timezone=True)), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("document_url", sa.String(1000)), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_freelancer_agreements_freelancer_id", "freelancer_agreements", ["freelancer_id"]); op.create_index("ix_freelancer_agreements_status", "freelancer_agreements", ["status"])
    op.create_table("freelancer_availability", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("freelancer_id", sa.Uuid(), sa.ForeignKey("freelancers.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="available"), sa.Column("available_from", sa.DateTime(timezone=True)), sa.Column("available_until", sa.DateTime(timezone=True)), sa.Column("weekly_hours", sa.Numeric(6,2)), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_freelancer_availability_freelancer_id", "freelancer_availability", ["freelancer_id"])
    op.create_table("freelancer_assignments", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("freelancer_id", sa.Uuid(), sa.ForeignKey("freelancers.id"), nullable=False), sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("role", sa.String(150)), sa.Column("allocation_percent", sa.Numeric(5,2), nullable=False, server_default="100"), sa.Column("status", sa.String(30), nullable=False, server_default="proposed"), sa.Column("start_at", sa.DateTime(timezone=True)), sa.Column("end_at", sa.DateTime(timezone=True)), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_freelancer_assignments_freelancer_id", "freelancer_assignments", ["freelancer_id"]); op.create_index("ix_freelancer_assignments_project_id", "freelancer_assignments", ["project_id"]); op.create_index("ix_freelancer_assignments_status", "freelancer_assignments", ["status"])
    op.create_table("freelancer_performance", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("freelancer_id", sa.Uuid(), sa.ForeignKey("freelancers.id", ondelete="CASCADE"), nullable=False), sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id")), sa.Column("period", sa.String(30), nullable=False), sa.Column("quality_score", sa.Numeric(5,2)), sa.Column("timeliness_score", sa.Numeric(5,2)), sa.Column("communication_score", sa.Numeric(5,2)), sa.Column("overall_score", sa.Numeric(5,2)), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_freelancer_performance_freelancer_id", "freelancer_performance", ["freelancer_id"]); op.create_index("ix_freelancer_performance_project_id", "freelancer_performance", ["project_id"])
    permissions = [
        ("freelancers.view", "View freelancer master records and workspace"), ("freelancers.create", "Create freelancer records"), ("freelancers.edit", "Edit freelancer records and skills"),
        ("freelancers.applications.view", "View freelancer applications"), ("freelancers.applications.create", "Create freelancer applications"), ("freelancers.applications.edit", "Update freelancer applications"), ("freelancers.applications.convert", "Convert selected applications to freelancers"),
        ("freelancers.evaluations.create", "Evaluate freelancer applications"), ("freelancers.agreements.manage", "Manage freelancer agreements"), ("freelancers.availability.manage", "Manage freelancer availability"), ("freelancers.assign", "Assign freelancers to projects"), ("freelancers.performance.manage", "Record freelancer performance"),
    ]
    permission_table = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)), sa.column("description", sa.String(500)))
    role_permission = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    role_table = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String(100)))
    for code, description in permissions:
        existing = op.get_bind().execute(sa.select(permission_table.c.id).where(permission_table.c.code == code)).scalar()
        if existing is None:
            existing = op.get_bind().execute(permission_table.insert().values(code=code, description=description).returning(permission_table.c.id)).scalar()
        for role_name in ("Founder / Super Admin",):
            role_id = op.get_bind().execute(sa.select(role_table.c.id).where(role_table.c.name == role_name)).scalar()
            if role_id is not None and op.get_bind().execute(sa.select(role_permission.c.permission_id).where(role_permission.c.role_id == role_id, role_permission.c.permission_id == existing)).scalar() is None:
                op.get_bind().execute(role_permission.insert().values(role_id=role_id, permission_id=existing))


def downgrade() -> None:
    bind = op.get_bind()
    permission_table = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)))
    codes = ["freelancers.view", "freelancers.create", "freelancers.edit", "freelancers.applications.view", "freelancers.applications.create", "freelancers.applications.edit", "freelancers.applications.convert", "freelancers.evaluations.create", "freelancers.agreements.manage", "freelancers.availability.manage", "freelancers.assign", "freelancers.performance.manage"]
    ids = [r[0] for r in bind.execute(sa.select(permission_table.c.id).where(permission_table.c.code.in_(codes))).all()]
    if ids:
        bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = ANY(:ids)"), {"ids": ids})
        bind.execute(sa.delete(permission_table).where(permission_table.c.id.in_(ids)))
    for table in ["freelancer_performance", "freelancer_assignments", "freelancer_availability", "freelancer_agreements", "freelancer_evaluations", "freelancer_applications", "freelancer_skills", "freelancers"]:
        op.drop_table(table)
