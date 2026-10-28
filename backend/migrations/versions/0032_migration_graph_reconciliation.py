"""Reconcile all remaining Alembic migration heads into one linear tip.

Revision ID: 0032_migration_graph_reconciliation
Revises: 0031_global_search, 0012_sales_commercial, 0014_task_milestone_deliverable_control, 0016_freelancer_constraints
"""

revision = "0032_migration_graph_reconciliation"
down_revision = (
    "0031_global_search",
    "0012_sales_commercial",
    "0014_task_milestone_deliverable_control",
    "0016_freelancer_constraints",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge existing migration branches without changing the schema."""
    pass


def downgrade() -> None:
    """Re-open the previously reconciled migration branches."""
    pass
