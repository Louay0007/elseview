import ipaddress
import json
import statistics
from collections import Counter
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from app.common.privacy_schemas import Key, Locale
from app.studies import advanced


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class AssetRef(Strict):
    asset_id: UUID
    asset_version: Literal[1]


class Option(Strict):
    id: Key
    label: dict[Locale, Annotated[str, Field(min_length=1, max_length=4000)]]


class ChoiceConfig(Strict):
    options: Annotated[list[Option], Field(min_length=2, max_length=100)]
    randomize_options: bool = False


class MultiConfig(ChoiceConfig):
    min_selected: Annotated[int, Field(ge=1, le=100)]
    max_selected: Annotated[int, Field(ge=1, le=100)]


class RatingConfig(Strict):
    min: int
    max: int
    step: Annotated[int, Field(ge=1)]
    endpoint_labels: dict[Literal["low", "high"], dict[Locale, str]]


class TextConfig(Strict):
    min_length: Annotated[int, Field(ge=1, le=10000)]
    max_length: Annotated[int, Field(ge=1, le=10000)]


class Variant(Option):
    asset_ref: AssetRef


class PreferenceConfig(Strict):
    variants: Annotated[list[Variant], Field(min_length=2, max_length=10)]
    randomization: Literal["uniform_permutation"]
    allow_tie: bool
    allow_none: bool


class ExposureConfig(Strict):
    asset_ref: AssetRef
    exposure_ms: Literal[5000]
    interruption_policy: Literal["invalidate"]
    recall_block_ids: Annotated[list[Key], Field(min_length=1, max_length=10)]


class AssetFlow(Strict):
    mode: Literal["asset_flow"]
    asset_refs: Annotated[list[AssetRef], Field(min_length=1, max_length=100)]


class ExternalLink(Strict):
    mode: Literal["external_link"]
    url: Annotated[str, Field(max_length=2048)]
    authorization_ref: Key

    @model_validator(mode="after")
    def destination(self):
        parsed = urlsplit(self.url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 443}
            or parsed.hostname in {"localhost", "localhost.localdomain"}
            or parsed.hostname.endswith((".local", ".internal"))
        ):
            raise ValueError("Only approved public HTTPS destinations are supported")
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            if "." not in parsed.hostname:
                raise ValueError("Public hostname required") from None
        else:
            if not address.is_global:
                raise ValueError("Public address required")
        return self


class PrototypeConfig(Strict):
    target: Annotated[AssetFlow | ExternalLink, Field(discriminator="mode")]
    success_mode: Literal["self_report"]
    time_limit_ms: Annotated[int, Field(ge=1, le=3600000)]


class Branch(Strict):
    source: Key
    operator: Literal["eq", "contains", "gte"]
    value: str | int
    target: Key | None


class Block(Strict):
    block_key: Key
    schema_version: Literal[1]
    required: bool
    prompt: dict[Locale, Annotated[str, Field(min_length=1, max_length=4000)]]
    branches: Annotated[list[Branch], Field(max_length=20)] = []


class SingleBlock(Block):
    type: Literal["survey.single"]
    config: ChoiceConfig


class MultiBlock(Block):
    type: Literal["survey.multi"]
    config: MultiConfig


class RatingBlock(Block):
    type: Literal["survey.rating"]
    config: RatingConfig


class TextBlock(Block):
    type: Literal["survey.text"]
    config: TextConfig


class PreferenceBlock(Block):
    type: Literal["preference"]
    config: PreferenceConfig


class ExposureBlock(Block):
    type: Literal["five_second"]
    config: ExposureConfig


class PrototypeBlock(Block):
    type: Literal["prototype.task"]
    config: PrototypeConfig


