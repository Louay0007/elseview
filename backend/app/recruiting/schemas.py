from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Attributes(Strict):
    age: int | None = Field(default=None, ge=18, le=120)
    devices: list[Literal["mobile", "desktop", "tablet"]] = Field(
        default_factory=list, max_length=3
    )
    languages: list[str] = Field(default_factory=list, max_length=10)


class Filters(Strict):
    min_age: int | None = Field(default=None, ge=18, le=120)
    max_age: int | None = Field(default=None, ge=18, le=120)
    device: Literal["mobile", "desktop", "tablet"] | None = None
    language: str | None = Field(default=None, max_length=35)
    verified_language: str | None = Field(default=None, max_length=35)

    @model_validator(mode="after")
    def compatible(self):
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("incompatible age range")
        return self


class PanelBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attributes: Attributes = Field(default_factory=Attributes)
    decision: Literal["granted", "withdrawn"]
    document_version: Literal["1"]
    presented_digest: str = Field(min_length=64, max_length=64)
    receipt_key: str = Field(min_length=1, max_length=128)


class ImportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rows: list[dict[str, str]] = Field(min_length=1, max_length=500)
    mapping: dict[str, str]
    source: str = Field(min_length=1, max_length=200)
    consent_confirmed: Literal[True]
    document_id: UUID
    retention_until: datetime
    duplicate_policy: Literal["skip", "reject"] = "skip"
    preview: bool = True


class ScreenerQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=20)
    eligible_options: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def choices(self):
        if len(set(self.options)) != len(self.options) or not set(self.eligible_options) <= set(
            self.options
        ):
            raise ValueError("invalid screener choices")
        return self


class QuotaBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capacity: int = Field(ge=1, le=100000)
    filters: Filters = Field(default_factory=Filters)


class ConfigBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capacity: int = Field(ge=1, le=100000)
    budget_millimes: int = Field(ge=0, le=10**12)
    reward_millimes: int = Field(ge=0, le=10**9)
    hold_seconds: int = Field(default=1800, ge=60, le=86400)
    filters: Filters = Field(default_factory=Filters)
    screeners: dict[str, ScreenerQuestion] = Field(default_factory=dict, max_length=20)
    quotas: list[QuotaBody] = Field(default_factory=list, max_length=20)
    screening_policy: Literal["uncompensated_disclosed"] = "uncompensated_disclosed"


class InviteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_kind: Literal["public", "private"]
    source_id: UUID
    expires_seconds: int = Field(default=86400, ge=60, le=604800)


class ScreenBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: dict[str, str] = Field(default_factory=dict, max_length=20)


class QualificationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["fr", "en", "ar"]
    assessment_version: Literal["development-basic-v1"]
    answers: list[str] = Field(min_length=2, max_length=2)


class PublicRecruitBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int = Field(ge=1, le=50)
    filters: Filters = Field(default_factory=Filters)
    expires_seconds: int = Field(default=86400, ge=60, le=604800)
