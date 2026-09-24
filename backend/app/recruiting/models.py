"""Purpose-separated recruitment data; private contacts never reference global identities."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


class Global:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ParticipantProfile(Global, Base):
    __tablename__ = "participant_profiles"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    attributes_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    __table_args__ = (
        CheckConstraint("status IN ('active','paused','withdrawn')", name="ck_profile_status"),
    )


class PanelConsent(Global, Base):
    __tablename__ = "panel_consents"
    profile_id: Mapped[UUID] = mapped_column(ForeignKey("participant_profiles.id"))
    decision: Mapped[str] = mapped_column(String(16))
    document_version: Mapped[str] = mapped_column(String(64))
    document_digest: Mapped[str] = mapped_column(String(64))
    request_digest: Mapped[str] = mapped_column(String(64))
    receipt_key: Mapped[str] = mapped_column(String(128))
    __table_args__ = (
        UniqueConstraint("profile_id", "receipt_key"),
        CheckConstraint(
            "decision IN ('granted','withdrawn') AND char_length(document_digest)=64",
            name="ck_panel_consent",
        ),
    )


class Qualification(Global, Base):
    __tablename__ = "qualifications"
    profile_id: Mapped[UUID] = mapped_column(ForeignKey("participant_profiles.id"))
    language: Mapped[str] = mapped_column(String(35))
    assessment_version: Mapped[str] = mapped_column(String(64))
    passed: Mapped[bool]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("profile_id", "language", "assessment_version"),)


class PrivateContact(Scoped, Base):
    __tablename__ = "private_contacts"
    contact_lookup_hash: Mapped[str] = mapped_column(String(64))
    attributes_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    source: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="active")
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("workspace_id", "contact_lookup_hash"),
        CheckConstraint("status IN ('active','suppressed','withdrawn')", name="ck_private_status"),
    )


class PrivateContactConsent(Scoped, Base):
    __tablename__ = "private_contact_consents"
    contact_id: Mapped[UUID]
    document_id: Mapped[UUID]
    decision: Mapped[str] = mapped_column(String(16))
    receipt_key: Mapped[str] = mapped_column(String(128))
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "contact_id"], ["private_contacts.workspace_id", "private_contacts.id"]
        ),
        ForeignKeyConstraint(
            ["workspace_id", "document_id"],
            ["consent_documents.workspace_id", "consent_documents.id"],
        ),
        UniqueConstraint("workspace_id", "contact_id", "receipt_key"),
        CheckConstraint("decision IN ('granted','withdrawn')", name="ck_private_consent"),
    )


class RecruitmentConfig(Scoped, Base):
    __tablename__ = "recruitment_configs"
    launch_id: Mapped[UUID]
    capacity: Mapped[int]
    budget_millimes: Mapped[int]
    reward_millimes: Mapped[int]
    hold_seconds: Mapped[int] = mapped_column(default=1800)
    filters_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    screener_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    screening_policy: Mapped[str] = mapped_column(String(32), default="uncompensated_disclosed")
    __table_args__ = (
        UniqueConstraint("workspace_id", "launch_id"),
        ForeignKeyConstraint(
            ["workspace_id", "launch_id"], ["launches.workspace_id", "launches.id"]
        ),
        CheckConstraint(
            "capacity > 0 AND budget_millimes >= 0 AND reward_millimes >= 0 AND hold_seconds BETWEEN 60 AND 86400",
            name="ck_recruitment_limits",
        ),
        CheckConstraint("screening_policy = 'uncompensated_disclosed'", name="ck_screen_policy"),
    )


class Candidate(Scoped, Base):
    __tablename__ = "candidates"
    launch_id: Mapped[UUID]
    subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    source_kind: Mapped[str] = mapped_column(String(16))
    source_id: Mapped[UUID | None]
    attributes_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="invited")
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        UniqueConstraint("workspace_id", "launch_id", "id"),
        UniqueConstraint("workspace_id", "launch_id", "subject_id"),
        UniqueConstraint("workspace_id", "launch_id", "source_kind", "source_id"),
        ForeignKeyConstraint(
            ["workspace_id", "launch_id"], ["launches.workspace_id", "launches.id"]
        ),
        CheckConstraint(
            "source_kind IN ('public','private') AND status IN ('invited','eligible','screened_out','withdrawn')",
            name="ck_candidate_state",
        ),
    )


class Invitation(Scoped, Base):
    __tablename__ = "invitations"
    candidate_id: Mapped[UUID]
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "candidate_id"], ["candidates.workspace_id", "candidates.id"]
        ),
    )


class QuotaCell(Scoped, Base):
    __tablename__ = "quota_cells"
    launch_id: Mapped[UUID]
    capacity: Mapped[int]
    filters_json: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (
        UniqueConstraint("workspace_id", "launch_id", "id"),
        ForeignKeyConstraint(
            ["workspace_id", "launch_id"], ["launches.workspace_id", "launches.id"]
        ),
        CheckConstraint("capacity > 0", name="ck_quota_capacity"),
    )


class Reservation(Scoped, Base):
    __tablename__ = "reservations"
    launch_id: Mapped[UUID]
    candidate_id: Mapped[UUID]
    state: Mapped[str] = mapped_column(String(16), default="held")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reward_millimes: Mapped[int]
    __table_args__ = (
        UniqueConstraint("workspace_id", "launch_id", "id"),
        UniqueConstraint("workspace_id", "candidate_id"),
        ForeignKeyConstraint(
            ["workspace_id", "launch_id", "candidate_id"],
            ["candidates.workspace_id", "candidates.launch_id", "candidates.id"],
        ),
        CheckConstraint(
            "state IN ('held','consumed','released','expired') AND reward_millimes >= 0",
            name="ck_reservation_state",
        ),
    )


class ReservationCell(Scoped, Base):
    __tablename__ = "reservation_cells"
    launch_id: Mapped[UUID]
    reservation_id: Mapped[UUID]
    cell_id: Mapped[UUID]
    __table_args__ = (
        UniqueConstraint("reservation_id", "cell_id"),
        ForeignKeyConstraint(
            ["workspace_id", "launch_id", "reservation_id"],
            ["reservations.workspace_id", "reservations.launch_id", "reservations.id"],
        ),
        ForeignKeyConstraint(
            ["workspace_id", "launch_id", "cell_id"],
            ["quota_cells.workspace_id", "quota_cells.launch_id", "quota_cells.id"],
        ),
    )


class ScreenerResult(Scoped, Base):
    __tablename__ = "screener_results"
    candidate_id: Mapped[UUID]
    request_digest: Mapped[str] = mapped_column(String(64))
    rules_digest: Mapped[str] = mapped_column(String(64))
    eligible: Mapped[bool]
    __table_args__ = (
        UniqueConstraint("workspace_id", "candidate_id"),
        ForeignKeyConstraint(
            ["workspace_id", "candidate_id"], ["candidates.workspace_id", "candidates.id"]
        ),
    )