BLOCK = TypeAdapter(
    Annotated[
        SingleBlock
        | MultiBlock
        | RatingBlock
        | TextBlock
        | PreferenceBlock
        | ExposureBlock
        | PrototypeBlock
        | advanced.RankBlock
        | advanced.SumBlock
        | advanced.ClickBlock
        | advanced.CardBlock
        | advanced.TreeBlock
        | advanced.IssueBlock
        | advanced.LanguageBlock,
        Field(discriminator="type"),
    ]
)
RENDERERS = frozenset(
    {
        "survey.single",
        "survey.multi",
        "survey.rating",
        "survey.text",
        "preference",
        "five_second",
        "prototype.task",
    }
)
EVENTS = {
    "survey.single": {"block.rendered"},
    "survey.multi": {"block.rendered"},
    "survey.rating": {"block.rendered"},
    "survey.text": {"block.rendered"},
    "preference": {"variant.rendered"},
    "five_second": {
        "exposure.started",
        "exposure.ended",
        "exposure.interrupted",
        "visibility.changed",
    },
    "prototype.task": {"prototype.launched", "prototype.returned", "prototype.step_reported"},
}


# Matches frontend/AdvancedMethods.jsx ADVANCED_METHOD_TYPES; actual renderers exist.
RENDERERS = RENDERERS | frozenset(advanced.VALUES)
EVENTS.update(advanced.EVENTS)


def parse_block(value):
    block = BLOCK.validate_json(json.dumps(value, allow_nan=False))
    if type(value.get("schema_version")) is not int:
        raise ValueError("Integer schema version required")
    config = block.config
    if block.type in advanced.VALUES:
        advanced.validate_config(block)
    if isinstance(config, ChoiceConfig):
        identifiers = [option.id for option in config.options]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Duplicate option key")
        if isinstance(
            config, MultiConfig
        ) and not config.min_selected <= config.max_selected <= len(identifiers):
            raise ValueError("Invalid choice limits")
    if isinstance(config, RatingConfig):
        if (
            config.min >= config.max
            or (config.max - config.min) % config.step
            or set(config.endpoint_labels) != {"low", "high"}
            or max(abs(config.min), abs(config.max)) > 1000000
        ):
            raise ValueError("Invalid rating scale")
    if isinstance(config, TextConfig) and config.min_length > config.max_length:
        raise ValueError("Invalid text limits")
    if isinstance(config, PreferenceConfig):
        identifiers = {variant.id for variant in config.variants}
        if len(identifiers) != len(config.variants) or identifiers & {"tie", "none"}:
            raise ValueError("Duplicate or reserved variant key")

    def check_text(item):
        if isinstance(item, str) and (
            not item.strip() or any(0xD800 <= ord(char) <= 0xDFFF for char in item)
        ):
            raise ValueError("Invalid text")
        if isinstance(item, dict):
            for child in item.values():
                check_text(child)
        if isinstance(item, list):
            for child in item:
                check_text(child)

    check_text(value)
    return block


def asset_refs(block):
    config = block.config
    if isinstance(config, advanced.ClickConfig):
        return [config.asset_ref]
    if isinstance(config, advanced.LanguageConfig):
        return [config.source_asset_ref]
    if isinstance(config, ExposureConfig):
        return [config.asset_ref]
    if isinstance(config, PreferenceConfig):
        return [variant.asset_ref for variant in config.variants]
    if isinstance(config, PrototypeConfig) and isinstance(config.target, AssetFlow):
        return config.target.asset_refs
    return []


