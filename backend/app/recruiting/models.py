"""Purpose-separated recruitment data; private contacts never reference global identities."""

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


class LanguageAssessmentVersion(Global, Base):
    __tablename__ = "language_assessment_versions"
    assessment_key: Mapped[str] = mapped_column(String(64))
    version: Mapped[int]
    language: Mapped[str] = mapped_column(String(24))
    schema_version: Mapped[int] = mapped_column(default=1)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    synthetic: Mapped[bool]
    state: Mapped[str] = mapped_column(String(16), default="draft")
    public_json: Mapped[dict] = mapped_column(JSONB)
    policy_json: Mapped[dict] = mapped_column(JSONB)
    public_digest: Mapped[str] = mapped_column(String(64))
    content_digest: Mapped[str] = mapped_column(String(64))
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_reference: Mapped[str | None] = mapped_column(String(128))
    __table_args__ = (
        UniqueConstraint("assessment_key", "version"),
        UniqueConstraint("id", "language"),
        CheckConstraint(
            "language IN ('tunisianArabic','formalArabic','french','arabizi')",
            name="ck_language_version_language",
        ),
        CheckConstraint(
            "state IN ('draft','approved','retired') AND schema_version = 1 AND version > 0",
            name="ck_language_version_state",
        ),
        CheckConstraint(
            "state = 'draft' OR (approved_by IS NOT NULL AND approved_by <> author_id AND approved_at IS NOT NULL AND review_reference IS NOT NULL)",
            name="ck_language_version_approval",
        ),
    )


class LanguageAssessmentKey(Base):
    __tablename__ = "language_assessment_keys"
    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("language_assessment_versions.id"), primary_key=True
    )
    material_json: Mapped[dict] = mapped_column(JSONB)


class LanguageAssessmentConsent(Global, Base):
    __tablename__ = "language_assessment_consents"
    profile_id: Mapped[UUID] = mapped_column(ForeignKey("participant_profiles.id"))
    decision: Mapped[str] = mapped_column(String(16))
    document_version: Mapped[str] = mapped_column(String(16))
    document_digest: Mapped[str] = mapped_column(String(64))
    receipt_key: Mapped[str] = mapped_column(String(128))
    request_digest: Mapped[str] = mapped_column(String(64))
    grant_id: Mapped[UUID | None]
    __table_args__ = (
        UniqueConstraint("profile_id", "receipt_key"),
        UniqueConstraint("profile_id", "id"),
        ForeignKeyConstraint(
            ["profile_id", "grant_id"],
            ["language_assessment_consents.profile_id", "language_assessment_consents.id"],
        ),
        CheckConstraint(
            "(decision = 'granted' AND grant_id IS NULL) OR (decision = 'withdrawn' AND grant_id IS NOT NULL)",
            name="ck_language_consent_scope",
        ),
    )


class LanguageAssessmentAttempt(Global, Base):
    __tablename__ = "language_assessment_attempts"
    profile_id: Mapped[UUID] = mapped_column(ForeignKey("participant_profiles.id"))
    version_id: Mapped[UUID]
    language: Mapped[str] = mapped_column(String(24))
    consent_grant_id: Mapped[UUID]
    sequence: Mapped[int]
    command_key: Mapped[str] = mapped_column(String(128))
    start_digest: Mapped[str] = mapped_column(String(64))
    submit_key: Mapped[str | None] = mapped_column(String(128))
    submission_digest: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), default="started")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responses_json: Mapped[dict | None] = mapped_column(JSONB)
    appeal_key: Mapped[str | None] = mapped_column(String(128))
    appeal_digest: Mapped[str | None] = mapped_column(String(64))
    appeal_reason: Mapped[str | None] = mapped_column(String(2000))
    appeal_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("profile_id", "command_key"),
        Index(
            "uq_language_active_attempt",
            "profile_id",
            "language",
            unique=True,
            postgresql_where=text("state IN ('started','submitted')"),
        ),
        Index("ix_language_attempt_retention", "retention_until"),
        Index("ix_language_attempt_queue", "state", "language", "submitted_at"),
        UniqueConstraint("profile_id", "language", "sequence"),
        ForeignKeyConstraint(
            ["version_id", "language"],
            ["language_assessment_versions.id", "language_assessment_versions.language"],
        ),
        ForeignKeyConstraint(
            ["profile_id", "consent_grant_id"],
            ["language_assessment_consents.profile_id", "language_assessment_consents.id"],
        ),
        CheckConstraint(
            "state IN ('started','submitted','adjudicated','abandoned','withdrawn') AND sequence > 0",
            name="ck_language_attempt_state",
        ),
    )


class LanguageAssessmentDecision(Global, Base):
    __tablename__ = "language_assessment_decisions"
    attempt_id: Mapped[UUID] = mapped_column(ForeignKey("language_assessment_attempts.id"))
    round: Mapped[int]
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    command_key: Mapped[str] = mapped_column(String(128))
    request_digest: Mapped[str] = mapped_column(String(64))
    verdict: Mapped[str] = mapped_column(String(24))
    findings_json: Mapped[dict | None] = mapped_column(JSONB)
    rationale: Mapped[str | None] = mapped_column(String(2000))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    previous_decision_id: Mapped[UUID | None]
    __table_args__ = (
        UniqueConstraint("attempt_id", "round"),
        UniqueConstraint("attempt_id", "command_key"),
        UniqueConstraint("attempt_id", "id"),
        ForeignKeyConstraint(
            ["attempt_id", "previous_decision_id"],
            ["language_assessment_decisions.attempt_id", "language_assessment_decisions.id"],
        ),
        CheckConstraint(
            "(round = 1 AND previous_decision_id IS NULL) OR (round = 2 AND previous_decision_id IS NOT NULL)",
            name="ck_language_decision_round",
        ),
        CheckConstraint(
            "(verdict = 'qualified' AND expires_at IS NOT NULL) OR (verdict IN ('not_qualified','inconclusive') AND expires_at IS NULL)",
            name="ck_language_decision_verdict",
        ),
    )


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
    """JSON attributes/provenance are copied at invitation time, never refreshed from source."""

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
    issued_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    candidate_id: Mapped[UUID]
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
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
