"""Communication & Activity History.

Revision ID: 0027_communication_activity_history
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0027_communication_activity_history"
down_revision = "0026_finance_payments"
branch_labels = None
depends_on = None

PERMISSIONS = [
    ("communication.dashboard.view", "View communication and activity dashboard"),
    ("communication.activities.view", "View communication and activity history"),
    ("communication.activities.create", "Record communication and activity history"),
    ("communication.activities.edit", "Edit communication and activity history"),
]


def _grant_permissions():
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


def upgrade():
    op.create_table(
        "communication_activity_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("activity_type", sa.String(40), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False, server_default="internal"),
        sa.Column("subject", sa.String(300)),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id")),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id")),
        sa.Column("prospect_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prospects.id")),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("opportunities.id")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id")),
        sa.Column("freelancer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("freelancers.id")),
        sa.Column("entity_type", sa.String(60)),
        sa.Column("entity_id", sa.String(100)),
        sa.Column("external_reference", sa.String(500)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for name, column in [("company", "company_id"), ("type", "activity_type"), ("occurred", "occurred_at"), ("client", "client_id"), ("contact", "contact_id"), ("prospect", "prospect_id"), ("opportunity", "opportunity_id"), ("project", "project_id"), ("freelancer", "freelancer_id"), ("entity", "entity_id")]:
        op.create_index(f"ix_communication_activity_records_{name}", "communication_activity_records", [column])
    _grant_permissions()


def downgrade():
    op.drop_table("communication_activity_records")
    permissions = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)))
    role_permissions = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    bind = op.get_bind()
    ids = bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_([p[0] for p in PERMISSIONS]))).scalars().all()
    if ids:
        bind.execute(role_permissions.delete().where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(permissions.delete().where(permissions.c.id.in_(ids)))
