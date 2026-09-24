"""Text-task assessment contracts; no speech or professional credential claims."""

import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Language = Literal["tunisianArabic", "formalArabic", "french", "arabizi"]
Verdict = Literal["qualified", "not_qualified", "inconclusive"]
SCOPE = "text_task_performance_not_speech_or_professional_credentials"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Choice(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    label: str = Field(min_length=1, max_length=500)


class Task(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    kind: Literal["single_choice", "text"]
    prompt: str = Field(min_length=1, max_length=2000)
    choices: list[Choice] = Field(default_factory=list, max_length=10)
    criteria: dict[str, str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def valid(self):
        if len({c.id for c in self.choices}) != len(self.choices):
            raise ValueError("duplicate option")
        if (self.kind == "single_choice" and len(self.choices) < 2) or (
            self.kind == "text" and self.choices
        ):
            raise ValueError("invalid task choices")
        if any(
            not k.isidentifier() or len(k) > 40 or not 1 <= len(v) <= 1000
            for k, v in self.criteria.items()
        ):
            raise ValueError("invalid criterion")
        return self


class Policy(Strict):
    duration_minutes: int = Field(default=30, ge=5, le=120, strict=True)
    max_starts_30_days: int = Field(default=3, ge=1, le=3, strict=True)
    cooldown_hours: int = Field(default=24, ge=24, le=720, strict=True)
    validity_days: int = Field(default=90, ge=1, le=365, strict=True)
    retention_days: int = Field(default=180, ge=32, le=365, strict=True)


class Material(Strict):
    answer_keys: dict[str, str] = Field(default_factory=dict, max_length=20)
    rubric: dict[str, dict[str, str]] = Field(min_length=1, max_length=20)


class VersionBody(Strict):
    assessment_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    version: int = Field(ge=1, le=10000, strict=True)
    language: Language
    schema_version: Literal[1] = 1
    synthetic: bool = Field(default=True, strict=True)
    tasks: list[Task] = Field(min_length=1, max_length=20)
    limitations: str = Field(min_length=1, max_length=2000)
    policy: Policy = Field(default_factory=Policy)
    material: Material

    @model_validator(mode="after")
    def complete(self):
        ids = {t.id for t in self.tasks}
        if len(ids) != len(self.tasks) or set(self.material.rubric) != ids:
            raise ValueError("invalid task references")
        choice_ids = {t.id for t in self.tasks if t.kind == "single_choice"}
        if set(self.material.answer_keys) != choice_ids:
            raise ValueError("missing or extra answer keys")
        for t in self.tasks:
            if set(self.material.rubric[t.id]) != set(t.criteria):
                raise ValueError("invalid rubric criteria")
            if any(not 1 <= len(v) <= 4000 for v in self.material.rubric[t.id].values()):
                raise ValueError("invalid rubric text")
            if t.kind == "single_choice" and self.material.answer_keys[t.id] not in {
                c.id for c in t.choices
            }:
                raise ValueError("invalid answer key")
        if (
            len(json.dumps(self.material.model_dump()).encode()) > 64000
            or len(json.dumps(self.model_dump(exclude={"material"})).encode()) > 64000
        ):
            raise ValueError("assessment content too large")
        return self


class ApprovalBody(Strict):
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_reference: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_:/.-]{2,127}$")
    content_validity_confirmed: Literal[True]


class RetireBody(Strict):
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ConsentBody(Strict):
    decision: Literal["granted", "withdrawn"]
    document_version: Literal["1"]
    presented_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    receipt_key: str = Field(min_length=1, max_length=128)
    grant_id: UUID | None = None

    @model_validator(mode="after")
    def scope(self):
        if (self.decision == "withdrawn") != (self.grant_id is not None):
            raise ValueError("withdrawal requires exact grant")
        return self


class StartBody(Strict):
    version_id: UUID
    consent_grant_id: UUID
    command_key: str = Field(min_length=1, max_length=128)


class SubmitBody(Strict):
    command_key: str = Field(min_length=1, max_length=128)
    responses: dict[str, str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def bounded(self):
        if (
            any(len(k) > 40 or not 1 <= len(v) <= 4000 for k, v in self.responses.items())
            or len(json.dumps(self.responses).encode()) > 64000
        ):
            raise ValueError("responses too large")
        return self


class AppealBody(Strict):
    command_key: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=2000)


class DecisionBody(Strict):
    command_key: str = Field(min_length=1, max_length=128)
    round: Literal[1, 2]
    verdict: Verdict
    findings: dict[str, dict[str, Literal["met", "not_met", "insufficient"]]] = Field(
        min_length=1, max_length=20
    )
    rationale: str = Field(min_length=1, max_length=2000)


class ConsentDocumentOut(Strict):
    version: str
    body: str
    digest: str


class ConsentOut(Strict):
    id: UUID
    decision: Literal["granted", "withdrawn"]
    grant_id: UUID | None
    created_at: datetime


class ConsentGrantOut(Strict):
    id: UUID
    document_version: str
    created_at: datetime
    withdrawn_at: datetime | None


class ConsentGrantsOut(Strict):
    items: list[ConsentGrantOut]
    next_offset: int | None


class VersionOut(Strict):
    id: UUID
    assessment_key: str
    version: int
    language: Language
    schema_version: int
    synthetic: bool
    state: Literal["draft", "approved", "retired"]
    policy: Policy
    limitations: str
    public_digest: str
    scope: Literal["text_task_performance_not_speech_or_professional_credentials"] = SCOPE


class VersionDetailOut(VersionOut):
    tasks: list[Task]
    content_digest: str


class CatalogueOut(Strict):
    items: list[VersionOut]
    languages: list[Language]
    next_offset: int | None


class DecisionOut(Strict):
    id: UUID
    round: int
    verdict: Verdict
    findings: dict[str, dict[str, str]] | None
    rationale: str | None
    decided_at: datetime
    expires_at: datetime | None
    previous_decision_id: UUID | None


class AttemptOut(Strict):
    id: UUID
    version_id: UUID
    language: Language
    state: Literal["started", "submitted", "adjudicated", "abandoned", "withdrawn"]
    consent_grant_id: UUID
    sequence: int
    started_at: datetime
    deadline_at: datetime
    submitted_at: datetime | None
    retention_until: datetime
    evidence_available: bool
    tasks: list[Task] | None
    responses: dict[str, str] | None
    appeal_requested_at: datetime | None
    appeal_reason: str | None
    decisions: list[DecisionOut]
    scope: Literal["text_task_performance_not_speech_or_professional_credentials"] = SCOPE


class QualificationOut(Strict):
    language: Language
    assessment_id: UUID
    assessment_version: int
    decision_id: UUID
    decided_at: datetime
    expires_at: datetime
    consent_grant_id: UUID


class LegacyOut(Strict):
    language: str
    passed: bool
    expires_at: datetime
    evidence_kind: Literal["legacy_development_not_reviewed"] = "legacy_development_not_reviewed"


class HistoryOut(Strict):
    current: list[QualificationOut]
    attempts: list[AttemptOut]
    legacy: list[LegacyOut]
    next_offset: int | None


class QueueItem(Strict):
    id: UUID
    version_id: UUID
    language: Language
    submitted_at: datetime
    appeal_requested_at: datetime | None


class QueueOut(Strict):
    items: list[QueueItem]
    next_offset: int | None


class PrivateMaterialOut(Strict):
    version_id: UUID
    material: Material


class SweepOut(Strict):
    purged: int
