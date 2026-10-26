"""Add Documents & Knowledge V1."""
from alembic import op
import sqlalchemy as sa

revision = "0024_documents_knowledge"
down_revision = "0023_product_management"
branch_labels = None
depends_on = None

PERMISSIONS = [
    ("documents.dashboard.view", "View documents and knowledge dashboard"),
    ("documents.view", "View company documents and knowledge"),
    ("documents.create", "Create documents and knowledge records"),
    ("documents.edit", "Manage documents and knowledge records"),
    ("documents.approve", "Approve documents and knowledge records"),
]


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("document_key", sa.String(100), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="company"),
        sa.Column("document_type", sa.String(60), nullable=False, server_default="general"),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("visibility", sa.String(30), nullable=False, server_default="internal"),
        sa.Column("version", sa.String(40), nullable=False, server_default="1.0"),
        sa.Column("description", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("external_url", sa.Text()),
        sa.Column("file_url", sa.Text()),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("reviewer_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("review_notes", sa.Text()),
        sa.Column("tags", sa.Text()),
        sa.Column("is_template", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("template_key", sa.String(100)),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="SET NULL")),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("freelancer_id", sa.Uuid(), sa.ForeignKey("freelancers.id", ondelete="SET NULL")),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="SET NULL")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "document_key", name="uq_documents_company_key"),
    )
    for col in ["company_id", "category", "document_type", "status", "visibility", "owner_user_id", "reviewer_user_id", "client_id", "project_id", "freelancer_id", "product_id", "is_template", "template_key"]:
        op.create_index(f"ix_documents_{col}", "documents", [col])

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
    op.drop_table("documents")
    permissions = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)))
    bind = op.get_bind()
    ids = bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_([p[0] for p in PERMISSIONS]))).scalars().all()
    if ids:
        bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN :ids").bindparams(sa.bindparam("ids", expanding=True)), {"ids": list(ids)})
        bind.execute(sa.delete(permissions).where(permissions.c.id.in_(ids)))
