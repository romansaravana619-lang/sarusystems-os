"""Harden Sales workflow permissions.

Revision ID: 0004_sales_workflow_hardening
Revises: 0003_sales_foundation
Create Date: 2026-10-25
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_sales_workflow_hardening"
down_revision = "0003_sales_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    permissions = [
        ("sales.requirements.approve", "Approve captured sales requirements"),
        ("sales.proposals.view", "View sales proposals"),
    ]
    permissions_table = sa.table(
        "permissions",
        sa.column("id", uuid_type),
        sa.column("code", sa.String),
        sa.column("description", sa.String),
    )
    for code, description in permissions:
        exists = op.get_bind().execute(
            sa.select(permissions_table.c.id).where(permissions_table.c.code == code)
        ).first()
        if exists is None:
            op.execute(permissions_table.insert().values(id=uuid4(), code=code, description=description))


def downgrade() -> None:
    permissions_table = sa.table("permissions", sa.column("code", sa.String))
    op.execute(permissions_table.delete().where(permissions_table.c.code.in_([
        "sales.requirements.approve",
        "sales.proposals.view",
    ])))
