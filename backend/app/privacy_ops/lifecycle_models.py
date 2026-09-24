"""Holds for unlinked private contacts, never inferred from a user identity."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.privacy_models import Scoped
from app.db import Base


class ContactHold(Scoped, Base):
    __tablename__ = "privacy_contact_holds"
    __table_args__ = (
        CheckConstraint("length(reason_code) BETWEEN 1 AND 64", name="ck_contact_hold_reason"),
    )
    # No resource FK: the identifier-only hold survives a quarantined restore.
    contact_id: Mapped[UUID] = mapped_column(index=True)
    reason_code: Mapped[str] = mapped_column(String(64))
    reviewed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    review_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
