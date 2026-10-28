"""Add Freelancer Work Management V1.

Revision ID: 0016_freelancer_work_management
Revises: 0015_freelancer_management
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_freelancer_work_management"
down_revision = "0015_freelancer_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "freelancer_task_executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), sa.ForeignKey("freelancer_assignments.id"), nullable=False),
        sa.Column("freelancer_id", sa.Uuid(), sa.ForeignKey("freelancers.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="assigned"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("submission_url", sa.String(1000)),
        sa.Column("work_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("task_id", name="uq_freelancer_task_execution_task"),
    )
    for name, table, cols in [
        ("ix_freelancer_task_executions_task_id", "freelancer_task_executions", ["task_id"]),
        ("ix_freelancer_task_executions_assignment_id", "freelancer_task_executions", ["assignment_id"]),
        ("ix_freelancer_task_executions_freelancer_id", "freelancer_task_executions", ["freelancer_id"]),
        ("ix_freelancer_task_executions_status", "freelancer_task_executions", ["status"]),
    ]:
        op.create_index(name, table, cols)

    op.create_table(
        "freelancer_progress_updates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("execution_id", sa.Uuid(), sa.ForeignKey("freelancer_task_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("update_text", sa.Text(), nullable=False),
        sa.Column("blocker", sa.Text()),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_freelancer_progress_updates_execution_id", "freelancer_progress_updates", ["execution_id"])
    op.create_index("ix_freelancer_progress_updates_created_by_user_id", "freelancer_progress_updates", ["created_by_user_id"])

    op.create_table(
        "freelancer_work_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("execution_id", sa.Uuid(), sa.ForeignKey("freelancer_task_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_freelancer_work_reviews_execution_id", "freelancer_work_reviews", ["execution_id"])
    op.create_index("ix_freelancer_work_reviews_reviewer_user_id", "freelancer_work_reviews", ["reviewer_user_id"])

    op.create_table(
        "freelancer_work_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("execution_id", sa.Uuid(), sa.ForeignKey("freelancer_task_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hours", sa.Numeric(8, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_freelancer_work_logs_execution_id", "freelancer_work_logs", ["execution_id"])
    op.create_index("ix_freelancer_work_logs_created_by_user_id", "freelancer_work_logs", ["created_by_user_id"])

    permissions = [
        ("freelancer_work.view", "View freelancer work execution workspace"),
        ("freelancer_work.assign", "Assign freelancer execution to a task"),
        ("freelancer_work.execute", "Acknowledge, execute, update progress and submit freelancer work"),
        ("freelancer_work.review", "Review freelancer work and request approval or revision"),
        ("freelancer_work.complete", "Approve completion of freelancer work and linked task"),
    ]
    permission_table = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)), sa.column("description", sa.String(500)))
    role_permission = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    role_table = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String(100)))
    bind = op.get_bind()
    for code, description in permissions:
        permission_id = bind.execute(sa.select(permission_table.c.id).where(permission_table.c.code == code)).scalar()
        if permission_id is None:
            permission_id = bind.execute(permission_table.insert().values(code=code, description=description).returning(permission_table.c.id)).scalar()
        role_id = bind.execute(sa.select(role_table.c.id).where(role_table.c.name == "Founder / Super Admin")).scalar()
        if role_id is not None and bind.execute(sa.select(role_permission.c.permission_id).where(role_permission.c.role_id == role_id, role_permission.c.permission_id == permission_id)).scalar() is None:
            bind.execute(role_permission.insert().values(role_id=role_id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permission_table = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)))
    codes = ["freelancer_work.view", "freelancer_work.assign", "freelancer_work.execute", "freelancer_work.review", "freelancer_work.complete"]
    ids = [row[0] for row in bind.execute(sa.select(permission_table.c.id).where(permission_table.c.code.in_(codes))).all()]
    if ids:
        bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = ANY(:ids)"), {"ids": ids})
        bind.execute(sa.delete(permission_table).where(permission_table.c.id.in_(ids)))
    for table in ["freelancer_work_logs", "freelancer_work_reviews", "freelancer_progress_updates", "freelancer_task_executions"]:
        op.drop_table(table)
