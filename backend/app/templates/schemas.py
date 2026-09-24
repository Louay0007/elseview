from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.common.privacy_schemas import Key, Locale, StrictBody
from app.studies.advanced import Dimension

Text = Annotated[str, Field(min_length=1, max_length=4000)]
Labels = dict[Locale, Text]


class AssetInput(StrictBody):
    asset_id: UUID
    asset_version: Annotated[int, Field(strict=True, ge=1, le=1)]


class OptionInput(StrictBody):
    id: Key
    label: Labels
    asset_ref: AssetInput | None = None


class LanguageInput(StrictBody):
    source_asset_ref: AssetInput
    source_text: Annotated[str, Field(min_length=1, max_length=10000)]
    source_language: Locale
    target_language: Locale
    rubric_version: Key
    dimensions: Annotated[list[Dimension], Field(min_length=1, max_length=100)]


class Inputs(StrictBody):
    language_review: LanguageInput | None = None
    context: Text
    translation_approval_ref: Text
    prompts: dict[Key, Labels]
    task_assets: dict[Key, Annotated[list[AssetInput], Field(min_length=1, max_length=100)]]
    endpoint_labels: dict[str, Labels]
    options: Annotated[list[OptionInput], Field(max_length=10)] = []
    reviewer_qualifications: dict[Locale, Text] = {}


class InstantiateBody(StrictBody):
    template_version: Annotated[int, Field(strict=True, ge=1)]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    retention_policy_id: UUID
    locales: Annotated[list[Locale], Field(min_length=1, max_length=4)]
    consent_documents: dict[Locale, UUID]
    inputs: Inputs
