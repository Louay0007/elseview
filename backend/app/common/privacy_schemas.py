from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Key = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
RequestKey = Annotated[str, Field(min_length=1, max_length=128)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Locale = Annotated[str, Field(pattern=r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$", max_length=35)]


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    @field_validator("*", mode="before")
    @classmethod
    def no_blank_strings(cls, value):
        if isinstance(value, str) and (
            not value.strip() or any(0xD800 <= ord(char) <= 0xDFFF for char in value)
        ):
            raise ValueError("Invalid text")
        return value


class DocumentBody(StrictBody):
    document_key: Key
    version: Annotated[int, Field(strict=True, ge=1)]
    locale: Locale
    purpose: Literal[
        "study", "recording", "ai_processing", "private_panel", "recontact", "accessibility_context"
    ]
    body: Annotated[str, Field(min_length=1, max_length=20000)]


class ReceiptBody(StrictBody):
    document_id: UUID
    study_version_id: UUID | None = None
    presented_digest: Digest
    decision: Literal["granted", "declined", "withdrawn"]
    receipt_key: RequestKey


class RetentionBody(StrictBody):
    policy_key: Key
    version: Annotated[int, Field(strict=True, ge=1)]
    raw_days: Annotated[int, Field(strict=True, ge=1, le=3650)]
    media_days: Annotated[int, Field(strict=True, ge=1, le=3650)]
    derived_days: Annotated[int, Field(strict=True, ge=1, le=3650)]
    export_days: Annotated[int, Field(strict=True, ge=1, le=3650)]
    legal_basis: Annotated[str, Field(min_length=1, max_length=128)]


class UploadBody(StrictBody):
    upload_key: RequestKey
    filename: Annotated[
        str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+\.(png|csv|txt|wav)$")
    ]
    media_type: Literal["image/png", "text/csv", "text/plain", "audio/wav"]
    purpose: Literal["stimulus", "attachment", "recording"]
    size_bytes: Annotated[int, Field(strict=True, ge=1, le=16777216)]
    checksum: Digest
    retention_policy_id: UUID


class PrivacyBody(StrictBody):
    kind: Literal["access", "withdrawal", "erasure"]
    request_key: RequestKey


class LinkBody(StrictBody):
    membership_id: UUID
