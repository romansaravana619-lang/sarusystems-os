"""company core ecosystem

Revision ID: 0009_company_core
Revises: 0008_service_management
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_company_core"
down_revision = "0008_service_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("legal_name", sa.String(250)), sa.Column("tagline", sa.String(500)), sa.Column("website", sa.String(500)),
        sa.Column("email", sa.String(320)), sa.Column("phone", sa.String(50)), sa.Column("address", sa.Text()),
        sa.Column("industry", sa.String(150)), sa.Column("business_model", sa.Text()), sa.Column("vision", sa.Text()), sa.Column("mission", sa.Text()),
        sa.Column("brand_primary_color", sa.String(30)), sa.Column("brand_secondary_color", sa.String(30)), sa.Column("logo_url", sa.String(1000)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_company_profiles_company_id", "company_profiles", ["company_id"], unique=True)
    for table, cols in {
        "departments": [("name", sa.String(150), False), ("code", sa.String(50), False), ("description", sa.Text(), True), ("owner_user_id", postgresql.UUID(as_uuid=True), True)],
        "company_goals": [("title", sa.String(250), False), ("description", sa.Text(), True), ("status", sa.String(50), False), ("priority", sa.String(30), False), ("target_date", sa.String(30), True), ("owner_user_id", postgresql.UUID(as_uuid=True), True)],
        "company_policies": [("title", sa.String(250), False), ("description", sa.Text(), True), ("policy_type", sa.String(100), False), ("status", sa.String(50), False), ("version", sa.Integer(), False)],
        "operating_rules": [("name", sa.String(250), False), ("description", sa.Text(), True), ("rule_type", sa.String(100), False), ("condition", sa.Text(), True), ("action", sa.Text(), True), ("priority", sa.Integer(), False)],
    }.items():
        op.create_table(table, sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False), *[sa.Column(n, t, nullable=not nullable) for n, t, nullable in cols], sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()) if table != "operating_rules" else sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        op.create_index(f"ix_{table}_company_id", table, ["company_id"])

    op.execute("INSERT INTO permissions (id, code, description, created_at, updated_at) VALUES (gen_random_uuid(), 'company.view', 'View company core', now(), now()) ON CONFLICT (code) DO NOTHING")
    for code, desc in [("company.edit", "Edit company profile and brand information"), ("company.departments.manage", "Manage company departments"), ("company.goals.manage", "Manage company goals"), ("company.policies.manage", "Manage company policies"), ("company.rules.manage", "Manage operating rules")]:
        op.execute(f"INSERT INTO permissions (id, code, description, created_at, updated_at) VALUES (gen_random_uuid(), '{code}', '{desc}', now(), now()) ON CONFLICT (code) DO NOTHING")


def downgrade() -> None:
    for table in ["operating_rules", "company_policies", "company_goals", "departments", "company_profiles"]:
        op.drop_table(table)
    op.execute("DELETE FROM permissions WHERE code IN ('company.view','company.edit','company.departments.manage','company.goals.manage','company.policies.manage','company.rules.manage')")
