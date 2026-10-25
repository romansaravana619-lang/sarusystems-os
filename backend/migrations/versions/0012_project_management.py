"""Add project management foundation.

Revision ID: 0012_project_management
Revises: 0011_crm_operational_fields
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_project_management"
down_revision = "0011_crm_operational_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("projects",
        sa.Column("id", uuid, primary_key=True), sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("client_id", uuid, sa.ForeignKey("clients.id"), nullable=False), sa.Column("opportunity_id", uuid, sa.ForeignKey("opportunities.id"), nullable=False, unique=True),
        sa.Column("owner_user_id", uuid, sa.ForeignKey("users.id")), sa.Column("code", sa.String(50), nullable=False, unique=True), sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("status", sa.String(40), nullable=False, server_default="requirements_pending"),
        sa.Column("start_at", sa.DateTime(timezone=True)), sa.Column("target_end_at", sa.DateTime(timezone=True)), sa.Column("budget", sa.Numeric(12,2)), sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("project_scopes", sa.Column("id", uuid, primary_key=True), sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("in_scope", sa.Text(), nullable=False), sa.Column("out_of_scope", sa.Text()), sa.Column("assumptions", sa.Text()), sa.Column("exclusions", sa.Text()), sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("approved_by_user_id", uuid, sa.ForeignKey("users.id")), sa.Column("approved_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("project_requirements", sa.Column("id", uuid, primary_key=True), sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("acceptance_criteria", sa.Text()), sa.Column("priority", sa.String(20), nullable=False, server_default="medium"), sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("approved_by_user_id", uuid, sa.ForeignKey("users.id")), sa.Column("approved_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("project_milestones", sa.Column("id", uuid, primary_key=True), sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("status", sa.String(30), nullable=False, server_default="pending"), sa.Column("due_at", sa.DateTime(timezone=True)), sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("project_deliverables", sa.Column("id", uuid, primary_key=True), sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("milestone_id", uuid, sa.ForeignKey("project_milestones.id", ondelete="SET NULL")), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("status", sa.String(30), nullable=False, server_default="pending"), sa.Column("submitted_at", sa.DateTime(timezone=True)), sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("review_notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("project_risks", sa.Column("id", uuid, primary_key=True), sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("severity", sa.String(20), nullable=False, server_default="medium"), sa.Column("status", sa.String(20), nullable=False, server_default="open"), sa.Column("mitigation", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("project_issues", sa.Column("id", uuid, primary_key=True), sa.Column("project_id", uuid, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("priority", sa.String(20), nullable=False, server_default="medium"), sa.Column("status", sa.String(20), nullable=False, server_default="open"), sa.Column("resolution", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    for table, cols in {"projects":["company_id","client_id","opportunity_id","status"],"project_requirements":["project_id","approved"],"project_milestones":["project_id","status"],"project_deliverables":["project_id","status"],"project_risks":["project_id","status"],"project_issues":["project_id","status"]}.items():
        for col in cols: op.create_index(f"ix_{table}_{col}", table, [col])
    op.add_column("tasks", sa.Column("project_id", uuid, sa.ForeignKey("projects.id"), nullable=True))
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    permissions = [
        ("projects.view","View projects and project workspaces"),("projects.create","Create projects from won opportunities"),("projects.edit","Edit project records and lifecycle"),
        ("projects.scope.edit","Create and edit project scope"),("projects.scope.approve","Approve project scope"),("projects.requirements.view","View project requirements"),("projects.requirements.create","Create project requirements"),("projects.requirements.approve","Approve project requirements"),
        ("projects.milestones.manage","Manage project milestones"),("projects.deliverables.manage","Manage project deliverables"),("projects.risks.manage","Manage project risks"),("projects.issues.manage","Manage project issues"),
    ]
    table = sa.table("permissions", sa.column("id", uuid), sa.column("code", sa.String), sa.column("description", sa.String))
    import uuid as uuidlib
    for code, description in permissions:
        if op.get_bind().execute(sa.select(table.c.id).where(table.c.code == code)).first() is None:
            op.execute(table.insert().values(id=uuidlib.uuid4(), code=code, description=description))


def downgrade() -> None:
    op.drop_index("ix_tasks_project_id", table_name="tasks"); op.drop_column("tasks", "project_id")
    for table in ["project_issues","project_risks","project_deliverables","project_milestones","project_requirements","project_scopes","projects"]: op.drop_table(table)
