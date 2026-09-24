from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Scoped:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsentDocument(Scoped, Base):
    __tablename__ = "consent_documents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_document_scope"),
        UniqueConstraint(
            "workspace_id", "document_key", "version", "locale", name="uq_document_version"
        ),
        CheckConstraint("version > 0", name="ck_document_version"),
        CheckConstraint(
            "purpose IN ('study','recording','ai_processing','private_panel','recontact','accessibility_context')",
            name="ck_document_purpose",
        ),
        CheckConstraint(
            "char_length(body) BETWEEN 1 AND 20000 AND char_length(digest) = 64",
            name="ck_document_body",
        ),
    )
    document_key: Mapped[str] = mapped_column(String(64))
    version: Mapped[int]
    locale: Mapped[str] = mapped_column(String(35))
    purpose: Mapped[str] = mapped_column(String(32))
    body: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))


class ConsentReceipt(Scoped, Base):
    __tablename__ = "consent_receipts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "document_id"],
            ["consent_documents.workspace_id", "consent_documents.id"],
            name="fk_receipt_document",
        ),
        UniqueConstraint("workspace_id", "subject_id", "receipt_key", name="uq_receipt_key"),
        ForeignKeyConstraint(
            ["workspace_id", "study_version_id"],
            ["study_versions.workspace_id", "study_versions.id"],
            name="fk_receipt_study_version",
        ),
        CheckConstraint(
            "decision IN ('granted','declined','withdrawn')", name="ck_receipt_decision"
        ),
    )
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[UUID]
    study_version_id: Mapped[UUID | None]
    receipt_key: Mapped[str] = mapped_column(String(128))
    decision: Mapped[str] = mapped_column(String(16))
    presented_digest: Mapped[str] = mapped_column(String(64))


class RetentionPolicy(Scoped, Base):
    __tablename__ = "retention_policies"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_retention_scope"),
        UniqueConstraint("workspace_id", "policy_key", "version", name="uq_retention_version"),
        CheckConstraint(
            "version > 0 AND raw_days BETWEEN 1 AND 3650 AND media_days BETWEEN 1 AND 3650 AND derived_days BETWEEN 1 AND 3650 AND export_days BETWEEN 1 AND 3650",
            name="ck_retention_limits",
        ),
    )
    policy_key: Mapped[str] = mapped_column(String(64))
    version: Mapped[int]
    raw_days: Mapped[int]
    media_days: Mapped[int]
    derived_days: Mapped[int]
    export_days: Mapped[int]
    legal_basis: Mapped[str] = mapped_column(String(128))


class PrivacyRequest(Scoped, Base):
    __tablename__ = "privacy_requests"
    __table_args__ = (
        UniqueConstraint("workspace_id", "subject_id", "request_key", name="uq_privacy_request"),
        CheckConstraint("kind IN ('access','withdrawal','erasure')", name="ck_privacy_kind"),
        CheckConstraint("state IN ('requested','processing','completed')", name="ck_privacy_state"),
    )
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    request_key: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(16), default="requested")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PrivacyRestriction(Scoped, Base):
    __tablename__ = "privacy_restrictions"
    __table_args__ = (UniqueConstraint("workspace_id", "subject_id", name="uq_privacy_subject"),)
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class Asset(Scoped, Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_asset_scope"),
        UniqueConstraint("storage_key", name="uq_asset_storage"),
        CheckConstraint(
            "storage_key ~ '^[0-9a-f]{32}$' AND checksum ~ '^[0-9a-f]{64}$'", name="ck_asset_keys"
        ),
        CheckConstraint(
            "(media_type = 'image/png' AND extension = 'png') OR (media_type = 'text/csv' AND extension = 'csv') OR (media_type = 'text/plain' AND extension = 'txt') OR (media_type = 'audio/wav' AND extension = 'wav' AND purpose = 'recording')",
            name="ck_asset_format",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "owner_id"],
            ["memberships.workspace_id", "memberships.user_id"],
            name="fk_asset_owner_scope",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "retention_policy_id"],
            ["retention_policies.workspace_id", "retention_policies.id"],
            name="fk_asset_retention",
        ),
        CheckConstraint(
            "state IN ('pending','uploading','quarantined','ready','blocked','purging','purged')",
            name="ck_asset_state",
        ),
        CheckConstraint(
            "purpose IN ('stimulus','attachment','recording')", name="ck_asset_purpose"
        ),
        CheckConstraint(
            "size_bytes > 0 AND size_bytes <= 16777216 AND char_length(checksum) = 64",
            name="ck_asset_size",
        ),
        CheckConstraint(
            "(width IS NULL OR width BETWEEN 1 AND 4096) AND (height IS NULL OR height BETWEEN 1 AND 4096)",
            name="ck_asset_dimensions",
        ),
    )
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    retention_policy_id: Mapped[UUID]
    storage_key: Mapped[str] = mapped_column(String(32))
    media_type: Mapped[str] = mapped_column(String(64))
    extension: Mapped[str] = mapped_column(String(8))
    purpose: Mapped[str] = mapped_column(String(16))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    checksum: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), default="pending")
    width: Mapped[int | None]
    height: Mapped[int | None]
    duration_ms: Mapped[int | None]
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class UploadIntent(Scoped, Base):
    __tablename__ = "upload_intents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "asset_id"],
            ["assets.workspace_id", "assets.id"],
            name="fk_upload_asset",
        ),
        UniqueConstraint("asset_id", name="uq_upload_asset"),
        UniqueConstraint("workspace_id", "uploader_id", "upload_key", name="uq_upload_key"),
    )
    asset_id: Mapped[UUID]
    uploader_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    upload_key: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssetLink(Scoped, Base):
    __tablename__ = "asset_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "asset_id"], ["assets.workspace_id", "assets.id"], name="fk_link_asset"
        ),
        ForeignKeyConstraint(
            ["workspace_id", "owner_membership_id"],
            ["memberships.workspace_id", "memberships.id"],
            name="fk_link_member",
        ),
        UniqueConstraint(
            "workspace_id",
            "asset_id",
            "owner_membership_id",
            "purpose",
            name="uq_asset_member_link",
        ),
        CheckConstraint("purpose IN ('stimulus','attachment','recording')", name="ck_link_purpose"),
    )
    asset_id: Mapped[UUID]
    owner_membership_id: Mapped[UUID]
    purpose: Mapped[str] = mapped_column(String(16))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
