"""Operational decisions, not a claim of regulatory compliance."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


class LegalHold(Scoped, Base):
    __tablename__ = "privacy_legal_holds"
    __table_args__ = (CheckConstraint("length(reason) BETWEEN 1 AND 2000", name="ck_hold_reason"),)
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), default="erasure")
    reason: Mapped[str] = mapped_column(Text)
    reviewed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    review_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewedRetention(Scoped, Base):
    __tablename__ = "privacy_reviewed_retention"
    __table_args__ = (
        UniqueConstraint("workspace_id", "purpose", "version"),
        CheckConstraint(
            "days BETWEEN 1 AND 3650 AND version > 0", name="ck_reviewed_retention_days"
        ),
    )
    purpose: Mapped[str] = mapped_column(String(32))
    version: Mapped[int]
    days: Mapped[int]
    reason: Mapped[str] = mapped_column(Text)
    reviewed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    review_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Tombstone(Scoped, Base):
    __tablename__ = "privacy_tombstones"
    __table_args__ = (
        UniqueConstraint("workspace_id", "subject_id", "purpose"),
        CheckConstraint("purpose IN ('erasure','restriction')", name="ck_tombstone_purpose"),
    )
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(32))


class RestoreEvent(Scoped, Base):
    """Durable identifiers only; no FK to the deliberately deleted resource."""

    __tablename__ = "privacy_restore_events"
    __table_args__ = (
        UniqueConstraint("workspace_id", "action", "resource_id"),
        CheckConstraint(
            "action IN ('session_withdraw','session_delete','asset_delete','ai_delete','snapshot_delete','export_delete','share_revoke','consent_revoke','dataset_delete','study_delete','recording_delete','contact_delete','candidate_delete','comment_delete','idempotency_scrub','audit_scrub')",
            name="ck_restore_event_action",
        ),
    )
    action: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[UUID]
