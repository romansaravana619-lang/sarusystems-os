"""Add Product Management V1 domain and workflows."""
from alembic import op
import sqlalchemy as sa

revision = "0023_product_management"
down_revision = "0022_social_media_reconciliation"
branch_labels = None
depends_on = None


PERMISSION_ROWS = [["products.dashboard.view","View product management dashboard"],["products.view","View products"],["products.create","Create products"],["products.edit","Manage products"],["products.roadmap.view","View product roadmaps"],["products.roadmap.edit","Manage product roadmaps"],["products.features.view","View product features"],["products.features.edit","Manage product features"],["products.requirements.view","View product requirements"],["products.requirements.edit","Manage product requirements"],["products.requirements.approve","Approve product requirements"],["products.issues.view","View product issues"],["products.issues.create","Create product issues"],["products.issues.edit","Manage product issues and retests"],["products.versions.view","View product versions"],["products.versions.edit","Manage product versions"],["products.releases.view","View product releases"],["products.releases.edit","Manage product releases"],["products.releases.approve","Approve product releases"],["products.documents.view","View product documentation"],["products.documents.edit","Manage product documentation"],["products.documents.approve","Approve product documentation"]]


def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("product_type", sa.String(40), nullable=False, server_default="internal"),
        sa.Column("lifecycle_status", sa.String(40), nullable=False, server_default="discovery"),
        sa.Column("current_version", sa.String(80)),
        sa.Column("repository_url", sa.Text()),
        sa.Column("documentation_url", sa.Text()),
        sa.Column("demo_url", sa.Text()),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "code", name="uq_products_company_code"),
        sa.UniqueConstraint("company_id", "name", name="uq_products_company_name"),
    )
    op.create_table(
        "product_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("name", sa.String(240)),
        sa.Column("status", sa.String(40), nullable=False, server_default="planned"),
        sa.Column("target_release_at", sa.DateTime(timezone=True)),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("changelog", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "version", name="uq_product_versions_version"),
    )
    op.create_table(
        "product_roadmap_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(40), nullable=False, server_default="feature"),
        sa.Column("status", sa.String(40), nullable=False, server_default="backlog"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("target_version_id", sa.Uuid(), sa.ForeignKey("product_versions.id", ondelete="SET NULL")),
        sa.Column("target_date", sa.DateTime(timezone=True)),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "product_features",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("roadmap_item_id", sa.Uuid(), sa.ForeignKey("product_roadmap_items.id", ondelete="SET NULL")),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("acceptance_criteria", sa.Text()),
        sa.Column("status", sa.String(40), nullable=False, server_default="proposed"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "code", name="uq_product_features_product_code"),
    )
    op.create_table(
        "product_requirements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_id", sa.Uuid(), sa.ForeignKey("product_features.id", ondelete="SET NULL")),
        sa.Column("requirement_key", sa.String(80), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("acceptance_criteria", sa.Text()),
        sa.Column("requirement_type", sa.String(40), nullable=False, server_default="functional"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "requirement_key", name="uq_product_requirements_key"),
    )
    op.create_table(
        "product_issues",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_id", sa.Uuid(), sa.ForeignKey("product_features.id", ondelete="SET NULL")),
        sa.Column("requirement_id", sa.Uuid(), sa.ForeignKey("product_requirements.id", ondelete="SET NULL")),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="SET NULL")),
        sa.Column("issue_key", sa.String(80), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("expected_result", sa.Text()),
        sa.Column("actual_result", sa.Text()),
        sa.Column("reproduction_steps", sa.Text()),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(40), nullable=False, server_default="open"),
        sa.Column("assigned_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("fix_date", sa.DateTime(timezone=True)),
        sa.Column("retest_result", sa.String(40)),
        sa.Column("founder_notes", sa.Text()),
        sa.Column("resolution", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "issue_key", name="uq_product_issues_key"),
    )
    op.create_table(
        "product_releases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", sa.Uuid(), sa.ForeignKey("product_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_key", sa.String(100), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="planned"),
        sa.Column("release_notes", sa.Text()),
        sa.Column("deployment_url", sa.Text()),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "release_key", name="uq_product_releases_key"),
    )
    op.create_table(
        "product_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_id", sa.Uuid(), sa.ForeignKey("product_features.id", ondelete="SET NULL")),
        sa.Column("version_id", sa.Uuid(), sa.ForeignKey("product_versions.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False, server_default="technical"),
        sa.Column("document_url", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("visibility", sa.String(30), nullable=False, server_default="internal"),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    for table, cols in {
        "products": ["company_id", "code", "name", "product_type", "lifecycle_status", "owner_user_id"],
        "product_versions": ["company_id", "product_id", "status", "target_release_at"],
        "product_roadmap_items": ["company_id", "product_id", "category", "status", "priority", "target_version_id", "target_date", "owner_user_id"],
        "product_features": ["company_id", "product_id", "roadmap_item_id", "status", "priority", "owner_user_id"],
        "product_requirements": ["company_id", "product_id", "feature_id", "requirement_type", "priority", "status"],
        "product_issues": ["company_id", "product_id", "feature_id", "requirement_id", "task_id", "severity", "priority", "status", "assigned_user_id"],
        "product_releases": ["company_id", "product_id", "version_id", "status", "released_at"],
        "product_documents": ["company_id", "product_id", "feature_id", "version_id", "document_type", "status", "visibility", "owner_user_id"],
    }.items():
        for col in cols:
            op.create_index(f"ix_{table}_{col}", table, [col])

    op.add_column("tasks", sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_tasks_product_id", "tasks", ["product_id"])

    permissions_table = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)), sa.column("description", sa.String(500)))
    roles_table = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String(100)))
    role_permissions = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))
    bind = op.get_bind()
    existing_roles = bind.execute(sa.select(roles_table.c.id)).scalars().all()
    for code, description in PERMISSION_ROWS:
        permission_id = bind.execute(sa.select(permissions_table.c.id).where(permissions_table.c.code == code)).scalar()
        if permission_id is None:
            permission_id = bind.execute(permissions_table.insert().values(code=code, description=description).returning(permissions_table.c.id)).scalar()
        for role_id in existing_roles:
            already_granted = bind.execute(
                sa.select(role_permissions.c.permission_id).where(
                    role_permissions.c.role_id == role_id,
                    role_permissions.c.permission_id == permission_id,
                )
            ).scalar()
            if already_granted is None:
                bind.execute(role_permissions.insert().values(role_id=role_id, permission_id=permission_id))


