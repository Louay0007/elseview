from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.common.privacy_schemas import StrictBody


class LocalTime(StrictBody):
    local: datetime
    fold: Literal[0, 1] | None = None


class SlotBody(StrictBody):
    version_id: UUID
    timezone: Annotated[str, Field(min_length=1, max_length=64)]
    starts: LocalTime
    ends: LocalTime
    capacity: Annotated[int, Field(strict=True, ge=1, le=100)] = 1
    join_url: Annotated[str, Field(max_length=2048, pattern=r"^https://[^\s]+$")]


class BookingBody(StrictBody):
    slot_id: UUID
    request_key: UUID


class RevisionBody(StrictBody):
    expected_revision: Annotated[int, Field(strict=True, ge=0)]


class RescheduleBody(RevisionBody):
    slot_id: UUID


class AttendanceBody(RevisionBody):
    attendance: Literal["attended", "absent"]
    note: Annotated[str, Field(min_length=1, max_length=2000)]


class DiaryWindow(StrictBody):
    opens: LocalTime
    due: LocalTime
    grace: LocalTime


class DiaryBody(StrictBody):
    base_session_id: UUID
    timezone: Annotated[str, Field(min_length=1, max_length=64)]
    windows: Annotated[list[DiaryWindow], Field(min_length=1, max_length=90)]


class DiaryStartBody(StrictBody):
    capability: Annotated[str, Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]


class RecordingBody(StrictBody):
    asset_id: UUID
    version_id: UUID
    subject_id: UUID
    consent_receipt_id: UUID


class SegmentBody(StrictBody):
    start_ms: Annotated[int, Field(strict=True, ge=0)]
    end_ms: Annotated[int, Field(strict=True, gt=0)]
    speaker: Annotated[str, Field(min_length=1, max_length=64)] = "unknown"
    text: Annotated[str, Field(min_length=1, max_length=20000)]


class TranscriptBody(StrictBody):
    segments: Annotated[list[SegmentBody], Field(min_length=1, max_length=1000)] | None = None
    text: Annotated[str, Field(min_length=1, max_length=200000)] | None = None

    @model_validator(mode="after")
    def one_source(self):
        if (self.segments is None) == (self.text is None):
            raise ValueError("Exactly one transcript source required")
        if self.segments and sum(len(s.text) for s in self.segments) > 200000:
            raise ValueError("Transcript too large")
        return self
