"""Reconcile Social Media V1 with approved platforms and performance storage."""
from alembic import op
import sqlalchemy as sa

revision = "0022_social_media_reconciliation"
down_revision = "0021_social_media_management"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("impressions", "reach", "likes", "comments", "shares", "saves", "clicks", "views"):
        op.add_column("social_posts", sa.Column(name, sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    for name in ("views", "clicks", "saves", "shares", "comments", "likes", "reach", "impressions"):
        op.drop_column("social_posts", name)
