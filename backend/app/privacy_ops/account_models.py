"""Durable global erasure receipts; never store passwords or status capabilities."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AccountErasure(Base):
    __tablename__ = "privacy_account_erasures"
    __table_args__ = (
        CheckConstraint("state IN ('pending','completed')", name="ck_account_erasure_state"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    request_key: Mapped[UUID] = mapped_column(unique=True)
    capability_hash: Mapped[str] = mapped_column(String(64))
    workspace_ids: Mapped[list] = mapped_column(JSONB, default=list)
    state: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
