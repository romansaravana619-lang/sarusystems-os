from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin, UUIDPrimaryKeyMixin


class Freelancer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancers"
    __table_args__ = (UniqueConstraint("company_id", "email", name="uq_freelancer_company_email"),)

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    freelancer_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    location: Mapped[str | None] = mapped_column(String(200))
    primary_role: Mapped[str | None] = mapped_column(String(150), index=True)
    department: Mapped[str | None] = mapped_column(String(100), index=True)
    experience_years: Mapped[float | None] = mapped_column(Numeric(5, 2))
    portfolio_url: Mapped[str | None] = mapped_column(String(1000))
    resume_url: Mapped[str | None] = mapped_column(String(1000))
    bio: Mapped[str | None] = mapped_column(Text)
    rate_type: Mapped[str] = mapped_column(String(30), nullable=False, default="project")
    rate_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="prospect", index=True)
    availability_status: Mapped[str] = mapped_column(String(30), nullable=False, default="available", index=True)
    source: Mapped[str | None] = mapped_column(String(100), index=True)
    notes: Mapped[str | None] = mapped_column(Text)


class FreelancerSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_skills"
    freelancer_id: Mapped[UUID] = mapped_column(ForeignKey("freelancers.id", ondelete="CASCADE"), nullable=False, index=True)
    skill: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    proficiency: Mapped[str] = mapped_column(String(30), nullable=False, default="intermediate")
    years: Mapped[float | None] = mapped_column(Numeric(5, 2))


class FreelancerApplication(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_applications"
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    freelancer_id: Mapped[UUID | None] = mapped_column(ForeignKey("freelancers.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    role_applied: Mapped[str | None] = mapped_column(String(150))
    source: Mapped[str | None] = mapped_column(String(100))
    portfolio_url: Mapped[str | None] = mapped_column(String(1000))
    resume_url: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="received", index=True)


class FreelancerEvaluation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_evaluations"
    application_id: Mapped[UUID] = mapped_column(ForeignKey("freelancer_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluator_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    technical_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    communication_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    reliability_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    portfolio_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    recommendation: Mapped[str] = mapped_column(String(30), nullable=False, default="review")
    notes: Mapped[str | None] = mapped_column(Text)


class FreelancerAgreement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_agreements"
    freelancer_id: Mapped[UUID] = mapped_column(ForeignKey("freelancers.id", ondelete="CASCADE"), nullable=False, index=True)
    agreement_type: Mapped[str] = mapped_column(String(80), nullable=False, default="project_based")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", index=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_url: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(Text)


class FreelancerAvailability(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_availability"
    freelancer_id: Mapped[UUID] = mapped_column(ForeignKey("freelancers.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="available")
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    weekly_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))
    notes: Mapped[str | None] = mapped_column(Text)


class FreelancerAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_assignments"
    freelancer_id: Mapped[UUID] = mapped_column(ForeignKey("freelancers.id"), nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(String(150))
    allocation_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="proposed", index=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class FreelancerPerformance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_performance"
    freelancer_id: Mapped[UUID] = mapped_column(ForeignKey("freelancers.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    period: Mapped[str] = mapped_column(String(30), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    timeliness_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    communication_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    notes: Mapped[str | None] = mapped_column(Text)
