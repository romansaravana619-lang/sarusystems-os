"""Complete client ecosystem persistence.

Revision ID: 0007_client_ecosystem
Revises: 0006_task_management
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_client_ecosystem"
down_revision = "0006_task_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.add_column("clients", sa.Column("website", sa.String(500)))
    op.add_column("clients", sa.Column("industry", sa.String(150)))
    op.add_column("clients", sa.Column("address", sa.Text()))
    op.add_column("clients", sa.Column("timezone", sa.String(100)))
    op.add_column("clients", sa.Column("preferred_contact_channel", sa.String(50)))
    op.add_column("clients", sa.Column("health_status", sa.String(30), nullable=False, server_default="healthy"))
    op.add_column("clients", sa.Column("health_score", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("clients", sa.Column("health_reason", sa.Text()))
    op.add_column("clients", sa.Column("last_health_reviewed_at", sa.DateTime(timezone=True)))
    op.add_column("clients", sa.Column("next_health_review_at", sa.DateTime(timezone=True)))
    op.add_column("clients", sa.Column("onboarding_completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_clients_health_status", "clients", ["health_status"])

    op.add_column("client_contacts", sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "client_onboarding_items",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("client_id", uuid_type, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_client_onboarding_items_client_id", "client_onboarding_items", ["client_id"])
    op.create_index("ix_client_onboarding_items_status", "client_onboarding_items", ["status"])

    op.create_table(
        "client_documents",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("client_id", uuid_type, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("external_document_id", sa.String(200)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_client_documents_client_id", "client_documents", ["client_id"])
    op.create_index("ix_client_documents_document_type", "client_documents", ["document_type"])
    op.create_index("ix_client_documents_status", "client_documents", ["status"])

    op.create_table(
        "client_relations",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("client_id", uuid_type, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(40), nullable=False),
        sa.Column("related_entity_id", uuid_type, nullable=False),
        sa.Column("label", sa.String(300)),
        sa.Column("status", sa.String(50)),
        sa.Column("notes", sa.Text()),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_client_relations_client_id", "client_relations", ["client_id"])
    op.create_index("ix_client_relations_relation_type", "client_relations", ["relation_type"])
    op.create_index("ix_client_relations_related_entity_id", "client_relations", ["related_entity_id"])
    op.create_index("ix_client_relations_occurred_at", "client_relations", ["occurred_at"])

    permissions = [
        ("clients.health", "Review and update client health"),
        ("clients.documents", "Manage client document metadata"),
    ]
    permissions_table = sa.table("permissions", sa.column("id", uuid_type), sa.column("code", sa.String), sa.column("description", sa.String))
    for code, description in permissions:
        exists = op.get_bind().execute(sa.select(permissions_table.c.id).where(permissions_table.c.code == code)).first()
        if exists is None:
            op.execute(permissions_table.insert().values(id=uuid4(), code=code, description=description))


def downgrade() -> None:
    permissions_table = sa.table("permissions", sa.column("code", sa.String))
    op.execute(permissions_table.delete().where(permissions_table.c.code.in_(["clients.health", "clients.documents"])))
    for name in ["occurred_at", "related_entity_id", "relation_type", "client_id"]:
        op.drop_index(f"ix_client_relations_{name}", table_name="client_relations")
    op.drop_table("client_relations")
    for name in ["status", "document_type", "client_id"]:
        op.drop_index(f"ix_client_documents_{name}" if name != "client_id" else "ix_client_documents_client_id", table_name="client_documents")
    op.drop_table("client_documents")
    for name in ["status", "client_id"]:
        op.drop_index(f"ix_client_onboarding_items_{name}" if name == "status" else "ix_client_onboarding_items_client_id", table_name="client_onboarding_items")
    op.drop_table("client_onboarding_items")
    op.drop_column("client_contacts", "is_primary")
    op.drop_index("ix_clients_health_status", table_name="clients")
    for column in ["onboarding_completed_at", "next_health_review_at", "last_health_reviewed_at", "health_reason", "health_score", "health_status", "preferred_contact_channel", "timezone", "address", "industry", "website"]:
        op.drop_column("clients", column)