def validate_structure(blocks, locales, rules):
    if (
        not 1 <= len(blocks) <= 100
        or not locales
        or len(locales) > 5
        or len(set(locales)) != len(locales)
    ):
        raise ValueError("Invalid study size or locales")
    parsed = [parse_block(block) for block in blocks]
    positions = {block.block_key: index for index, block in enumerate(parsed)}
    if len(positions) != len(parsed) or set(rules) - set(positions):
        raise ValueError("Duplicate or unknown block key")
    for index, block in enumerate(parsed):
        if block.type not in RENDERERS:
            raise ValueError("Participant renderer unavailable")
        labels = [block.prompt]
        for name in ("cards", "categories", "nodes"):
            labels += [item.label for item in getattr(block.config, name, [])]
        if isinstance(block.config, (advanced.RankConfig, advanced.SumConfig)):
            labels += [o.label for o in block.config.options]
        if isinstance(block.config, advanced.IssueConfig):
            task = positions.get(block.config.task_block_id)
            if (
                task is None
                or task >= index
                or parsed[task].type not in {"prototype.task", "first_click", "tree_test"}
            ):
                raise ValueError("Issue must reference an earlier task")
        if isinstance(block.config, advanced.LanguageConfig) and (
            block.config.source_language not in locales
            or block.config.target_language not in locales
        ):
            raise ValueError("Unsupported source or target language")
        if isinstance(block.config, ChoiceConfig):
            labels += [option.label for option in block.config.options]
        if isinstance(block.config, PreferenceConfig):
            labels += [variant.label for variant in block.config.variants]
        if isinstance(block.config, RatingConfig):
            labels += list(block.config.endpoint_labels.values())
        if any(set(label) != set(locales) for label in labels):
            raise ValueError("Missing or unapproved translations")
        for branch in block.branches:
            if (
                branch.source not in positions
                or positions[branch.source] > index
                or (
                    branch.target is not None
                    and (branch.target not in positions or positions[branch.target] <= index)
                )
            ):
                raise ValueError("Dangling, cyclic or forward-answer dependency")
            source = parsed[positions[branch.source]]
            if branch.operator == "contains":
                valid = source.type == "survey.multi" and branch.value in [
                    option.id for option in source.config.options
                ]
            elif branch.operator == "gte":
                valid = (
                    source.type == "survey.rating"
                    and type(branch.value) is int
                    and source.config.min <= branch.value <= source.config.max
                )
            else:
                valid = source.type == "survey.single" and branch.value in [
                    option.id for option in source.config.options
                ]
            if not valid:
                raise ValueError("Branch condition does not match its source")
        rule = rules.get(block.block_key, {})
        if set(rule) - {"expected_option", "authorization", "min_text_length", "min_elapsed_ms"}:
            raise ValueError("Unknown private rule")
        for key, kind, maximum in (
            ("min_text_length", "survey.text", 10000),
            ("min_elapsed_ms", "prototype.task", 3600000),
        ):
            if key in rule and (
                block.type != kind or type(rule[key]) is not int or not 1 <= rule[key] <= maximum
            ):
                raise ValueError("Invalid private quality threshold")
        if "expected_option" in rule and (
            block.type != "survey.single"
            or rule["expected_option"] not in [option.id for option in block.config.options]
        ):
            raise ValueError("Invalid private answer rule")
        if isinstance(block.config, ExposureConfig):
            if len(set(block.config.recall_block_ids)) != len(block.config.recall_block_ids):
                raise ValueError("Duplicate recall key")
            for key in block.config.recall_block_ids:
                if (
                    key not in positions
                    or positions[key] <= index
                    or parsed[positions[key]].type != "survey.text"
                ):
                    raise ValueError("Recall must reference a subsequent text block")
            if block.branches:
                raise ValueError("Exposure cannot bypass its recall prompts")
        if isinstance(block.config, PrototypeConfig) and isinstance(
            block.config.target, ExternalLink
        ):
            authorization = rule.get("authorization", {})
            if (
                set(authorization) != {"reference", "build_revision", "approved"}
                or authorization["approved"] is not True
                or authorization["reference"] != block.config.target.authorization_ref
                or not isinstance(authorization["build_revision"], str)
                or not 1 <= len(authorization["build_revision"].strip()) <= 128
            ):
                raise ValueError(
                    "External prototype requires recorded authorization and build revision"
                )
        elif "authorization" in rule:
            raise ValueError("Authorization belongs only to external prototypes")
    return parsed


class TextValue(Strict):
    text: Annotated[str, Field(min_length=1, max_length=10000)]
    language: Locale


class SingleValue(Strict):
    option_id: Key


class MultiValue(Strict):
    option_ids: Annotated[list[Key], Field(min_length=1, max_length=100)]


class RatingValue(Strict):
    value: int


class PreferenceValue(Strict):
    assignment_id: Annotated[str, Field(min_length=1, max_length=128)]
    decision: Literal["variant", "tie", "none"]
    selected_variant_id: Key | None
    reason: TextValue


class ExposureValue(Strict):
    attempt_id: Annotated[str, Field(min_length=1, max_length=128)]
    visible_ms: Annotated[int, Field(ge=0, le=3600000)]
    interrupted: bool


class PrototypeValue(Strict):
    outcome: Literal["completed", "failed", "gave_up"]
    elapsed_ms: Annotated[int, Field(ge=0, le=3600000)]
    notes: TextValue | None = None
    termination_reason: Literal["timeout"] | None = None


