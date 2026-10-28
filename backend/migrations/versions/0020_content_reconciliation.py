"""Reconcile Content Management V1 with approved content workflow."""
from alembic import op
import sqlalchemy as sa

revision = "0020_content_reconciliation"
down_revision = "0019_content_management"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("content_ideas", sa.Column("campaign_id", sa.Uuid(), sa.ForeignKey("marketing_campaigns.id", ondelete="SET NULL")))
    op.create_index("ix_content_ideas_campaign_id", "content_ideas", ["campaign_id"])
    op.add_column("content_assets", sa.Column("script", sa.Text()))
    op.add_column("content_assets", sa.Column("brand_qa_status", sa.String(30), nullable=False, server_default="pending"))
    op.add_column("content_assets", sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id")))
    op.add_column("content_assets", sa.Column("approved_at", sa.DateTime(timezone=True)))
    op.create_index("ix_content_assets_brand_qa_status", "content_assets", ["brand_qa_status"])
    op.create_index("ix_content_assets_approved_by_user_id", "content_assets", ["approved_by_user_id"])


def downgrade():
    op.drop_index("ix_content_assets_approved_by_user_id", table_name="content_assets")
    op.drop_index("ix_content_assets_brand_qa_status", table_name="content_assets")
    op.drop_column("content_assets", "approved_at")
    op.drop_column("content_assets", "approved_by_user_id")
    op.drop_column("content_assets", "brand_qa_status")
    op.drop_column("content_assets", "script")
    op.drop_index("ix_content_ideas_campaign_id", table_name="content_ideas")
    op.drop_column("content_ideas", "campaign_id")
