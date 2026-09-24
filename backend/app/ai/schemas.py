from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunBody(Strict):
    study_id: UUID
    snapshot_id: UUID | None = None
    operation: Operation
    instruction: str = Field(default="", max_length=2000)
    command_key: str = Field(min_length=1, max_length=100)
    researcher_text_approved: bool = False


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
