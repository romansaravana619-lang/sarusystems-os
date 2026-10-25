"""Add service catalog and delivery templates.

Revision ID: 0008_service_management
Revises: 0007_client_ecosystem
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_service_management"
down_revision = "0007_client_ecosystem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "services",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("description", sa.Text()),
        sa.Column("pricing_model", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("base_price", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("typical_duration_days", sa.Integer()),
        sa.Column("required_skills", sa.Text()),
        sa.Column("freelancer_roles", sa.Text()),
        sa.Column("workflow_template", sa.Text()),
        sa.Column("deliverable_template", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "code", name="uq_services_company_code"),
    )
    op.create_index("ix_services_company_id", "services", ["company_id"])
    op.create_index("ix_services_code", "services", ["code"])
    op.create_index("ix_services_category", "services", ["category"])

    for table_name in ("service_requirements", "service_deliverables"):
        op.create_table(
            table_name,
            sa.Column("id", uuid_type, primary_key=True, nullable=False),
            sa.Column("service_id", uuid_type, sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index(f"ix_{table_name}_service_id", table_name, ["service_id"])

    permissions = [
        ("services.view", "View service catalog"),
        ("services.create", "Create services"),
        ("services.edit", "Edit services, requirements and deliverables"),
    ]
    permissions_table = sa.table("permissions", sa.column("id", uuid_type), sa.column("code", sa.String), sa.column("description", sa.String))
    for code, description in permissions:
        exists = op.get_bind().execute(sa.select(permissions_table.c.id).where(permissions_table.c.code == code)).first()
        if exists is None:
            op.execute(permissions_table.insert().values(id=uuid4(), code=code, description=description))


def downgrade() -> None:
    permissions_table = sa.table("permissions", sa.column("code", sa.String))
    op.execute(permissions_table.delete().where(permissions_table.c.code.in_(["services.view", "services.create", "services.edit"])))
    op.drop_index("ix_service_deliverables_service_id", table_name="service_deliverables")
    op.drop_table("service_deliverables")
    op.drop_index("ix_service_requirements_service_id", table_name="service_requirements")
    op.drop_table("service_requirements")
    op.drop_index("ix_services_category", table_name="services")
    op.drop_index("ix_services_code", table_name="services")
    op.drop_index("ix_services_company_id", table_name="services")
    op.drop_table("services")
