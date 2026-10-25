"""Add CRM foundation entities.

Revision ID: 0002_crm_foundation
Revises: 0001_initial_identity
Create Date: 2026-10-25
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_crm_foundation"
down_revision = "0001_initial_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    common = [
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]

    op.create_table(
        "prospects",
        *common,
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("company_name", sa.String(200)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(50)),
        sa.Column("source", sa.String(100)),
        sa.Column("status", sa.String(50), nullable=False, server_default="new"),
        sa.Column("owner_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("notes", sa.String(4000)),
    )
    op.create_index("ix_prospects_company_id", "prospects", ["company_id"])
    op.create_index("ix_prospects_email", "prospects", ["email"])
    op.create_index("ix_prospects_status", "prospects", ["status"])
    op.create_index("ix_prospects_owner_user_id", "prospects", ["owner_user_id"])

    op.create_table(
        "contacts",
        *common,
        sa.Column("prospect_id", uuid_type, sa.ForeignKey("prospects.id"), unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("company_name", sa.String(200)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(50)),
        sa.Column("notes", sa.String(4000)),
    )
    op.create_index("ix_contacts_company_id", "contacts", ["company_id"])
    op.create_index("ix_contacts_prospect_id", "contacts", ["prospect_id"], unique=True)
    op.create_index("ix_contacts_email", "contacts", ["email"])

    op.create_table(
        "opportunities",
        *common,
        sa.Column("contact_id", uuid_type, sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("service", sa.String(200)),
        sa.Column("stage", sa.String(50), nullable=False, server_default="qualification"),
        sa.Column("estimated_value", sa.Float()),
        sa.Column("owner_user_id", uuid_type, sa.ForeignKey("users.id")),
        sa.Column("notes", sa.String(4000)),
    )
    op.create_index("ix_opportunities_company_id", "opportunities", ["company_id"])
    op.create_index("ix_opportunities_contact_id", "opportunities", ["contact_id"])
    op.create_index("ix_opportunities_stage", "opportunities", ["stage"])
    op.create_index("ix_opportunities_owner_user_id", "opportunities", ["owner_user_id"])

    permissions = [
        ("crm.prospects.view", "View CRM prospects"),
        ("crm.prospects.create", "Create CRM prospects"),
        ("crm.prospects.edit", "Edit CRM prospects"),
        ("crm.prospects.convert", "Convert CRM prospects to contacts"),
        ("crm.contacts.view", "View CRM contacts"),
        ("crm.contacts.create", "Create CRM contacts"),
        ("crm.opportunities.view", "View CRM opportunities"),
        ("crm.opportunities.create", "Create CRM opportunities"),
        ("crm.opportunities.edit", "Edit CRM opportunities"),
    ]
    permissions_table = sa.table(
        "permissions",
        sa.column("id", uuid_type),
        sa.column("code", sa.String),
        sa.column("description", sa.String),
    )
    for code, description in permissions:
        op.execute(
            permissions_table.insert().values(
                id=uuid4(), code=code, description=description
            )
        )


def downgrade() -> None:
    op.drop_index("ix_opportunities_owner_user_id", table_name="opportunities")
    op.drop_index("ix_opportunities_stage", table_name="opportunities")
    op.drop_index("ix_opportunities_contact_id", table_name="opportunities")
    op.drop_index("ix_opportunities_company_id", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_index("ix_contacts_email", table_name="contacts")
    op.drop_index("ix_contacts_prospect_id", table_name="contacts")
    op.drop_index("ix_contacts_company_id", table_name="contacts")
    op.drop_table("contacts")
    op.drop_index("ix_prospects_owner_user_id", table_name="prospects")
    op.drop_index("ix_prospects_status", table_name="prospects")
    op.drop_index("ix_prospects_email", table_name="prospects")
    op.drop_index("ix_prospects_company_id", table_name="prospects")
    op.drop_table("prospects")
