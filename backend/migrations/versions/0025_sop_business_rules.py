"""Add SOP and Business Rules Engine V1."""
from alembic import op
import sqlalchemy as sa

revision = "0025_sop_business_rules"
down_revision = "0024_documents_knowledge"
branch_labels = None
depends_on = None

PERMISSIONS = [
    ("rules_engine.dashboard.view", "View SOP and business rules dashboard"),
    ("rules_engine.sops.view", "View SOP definitions"),
    ("rules_engine.sops.create", "Create SOP definitions"),
    ("rules_engine.sops.edit", "Manage SOP definitions"),
    ("rules_engine.rules.view", "View business rules"),
    ("rules_engine.rules.create", "Create business rules"),
    ("rules_engine.rules.edit", "Manage business rules"),
    ("rules_engine.evaluate", "Evaluate enforced business rules"),
]


def upgrade():
    op.create_table(
        "sop_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("sop_key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("purpose", sa.Text()),
        sa.Column("scope", sa.Text()),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("required_roles", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("entry_conditions", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("steps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("exit_conditions", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("prohibited_actions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("linked_document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="SET NULL")),
        sa.Column("notes", sa.Text()),
        sa.Column("is_enforced", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "sop_key", name="uq_sops_company_key"),
    )
    op.create_index("ix_sop_definitions_company_id", "sop_definitions", ["company_id"])
    op.create_index("ix_sop_definitions_status", "sop_definitions", ["status"])
    op.create_index("ix_sop_definitions_owner_user_id", "sop_definitions", ["owner_user_id"])
    op.create_index("ix_sop_definitions_linked_document_id", "sop_definitions", ["linked_document_id"])

    op.create_table(
        "business_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("rule_key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("trigger_event", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("applies_to", sa.String(100), nullable=False),
        sa.Column("required_conditions", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("prohibited_conditions", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("required_actions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("prohibited_actions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("allowed_roles", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("allowed_user_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enforcement_mode", sa.String(20), nullable=False, server_default="block"),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("reviewer_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("is_enforced", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "rule_key", name="uq_rules_company_key"),
    )
    for col in ["company_id", "status", "trigger_event", "applies_to", "priority", "owner_user_id", "reviewer_user_id", "is_enforced"]:
        op.create_index(f"ix_business_rules_{col}", "business_rules", [col])

    permissions = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)), sa.column("description", sa.String(500)))
    roles = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String(100)))
    role_permissions = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    bind = op.get_bind()
    founder_roles = bind.execute(sa.select(roles.c.id).where(sa.or_(roles.c.name.ilike("%founder%"), roles.c.name.ilike("%super admin%")))).scalars().all()
    for code, description in PERMISSIONS:
        pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if pid is None:
            pid = bind.execute(permissions.insert().values(code=code, description=description).returning(permissions.c.id)).scalar()
        for rid in founder_roles:
            exists = bind.execute(sa.select(role_permissions.c.permission_id).where(role_permissions.c.role_id == rid, role_permissions.c.permission_id == pid)).scalar()
            if exists is None:
                bind.execute(role_permissions.insert().values(role_id=rid, permission_id=pid))


def downgrade():
    op.drop_table("business_rules")
    op.drop_table("sop_definitions")
    permissions = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)))
    bind = op.get_bind()
    ids = bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_([p[0] for p in PERMISSIONS]))).scalars().all()
    if ids:
        bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN :ids").bindparams(sa.bindparam("ids", expanding=True)), {"ids": list(ids)})
        bind.execute(sa.delete(permissions).where(permissions.c.id.in_(ids)))
