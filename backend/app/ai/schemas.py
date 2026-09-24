from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .profiles import Depth

Operation = Literal[
    "study_helper",
    "themes",
    "failure_clustering",
    "translation",
    "report_writer",
    "research_qa",
    "quality_suggestion",
    "campaign_clarity",
    "sentiment_suggestion",
    "comparison_report",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EstimateBody(Strict):
    study_id: UUID
    snapshot_id: UUID | None = None
    operation: Operation
    instruction: str = Field(default="", max_length=2000)
    researcher_text_approved: bool = False
    depth: Depth = "standard"
    profile_revision: Literal["1", "2"] = "1"
    right_snapshot_id: UUID | None = None

    @model_validator(mode="after")
    def supported_graph(self):
        if self.profile_revision == "2":
            if self.operation not in {"themes", "failure_clustering", "comparison_report"}:
                raise ValueError(
                    "Operation is not supported by revision 2; subgroup execution is unavailable"
                )
            if not self.snapshot_id:
                raise ValueError("Revision 2 requires an exact snapshot")
            if self.operation == "comparison_report":
                if not self.right_snapshot_id or self.right_snapshot_id == self.snapshot_id:
                    raise ValueError("Comparison requires two distinct snapshots")
            elif self.right_snapshot_id:
                raise ValueError("Text analysis accepts one snapshot")
        elif self.operation == "comparison_report" or self.right_snapshot_id:
            raise ValueError("Comparison requires explicit profile_revision 2")
        return self


class RunBody(EstimateBody):
    command_key: str = Field(min_length=1, max_length=100)
    plan_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    max_reserved_cost: str | None = Field(default=None, pattern=r"^[0-9]{1,10}(\.[0-9]{1,8})?$")
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def confirmed_graph(self):
        if self.profile_revision == "2" and any(
            value is None for value in (self.plan_digest, self.max_reserved_cost, self.currency)
        ):
            raise ValueError("Revision 2 requires estimate digest, cost ceiling and currency")
        if self.profile_revision == "1" and any(
            value is not None for value in (self.plan_digest, self.max_reserved_cost, self.currency)
        ):
            raise ValueError("Confirmation fields require revision 2")
        return self


class Evidence(Strict):
    source_id: str = Field(max_length=100)
    quote: str = Field(min_length=1, max_length=2000)


class Finding(Strict):
    text: str = Field(min_length=1, max_length=4000)
    evidence: list[Evidence] = Field(max_length=30)


class Draft(Strict):
    findings: list[Finding] = Field(max_length=30)
    limitations: list[str] = Field(min_length=1, max_length=20)
    insufficient_evidence: bool


class ReconcileBody(Strict):
    actual_cost: Decimal = Field(ge=0, max_digits=18, decimal_places=8)
    reference: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.:-]+$")


class ComparisonFinding(Strict):
    text: str = Field(min_length=1, max_length=4000)
    metric_refs: list[str] = Field(min_length=1, max_length=30)


class ComparisonDraft(Strict):
    findings: list[ComparisonFinding] = Field(max_length=30)
    limitations: list[str] = Field(min_length=1, max_length=20)
    insufficient_evidence: bool
