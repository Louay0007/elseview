"""Participant data, deliberately independent of workspace memberships."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


class CollectionSession(Scoped, Base):
    __tablename__ = "collection_sessions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_collection_session_scope"),
        Index(
            "uq_collection_candidate_base",
            "candidate_id",
            unique=True,
            postgresql_where=text("diary_occurrence_id IS NULL"),
        ),
        Index(
            "uq_collection_diary_occurrence",
            "diary_occurrence_id",
            unique=True,
            postgresql_where=text("diary_occurrence_id IS NOT NULL"),
        ),
        UniqueConstraint("capability_hash", name="uq_collection_capability"),
        ForeignKeyConstraint(
            ["workspace_id", "version_id"], ["study_versions.workspace_id", "study_versions.id"]
        ),
        ForeignKeyConstraint(
            ["workspace_id", "launch_id", "candidate_id"],
            ["candidates.workspace_id", "candidates.launch_id", "candidates.id"],
        ),
        ForeignKeyConstraint(
            ["workspace_id", "launch_id"], ["launches.workspace_id", "launches.id"]
        ),
        CheckConstraint(
            "state IN ('active','submitted','withdrawn','erased')", name="ck_collection_state"
        ),
        CheckConstraint("revision >= 0 AND last_sequence >= -1", name="ck_collection_revision"),
    )
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("candidates.id"))
    diary_occurrence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "diary_occurrences.id",
            ondelete="CASCADE",
            use_alter=True,
            name="fk_collection_diary_occurrence",
        )
    )
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    version_id: Mapped[UUID]
    launch_id: Mapped[UUID] = mapped_column(ForeignKey("launches.id"))
    consent_receipt_id: Mapped[UUID | None] = mapped_column(ForeignKey("consent_receipts.id"))
    capability_hash: Mapped[str] = mapped_column(String(64))
    start_hash: Mapped[str] = mapped_column(String(64))
    locale: Mapped[str] = mapped_column(String(35))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(16), default="active")
    revision: Mapped[int] = mapped_column(default=0)
    last_sequence: Mapped[int] = mapped_column(default=-1)
    assignments: Mapped[dict] = mapped_column(JSONB, default=dict)
    submitted_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality_job_id: Mapped[UUID | None] = mapped_column(ForeignKey("jobs.id"))
    quality_summary: Mapped[dict | None] = mapped_column(JSONB)


class Answer(Base):
    __tablename__ = "collection_answers"
    __table_args__ = (
        UniqueConstraint("session_id", "id", name="uq_answer_session_id"),
        UniqueConstraint("session_id", "block_key", "occurrence", name="uq_collection_answer"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("collection_sessions.id"), index=True)
    block_key: Mapped[str] = mapped_column(String(64))
    occurrence: Mapped[int] = mapped_column(default=0)
    current_revision: Mapped[int] = mapped_column(default=0)
    final_revision: Mapped[int | None]
    active: Mapped[bool] = mapped_column(default=True)


class AnswerRevision(Base):
    __tablename__ = "answer_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "answer_id"],
            ["collection_answers.session_id", "collection_answers.id"],
            name="fk_revision_answer_session",
        ),
        UniqueConstraint("answer_id", "revision", name="uq_answer_revision"),
        UniqueConstraint("session_id", "client_event_id", name="uq_answer_client_event"),
        CheckConstraint("revision > 0", name="ck_answer_revision"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("collection_sessions.id"))
    answer_id: Mapped[UUID] = mapped_column(ForeignKey("collection_answers.id"))
    revision: Mapped[int]
    client_event_id: Mapped[UUID]
    request_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16))
    value: Mapped[dict | None] = mapped_column(JSONB)
    reason_code: Mapped[str | None] = mapped_column(String(24))
    receipt: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResponseEvent(Base):
    __tablename__ = "response_events"
    __table_args__ = (
        Index(
            "uq_first_click_per_block",
            "session_id",
            "block_key",
            unique=True,
            postgresql_where=text("kind = 'first_click.recorded'"),
        ),
        UniqueConstraint("session_id", "client_event_id", name="uq_response_client_event"),
        UniqueConstraint("session_id", "sequence", name="uq_response_sequence"),
        CheckConstraint(
            "provenance IN ('client_observed','server_created')", name="ck_event_provenance"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("collection_sessions.id"), index=True)
    block_key: Mapped[str | None] = mapped_column(String(64))
    client_event_id: Mapped[UUID | None]
    sequence: Mapped[int | None]
    kind: Mapped[str] = mapped_column(String(64))
    provenance: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InteractionAttempt(Base):
    __tablename__ = "interaction_attempts"
    __table_args__ = (UniqueConstraint("session_id", "block_key", name="uq_interaction_attempt"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("collection_sessions.id"))
    block_key: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(24), default="started")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    visible_ms: Mapped[int | None]
