"""Notification Engine.

Revision ID: 0029_notification_engine
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0029_notification_engine"
down_revision = "0028_calendar_scheduling"
branch_labels = None
depends_on = None

PERMISSIONS = [
    ("notifications.dashboard.view", "View notification dashboard"),
    ("notifications.view", "View own notifications"),
    ("notifications.create", "Create notifications"),
    ("notifications.manage", "Read and archive own notifications"),
    ("notifications.preferences.view", "View notification preferences"),
    ("notifications.preferences.edit", "Edit notification preferences"),
]

def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notification_type", sa.String(60), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False, server_default="in_app"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="unread"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("source_type", sa.String(80)),
        sa.Column("source_id", sa.String(100)),
        sa.Column("action_url", sa.String(1000)),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for name, col in [("company", "company_id"), ("recipient", "recipient_user_id"), ("type", "notification_type"), ("status", "status"), ("priority", "priority"), ("scheduled", "scheduled_for"), ("source", "source_id")]:
        op.create_index(f"ix_notifications_{name}", "notifications", [col])
    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notification_type", sa.String(60), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "user_id", "notification_type", "channel", name="uq_notification_preference"),
    )
    op.create_index("ix_notification_preferences_company", "notification_preferences", ["company_id"])
    op.create_index("ix_notification_preferences_user", "notification_preferences", ["user_id"])
    op.create_index("ix_notification_preferences_type", "notification_preferences", ["notification_type"])

    permissions = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)), sa.column("description", sa.String(500)))
    roles = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String(100)))
    role_permissions = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    bind = op.get_bind()
    role_ids = bind.execute(sa.select(roles.c.id).where(sa.or_(roles.c.name.ilike("%founder%"), roles.c.name.ilike("%super admin%")))).scalars().all()
    for code, description in PERMISSIONS:
        pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if pid is None: pid = bind.execute(permissions.insert().values(code=code, description=description).returning(permissions.c.id)).scalar()
        for rid in role_ids:
            if bind.execute(sa.select(role_permissions.c.permission_id).where(role_permissions.c.role_id == rid, role_permissions.c.permission_id == pid)).scalar() is None:
                bind.execute(role_permissions.insert().values(role_id=rid, permission_id=pid))

def downgrade():
    permissions = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)))
    role_permissions = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    bind = op.get_bind()
    ids = bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_([x[0] for x in PERMISSIONS]))).scalars().all()
    if ids:
        bind.execute(role_permissions.delete().where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(permissions.delete().where(permissions.c.id.in_(ids)))
    op.drop_table("notification_preferences")
    op.drop_table("notifications")