VALUES = {
    "survey.single": SingleValue,
    "survey.multi": MultiValue,
    "survey.rating": RatingValue,
    "survey.text": TextValue,
    "preference": PreferenceValue,
    "five_second": ExposureValue,
    "prototype.task": PrototypeValue,
}


class Answer(Strict):
    status: Literal["responded", "skipped", "unable"]
    value: dict | None
    reason_code: Literal["technical", "accessibility", "declined", "other"] | None = None


def validate_answer(block, data, locales, assignment_id=None, attempt_id=None):
    answer = Answer.model_validate(data)
    if answer.status != "responded":
        if (
            answer.value is not None
            or (answer.status == "skipped" and block.required)
            or (answer.status == "unable") != (answer.reason_code is not None)
        ):
            raise ValueError("Invalid missing-answer status")
        return answer.model_dump()
    if answer.value is None or answer.reason_code is not None:
        raise ValueError("Responded answer requires a value")
    if block.type in advanced.VALUES:
        value = advanced.VALUES[block.type].model_validate_json(
            json.dumps(answer.value, allow_nan=False)
        )
        advanced.validate_value(block, value, locales)
        return answer.model_dump() | {"value": value.model_dump(mode="json", exclude_unset=True)}
    value = VALUES[block.type].model_validate(answer.value)
    config = block.config
    if isinstance(value, SingleValue) and value.option_id not in [
        option.id for option in config.options
    ]:
        raise ValueError("Unknown choice")
    if isinstance(value, MultiValue) and (
        len(set(value.option_ids)) != len(value.option_ids)
        or not config.min_selected <= len(value.option_ids) <= config.max_selected
        or set(value.option_ids) - {option.id for option in config.options}
    ):
        raise ValueError("Invalid choices")
    if isinstance(value, RatingValue) and (
        not config.min <= value.value <= config.max or (value.value - config.min) % config.step
    ):
        raise ValueError("Invalid rating")
    text_values = [
        item
        for item in (
            value if isinstance(value, TextValue) else None,
            getattr(value, "reason", None),
            getattr(value, "notes", None),
        )
        if item is not None
    ]
    for item in text_values:
        if (
            not item.text.strip()
            or item.language not in locales
            or any(0xD800 <= ord(char) <= 0xDFFF for char in item.text)
        ):
            raise ValueError("Invalid original text")
    if (
        isinstance(value, TextValue)
        and not config.min_length <= len(value.text) <= config.max_length
    ):
        raise ValueError("Text length outside bounds")
    if isinstance(value, PreferenceValue):
        if (
            value.assignment_id != assignment_id
            or (
                value.decision == "variant"
                and value.selected_variant_id not in {variant.id for variant in config.variants}
            )
            or (value.decision != "variant" and value.selected_variant_id is not None)
            or (value.decision == "tie" and not config.allow_tie)
            or (value.decision == "none" and not config.allow_none)
        ):
            raise ValueError("Invalid preference assignment or decision")
    if isinstance(value, ExposureValue) and value.attempt_id != attempt_id:
        raise ValueError("Invalid exposure attempt")
    if (
        isinstance(value, PrototypeValue)
        and value.termination_reason == "timeout"
        and value.outcome == "completed"
    ):
        raise ValueError("Timeout is not completion")
    if (
        isinstance(value, PrototypeValue)
        and value.elapsed_ms > config.time_limit_ms
        and value.termination_reason != "timeout"
    ):
        raise ValueError("Over-limit task requires explicit timeout status")
    return answer.model_dump() | {"value": value.model_dump()}


def next_key(blocks, current_index, answers):
    for branch in blocks[current_index].branches:
        source = answers.get(branch.source, {}).get("value") or {}
        actual = source.get("option_id", source.get("option_ids", source.get("value")))
        matched = (
            (branch.operator == "eq" and actual == branch.value)
            or (
                branch.operator == "contains"
                and isinstance(actual, list)
                and branch.value in actual
            )
            or (branch.operator == "gte" and type(actual) is int and actual >= branch.value)
        )
        if matched:
            return branch.target
    return blocks[current_index + 1].block_key if current_index + 1 < len(blocks) else None


