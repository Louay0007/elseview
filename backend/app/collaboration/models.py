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
