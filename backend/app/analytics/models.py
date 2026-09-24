"""Immutable analysis facts; mutable lifecycle pointers contain no participant payload."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


def scope(name):
    return UniqueConstraint("workspace_id", "id", name="uq_" + name + "_scope")


def fk(column, table):
    return ForeignKeyConstraint(["workspace_id", column], [table + ".workspace_id", table + ".id"])


class AnalysisSnapshot(Scoped, Base):
    __tablename__ = "analysis_snapshots"
    __table_args__ = (
        scope("analysis"),
        fk("study_id", "studies"),
        fk("version_id", "study_versions"),
        CheckConstraint("state IN ('building','ready','invalidated')"),
        CheckConstraint("source_count BETWEEN 0 AND 1000"),
        CheckConstraint("consent_epoch >= 0"),
        CheckConstraint(
            "char_length(definition_digest)=64 AND char_length(manifest_digest)=64 AND jsonb_typeof(metrics)='object'"
        ),
    )
    study_id: Mapped[UUID]
    version_id: Mapped[UUID]
    state: Mapped[str] = mapped_column(String(16), default="building")
    source_count: Mapped[int]
    consent_epoch: Mapped[int]
    definition_digest: Mapped[str] = mapped_column(String(64))
    manifest_digest: Mapped[str] = mapped_column(String(64))
    metrics: Mapped[dict] = mapped_column(JSONB)


class SnapshotSource(Scoped, Base):
    __tablename__ = "snapshot_sources"
    __table_args__ = (
        scope("source"),
        fk("snapshot_id", "analysis_snapshots"),
        UniqueConstraint("snapshot_id", "session_id"),
        CheckConstraint(
            "exclusion_reason IN ('included','not_submitted','not_accepted','consent')"
        ),
        CheckConstraint("char_length(digest) = 64 AND consent_epoch >= 0"),
        CheckConstraint(
            "jsonb_typeof(revisions)='object' AND (exclusion_reason <> 'included' OR (decision IS NOT NULL AND jsonb_typeof(decision)='object' AND consent_receipt_id IS NOT NULL))"
        ),
    )
    snapshot_id: Mapped[UUID]
    session_id: Mapped[UUID]  # intentionally detached on privacy purge before collection rows
    consent_receipt_id: Mapped[UUID | None]
    consent_epoch: Mapped[int]
    decision: Mapped[dict | None] = mapped_column(JSONB)
    revisions: Mapped[dict] = mapped_column(JSONB)
    digest: Mapped[str] = mapped_column(String(64))
    exclusion_reason: Mapped[str] = mapped_column(String(24))


class Report(Scoped, Base):
    __tablename__ = "reports"
    __table_args__ = (scope("report"), fk("study_id", "studies"), CheckConstraint("revision > 0"))
    study_id: Mapped[UUID]
    revision: Mapped[int] = mapped_column(default=1)


class ReportVersion(Scoped, Base):
    __tablename__ = "report_versions"
    __table_args__ = (
        scope("report_version"),
        fk("report_id", "reports"),
        fk("snapshot_id", "analysis_snapshots"),
        UniqueConstraint("report_id", "number"),
        CheckConstraint("state IN ('draft','approved','invalidated')"),
        CheckConstraint("number > 0"),
    )
    report_id: Mapped[UUID]
    snapshot_id: Mapped[UUID]
    number: Mapped[int]
    state: Mapped[str] = mapped_column(String(16), default="draft")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Export(Scoped, Base):
    __tablename__ = "exports"
    __table_args__ = (
        scope("export"),
        fk("report_version_id", "report_versions"),
        CheckConstraint("format IN ('json','csv')"),
        CheckConstraint("scope IN ('summary','raw')"),
        CheckConstraint("state IN ('ready','invalidated')"),
    )
    report_version_id: Mapped[UUID]
    format: Mapped[str] = mapped_column(String(8))
    scope: Mapped[str] = mapped_column(String(8))
    state: Mapped[str] = mapped_column(String(16), default="ready")


class ReportShare(Scoped, Base):
    __tablename__ = "report_shares"
    __table_args__ = (
        scope("share"),
        fk("report_version_id", "report_versions"),
        UniqueConstraint("token_hash"),
        CheckConstraint("char_length(token_hash) = 64"),
        CheckConstraint("expires_at > created_at"),
    )
    report_version_id: Mapped[UUID]
    issuer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
