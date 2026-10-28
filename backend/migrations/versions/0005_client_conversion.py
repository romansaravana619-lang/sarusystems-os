"""Add client conversion and onboarding entities.

Revision ID: 0005_client_conversion
Revises: 0004_sales_workflow_hardening
Create Date: 2026-10-25
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_client_conversion"
down_revision = "0004_sales_workflow_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "clients",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("opportunity_id", uuid_type, sa.ForeignKey("opportunities.id"), nullable=False, unique=True),
        sa.Column("source_contact_id", uuid_type, sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("company_name", sa.String(200)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(50)),
        sa.Column("status", sa.String(50), nullable=False, server_default="onboarding"),
        sa.Column("owner_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("onboarding_started_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_clients_company_id", "clients", ["company_id"])
    op.create_index("ix_clients_opportunity_id", "clients", ["opportunity_id"])
    op.create_index("ix_clients_source_contact_id", "clients", ["source_contact_id"])
    op.create_index("ix_clients_code", "clients", ["code"])
    op.create_index("ix_clients_email", "clients", ["email"])
    op.create_index("ix_clients_status", "clients", ["status"])
    op.create_index("ix_clients_owner_user_id", "clients", ["owner_user_id"])

    op.create_table(
        "client_contacts",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("client_id", uuid_type, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(50)),
        sa.Column("role", sa.String(100)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_client_contacts_client_id", "client_contacts", ["client_id"])
    op.create_index("ix_client_contacts_email", "client_contacts", ["email"])

    op.create_table(
        "client_agreements",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("client_id", uuid_type, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("document_id", sa.String(100)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_client_agreements_client_id", "client_agreements", ["client_id"])
    op.create_index("ix_client_agreements_status", "client_agreements", ["status"])

    permissions = [
        ("clients.view", "View company clients"),
        ("clients.create", "Convert won opportunities into clients"),
        ("clients.edit", "Edit clients and client records"),
        ("clients.onboarding", "Start client onboarding"),
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
    op.execute(
        permissions_table.delete().where(
            permissions_table.c.code.in_(
                ["clients.view", "clients.create", "clients.edit", "clients.onboarding"]
            )
        )
    )
    op.drop_index("ix_client_agreements_status", table_name="client_agreements")
    op.drop_index("ix_client_agreements_client_id", table_name="client_agreements")
    op.drop_table("client_agreements")
    op.drop_index("ix_client_contacts_email", table_name="client_contacts")
    op.drop_index("ix_client_contacts_client_id", table_name="client_contacts")
    op.drop_table("client_contacts")
    op.drop_index("ix_clients_owner_user_id", table_name="clients")
    op.drop_index("ix_clients_status", table_name="clients")
    op.drop_index("ix_clients_email", table_name="clients")
    op.drop_index("ix_clients_code", table_name="clients")
    op.drop_index("ix_clients_source_contact_id", table_name="clients")
    op.drop_index("ix_clients_opportunity_id", table_name="clients")
    op.drop_index("ix_clients_company_id", table_name="clients")
    op.drop_table("clients")
