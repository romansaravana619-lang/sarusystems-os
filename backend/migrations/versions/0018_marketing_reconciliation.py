"""Reconcile Marketing Management V1 operational gaps."""
from alembic import op
import sqlalchemy as sa

revision = "0018_marketing_reconciliation"
down_revision = "0017_marketing_management"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("marketing_campaigns", sa.Column("target_leads", sa.Integer()))
    op.add_column("marketing_campaigns", sa.Column("target_conversions", sa.Integer()))
    op.add_column("marketing_campaigns", sa.Column("target_spend", sa.Numeric(12, 2)))
    op.add_column("marketing_campaigns", sa.Column("target_revenue", sa.Numeric(12, 2)))
    op.add_column("marketing_campaign_metrics", sa.Column("revenue", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.create_unique_constraint("uq_marketing_campaign_metric_date", "marketing_campaign_metrics", ["campaign_id", "metric_date"])

    permissions = [
        ("marketing.audiences.edit", "Edit marketing audience definitions"),
    ]
    pt = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)), sa.column("description", sa.String(500)))
    rt = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String(100)))
    rpt = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    bind = op.get_bind()
    role = bind.execute(sa.select(rt.c.id).where(rt.c.name == "Founder / Super Admin")).scalar()
    for code, description in permissions:
        pid = bind.execute(sa.select(pt.c.id).where(pt.c.code == code)).scalar()
        if pid is None:
            pid = bind.execute(pt.insert().values(code=code, description=description).returning(pt.c.id)).scalar()
        if role is not None and bind.execute(sa.select(rpt.c.permission_id).where(rpt.c.role_id == role, rpt.c.permission_id == pid)).scalar() is None:
            bind.execute(rpt.insert().values(role_id=role, permission_id=pid))


def downgrade():
    op.drop_constraint("uq_marketing_campaign_metric_date", "marketing_campaign_metrics", type_="unique")
    op.drop_column("marketing_campaign_metrics", "revenue")
    op.drop_column("marketing_campaigns", "target_revenue")
    op.drop_column("marketing_campaigns", "target_spend")
    op.drop_column("marketing_campaigns", "target_conversions")
    op.drop_column("marketing_campaigns", "target_leads")
