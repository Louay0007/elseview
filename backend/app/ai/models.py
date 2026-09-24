from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


class AIRun(Scoped, Base):
    __tablename__ = "ai_runs"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued','running','draft','approved','failed','uncertain','invalidated')",
            name="ck_ai_run_state",
        ),
        UniqueConstraint("workspace_id", "requester_id", "command_key", name="uq_ai_command"),
    )
    study_id: Mapped[UUID | None] = mapped_column(ForeignKey("studies.id", ondelete="SET NULL"))
    snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("analysis_snapshots.id", ondelete="SET NULL")
    )
    requester_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("jobs.id"))
    command_key: Mapped[str] = mapped_column(String(100))
    request_hash: Mapped[str] = mapped_column(String(64))
    cache_key: Mapped[str] = mapped_column(String(64), index=True)
    operation: Mapped[str] = mapped_column(String(32))
    instruction: Mapped[str] = mapped_column(String(2000))
    privacy_epoch: Mapped[int]
    state: Mapped[str] = mapped_column(String(24), default="queued")
    config: Mapped[dict] = mapped_column(JSONB)
    coverage: Mapped[dict] = mapped_column(JSONB, default=dict)
    output: Mapped[dict | None] = mapped_column(JSONB)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIAttempt(Scoped, Base):
    __tablename__ = "ai_attempts"
    __table_args__ = (
        CheckConstraint(
            "state IN ('reserved','sent','uncertain','settled','released')",
            name="ck_ai_attempt_state",
        ),
        UniqueConstraint("run_id", name="uq_ai_attempt_run"),
        CheckConstraint(
            "reserved_cost >= 0 AND (actual_cost IS NULL OR actual_cost >= 0)", name="ck_ai_cost"
        ),
    )
    run_id: Mapped[UUID] = mapped_column(ForeignKey("ai_runs.id"))
    state: Mapped[str] = mapped_column(String(24), default="reserved")
    reserved_cost: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    budget_day: Mapped[str] = mapped_column(String(10))
    request_id: Mapped[str | None] = mapped_column(String(200))
    usage: Mapped[dict | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(64))
    reconciliation: Mapped[str | None] = mapped_column(String(100))


class AIEvidence(Scoped, Base):
    __tablename__ = "ai_evidence"
    run_id: Mapped[UUID] = mapped_column(ForeignKey("ai_runs.id"))
    source_id: Mapped[str] = mapped_column(String(100))
    start: Mapped[int]
    end: Mapped[int]
    quote_hash: Mapped[str] = mapped_column(String(64))


class UsageBudget(Scoped, Base):
    __tablename__ = "usage_budgets"
    __table_args__ = (
        UniqueConstraint("workspace_id", "scope", "currency", name="uq_ai_budget"),
        CheckConstraint("reserved >= 0 AND spent >= 0", name="ck_ai_budget_nonnegative"),
    )
    scope: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(3))
    reserved: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=Decimal(0))
    spent: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=Decimal(0))
