"""Company core ecosystem.

Revision ID: 0009_company_core
Revises: 0008_service_management
"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_company_core"
down_revision = "0008_service_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table("company_profiles", sa.Column("id", uuid_type, primary_key=True, nullable=False), sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("legal_name", sa.String(250)), sa.Column("tagline", sa.String(500)), sa.Column("website", sa.String(500)), sa.Column("email", sa.String(320)), sa.Column("phone", sa.String(50)), sa.Column("address", sa.Text()), sa.Column("industry", sa.String(150)), sa.Column("business_model", sa.Text()), sa.Column("vision", sa.Text()), sa.Column("mission", sa.Text()), sa.Column("brand_primary_color", sa.String(30)), sa.Column("brand_secondary_color", sa.String(30)), sa.Column("logo_url", sa.String(1000)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_company_profiles_company_id", "company_profiles", ["company_id"], unique=True)
    op.create_table("departments", sa.Column("id", uuid_type, primary_key=True, nullable=False), sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(150), nullable=False), sa.Column("code", sa.String(50), nullable=False), sa.Column("description", sa.Text()), sa.Column("owner_user_id", uuid_type, sa.ForeignKey("users.id")), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("company_id", "code", name="uq_departments_company_code"))
    op.create_index("ix_departments_company_id", "departments", ["company_id"])
    op.create_index("ix_departments_owner_user_id", "departments", ["owner_user_id"])
    op.create_table("company_goals", sa.Column("id", uuid_type, primary_key=True, nullable=False), sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(250), nullable=False), sa.Column("description", sa.Text()), sa.Column("status", sa.String(50), nullable=False, server_default="active"), sa.Column("priority", sa.String(30), nullable=False, server_default="medium"), sa.Column("target_date", sa.String(30)), sa.Column("owner_user_id", uuid_type, sa.ForeignKey("users.id")), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()))
    op.create_index("ix_company_goals_company_id", "company_goals", ["company_id"]); op.create_index("ix_company_goals_status", "company_goals", ["status"]); op.create_index("ix_company_goals_owner_user_id", "company_goals", ["owner_user_id"])
    op.create_table("company_policies", sa.Column("id", uuid_type, primary_key=True, nullable=False), sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(250), nullable=False), sa.Column("description", sa.Text()), sa.Column("policy_type", sa.String(100), nullable=False, server_default="general"), sa.Column("status", sa.String(50), nullable=False, server_default="active"), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_company_policies_company_id", "company_policies", ["company_id"])
    op.create_table("operating_rules", sa.Column("id", uuid_type, primary_key=True, nullable=False), sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(250), nullable=False), sa.Column("description", sa.Text()), sa.Column("rule_type", sa.String(100), nullable=False, server_default="operating"), sa.Column("condition", sa.Text()), sa.Column("action", sa.Text()), sa.Column("priority", sa.Integer(), nullable=False, server_default="100"), sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_operating_rules_company_id", "operating_rules", ["company_id"])
    permissions = [("company.view", "View company core"), ("company.edit", "Edit company profile and brand information"), ("company.departments.manage", "Manage company departments"), ("company.goals.manage", "Manage company goals"), ("company.policies.manage", "Manage company policies"), ("company.rules.manage", "Manage operating rules")]
    table = sa.table("permissions", sa.column("id", uuid_type), sa.column("code", sa.String), sa.column("description", sa.String))
    for code, description in permissions:
        if op.get_bind().execute(sa.select(table.c.id).where(table.c.code == code)).first() is None:
            op.execute(table.insert().values(id=uuid4(), code=code, description=description))


def downgrade() -> None:
    table = sa.table("permissions", sa.column("code", sa.String))
    op.execute(table.delete().where(table.c.code.in_(["company.view", "company.edit", "company.departments.manage", "company.goals.manage", "company.policies.manage", "company.rules.manage"])))
    op.drop_index("ix_operating_rules_company_id", table_name="operating_rules"); op.drop_table("operating_rules")
    op.drop_index("ix_company_policies_company_id", table_name="company_policies"); op.drop_table("company_policies")
    op.drop_index("ix_company_goals_owner_user_id", table_name="company_goals"); op.drop_index("ix_company_goals_status", table_name="company_goals"); op.drop_index("ix_company_goals_company_id", table_name="company_goals"); op.drop_table("company_goals")
    op.drop_index("ix_departments_owner_user_id", table_name="departments"); op.drop_index("ix_departments_company_id", table_name="departments"); op.drop_table("departments")
    op.drop_index("ix_company_profiles_company_id", table_name="company_profiles"); op.drop_table("company_profiles")
