from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin, UUIDPrimaryKeyMixin


class FreelancerTaskExecution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_task_executions"
    __table_args__ = (UniqueConstraint("task_id", name="uq_freelancer_task_execution_task"),)

    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("freelancer_assignments.id"), nullable=False, index=True)
    freelancer_id: Mapped[UUID] = mapped_column(ForeignKey("freelancers.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="assigned", index=True)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submission_url: Mapped[str | None] = mapped_column(String(1000))
    work_notes: Mapped[str | None] = mapped_column(Text)


class FreelancerProgressUpdate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_progress_updates"

    execution_id: Mapped[UUID] = mapped_column(ForeignKey("freelancer_task_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    update_text: Mapped[str] = mapped_column(Text, nullable=False)
    blocker: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)


class FreelancerWorkReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_work_reviews"

    execution_id: Mapped[UUID] = mapped_column(ForeignKey("freelancer_task_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FreelancerWorkLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freelancer_work_logs"

    execution_id: Mapped[UUID] = mapped_column(ForeignKey("freelancer_task_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    work_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hours: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
