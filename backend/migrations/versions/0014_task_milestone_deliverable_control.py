"""Add approved task/milestone/deliverable control fields.

Revision ID: 0014_task_milestone_deliverable_control
Revises: 0013_task_management_reconciliation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_task_milestone_deliverable_control"
down_revision = "0013_task_management_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)

    op.add_column("project_milestones", sa.Column("objective", sa.Text(), nullable=True))
    op.add_column("project_milestones", sa.Column("acceptance_criteria", sa.Text(), nullable=True))
    op.add_column("project_milestones", sa.Column("founder_review", sa.Text(), nullable=True))
    op.add_column("project_milestones", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("project_deliverables", sa.Column("task_id", uuid, sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True))
    op.add_column("project_deliverables", sa.Column("acceptance_criteria", sa.Text(), nullable=True))
    op.add_column("project_deliverables", sa.Column("revision_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("project_deliverables", sa.Column("final_approval", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("project_deliverables", sa.Column("final_file_or_repository", sa.Text(), nullable=True))
    op.create_index("ix_project_deliverables_task_id", "project_deliverables", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_project_deliverables_task_id", table_name="project_deliverables")
    op.drop_column("project_deliverables", "final_file_or_repository")
    op.drop_column("project_deliverables", "final_approval")
    op.drop_column("project_deliverables", "revision_required")
    op.drop_column("project_deliverables", "acceptance_criteria")
    op.drop_column("project_deliverables", "task_id")
    op.drop_column("project_milestones", "completed_at")
    op.drop_column("project_milestones", "founder_review")
    op.drop_column("project_milestones", "acceptance_criteria")
    op.drop_column("project_milestones", "objective")
