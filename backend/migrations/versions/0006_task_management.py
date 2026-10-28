"""Add task management foundation.

Revision ID: 0006_task_management
Revises: 0005_client_conversion
Create Date: 2026-10-25
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_task_management"
down_revision = "0005_client_conversion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "tasks",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(50), nullable=False, server_default="backlog"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("owner_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("client_id", uuid_type, sa.ForeignKey("clients.id")),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for name, column in [
        ("company_id", "company_id"),
        ("status", "status"),
        ("priority", "priority"),
        ("owner_user_id", "owner_user_id"),
        ("client_id", "client_id"),
        ("due_at", "due_at"),
    ]:
        op.create_index(f"ix_tasks_{name}", "tasks", [column])

    op.create_table(
        "task_checklist_items",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("task_id", uuid_type, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_task_checklist_items_task_id", "task_checklist_items", ["task_id"])

    permissions = [
        ("tasks.view", "View company tasks"),
        ("tasks.create", "Create company tasks"),
        ("tasks.edit", "Edit task details and lifecycle"),
        ("tasks.assign", "Assign tasks to active company users"),
        ("tasks.complete", "Complete tasks"),
    ]
    permissions_table = sa.table(
        "permissions",
        sa.column("id", uuid_type),
        sa.column("code", sa.String),
        sa.column("description", sa.String),
    )
    for code, description in permissions:
        exists = op.get_bind().execute(sa.select(permissions_table.c.id).where(permissions_table.c.code == code)).first()
        if exists is None:
            op.execute(permissions_table.insert().values(id=uuid4(), code=code, description=description))


def downgrade() -> None:
    permissions_table = sa.table("permissions", sa.column("code", sa.String))
    op.execute(permissions_table.delete().where(permissions_table.c.code.in_([
        "tasks.view", "tasks.create", "tasks.edit", "tasks.assign", "tasks.complete"
    ])))
    op.drop_index("ix_task_checklist_items_task_id", table_name="task_checklist_items")
    op.drop_table("task_checklist_items")
    for name in ["due_at", "client_id", "owner_user_id", "priority", "status", "company_id"]:
        op.drop_index(f"ix_tasks_{name}", table_name="tasks")
    op.drop_table("tasks")
