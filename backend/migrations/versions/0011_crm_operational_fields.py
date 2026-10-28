"""Add CRM operational prospect fields.

Revision ID: 0011_crm_operational_fields
Revises: 0010_founder_actions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_crm_operational_fields"
down_revision = "0010_founder_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    additions = [
        ("location", sa.String(200)), ("website", sa.String(500)), ("preferred_channel", sa.String(50)),
        ("outreach_channel", sa.String(50)), ("problem_observed", sa.String(2000)), ("potential_service", sa.String(200)),
        ("discovery_angle", sa.String(2000)), ("why_selected", sa.String(2000)),
        ("first_contact_at", sa.DateTime(timezone=True)), ("follow_up_count", sa.Integer(), 0),
    ]
    for item in additions:
        name, col = item[0], item[1]
        kwargs = {"nullable": True}
        if len(item) == 3: kwargs["nullable"] = False; kwargs["server_default"] = str(item[2])
        op.add_column("prospects", sa.Column(name, col, **kwargs))
    for name in ("location", "outreach_channel", "first_contact_at"):
        op.create_index(f"ix_prospects_{name}", "prospects", [name])

    permissions = [
        ("crm.dashboard.view", "View CRM pipeline and operating metrics"),
        ("crm.pipeline.view", "View CRM pipeline and attribution breakdowns"),
    ]
    table = sa.table("permissions", sa.column("id", uuid_type), sa.column("code", sa.String), sa.column("description", sa.String))
    import uuid
    for code, description in permissions:
        if op.get_bind().execute(sa.select(table.c.id).where(table.c.code == code)).first() is None:
            op.execute(table.insert().values(id=uuid.uuid4(), code=code, description=description))


def downgrade() -> None:
    for name in ("first_contact_at", "outreach_channel", "location"):
        op.drop_index(f"ix_prospects_{name}", table_name="prospects")
    for name in ("follow_up_count", "first_contact_at", "why_selected", "discovery_angle", "potential_service", "problem_observed", "outreach_channel", "preferred_channel", "website", "location"):
        op.drop_column("prospects", name)
