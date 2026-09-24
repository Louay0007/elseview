from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.common.privacy_schemas import Locale, StrictBody

Capabilities = Literal["read", "edit", "publish", "preview", "raw", "export", "ai", "review"]


class StudyBody(StrictBody):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    retention_policy_id: UUID
    ai_policy: Literal["human_only", "assisted"] = "human_only"


class VersionBody(StrictBody):
    expected_revision: Annotated[int, Field(strict=True, ge=1)]
    blocks_json: Annotated[list[dict], Field(max_length=100)]
    rules_json: dict[str, dict] = {}
    locales: Annotated[list[Locale], Field(min_length=1, max_length=5)] = ["fr"]
    consent_documents: dict[Locale, UUID] = {}


class RevisionBody(StrictBody):
    expected_revision: Annotated[int, Field(strict=True, ge=1)]


class GrantBody(StrictBody):
    membership_id: UUID
    capabilities: Annotated[list[Capabilities], Field(min_length=1, max_length=8)]

    @field_validator("capabilities")
    @classmethod
    def unique(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Duplicate capability")
        return value


class StateBody(StrictBody):
    status: Literal["paused", "ready", "closed", "archived"]


class PreviewBody(StrictBody):
    locale: Locale


class PreviewAnswers(StrictBody):
    answers: dict[str, dict] = {}
