"""Reconcile task management with the approved V1 workflow.

Revision ID: 0013_task_management_reconciliation
Revises: 0012_project_management
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_task_management_reconciliation"
down_revision = "0012_project_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.add_column("tasks", sa.Column("milestone_id", uuid, sa.ForeignKey("project_milestones.id"), nullable=True))
    op.add_column("tasks", sa.Column("required_deliverable_id", uuid, sa.ForeignKey("project_deliverables.id"), nullable=True))
    op.add_column("tasks", sa.Column("expected_output", sa.Text(), nullable=True))
    op.add_column("tasks", sa.Column("start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("estimated_hours", sa.Numeric(8, 2), nullable=True))
    op.add_column("tasks", sa.Column("founder_notes", sa.Text(), nullable=True))
    op.create_index("ix_tasks_milestone_id", "tasks", ["milestone_id"])
    op.create_index("ix_tasks_required_deliverable_id", "tasks", ["required_deliverable_id"])
    op.create_index("ix_tasks_start_at", "tasks", ["start_at"])

    op.create_table(
        "task_dependencies",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("task_id", uuid, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("depends_on_task_id", uuid, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency_pair"),
    )
    op.create_index("ix_task_dependencies_task_id", "task_dependencies", ["task_id"])
    op.create_index("ix_task_dependencies_depends_on_task_id", "task_dependencies", ["depends_on_task_id"])

    op.create_table(
        "task_blockers",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("task_id", uuid, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("blocker", sa.Text(), nullable=False),
        sa.Column("blocked_by", sa.String(200), nullable=True),
        sa.Column("identified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("required_action", sa.Text(), nullable=False),
        sa.Column("owner_user_id", uuid, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_task_blockers_task_id", "task_blockers", ["task_id"])
    op.create_index("ix_task_blockers_owner_user_id", "task_blockers", ["owner_user_id"])
    op.create_index("ix_task_blockers_status", "task_blockers", ["status"])

    permissions = [
        ("tasks.submit", "Submit tasks for review"),
        ("tasks.review", "Review tasks and request revisions"),
    ]
    bind = op.get_bind()
    permission_table = sa.table("permissions", sa.column("id", uuid), sa.column("code", sa.String), sa.column("description", sa.String))
    role_table = sa.table("roles", sa.column("id", uuid), sa.column("name", sa.String))
    role_permission = sa.table("role_permissions", sa.column("role_id", uuid), sa.column("permission_id", uuid))
    import uuid as uuidlib
    founder_roles = bind.execute(sa.select(role_table.c.id).where(role_table.c.name == "Founder / Super Admin")).all()
    for code, description in permissions:
        row = bind.execute(sa.select(permission_table.c.id).where(permission_table.c.code == code)).first()
        permission_id = row[0] if row else uuidlib.uuid4()
        if row is None:
            op.execute(permission_table.insert().values(id=permission_id, code=code, description=description))
        for role_row in founder_roles:
            exists = bind.execute(sa.select(role_permission.c.role_id).where(role_permission.c.role_id == role_row[0], role_permission.c.permission_id == permission_id)).first()
            if exists is None:
                op.execute(role_permission.insert().values(role_id=role_row[0], permission_id=permission_id))


def downgrade() -> None:
    op.drop_index("ix_task_blockers_status", table_name="task_blockers")
    op.drop_index("ix_task_blockers_owner_user_id", table_name="task_blockers")
    op.drop_index("ix_task_blockers_task_id", table_name="task_blockers")
    op.drop_table("task_blockers")
    op.drop_index("ix_task_dependencies_depends_on_task_id", table_name="task_dependencies")
    op.drop_index("ix_task_dependencies_task_id", table_name="task_dependencies")
    op.drop_table("task_dependencies")
    op.drop_index("ix_tasks_start_at", table_name="tasks")
    op.drop_index("ix_tasks_required_deliverable_id", table_name="tasks")
    op.drop_index("ix_tasks_milestone_id", table_name="tasks")
    op.drop_column("tasks", "founder_notes")
    op.drop_column("tasks", "estimated_hours")
    op.drop_column("tasks", "start_at")
    op.drop_column("tasks", "expected_output")
    op.drop_column("tasks", "required_deliverable_id")
    op.drop_column("tasks", "milestone_id")
