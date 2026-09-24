from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HistoryPage[T](BaseModel):
    items: list[T]
    next_offset: int | None


class HistoryWorkspace(BaseModel):
    workspace_id: UUID


class ResponseHistory(BaseModel):
    session_id: UUID
    version_id: UUID
    occurrence_id: UUID | None
    locale: str
    submitted_at: datetime | None
    review_state: Literal["pending", "accepted", "rejected", "disputed", "appealed", "erased"]
    appeal_state: Literal["open", "upheld", "overturned"] | None


class RewardHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount_millimes: int
    currency: Literal["TND"]
    state: Literal["earned", "paid"]
    created_at: datetime
    settled_at: datetime | None
    manual_record_only: Literal[True] = True


class PaymentHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    state: Literal["recorded", "failed", "reversed"]
    created_at: datetime
    manual_record_only: Literal[True] = True


class AttendanceHistory(BaseModel):
    id: UUID
    version_id: UUID
    state: Literal["booked", "cancelled"]
    attendance: Literal["unknown", "attended", "absent"]
    attendance_at: datetime | None
    starts_at: datetime
    ends_at: datetime
    timezone: str
