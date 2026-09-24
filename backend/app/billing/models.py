"""Minimal commercial records. Source IDs are opaque; never answer/contact data."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


def scope():
    return UniqueConstraint("workspace_id", "id")


def fk(column, table):
    return ForeignKeyConstraint(["workspace_id", column], [f"{table}.workspace_id", f"{table}.id"])


class PlanVersion(Scoped, Base):
    __tablename__ = "billing_plan_versions"
    __table_args__ = (
        scope(),
        UniqueConstraint("workspace_id", "key", "version"),
        CheckConstraint("version > 0"),
    )
    key: Mapped[str] = mapped_column(String(80))
    version: Mapped[int]
    snapshot: Mapped[dict] = mapped_column(JSONB)
    reviewed_by: Mapped[UUID]


class Subscription(Scoped, Base):
    __tablename__ = "billing_subscriptions"
    __table_args__ = (
        scope(),
        fk("plan_id", "billing_plan_versions"),
        CheckConstraint("ends_at > starts_at"),
    )
    plan_id: Mapped[UUID]
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Grant(Scoped, Base):
    __tablename__ = "billing_grants"
    __table_args__ = (
        scope(),
        fk("subscription_id", "billing_subscriptions"),
        UniqueConstraint("workspace_id", "source_id"),
        CheckConstraint(
            "kind IN ('publication','response','ai_addon','specialist') AND units > 0 AND units <= 1000000"
        ),
    )
    subscription_id: Mapped[UUID]
    source_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(24))
    units: Mapped[int]


class Usage(Scoped, Base):
    __tablename__ = "billing_usage"
    __table_args__ = (
        scope(),
        fk("subscription_id", "billing_subscriptions"),
        UniqueConstraint("workspace_id", "kind", "source_id"),
        CheckConstraint(
            "kind IN ('publication','response','ai_addon','specialist') AND state IN ('reserved','consumed','released')"
        ),
        CheckConstraint("net >= 0 AND tax >= 0 AND net + tax <= 1000000000000"),
    )
    subscription_id: Mapped[UUID]
    source_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(24))
    state: Mapped[str] = mapped_column(String(16))
    included_allocation: Mapped[bool] = mapped_column(nullable=False)
    net: Mapped[int] = mapped_column(BigInteger)
    tax: Mapped[int] = mapped_column(BigInteger)


class Invoice(Scoped, Base):
    __tablename__ = "billing_invoices"
    __table_args__ = (
        scope(),
        UniqueConstraint("workspace_id", "command_id"),
        UniqueConstraint("transaction_id"),
        fk("subscription_id", "billing_subscriptions"),
        fk("transaction_id", "ledger_transactions"),
        fk("credit_of", "billing_invoices"),
        UniqueConstraint("credit_of"),
        CheckConstraint("net >= 0 AND tax >= 0 AND net + tax > 0 AND net + tax <= 1000000000000"),
    )
    subscription_id: Mapped[UUID]
    command_id: Mapped[UUID]
    credit_of: Mapped[UUID | None]
    transaction_id: Mapped[UUID]
    snapshot: Mapped[dict] = mapped_column(JSONB)
    net: Mapped[int] = mapped_column(BigInteger)
    tax: Mapped[int] = mapped_column(BigInteger)


class InvoiceLine(Scoped, Base):
    __tablename__ = "billing_invoice_lines"
    __table_args__ = (
        fk("invoice_id", "billing_invoices"),
        fk("usage_id", "billing_usage"),
        UniqueConstraint("usage_id"),
    )
    invoice_id: Mapped[UUID]
    usage_id: Mapped[UUID]


class CustomerPayment(Scoped, Base):
    __tablename__ = "billing_customer_payments"
    __table_args__ = (
        scope(),
        fk("invoice_id", "billing_invoices"),
        fk("transaction_id", "ledger_transactions"),
        fk("reversal_of", "billing_customer_payments"),
        UniqueConstraint("reversal_of"),
        UniqueConstraint("workspace_id", "command_id"),
        UniqueConstraint("transaction_id"),
        UniqueConstraint("workspace_id", "reference"),
        CheckConstraint("amount > 0 AND amount <= 1000000000000"),
    )
    invoice_id: Mapped[UUID]
    transaction_id: Mapped[UUID]
    command_id: Mapped[UUID]
    reversal_of: Mapped[UUID | None]
    reference: Mapped[str] = mapped_column(String(120))
    evidence_digest: Mapped[str] = mapped_column(String(64))
    amount: Mapped[int] = mapped_column(BigInteger)
