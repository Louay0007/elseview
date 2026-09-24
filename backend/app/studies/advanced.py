"""Strict advanced-method contracts and deterministic private evaluation."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.privacy_schemas import Key, Locale


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    @field_validator("asset_version", "schema_version", mode="before", check_fields=False)
    @classmethod
    def strict_literals(cls, value, info):
        if info.field_name in {"asset_version", "schema_version"} and type(value) is not int:
            raise ValueError("Integer version required")
        return value


class AssetRef(Strict):
    asset_id: UUID
    asset_version: Literal[1]


class Option(Strict):
    id: Key
    label: dict[Locale, Annotated[str, Field(min_length=1, max_length=4000)]]


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


Text = Annotated[str, Field(min_length=1, max_length=10000)]
Ids = Annotated[list[Key], Field(max_length=100)]
Unit = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Millis = Annotated[int, Field(ge=0, le=3600000)]


class Original(Strict):
    text: Text
    language: Locale


class RankConfig(Strict):
    options: Annotated[list[Option], Field(min_length=2, max_length=100)]
    rank_count: Annotated[int, Field(ge=1, le=100)]


class SumConfig(Strict):
    options: Annotated[list[Option], Field(min_length=2, max_length=100)]
    total_points: Annotated[int, Field(ge=1, le=10000)]


class ClickConfig(Strict):
    asset_ref: AssetRef
    coordinate_space: Literal["normalized_asset"]
    input_modes: list[Literal["pointer", "keyboard_cursor"]]
    asset_width: Annotated[int, Field(ge=1, le=4096)]
    asset_height: Annotated[int, Field(ge=1, le=4096)]


class AOI(Strict):
    id: Key
    polygon: Annotated[
        list[Annotated[list[Unit], Field(min_length=2, max_length=2)]],
        Field(min_length=3, max_length=100),
    ]
    success: bool


class ClickEvaluation(Strict):
    aois: Annotated[list[AOI], Field(max_length=50)]


class CardConfig(Strict):
    mode: Literal["open", "closed", "hybrid"]
    cards: Annotated[list[Option], Field(min_length=1, max_length=100)]
    categories: Annotated[list[Option], Field(max_length=100)]
    allow_unplaced: bool


class Node(Option):
    parent_id: Key | None
    selectable: bool


class TreeConfig(Strict):
    nodes: Annotated[list[Node], Field(min_length=1, max_length=100)]
    root_id: Key


class TreeEvaluation(Strict):
    target_paths: Annotated[
        list[Annotated[list[Key], Field(min_length=1, max_length=100)]],
        Field(min_length=1, max_length=100),
    ]


class IssueConfig(Strict):
    task_block_id: Key
    capture_context: bool
    criterion_refs: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=128)]], Field(max_length=100)
    ]


class Dimension(Strict):
    id: Key
    min: Annotated[int, Field(ge=-10000, le=10000)]
    max: Annotated[int, Field(ge=-10000, le=10000)]


class LanguageConfig(Strict):
    source_asset_ref: AssetRef
    source_text: Text
    source_language: Locale
    target_language: Locale
    rubric_version: Key
    dimensions: Annotated[list[Dimension], Field(min_length=1, max_length=100)]


class RankBlock(Block):
    type: Literal["survey.ranking"]
    config: RankConfig


class SumBlock(Block):
    type: Literal["survey.constant_sum"]
    config: SumConfig


class ClickBlock(Block):
    type: Literal["first_click"]
    config: ClickConfig
    evaluation: ClickEvaluation | None = None


class CardBlock(Block):
    type: Literal["card_sort"]
    config: CardConfig


class TreeBlock(Block):
    type: Literal["tree_test"]
    config: TreeConfig
    evaluation: TreeEvaluation | None = None


class IssueBlock(Block):
    type: Literal["accessibility.issue"]
    config: IssueConfig


class LanguageBlock(Block):
    type: Literal["language.review"]
    config: LanguageConfig


class RankValue(Strict):
    ordered_option_ids: Ids


class Allocation(Strict):
    option_id: Key
    points: Annotated[int, Field(ge=0, le=10000)]


class SumValue(Strict):
    allocations: Annotated[list[Allocation], Field(min_length=2, max_length=100)]


class ClickValue(Strict):
    asset_id: UUID
    asset_version: Literal[1]
    x: Unit
    y: Unit
    elapsed_ms: Millis
    input_mode: Literal["pointer", "keyboard_cursor"]


class Group(Strict):
    group_id: Key
    card_ids: Ids
    label: Original | None = None


class CardValue(Strict):
    groups: Annotated[list[Group], Field(max_length=100)]
    unplaced_card_ids: Ids


class TreeValue(Strict):
    visited_node_ids: Annotated[list[Key], Field(min_length=1, max_length=10000)]
    selected_node_id: Key | None
    outcome: Literal["selected", "gave_up"]
    elapsed_ms: Millis


class Context(Strict):
    input_method: Annotated[str, Field(min_length=1, max_length=128)]
    assistive_technology: Annotated[str, Field(min_length=1, max_length=128)]


class Issue(Strict):
    description: Original
    impact: Literal["blocked", "difficult", "minor"]
    context: Context | None = None
    criterion_ref: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    evidence_asset_ref: AssetRef | None = None


class IssueValue(Strict):
    issues: Annotated[list[Issue], Field(max_length=100)]


class Rating(Strict):
    dimension_id: Key
    value: int


class LanguageIssue(Strict):
    quote: Text
    explanation: Original


class LanguageValue(Strict):
    ratings: Annotated[list[Rating], Field(min_length=1, max_length=100)]
    issues: Annotated[list[LanguageIssue], Field(max_length=100)]
    rewrite: Original | None = None


VALUES = {
    "survey.ranking": RankValue,
    "survey.constant_sum": SumValue,
    "first_click": ClickValue,
    "card_sort": CardValue,
    "tree_test": TreeValue,
    "accessibility.issue": IssueValue,
    "language.review": LanguageValue,
}
EVENTS = {k: {"block.rendered"} for k in VALUES}
EVENTS["first_click"].add("first_click.recorded")
EVENTS["card_sort"].add("card_sort.changed")
EVENTS["tree_test"].add("tree.node_visited")


def unique(items):
    if len(items) != len(set(items)):
        raise ValueError("Duplicate identifier")


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_edge(p, a, b):
    return (
        abs(cross(a, b, p)) <= 1e-12
        and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
    )


def intersects(a, b, c, d):
    return (cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0) or any(
        (on_edge(c, a, b), on_edge(d, a, b), on_edge(a, c, d), on_edge(b, c, d))
    )


def polygon_valid(p):
    unique([tuple(v) for v in p])
    if abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1], strict=False))) <= 1e-12:
        raise ValueError("Zero area polygon")
    for i, a in enumerate(p):
        b = p[(i + 1) % len(p)]
        previous = p[(i - 1) % len(p)]
        if on_edge(b, previous, a) or on_edge(previous, a, b):
            raise ValueError("Adjacent polygon edges overlap")
        for j in range(i + 1, len(p)):
            if j == i + 1 or (i == 0 and j == len(p) - 1):
                continue
            if intersects(a, b, p[j], p[(j + 1) % len(p)]):
                raise ValueError("Non simple polygon")


def contains(p, point):
    inside = False
    for a, b in zip(p, p[1:] + p[:1], strict=False):
        if on_edge(point, a, b):
            return True
        if (a[1] > point[1]) != (b[1] > point[1]) and point[0] < (b[0] - a[0]) * (
            point[1] - a[1]
        ) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def validate_config(block):
    c = block.config
    for name in ("options", "cards", "categories", "nodes", "dimensions"):
        if hasattr(c, name):
            unique([v.id for v in getattr(c, name)])
    if isinstance(c, RankConfig) and c.rank_count > len(c.options):
        raise ValueError("Rank count exceeds options")
    if isinstance(c, ClickConfig):
        if c.input_modes not in [["pointer"], ["pointer", "keyboard_cursor"]]:
            raise ValueError("Invalid input modes")
        if block.evaluation:
            unique([a.id for a in block.evaluation.aois])
            for a in block.evaluation.aois:
                polygon_valid(a.polygon)
    if isinstance(c, CardConfig):
        if c.mode == "open" and c.categories or c.mode == "closed" and not c.categories:
            raise ValueError("Invalid categories")
    if isinstance(c, TreeConfig):
        nodes = {n.id: n for n in c.nodes}
        if c.root_id not in nodes or nodes[c.root_id].parent_id is not None:
            raise ValueError("Invalid root")
        for n in c.nodes:
            seen = set()
            key = n.id
            while key != c.root_id:
                if key in seen or key not in nodes:
                    raise ValueError("Disconnected or cyclic tree")
                seen.add(key)
                key = nodes[key].parent_id
        if block.evaluation:
            unique([tuple(p) for p in block.evaluation.target_paths])
            for p in block.evaluation.target_paths:
                if (
                    p[0] != c.root_id
                    or any(k not in nodes for k in p)
                    or not nodes[p[-1]].selectable
                    or any(nodes[b].parent_id != a for a, b in zip(p, p[1:], strict=False))
                ):
                    raise ValueError("Invalid target path")
    if isinstance(c, LanguageConfig) and any(d.min >= d.max for d in c.dimensions):
        raise ValueError("Invalid rubric")


def validate_value(block, v, locales):
    c = block.config

    def text(t):
        if (
            not t.text.strip()
            or t.language not in locales
            or any(0xD800 <= ord(ch) <= 0xDFFF for ch in t.text)
        ):
            raise ValueError("Invalid original text")

    if isinstance(v, RankValue):
        unique(v.ordered_option_ids)
        if len(v.ordered_option_ids) != c.rank_count or set(v.ordered_option_ids) - {
            o.id for o in c.options
        }:
            raise ValueError("Invalid ranking")
    if isinstance(v, SumValue):
        unique([a.option_id for a in v.allocations])
        if {a.option_id for a in v.allocations} != {o.id for o in c.options} or sum(
            a.points for a in v.allocations
        ) != c.total_points:
            raise ValueError("Invalid allocation")
    if isinstance(v, ClickValue):
        if (
            v.asset_id != c.asset_ref.asset_id
            or v.asset_version != c.asset_ref.asset_version
            or v.input_mode not in c.input_modes
        ):
            raise ValueError("Invalid click")
    if isinstance(v, CardValue):
        unique([g.group_id for g in v.groups])
        configured = {g.id for g in c.categories}
        placed = [k for g in v.groups for k in g.card_ids] + v.unplaced_card_ids
        unique(placed)
        if (
            set(placed) != {card.id for card in c.cards}
            or v.unplaced_card_ids
            and not c.allow_unplaced
        ):
            raise ValueError("Invalid card placement")
        if not configured <= {g.group_id for g in v.groups}:
            raise ValueError("Missing configured groups")
        for g in v.groups:
            if g.group_id in configured:
                if g.label is not None:
                    raise ValueError("Configured labels are immutable")
            elif c.mode == "closed" or g.label is None:
                raise ValueError("Invalid new group")
            else:
                text(g.label)
    if isinstance(v, TreeValue):
        nodes = {n.id: n for n in c.nodes}
        p = v.visited_node_ids
        if (
            p[0] != c.root_id
            or any(k not in nodes for k in p)
            or any(
                nodes[a].parent_id != b and nodes[b].parent_id != a
                for a, b in zip(p, p[1:], strict=False)
            )
        ):
            raise ValueError("Invalid navigation path")
        if v.outcome == "gave_up":
            if v.selected_node_id is not None:
                raise ValueError("Gave up cannot select")
        elif v.selected_node_id != p[-1] or not nodes[p[-1]].selectable:
            raise ValueError("Invalid selection")
    if isinstance(v, IssueValue):
        for i in v.issues:
            text(i.description)
            if i.criterion_ref is not None and i.criterion_ref not in c.criterion_refs:
                raise ValueError("Unknown criterion")
            # No purpose-specific consent/evidence upload capability is available in v1.
            if (
                i.context is not None and not c.capture_context
            ) or i.evidence_asset_ref is not None:
                raise ValueError("Separate consent and evidence permission required")
    if isinstance(v, LanguageValue):
        unique([r.dimension_id for r in v.ratings])
        dims = {d.id: d for d in c.dimensions}
        if {r.dimension_id for r in v.ratings} != set(dims) or any(
            not dims[r.dimension_id].min <= r.value <= dims[r.dimension_id].max for r in v.ratings
        ):
            raise ValueError("Invalid rubric ratings")
        for i in v.issues:
            text(i.explanation)
            if i.quote not in c.source_text:
                raise ValueError("Quote not in pinned source")
        if v.rewrite:
            if not v.rewrite.text.strip() or any(
                0xD800 <= ord(ch) <= 0xDFFF for ch in v.rewrite.text
            ):
                raise ValueError("Invalid rewrite text")
            if v.rewrite.language != c.target_language:
                raise ValueError("Rewrite language mismatch")


def project(result, locale):
    result.pop("evaluation", None)
    for name in ("options", "cards", "categories", "nodes"):
        for item in result["config"].get(name, []):
            if isinstance(item["label"], dict):
                item["label"] = item["label"][locale]
    return result


def reduce(block, valid, starts, metric, exclusions):
    """Only aggregate facts; no quotes, category text, coordinates or context in reports."""
    from itertools import combinations
    from statistics import median

    def m(n, d):
        return metric(n, d, exclusions, provenance="client_observed", method_metric_version="p11.1")

    def mean(values):
        result = m(len(values), len(values))
        result.update(
            value=sum(values) / len(values) if values else None,
            aggregation="mean",
            sample_n=len(values),
        )
        return result

    c = block.config
    if isinstance(c, RankConfig):
        return {
            "mean_rank": {
                o.id: mean(
                    [
                        v["ordered_option_ids"].index(o.id) + 1
                        for v in valid
                        if o.id in v["ordered_option_ids"]
                    ]
                )
                for o in c.options
            }
        }
    if isinstance(c, SumConfig):
        return {
            "mean_points": {
                o.id: mean(
                    [a["points"] for v in valid for a in v["allocations"] if a["option_id"] == o.id]
                )
                for o in c.options
            }
        }
    if isinstance(c, ClickConfig):
        aois = block.evaluation.aois if block.evaluation else []
        strata = {}
        for mode in c.input_modes:
            values = [v for v in valid if v["input_mode"] == mode]
            hits = [[a for a in aois if contains(a.polygon, [v["x"], v["y"]])] for v in values]
            strata[mode] = {
                "first_clicks": m(len(values), starts),
                "success": m(sum(any(a.success for a in h) for h in hits), len(values))
                if block.evaluation
                else {"status": "not_configured"},
                "aoi_hits": {a.id: m(sum(a in h for h in hits), len(values)) for a in aois},
                "heatmap": {
                    "coordinate_space": "normalized_asset",
                    "grid_size": 10,
                    "distribution": {
                        f"{x}:{y}": m(
                            sum(
                                min(int(v["x"] * 10), 9) == x and min(int(v["y"] * 10), 9) == y
                                for v in values
                            ),
                            len(values),
                        )
                        for y in range(10)
                        for x in range(10)
                    },
                },
            }
        return {"input_modes": strata, "no_click": m(starts - len(valid), starts)}
    if isinstance(c, CardConfig):
        pairs = {}
        for a, b in combinations([x.id for x in c.cards], 2):
            together = placed = 0
            for v in valid:
                groups = {card: g["group_id"] for g in v["groups"] for card in g["card_ids"]}
                if a in groups and b in groups:
                    placed += 1
                    together += groups[a] == groups[b]
            pairs[a + ":" + b] = m(together, placed)
        return {"co_grouping": pairs}
    if isinstance(c, TreeConfig):
        targets = block.evaluation.target_paths if block.evaluation else []
        counts = {"direct": 0, "indirect": 0, "failed": 0, "unknown": starts - len(valid)}
        for v in valid:
            target = next((p for p in targets if p[-1] == v["selected_node_id"]), None)
            kind = (
                "unknown"
                if not block.evaluation
                else "failed"
                if target is None
                else "direct"
                if target == v["visited_node_ids"]
                else "indirect"
            )
            counts[kind] += 1
        times = [v["elapsed_ms"] for v in valid if v["outcome"] == "selected"]
        timing = m(len(times), len(times))
        timing.update(
            value=median(times) if times else None,
            aggregation="median",
            unit="ms",
            sample_n=len(times),
        )
        return {"outcomes": {k: m(n, starts) for k, n in counts.items()}, "time_selected": timing}
    if isinstance(c, IssueConfig):
        return {
            "participants_reporting_impact": {
                impact: m(
                    sum(any(i["impact"] == impact for i in v["issues"]) for v in valid), len(valid)
                )
                for impact in ["blocked", "difficult", "minor"]
            },
            "interpretation": "reported_barriers_not_conformance_certification",
        }
    if isinstance(c, LanguageConfig):
        return {
            "mean_rating": {
                d.id: mean(
                    [r["value"] for v in valid for r in v["ratings"] if r["dimension_id"] == d.id]
                )
                for d in c.dimensions
            },
            "participants_reporting_issues": m(sum(bool(v["issues"]) for v in valid), len(valid)),
            "rubric_version": c.rubric_version,
            "reviewer_basis": "participant_self_report_unverified",
        }
    return {}
