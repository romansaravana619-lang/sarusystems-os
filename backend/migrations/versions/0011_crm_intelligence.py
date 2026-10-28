"""Expand CRM lead intelligence and follow-up history."""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_crm_intelligence"
down_revision = "0010_founder_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.add_column("prospects", sa.Column("industry", sa.String(100)))
    op.add_column("prospects", sa.Column("lead_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("prospects", sa.Column("qualification_level", sa.String(20), nullable=False, server_default="COLD"))
    op.add_column("prospects", sa.Column("next_action", sa.String(500)))
    op.add_column("prospects", sa.Column("next_action_at", sa.DateTime(timezone=True)))
    op.add_column("prospects", sa.Column("last_contact_at", sa.DateTime(timezone=True)))
    for name in ["industry", "lead_score", "qualification_level", "next_action_at", "last_contact_at"]:
        op.create_index(f"ix_prospects_{name}", "prospects", [name])
    op.create_table("crm_communication_activities", sa.Column("id", uuid_type, primary_key=True, nullable=False), sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id"), nullable=False), sa.Column("prospect_id", uuid_type, sa.ForeignKey("prospects.id")), sa.Column("contact_id", uuid_type, sa.ForeignKey("contacts.id")), sa.Column("channel", sa.String(50), nullable=False), sa.Column("direction", sa.String(20), nullable=False, server_default="outbound"), sa.Column("subject", sa.String(300)), sa.Column("summary", sa.String(4000), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("actor_user_id", uuid_type, sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    for name, column in [("company_id", "company_id"), ("prospect_id", "prospect_id"), ("contact_id", "contact_id"), ("occurred_at", "occurred_at")]: op.create_index(f"ix_crm_communication_activities_{name}", "crm_communication_activities", [column])
    op.create_table("crm_follow_ups", sa.Column("id", uuid_type, primary_key=True, nullable=False), sa.Column("company_id", uuid_type, sa.ForeignKey("companies.id"), nullable=False), sa.Column("prospect_id", uuid_type, sa.ForeignKey("prospects.id")), sa.Column("contact_id", uuid_type, sa.ForeignKey("contacts.id")), sa.Column("owner_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False), sa.Column("title", sa.String(300), nullable=False), sa.Column("due_at", sa.DateTime(timezone=True), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="open"), sa.Column("notes", sa.String(4000)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    for name in ["company_id", "prospect_id", "due_at", "status"]: op.create_index(f"ix_crm_follow_ups_{name}", "crm_follow_ups", [name])
    permissions = [("crm.communication.view", "View CRM communication history"), ("crm.communication.create", "Record CRM communication history"), ("crm.followups.view", "View CRM follow-ups"), ("crm.followups.create", "Create CRM follow-ups"), ("crm.followups.edit", "Edit CRM follow-ups")]
    permissions_table = sa.table("permissions", sa.column("id", uuid_type), sa.column("code", sa.String), sa.column("description", sa.String))
    for code, description in permissions: op.execute(permissions_table.insert().values(id=uuid4(), code=code, description=description))


def downgrade() -> None:
    op.drop_table("crm_follow_ups")
    op.drop_table("crm_communication_activities")
    for name in ["last_contact_at", "next_action_at", "lead_score", "qualification_level", "industry"]: op.drop_index(f"ix_prospects_{name}", table_name="prospects")
    for name in ["last_contact_at", "next_action_at", "lead_score", "qualification_level", "industry"]: op.drop_column("prospects", name)
