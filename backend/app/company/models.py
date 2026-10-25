from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin, UUIDPrimaryKeyMixin


class CompanyProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "company_profiles"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(250))
    tagline: Mapped[str | None] = mapped_column(String(500))
    website: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(150))
    business_model: Mapped[str | None] = mapped_column(Text)
    vision: Mapped[str | None] = mapped_column(Text)
    mission: Mapped[str | None] = mapped_column(Text)
    brand_primary_color: Mapped[str | None] = mapped_column(String(30))
    brand_secondary_color: Mapped[str | None] = mapped_column(String(30))
    logo_url: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Department(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "departments"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Goal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "company_goals"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", index=True)
    priority: Mapped[str] = mapped_column(String(30), nullable=False, default="medium")
    target_date: Mapped[str | None] = mapped_column(String(30))
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CompanyPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "company_policies"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    policy_type: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OperatingRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "operating_rules"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rule_type: Mapped[str] = mapped_column(String(100), nullable=False, default="operating")
    condition: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
