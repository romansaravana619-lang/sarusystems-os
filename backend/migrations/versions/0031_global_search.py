"""Global Search permission.

Revision ID: 0031_global_search
"""
from alembic import op
import sqlalchemy as sa

revision = "0031_global_search"
down_revision = "0030_analytics"
branch_labels = None
depends_on = None

PERMISSIONS = [("global_search.view", "Search company records across connected modules")]


def upgrade():
    permissions = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)), sa.column("description", sa.String(500)))
    roles = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String(100)))
    role_permissions = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    bind = op.get_bind()
    role_ids = bind.execute(sa.select(roles.c.id).where(sa.or_(roles.c.name.ilike("%founder%"), roles.c.name.ilike("%super admin%")))).scalars().all()
    for code, description in PERMISSIONS:
        pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if pid is None:
            pid = bind.execute(permissions.insert().values(code=code, description=description).returning(permissions.c.id)).scalar()
        for rid in role_ids:
            exists = bind.execute(sa.select(role_permissions.c.permission_id).where(role_permissions.c.role_id == rid, role_permissions.c.permission_id == pid)).scalar()
            if exists is None:
                bind.execute(role_permissions.insert().values(role_id=rid, permission_id=pid))


def downgrade():
    permissions = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)))
    role_permissions = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    bind = op.get_bind()
    ids = bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_([x[0] for x in PERMISSIONS]))).scalars().all()
    if ids:
        bind.execute(role_permissions.delete().where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(permissions.delete().where(permissions.c.id.in_(ids)))
