from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class Study(Scoped, Base):
    __tablename__ = "studies"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_study_scope"),
        ForeignKeyConstraint(
            ["workspace_id", "owner_membership_id"],
            ["memberships.workspace_id", "memberships.id"],
            name="fk_study_owner",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "retention_policy_id"],
            ["retention_policies.workspace_id", "retention_policies.id"],
            name="fk_study_retention",
        ),
        CheckConstraint(
            "status IN ('draft','ready','paused','closed','archived')", name="ck_study_status"
        ),
        CheckConstraint("ai_policy IN ('human_only','assisted')", name="ck_study_ai_policy"),
        CheckConstraint("char_length(title) BETWEEN 1 AND 200", name="ck_study_title"),
    )
    title: Mapped[str] = mapped_column(String(200))
    owner_membership_id: Mapped[UUID]
    retention_policy_id: Mapped[UUID]
    status: Mapped[str] = mapped_column(String(16), default="draft")
    ai_policy: Mapped[str] = mapped_column(String(16), default="human_only")


class StudyVersion(Scoped, Base):
    __tablename__ = "study_versions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_version_scope"),
        UniqueConstraint("workspace_id", "study_id", "number", name="uq_study_version"),
        Index(
            "uq_one_study_draft", "study_id", unique=True, postgresql_where=text("state = 'draft'")
        ),
        ForeignKeyConstraint(
            ["workspace_id", "study_id"],
            ["studies.workspace_id", "studies.id"],
            name="fk_version_study",
        ),
        CheckConstraint(
            "state IN ('draft','published') AND revision > 0 AND number > 0",
            name="ck_version_state",
        ),
        CheckConstraint(
            "(state = 'draft' AND published_at IS NULL AND content_hash IS NULL) OR (state = 'published' AND published_at IS NOT NULL AND char_length(content_hash) = 64)",
            name="ck_version_publication",
        ),
        CheckConstraint(
            "jsonb_typeof(blocks_json) = 'array' AND jsonb_array_length(blocks_json) <= 100 AND jsonb_typeof(rules_json) = 'object' AND jsonb_typeof(locales) = 'array' AND jsonb_typeof(consent_documents) = 'object'",
            name="ck_version_json",
        ),
    )
    study_id: Mapped[UUID]
    number: Mapped[int]
    revision: Mapped[int] = mapped_column(default=1)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    blocks_json: Mapped[list] = mapped_column(JSONB, default=list)
    rules_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    locales: Mapped[list] = mapped_column(JSONB, default=lambda: ["fr"])
    consent_documents: Mapped[dict] = mapped_column(JSONB, default=dict)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StudyGrant(Scoped, Base):
    __tablename__ = "study_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "study_id"],
            ["studies.workspace_id", "studies.id"],
            name="fk_grant_study",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "membership_id"],
            ["memberships.workspace_id", "memberships.id"],
            name="fk_grant_member",
        ),
        UniqueConstraint("workspace_id", "study_id", "membership_id", name="uq_study_grant"),
        CheckConstraint(
            'jsonb_typeof(capabilities) = \'array\' AND capabilities <@ \'["read","edit","publish","preview","raw","export","ai","review"]\'::jsonb',
            name="ck_grant_capabilities",
        ),
    )
    study_id: Mapped[UUID]
    membership_id: Mapped[UUID]
    capabilities: Mapped[list] = mapped_column(JSONB)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Launch(Scoped, Base):
    __tablename__ = "launches"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_launch_scope"),
        ForeignKeyConstraint(
            ["workspace_id", "version_id"],
            ["study_versions.workspace_id", "study_versions.id"],
            name="fk_launch_version",
        ),
        UniqueConstraint("workspace_id", "version_id", name="uq_launch_version"),
        CheckConstraint("state IN ('ready','paused','closed')", name="ck_launch_state"),
    )
    version_id: Mapped[UUID]
    state: Mapped[str] = mapped_column(String(16), default="ready")
