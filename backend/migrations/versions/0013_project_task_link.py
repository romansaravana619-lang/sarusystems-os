"""Link tasks to projects for project delivery traceability."""

from alembic import op
import sqlalchemy as sa

revision = "0013_project_task_link"
down_revision = "0012_project_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("project_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_tasks_project_id_projects",
        "tasks",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_project_id", table_name="tasks")
    op.drop_constraint("fk_tasks_project_id_projects", "tasks", type_="foreignkey")
    op.drop_column("tasks", "project_id")
