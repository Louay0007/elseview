from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.common.privacy_schemas import Key, Locale, StrictBody


class StartBody(StrictBody):
    invitation_token: Annotated[str, Field(min_length=20, max_length=4096)]
    capability: Annotated[str, Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]
    locale: Locale
    document_id: UUID
    presented_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    consent: Literal["granted"]


class AnswerBody(StrictBody):
    version_id: UUID | None = None
    occurrence_id: UUID | None = None
    schema_version: Literal[1]
    expected_revision: Annotated[int, Field(strict=True, ge=0)]
    client_event_id: UUID
    occurrence: Literal[0] = 0
    status: Literal["responded", "skipped", "unable"]
    value: dict | None
    reason_code: Literal["technical", "accessibility", "declined", "other"] | None = None

    @field_validator("schema_version", "occurrence", mode="before")
    @classmethod
    def integer_literal(cls, value):
        if type(value) is not int:
            raise ValueError("Integer required")
        return value

    @property
    def answer(self):
        return {"status": self.status, "value": self.value, "reason_code": self.reason_code}


class EventBody(StrictBody):
    block_key: Key
    event: dict


class BatchBody(StrictBody):
    version_id: UUID
    events: Annotated[list[EventBody], Field(min_length=1, max_length=100)]


class SubmitBody(StrictBody):
    version_id: UUID
    occurrence_id: UUID | None = None
    expected_revision: Annotated[int, Field(strict=True, ge=0)]
