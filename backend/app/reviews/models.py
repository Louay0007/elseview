"""Human review and minimal manual-money records; no transfer integration."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


class ReviewCase(Scoped, Base):
    __tablename__ = "review_cases"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("session_id"),
        ForeignKeyConstraint(
            ["workspace_id", "session_id"],
            ["collection_sessions.workspace_id", "collection_sessions.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "state IN ('pending','accepted','rejected','disputed','appealed','erased') AND generation >= 0"
        ),
    )
    session_id: Mapped[UUID]
    state: Mapped[str] = mapped_column(String(16), default="pending")
    generation: Mapped[int] = mapped_column(default=0)
    final_decision_id: Mapped[UUID | None]
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QualityFlag(Scoped, Base):
    __tablename__ = "quality_flags"
    __table_args__ = (
        UniqueConstraint("case_id", "policy", "block_key", "code"),
        ForeignKeyConstraint(
            ["workspace_id", "case_id"],
            ["review_cases.workspace_id", "review_cases.id"],
            ondelete="CASCADE",
        ),
    )
    case_id: Mapped[UUID]
    policy: Mapped[str] = mapped_column(String(80))
    block_key: Mapped[str] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(80))


class ReviewAssignment(Scoped, Base):
    __tablename__ = "review_assignments"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("case_id", "round"),
        UniqueConstraint("case_id", "reviewer_id"),
        ForeignKeyConstraint(
            ["workspace_id", "case_id"],
            ["review_cases.workspace_id", "review_cases.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("round > 0 AND kind IN ('independent','adjudication','appeal')"),
    )
    case_id: Mapped[UUID]
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    round: Mapped[int]
    kind: Mapped[str] = mapped_column(String(20))


class ReviewDecision(Scoped, Base):
    __tablename__ = "review_decisions"
    __table_args__ = (
        UniqueConstraint("assignment_id"),
        ForeignKeyConstraint(
            ["workspace_id", "assignment_id"],
            ["review_assignments.workspace_id", "review_assignments.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "verdict IN ('accepted','rejected') AND length(trim(rationale)) > 0 AND (verdict != 'rejected' OR jsonb_array_length(evidence) > 0)"
        ),
    )
    assignment_id: Mapped[UUID]
    verdict: Mapped[str] = mapped_column(String(16))
    rationale: Mapped[str] = mapped_column(String(2000))
    evidence: Mapped[list] = mapped_column(JSONB)
    command_key: Mapped[UUID]


class Appeal(Scoped, Base):
    __tablename__ = "appeals"
    __table_args__ = (
        UniqueConstraint("case_id"),
        ForeignKeyConstraint(
            ["workspace_id", "case_id"],
            ["review_cases.workspace_id", "review_cases.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("length(trim(reason)) > 0 AND state IN ('open','upheld','overturned')"),
    )
    case_id: Mapped[UUID]
    reason: Mapped[str] = mapped_column(String(2000))
    state: Mapped[str] = mapped_column(String(16), default="open")
    command_key: Mapped[UUID]


class FinancialRetentionPolicy(Scoped, Base):
    __tablename__ = "financial_retention_policies"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        CheckConstraint(
            "settled_days >= 0 AND settled_days <= 36500 AND length(trim(rationale)) > 0"
        ),
    )
    settled_days: Mapped[int]
    rationale: Mapped[str] = mapped_column(String(1000))
    reviewed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class RewardRecord(Scoped, Base):
    __tablename__ = "reward_records"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("workspace_id", "source_key"),
        ForeignKeyConstraint(
            ["workspace_id", "retention_policy_id"],
            ["financial_retention_policies.workspace_id", "financial_retention_policies.id"],
        ),
        CheckConstraint(
            "amount_millimes > 0 AND amount_millimes <= 1000000000000 AND currency = 'TND' AND state IN ('earned','paid')"
        ),
    )
    source_key: Mapped[str] = mapped_column(String(100))
    subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    amount_millimes: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    state: Mapped[str] = mapped_column(String(16), default="earned")
    retention_policy_id: Mapped[UUID]
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PayoutRecord(Scoped, Base):
    __tablename__ = "payout_records"
    __table_args__ = (
        Index(
            "uq_payout_live", "reward_id", unique=True, postgresql_where=text("state = 'recorded'")
        ),
        UniqueConstraint("workspace_id", "external_reference"),
        UniqueConstraint("workspace_id", "command_key"),
        ForeignKeyConstraint(
            ["workspace_id", "reward_id"], ["reward_records.workspace_id", "reward_records.id"]
        ),
        CheckConstraint("state IN ('recorded','failed','reversed') AND length(trim(evidence)) > 0"),
    )
    reward_id: Mapped[UUID]
    command_key: Mapped[UUID]
    external_reference: Mapped[str] = mapped_column(String(120))
    evidence: Mapped[str] = mapped_column(String(1000))
    state: Mapped[str] = mapped_column(String(16))
    transaction_id: Mapped[UUID | None] = mapped_column(ForeignKey("ledger_transactions.id"))


class LedgerAccount(Scoped, Base):
    __tablename__ = "ledger_accounts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("workspace_id", "code"),
        CheckConstraint(
            "currency = 'TND' AND code IN ('expense','payable','manual_cash','customer_receivable','billing_revenue','billing_tax')"
        ),
    )
    code: Mapped[str] = mapped_column(String(24))
    currency: Mapped[str] = mapped_column(String(3), default="TND")


class LedgerTransaction(Scoped, Base):
    __tablename__ = "ledger_transactions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("workspace_id", "command_key"),
        UniqueConstraint("reversal_of"),
        ForeignKeyConstraint(
            ["workspace_id", "reversal_of"],
            ["ledger_transactions.workspace_id", "ledger_transactions.id"],
        ),
        CheckConstraint("currency = 'TND'"),
    )
    command_key: Mapped[str] = mapped_column(String(160))
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    reversal_of: Mapped[UUID | None]


class LedgerEntry(Scoped, Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "transaction_id"],
            ["ledger_transactions.workspace_id", "ledger_transactions.id"],
        ),
        ForeignKeyConstraint(
            ["workspace_id", "account_id"], ["ledger_accounts.workspace_id", "ledger_accounts.id"]
        ),
        CheckConstraint(
            "amount_millimes != 0 AND amount_millimes BETWEEN -1000000000000 AND 1000000000000"
        ),
    )
    transaction_id: Mapped[UUID]
    account_id: Mapped[UUID]
    amount_millimes: Mapped[int] = mapped_column(BigInteger)