def downgrade():
    for table, cols in {
        "product_documents": ["company_id", "product_id", "feature_id", "version_id", "document_type", "status", "visibility", "owner_user_id"],
        "product_releases": ["company_id", "product_id", "version_id", "status", "released_at"],
        "product_issues": ["company_id", "product_id", "feature_id", "requirement_id", "task_id", "severity", "priority", "status", "assigned_user_id"],
        "product_requirements": ["company_id", "product_id", "feature_id", "requirement_type", "priority", "status"],
        "product_features": ["company_id", "product_id", "roadmap_item_id", "status", "priority", "owner_user_id"],
        "product_roadmap_items": ["company_id", "product_id", "category", "status", "priority", "target_version_id", "target_date", "owner_user_id"],
        "product_versions": ["company_id", "product_id", "status", "target_release_at"],
        "products": ["company_id", "code", "name", "product_type", "lifecycle_status", "owner_user_id"],
    }.items():
        for col in cols:
            op.drop_index(f"ix_{table}_{col}", table_name=table)
    op.drop_index("ix_tasks_product_id", table_name="tasks")
    op.drop_column("tasks", "product_id")
    for table in ["product_documents", "product_releases", "product_issues", "product_requirements", "product_features", "product_roadmap_items", "product_versions", "products"]:
        op.drop_table(table)
    permission_codes = [row[0] for row in PERMISSION_ROWS]
    permissions_table = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String(150)))
    role_permissions = sa.table("role_permissions", sa.column("permission_id", sa.Uuid()))
    bind = op.get_bind()
    ids = [row[0] for row in bind.execute(sa.select(permissions_table.c.id).where(permissions_table.c.code.in_(permission_codes))).all()]
    if ids:
        bind.execute(role_permissions.delete().where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(permissions_table.delete().where(permissions_table.c.id.in_(ids)))
