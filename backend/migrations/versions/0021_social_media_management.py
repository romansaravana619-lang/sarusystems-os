"""Add Social Media Management V1."""
from alembic import op
import sqlalchemy as sa

revision = "0021_social_media_management"
down_revision = "0020_content_reconciliation"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("social_posts",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False), sa.Column("platform", sa.String(40), nullable=False), sa.Column("post_id", sa.String(120), nullable=False),
        sa.Column("post_title", sa.String(240)), sa.Column("post_content", sa.Text()), sa.Column("alt_text", sa.Text()), sa.Column("creative_url", sa.Text()), sa.Column("external_link", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"), sa.Column("post_date", sa.DateTime(timezone=True)), sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("company_id", "platform", "post_id", name="uq_social_post_identity"))
    for col in ["company_id", "platform", "status", "post_date"]: op.create_index(f"ix_social_posts_{col}", "social_posts", [col])
    permissions = [
        ("social_media.dashboard.view", "View social media dashboard"), ("social_media.posts.view", "View social media posts"),
        ("social_media.posts.create", "Create social media posts"), ("social_media.posts.edit", "Manage social media posts"),
    ]
    pt = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)), sa.column("description", sa.String(500)))
    rt = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String(100)))
    rpt = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    bind = op.get_bind(); role = bind.execute(sa.select(rt.c.id).where(rt.c.name == "Founder / Super Admin")).scalar()
    for code, desc in permissions:
        pid = bind.execute(sa.select(pt.c.id).where(pt.c.code == code)).scalar()
        if pid is None: pid = bind.execute(pt.insert().values(code=code, description=desc).returning(pt.c.id)).scalar()
        if role and bind.execute(sa.select(rpt.c.permission_id).where(rpt.c.role_id == role, rpt.c.permission_id == pid)).scalar() is None: bind.execute(rpt.insert().values(role_id=role, permission_id=pid))

def downgrade():
    for col in ["company_id", "platform", "status", "post_date"]: op.drop_index(f"ix_social_posts_{col}", table_name="social_posts")
    op.drop_table("social_posts")
