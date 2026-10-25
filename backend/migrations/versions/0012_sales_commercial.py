"""Add quotations, negotiations and deal loss reasons; merge CRM heads."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = "0012_sales_commercial"
down_revision = "0011_crm_operational_fields"
depends_on = "0011_crm_intelligence"
branch_labels = None


def upgrade() -> None:
    u = postgresql.UUID(as_uuid=True)
    op.create_table("quotations",
        sa.Column("id", u, primary_key=True), sa.Column("opportunity_id", u, sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("proposal_id", u, sa.ForeignKey("proposals.id")), sa.Column("quotation_number", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("subtotal", sa.Numeric(12,2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(12,2), nullable=False, server_default="0"), sa.Column("total_amount", sa.Numeric(12,2), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True)), sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text()), sa.Column("created_by_user_id", u, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("negotiations",
        sa.Column("id", u, primary_key=True), sa.Column("opportunity_id", u, sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("proposal_id", u, sa.ForeignKey("proposals.id")), sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("requested_amount", sa.Numeric(12,2)), sa.Column("summary", sa.Text(), nullable=False), sa.Column("next_action", sa.String(500)),
        sa.Column("next_action_at", sa.DateTime(timezone=True)), sa.Column("created_by_user_id", u, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    for table, cols in (("quotations", ["opportunity_id","proposal_id","status"]),("negotiations", ["opportunity_id","proposal_id","status"])):
        for col in cols: op.create_index(f"ix_{table}_{col}", table, [col])
    op.add_column("deal_outcomes", sa.Column("lost_reason", sa.String(200)))
    permissions = [("sales.dashboard.view","View sales pipeline and conversion metrics"),("sales.quotations.view","View sales quotations"),("sales.quotations.create","Create sales quotations"),("sales.quotations.edit","Edit sales quotations"),("sales.negotiations.view","View sales negotiations"),("sales.negotiations.create","Create sales negotiations"),("sales.negotiations.edit","Edit sales negotiations")]
    table=sa.table("permissions",sa.column("id",u),sa.column("code",sa.String),sa.column("description",sa.String))
    for code,desc in permissions:
        if op.get_bind().execute(sa.select(table.c.id).where(table.c.code==code)).first() is None:
            op.execute(table.insert().values(id=uuid.uuid4(),code=code,description=desc))


def downgrade() -> None:
    op.drop_column("deal_outcomes","lost_reason")
    op.drop_table("negotiations")
    op.drop_table("quotations")
