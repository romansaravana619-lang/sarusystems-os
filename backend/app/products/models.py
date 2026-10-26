from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin, UUIDPrimaryKeyMixin


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "products"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    product_type: Mapped[str] = mapped_column(String(40), nullable=False, default="internal", index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(40), nullable=False, default="discovery", index=True)
    current_version: Mapped[str | None] = mapped_column(String(80))
    repository_url: Mapped[str | None] = mapped_column(Text)
    documentation_url: Mapped[str | None] = mapped_column(Text)
    demo_url: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_products_company_code"),
        UniqueConstraint("company_id", "name", name="uq_products_company_name"),
    )


class ProductRoadmapItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_roadmap_items"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="feature", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="backlog", index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    target_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("product_versions.id", ondelete="SET NULL"), index=True)
    target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)


class ProductFeature(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_features"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    roadmap_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("product_roadmap_items.id", ondelete="SET NULL"), index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="proposed", index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("product_id", "code", name="uq_product_features_product_code"),
    )


class ProductRequirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_requirements"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_id: Mapped[UUID | None] = mapped_column(ForeignKey("product_features.id", ondelete="SET NULL"), index=True)
    requirement_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    requirement_type: Mapped[str] = mapped_column(String(40), nullable=False, default="functional", index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft", index=True)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("product_id", "requirement_key", name="uq_product_requirements_key"),
    )


class ProductIssue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_issues"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_id: Mapped[UUID | None] = mapped_column(ForeignKey("product_features.id", ondelete="SET NULL"), index=True)
    requirement_id: Mapped[UUID | None] = mapped_column(ForeignKey("product_requirements.id", ondelete="SET NULL"), index=True)
    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), index=True)
    issue_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    expected_result: Mapped[str | None] = mapped_column(Text)
    actual_result: Mapped[str | None] = mapped_column(Text)
    reproduction_steps: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open", index=True)
    assigned_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    fix_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retest_result: Mapped[str | None] = mapped_column(String(40))
    founder_notes: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("product_id", "issue_key", name="uq_product_issues_key"),
    )


class ProductVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_versions"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="planned", index=True)
    target_release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    changelog: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("product_id", "version", name="uq_product_versions_version"),
    )


class ProductRelease(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_releases"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("product_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    release_key: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="planned", index=True)
    release_notes: Mapped[str | None] = mapped_column(Text)
    deployment_url: Mapped[str | None] = mapped_column(Text)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("product_id", "release_key", name="uq_product_releases_key"),
    )


class ProductDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_documents"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_id: Mapped[UUID | None] = mapped_column(ForeignKey("product_features.id", ondelete="SET NULL"), index=True)
    version_id: Mapped[UUID | None] = mapped_column(ForeignKey("product_versions.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, default="technical", index=True)
    document_url: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft", index=True)
    visibility: Mapped[str] = mapped_column(String(30), nullable=False, default="internal", index=True)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
