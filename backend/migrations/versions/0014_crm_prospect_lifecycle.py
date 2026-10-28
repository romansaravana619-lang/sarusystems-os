"""Align prospect status values with the approved CRM lead lifecycle.

Revision ID: 0014_crm_prospect_lifecycle
Revises: 0013_task_management_reconciliation
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_crm_prospect_lifecycle"
down_revision = "0013_task_management_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    prospect = sa.table("prospects", sa.column("status", sa.String(length=30)))
    bind = op.get_bind()
    bind.execute(prospect.update().where(prospect.c.status == "qualified").values(status="responded"))
    bind.execute(prospect.update().where(prospect.c.status == "discovery").values(status="discovery_scheduled"))
    bind.execute(prospect.update().where(prospect.c.status == "proposal").values(status="proposal_sent"))
    bind.execute(prospect.update().where(prospect.c.status == "nurture").values(status="on_hold"))


def downgrade() -> None:
    prospect = sa.table("prospects", sa.column("status", sa.String(length=30)))
    bind = op.get_bind()
    bind.execute(prospect.update().where(prospect.c.status == "responded").values(status="qualified"))
    bind.execute(prospect.update().where(prospect.c.status == "discovery_scheduled").values(status="discovery"))
    bind.execute(prospect.update().where(prospect.c.status == "proposal_sent").values(status="proposal"))
    bind.execute(prospect.update().where(prospect.c.status == "on_hold").values(status="nurture"))
