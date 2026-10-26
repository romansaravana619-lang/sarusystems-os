"""Reconcile social media with performance metrics and content/campaign links."""
from alembic import op
import sqlalchemy as sa

revision = "0022_social_media_reconciliation"
down_revision = "0022_social_media_performance"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("social_posts", sa.Column("content_asset_id", sa.Uuid(), sa.ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True))
    op.add_column("social_posts", sa.Column("campaign_id", sa.Uuid(), sa.ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_social_posts_content_asset_id", "social_posts", ["content_asset_id"])
    op.create_index("ix_social_posts_campaign_id", "social_posts", ["campaign_id"])


def downgrade():
    op.drop_index("ix_social_posts_campaign_id", table_name="social_posts")
    op.drop_index("ix_social_posts_content_asset_id", table_name="social_posts")
    op.drop_column("social_posts", "campaign_id")
    op.drop_column("social_posts", "content_asset_id")
