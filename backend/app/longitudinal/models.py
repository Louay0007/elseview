"""Version-bound interview, diary and private transcript records."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


class ScheduleSlot(Scoped, Base):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        ForeignKeyConstraint(
            ["workspace_id", "version_id"], ["study_versions.workspace_id", "study_versions.id"]
        ),
        CheckConstraint("ends_at > starts_at AND capacity BETWEEN 1 AND 100"),
    )
    version_id: Mapped[UUID]
    host_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64))
    capacity: Mapped[int]
    join_url: Mapped[str] = mapped_column(Text)


class Booking(Scoped, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("subject_id", "request_key"),
        ForeignKeyConstraint(
            ["workspace_id", "slot_id"], ["schedule_slots.workspace_id", "schedule_slots.id"]
        ),
        CheckConstraint("state IN ('booked','cancelled')"),
        CheckConstraint("attendance IN ('unknown','attended','absent')"),
        ForeignKeyConstraint(
            ["workspace_id", "attendance_actor_id"],
            ["memberships.workspace_id", "memberships.user_id"],
        ),
        CheckConstraint(
            "(attendance = 'unknown' AND attendance_actor_id IS NULL AND attendance_at IS NULL) OR (attendance <> 'unknown' AND attendance_actor_id IS NOT NULL AND attendance_at IS NOT NULL AND attendance_note IS NOT NULL)",
            name="ck_booking_attendance_attribution",
        ),
    )
    slot_id: Mapped[UUID]
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    request_key: Mapped[UUID]
    state: Mapped[str] = mapped_column(String(16), default="booked")
    revision: Mapped[int] = mapped_column(default=0)
    attendance: Mapped[str] = mapped_column(String(16), default="unknown")
    attendance_note: Mapped[str | None] = mapped_column(Text)
    attendance_actor_id: Mapped[UUID | None]
    attendance_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DiaryOccurrence(Scoped, Base):
    __tablename__ = "diary_occurrences"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("base_session_id", "ordinal"),
        ForeignKeyConstraint(
            ["workspace_id", "base_session_id"],
            ["collection_sessions.workspace_id", "collection_sessions.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("ordinal >= 0 AND opens_at < due_at AND due_at <= grace_at"),
    )
    base_session_id: Mapped[UUID]
    ordinal: Mapped[int]
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    grace_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64))


class Notification(Scoped, Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("booking_id", "booking_revision"),)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"))
    booking_revision: Mapped[int]
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("jobs.id"))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Recording(Scoped, Base):
    __tablename__ = "recordings"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("asset_id"),
        ForeignKeyConstraint(["workspace_id", "asset_id"], ["assets.workspace_id", "assets.id"]),
        ForeignKeyConstraint(
            ["workspace_id", "version_id"], ["study_versions.workspace_id", "study_versions.id"]
        ),
    )
    asset_id: Mapped[UUID]
    version_id: Mapped[UUID]
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    consent_receipt_id: Mapped[UUID] = mapped_column(ForeignKey("consent_receipts.id"))
    duration_ms: Mapped[int]
    transcript_hash: Mapped[str | None] = mapped_column(String(64))
    revoked: Mapped[bool] = mapped_column(default=False)


class TranscriptSegment(Scoped, Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        UniqueConstraint("recording_id", "ordinal"),
        ForeignKeyConstraint(
            ["workspace_id", "recording_id"], ["recordings.workspace_id", "recordings.id"]
        ),
        CheckConstraint("start_ms >= 0 AND end_ms > start_ms AND ordinal >= 0"),
    )
    recording_id: Mapped[UUID]
    ordinal: Mapped[int]
    start_ms: Mapped[int]
    end_ms: Mapped[int]
    speaker: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
