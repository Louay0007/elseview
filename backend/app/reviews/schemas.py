from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AssignmentBody(Body):
    reviewer_id: UUID
    kind: Literal["independent", "adjudication", "appeal"] = "independent"


class DecisionBody(Body):
    command_key: UUID
    verdict: Literal["accepted", "rejected"]
    rationale: str = Field(min_length=1, max_length=2000)
    evidence: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("evidence")
    @classmethod
    def evidence_bounds(cls, values):
        if any(not v.strip() or len(v) > 500 for v in values):
            raise ValueError("Evidence must be nonempty and bounded")
        return values

    @model_validator(mode="after")
    def reject_needs_evidence(self):
        if self.verdict == "rejected" and not self.evidence:
            raise ValueError("Rejection requires evidence")
        return self


class AppealBody(Body):
    command_key: UUID
    reason: str = Field(min_length=1, max_length=2000)


class RetentionBody(Body):
    settled_days: int = Field(ge=0, le=36500, strict=True)
    rationale: str = Field(min_length=1, max_length=1000)


class PayoutBody(Body):
    command_key: UUID
    amount_millimes: int = Field(gt=0, le=1_000_000_000_000, strict=True)
    currency: Literal["TND"] = "TND"
    external_reference: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:/-]+$")
    evidence: str = Field(
        min_length=1,
        max_length=1000,
        description="Non-sensitive reconciliation evidence; never bank credentials or identity documents",
    )
    failed: bool = False
