"""Collaboration credentials contain only hashes; webhook rows contain no research payload."""

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


class APIKey(Scoped, Base):
    __tablename__ = "api_keys"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scopes: Mapped[list] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReportComment(Scoped, Base):
    __tablename__ = "report_comments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "report_id"],
            ["reports.workspace_id", "reports.id"],
            ondelete="CASCADE",
        ),
    )
    report_id: Mapped[UUID]
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)  # Always classified raw; never in granted views.
    restricted: Mapped[bool] = mapped_column(default=False)


class ReportGrant(Scoped, Base):
    __tablename__ = "report_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "report_id"],
            ["reports.workspace_id", "reports.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("report_id", "recipient_id"),
    )
    report_id: Mapped[UUID]
    issuer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int]
    revoked: Mapped[bool] = mapped_column(default=False)


class TemplateGrant(Scoped, Base):
    __tablename__ = "template_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "instance_id"],
            ["template_instances.workspace_id", "template_instances.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("instance_id", "recipient_id"),
    )
    instance_id: Mapped[UUID]
    issuer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    revoked: Mapped[bool] = mapped_column(default=False)


class NotificationPreference(Scoped, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    reminders: Mapped[bool] = mapped_column(default=True)
    email_reminders: Mapped[bool] = mapped_column(default=False, server_default="false")


class NotificationDelivery(Scoped, Base):
    """Source references only; SMTP content is reconstructed after authorization."""

    __tablename__ = "notification_deliveries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "invitation_id"],
            ["invitations.workspace_id", "invitations.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "notification_id"],
            ["notifications.workspace_id", "notifications.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "occurrence_id"],
            ["diary_occurrences.workspace_id", "diary_occurrences.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "(purpose = 'recruitment_invite' AND invitation_id IS NOT NULL AND notification_id IS NULL AND occurrence_id IS NULL) OR "
            "(purpose = 'interview_reminder' AND notification_id IS NOT NULL AND invitation_id IS NULL AND occurrence_id IS NULL) OR "
            "(purpose = 'diary_reminder' AND occurrence_id IS NOT NULL AND invitation_id IS NULL AND notification_id IS NULL)",
            name="ck_notification_delivery_source",
        ),
        CheckConstraint(
            "state IN ('pending','dispatching','sent','failed','uncertain','cancelled')",
            name="ck_notification_delivery_state",
        ),
        CheckConstraint("attempts BETWEEN 0 AND 3", name="ck_notification_delivery_attempts"),
    )
    recipient_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    issuer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    invitation_id: Mapped[UUID | None] = mapped_column(index=True)
    notification_id: Mapped[UUID | None] = mapped_column(index=True)
    occurrence_id: Mapped[UUID | None] = mapped_column(index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    privacy_epoch: Mapped[int]
    state: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    outcome: Mapped[str | None] = mapped_column(String(32))
    attempts: Mapped[int] = mapped_column(default=0)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None]
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Integration(Scoped, Base):
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("workspace_id", "id"),)
    creator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    destination: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(default=False)
    revision: Mapped[int] = mapped_column(default=1)


class WebhookDelivery(Scoped, Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "integration_id"], ["integrations.workspace_id", "integrations.id"]
        ),
        UniqueConstraint("integration_id", "command_key"),
        CheckConstraint("state IN ('pending','succeeded','failed','cancelled')"),
    )
    integration_id: Mapped[UUID]
    integration_revision: Mapped[int]
    requester_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    command_key: Mapped[UUID]
    state: Mapped[str] = mapped_column(String(16), default="pending")
