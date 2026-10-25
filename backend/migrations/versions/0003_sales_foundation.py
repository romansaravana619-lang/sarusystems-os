"""Add Sales foundation entities.

Revision ID: 0003_sales_foundation
Revises: 0002_crm_foundation
Create Date: 2026-10-25
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_sales_foundation"
down_revision = "0002_crm_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "discoveries",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("opportunity_id", uuid_type, sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("business_problem", sa.Text()),
        sa.Column("goals", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_discoveries_opportunity_id", "discoveries", ["opportunity_id"])
    op.create_index("ix_discoveries_created_by_user_id", "discoveries", ["created_by_user_id"])

    op.create_table(
        "requirements",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("opportunity_id", uuid_type, sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text()),
        sa.Column("acceptance_criteria", sa.Text()),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approved_by_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_requirements_opportunity_id", "requirements", ["opportunity_id"])
    op.create_index("ix_requirements_approved_by_user_id", "requirements", ["approved_by_user_id"])
    op.create_index("ix_requirements_created_by_user_id", "requirements", ["created_by_user_id"])

    op.create_table(
        "proposals",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("opportunity_id", uuid_type, sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_proposals_opportunity_id", "proposals", ["opportunity_id"])
    op.create_index("ix_proposals_status", "proposals", ["status"])
    op.create_index("ix_proposals_created_by_user_id", "proposals", ["created_by_user_id"])

    op.create_table(
        "deal_outcomes",
        sa.Column("opportunity_id", uuid_type, sa.ForeignKey("opportunities.id"), primary_key=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("decided_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
    )

    permissions = [
        ("sales.discovery.view", "View opportunity discoveries"),
        ("sales.discovery.create", "Create opportunity discoveries"),
        ("sales.requirements.view", "View opportunity requirements"),
        ("sales.requirements.create", "Create opportunity requirements"),
        ("sales.proposals.create", "Create sales proposals"),
        ("sales.proposals.edit", "Edit sales proposals"),
        ("sales.deal.decide", "Mark sales deals won or lost"),
    ]
    permissions_table = sa.table("permissions", sa.column("id", uuid_type), sa.column("code", sa.String), sa.column("description", sa.String))
    for code, description in permissions:
        op.execute(permissions_table.insert().values(id=uuid4(), code=code, description=description))


def downgrade() -> None:
    op.drop_table("deal_outcomes")
    op.drop_index("ix_proposals_created_by_user_id", table_name="proposals")
    op.drop_index("ix_proposals_status", table_name="proposals")
    op.drop_index("ix_proposals_opportunity_id", table_name="proposals")
    op.drop_table("proposals")
    op.drop_index("ix_requirements_created_by_user_id", table_name="requirements")
    op.drop_index("ix_requirements_approved_by_user_id", table_name="requirements")
    op.drop_index("ix_requirements_opportunity_id", table_name="requirements")
    op.drop_table("requirements")
    op.drop_index("ix_discoveries_created_by_user_id", table_name="discoveries")
    op.drop_index("ix_discoveries_opportunity_id", table_name="discoveries")
    op.drop_table("discoveries")
