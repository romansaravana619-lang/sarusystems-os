"""Founder action and attention tracking.

Revision ID: 0010_founder_actions
Revises: 0009_company_core
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_founder_actions"
down_revision = "0009_company_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "founder_actions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("source_module", sa.String(100), nullable=False),
        sa.Column("source_entity_id", uuid_type),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_action", sa.Text(), nullable=False),
        sa.Column("owner_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("founder_notes", sa.Text()),
        sa.Column("resolution_date", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for name, columns in {
        "ix_founder_actions_company_id": ["company_id"],
        "ix_founder_actions_category": ["category"],
        "ix_founder_actions_source_module": ["source_module"],
        "ix_founder_actions_source_entity_id": ["source_entity_id"],
        "ix_founder_actions_priority": ["priority"],
        "ix_founder_actions_owner_user_id": ["owner_user_id"],
        "ix_founder_actions_due_date": ["due_date"],
        "ix_founder_actions_status": ["status"],
    }.items():
        op.create_index(name, "founder_actions", columns)

    permissions = [
        ("command_center.actions.view", "View founder action and attention records"),
        ("command_center.actions.create", "Create founder action and attention records"),
        ("command_center.actions.edit", "Update founder action and attention records"),
    ]
    table = sa.table("permissions", sa.column("id", uuid_type), sa.column("code", sa.String), sa.column("description", sa.String))
    for code, description in permissions:
        if op.get_bind().execute(sa.select(table.c.id).where(table.c.code == code)).first() is None:
            import uuid
            op.execute(table.insert().values(id=uuid.uuid4(), code=code, description=description))


def downgrade() -> None:
    op.drop_index("ix_founder_actions_status", table_name="founder_actions")
    op.drop_index("ix_founder_actions_due_date", table_name="founder_actions")
    op.drop_index("ix_founder_actions_owner_user_id", table_name="founder_actions")
    op.drop_index("ix_founder_actions_priority", table_name="founder_actions")
    op.drop_index("ix_founder_actions_source_entity_id", table_name="founder_actions")
    op.drop_index("ix_founder_actions_source_module", table_name="founder_actions")
    op.drop_index("ix_founder_actions_category", table_name="founder_actions")
    op.drop_index("ix_founder_actions_company_id", table_name="founder_actions")
    op.drop_table("founder_actions")
