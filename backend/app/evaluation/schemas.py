"""Standalone human workbench wire contracts; all snapshots are immutable."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

Text = Annotated[str, Field(min_length=1, max_length=20000, pattern=r"\S")]
Key = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[\w-]+$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Rights(Strict):
    owner: Text
    compensation_terms: Text
    reuse_permission: bool
    training_permission: bool
    label_license: Text
    consent_scope: Text


class Dimension(Strict):
    id: Key
    min: StrictInt
    max: StrictInt

    @model_validator(mode="after")
    def bounds(self):
        if not -1000 <= self.min < self.max <= 1000:
            raise ValueError("Invalid rubric bounds")
        return self


class Label(Strict):
    id: Key
    label: Text


class Schema(Strict):
    task: Literal[
        "classification", "text_spans", "image_polygons", "pairwise", "language_review", "sandbox"
    ]
    instructions: Text
    instructions_version: Key
    labels: list[Label] = Field(default_factory=list, max_length=100)
    min_annotations: Annotated[StrictInt, Field(ge=0, le=100)] = 0
    max_annotations: Annotated[StrictInt, Field(ge=0, le=100)] = 100
    allow_overlap: bool = False
    dimensions: list[Dimension] = Field(default_factory=list, max_length=20)
    rubric_version: Key | None = None
    language_basis: Text | None = None

    @model_validator(mode="after")
    def coherent(self):
        if self.min_annotations > self.max_annotations:
            raise ValueError("Invalid annotation counts")
        for values in (self.labels, self.dimensions):
            if len({v.id for v in values}) != len(values):
                raise ValueError("Duplicate identifiers")
        if self.task in {"classification", "text_spans", "image_polygons"} and not self.labels:
            raise ValueError("Labels required")
        if self.task in {"pairwise", "language_review"} and (
            not self.dimensions or not self.rubric_version or not self.language_basis
        ):
            raise ValueError("Rubric and language basis required")
        return self


class Candidate(Strict):
    text: Text
    model_revision: Text
    settings: dict = Field(default_factory=dict)


class Scenario(Strict):
    revision: Key
    business_policy_version: Key
    instructions: Text
    approved: Literal[True]
    fictional_inputs_only: Literal[True]
    mode: Literal["manual_transcript"] = "manual_transcript"
    max_turns: Annotated[StrictInt, Field(ge=1, le=50)]
    max_duration_ms: Annotated[StrictInt, Field(ge=1, le=3600000)]
    max_characters: Annotated[StrictInt, Field(ge=1, le=50000)] = 10000


class AssetRef(Strict):
    asset_id: UUID
    asset_version: Literal[1] = 1


class Source(Strict):
    text: Text
    language: Key
    asset_ref: AssetRef | None = None
    candidates: list[Candidate] = Field(default_factory=list, max_length=2)
    scenario: Scenario | None = None
    testcase: Text | None = None


class ItemBody(Strict):
    key: Key
    source: Source
    partition: Literal["train", "evaluation"]


class DatasetBody(Strict):
    study_id: UUID
    key: Key
    version: Annotated[StrictInt, Field(ge=1)]
    rights: Rights
    schema_: Schema = Field(alias="schema")
    items: list[ItemBody] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def valid_items(self):
        if len({i.key for i in self.items}) != len(self.items):
            raise ValueError("Duplicate item keys")
        for item in self.items:
            s = item.source
            if self.schema_.task == "pairwise" and len(s.candidates) != 2:
                raise ValueError("Two frozen candidates required")
            if self.schema_.task in {"pairwise", "language_review"} and not s.testcase:
                raise ValueError("Approved test case required")
            if self.schema_.task == "sandbox" and not s.scenario:
                raise ValueError("Approved fictional scenario required")
            if self.schema_.task == "image_polygons" and not s.asset_ref:
                raise ValueError("Image required")
            if item.partition == "train" and not self.rights.training_permission:
                raise ValueError("Training rights required")
        return self


class AssignmentBody(Strict):
    item_id: UUID
    reviewer_id: UUID
    kind: Literal["independent", "adjudication"] = "independent"


class Reason(Strict):
    text: Text
    language: Key


class Rating(Strict):
    candidate_id: Literal["left", "right", "source"]
    dimension_id: Key
    value: StrictInt


class Annotation(Strict):
    label_id: Key
    start: StrictInt | None = None
    end: StrictInt | None = None
    polygon: list[tuple[float, float]] | None = Field(default=None, min_length=3, max_length=100)


class Turn(Strict):
    role: Literal["user", "assistant"]
    text: Text
    language: Key


class OutcomeBody(Strict):
    reason: Reason
    annotations: list[Annotation] = Field(default_factory=list, max_length=100)
    choice: Literal["left", "right", "tie", "both_bad", "cannot_judge"] | None = None
    ratings: list[Rating] = Field(default_factory=list, max_length=40)
    outcome: Literal["completed", "failed", "gave_up", "infrastructure_failure"] | None = None
    turns: list[Turn] = Field(default_factory=list, max_length=50)
    duration_ms: Annotated[StrictInt, Field(ge=0, le=3600000)] | None = None
    scenario_revision: Key | None = None
    fictional_confirmation: Literal[True] | None = None


class ExportReviewBody(Strict):
    reason: Reason