class Event(Strict):
    kind: Annotated[str, Field(max_length=64)]
    client_event_id: UUID
    sequence: Annotated[int, Field(ge=0, le=100000)]
    elapsed_ms: Annotated[int, Field(ge=0, le=3600000)]
    metadata: dict = {}


def validate_event(block, payload, attempt_id=None):
    event = Event.model_validate_json(json.dumps(payload, allow_nan=False))
    if event.kind not in EVENTS[block.type]:
        raise ValueError("Event not permitted for this method")
    metadata = event.metadata
    if event.kind == "first_click.recorded":
        value = advanced.ClickValue.model_validate_json(json.dumps(metadata, allow_nan=False))
        advanced.validate_value(block, value, [])
        valid = value.elapsed_ms == event.elapsed_ms
    elif event.kind == "card_sort.changed":
        valid = (
            set(metadata) == {"card_id", "placed_count"}
            and metadata["card_id"] in {c.id for c in block.config.cards}
            and type(metadata["placed_count"]) is int
            and 0 <= metadata["placed_count"] <= len(block.config.cards)
        )
    elif event.kind == "tree.node_visited":
        valid = set(metadata) == {"node_id"} and metadata["node_id"] in {
            n.id for n in block.config.nodes
        }
    elif event.kind.startswith("exposure."):
        valid = set(metadata) == {"attempt_id"} and metadata["attempt_id"] == attempt_id
    elif event.kind == "visibility.changed":
        valid = (
            set(metadata) == {"visibility", "attempt_id"}
            and metadata["visibility"] in {"visible", "hidden"}
            and metadata["attempt_id"] == attempt_id
        )
    elif event.kind == "variant.rendered":
        valid = set(metadata) == {"variant_id"} and metadata["variant_id"] in {
            variant.id for variant in block.config.variants
        }
    elif event.kind == "prototype.step_reported":
        valid = (
            isinstance(block.config.target, AssetFlow)
            and set(metadata) == {"step_index"}
            and type(metadata["step_index"]) is int
            and 0 <= metadata["step_index"] < len(block.config.target.asset_refs)
        )
    else:
        valid = not metadata
    if not valid:
        raise ValueError("Invalid event metadata")
    return event.model_dump(mode="json") | {"provenance": "client_observed"}


def reduce_answers(block, answers):
    valid = [answer["value"] for answer in answers if answer["status"] == "responded"]
    counts = Counter(answer["status"] for answer in answers)
    result = {
        "metric_version": 1,
        "source_unit": "answer",
        "started": len(answers),
        "responded": len(valid),
        "skipped": counts["skipped"],
        "unable": counts["unable"],
        "denominator": len(valid),
        "preview": True,
    }
    if block.type in {"survey.single", "survey.multi"}:
        selections = Counter(
            key
            for value in valid
            for key in (
                [value["option_id"]] if block.type == "survey.single" else value["option_ids"]
            )
        )
        result["selections"] = {
            option.id: {
                "numerator": selections[option.id],
                "denominator": len(valid),
                "rate": selections[option.id] / len(valid) if valid else None,
            }
            for option in block.config.options
        }
    elif block.type == "survey.rating":
        result["median"] = statistics.median([value["value"] for value in valid]) if valid else None
        result["distribution"] = dict(Counter(value["value"] for value in valid))
    elif block.type == "preference":
        result["decisions"] = dict(
            Counter(value.get("selected_variant_id") or value["decision"] for value in valid)
        )
    elif block.type == "prototype.task":
        completed = [value["elapsed_ms"] for value in valid if value["outcome"] == "completed"]
        result.update(
            numerator=len(completed),
            denominator=len(answers),
            rate=len(completed) / len(answers) if answers else None,
            median_completed_ms=statistics.median(completed) if completed else None,
            provenance="self_report",
        )
    elif block.type == "five_second":
        result["timing_valid"] = sum(
            not value["interrupted"] and 4900 <= value["visible_ms"] <= 5250 for value in valid
        )
        result["provenance"] = "client_observed_preview_only"
    if block.type in advanced.VALUES:
        from app.analytics.metrics import metric

        result.update(advanced.reduce(block, valid, len(answers), metric, {}))
    return result
