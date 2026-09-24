"""Pure P11 contracts; these tests never open a database."""

from uuid import uuid4

import pytest

from app.analytics.metrics import reduce_block
from app.studies import advanced, methods
from app.studies.service import safe_block

ASSET = str(uuid4())
OPTIONS = [{"id": k, "label": {"en": k}} for k in ["a", "b", "c"]]


def block(kind, config, **extra):
    return methods.parse_block(
        dict(
            block_key="b1",
            schema_version=1,
            type=kind,
            required=True,
            prompt={"en": "Task"},
            config=config,
            **extra,
        )
    )


def answer(b, v):
    return methods.validate_answer(b, {"status": "responded", "value": v}, ["en"])


def click():
    return block(
        "first_click",
        dict(
            asset_ref={"asset_id": ASSET, "asset_version": 1},
            coordinate_space="normalized_asset",
            input_modes=["pointer", "keyboard_cursor"],
            asset_width=100,
            asset_height=50,
        ),
        evaluation={
            "aois": [
                {
                    "id": "hit",
                    "polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
                    "success": True,
                }
            ]
        },
    )


def click_value(**kwargs):
    return dict(
        asset_id=ASSET, asset_version=1, x=0.5, y=0.5, elapsed_ms=20, input_mode="pointer", **kwargs
    )


def test_ranking_partial_denominators():
    b = block("survey.ranking", {"options": OPTIONS, "rank_count": 2})
    a = answer(b, {"ordered_option_ids": ["a", "b"]})
    result = reduce_block(b, [a])["mean_rank"]
    assert result["a"]["value"] == 1 and result["c"]["value"] is None
    for ids in [["a", "a"], ["a"], ["a", "x"]]:
        with pytest.raises(ValueError):
            answer(b, {"ordered_option_ids": ids})


@pytest.mark.parametrize("points", [1.0, True, -1, 10001, "1"])
def test_constant_sum_strict(points):
    b = block("survey.constant_sum", {"options": OPTIONS[:2], "total_points": 2})
    with pytest.raises(ValueError):
        answer(
            b,
            {
                "allocations": [
                    {"option_id": "a", "points": points},
                    {"option_id": "b", "points": 1},
                ]
            },
        )


def test_constant_sum_complete():
    b = block("survey.constant_sum", {"options": OPTIONS[:2], "total_points": 2})
    answer(b, {"allocations": [{"option_id": "a", "points": 0}, {"option_id": "b", "points": 2}]})
    with pytest.raises(ValueError):
        answer(
            b, {"allocations": [{"option_id": "a", "points": 1}, {"option_id": "a", "points": 1}]}
        )


@pytest.mark.parametrize("x", [-0.001, 1.001, float("nan"), float("inf"), True, "0.5"])
def test_click_bad_coordinate(x):
    value = click_value()
    value["x"] = x
    with pytest.raises(ValueError):
        answer(click(), value)


def test_click_private_projection_and_overlap_boundary():
    b = click()
    p = safe_block({"locale": "en", "jti": "demo"}, b)
    assert "evaluation" not in p
    assert advanced.contains(b.evaluation.aois[0].polygon, [1.0, 0.5])
    a = answer(b, click_value())
    assert reduce_block(b, [a])["input_modes"]["pointer"]["success"]["value"] == 1
    a["value"]["input_mode"] = "keyboard_cursor"
    assert reduce_block(b, [a])["input_modes"]["pointer"]["success"]["denominator"] == 0


@pytest.mark.parametrize(
    "p",
    [
        [[0.0, 0.0], [1.0, 1.0], [0.0, 1.0], [1.0, 0.0]],
        [[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]],
        [[0.0, 0.0], [1.0, 0.0], [0.0, 0.0]],
    ],
)
def test_invalid_polygon(p):
    with pytest.raises(ValueError):
        advanced.polygon_valid(p)


def test_click_event_contract():
    b = click()
    e = dict(
        kind="first_click.recorded",
        client_event_id=str(uuid4()),
        sequence=1,
        elapsed_ms=20,
        metadata=click_value(),
    )
    assert methods.validate_event(b, e)["provenance"] == "client_observed"
    e["elapsed_ms"] = 21
    with pytest.raises(ValueError):
        methods.validate_event(b, e)


def test_card_empty_categories_and_unplaced():
    b = block(
        "card_sort", dict(mode="closed", cards=OPTIONS, categories=OPTIONS[:2], allow_unplaced=True)
    )
    v = dict(
        groups=[{"group_id": "a", "card_ids": ["a", "b"]}, {"group_id": "b", "card_ids": []}],
        unplaced_card_ids=["c"],
    )
    a = answer(b, v)
    assert reduce_block(b, [a])["co_grouping"]["a:c"]["denominator"] == 0
    v["groups"].pop()
    with pytest.raises(ValueError):
        answer(b, v)


def tree():
    return block(
        "tree_test",
        dict(
            nodes=[
                dict(id="a", label={"en": "a"}, parent_id=None, selectable=False),
                dict(id="b", label={"en": "b"}, parent_id="a", selectable=True),
                dict(id="c", label={"en": "c"}, parent_id="a", selectable=True),
            ],
            root_id="a",
        ),
        evaluation={"target_paths": [["a", "b"]]},
    )


def test_tree_detour_and_impossible_transition():
    b = tree()
    v = dict(
        visited_node_ids=["a", "c", "a", "b"],
        selected_node_id="b",
        outcome="selected",
        elapsed_ms=30,
    )
    assert reduce_block(b, [answer(b, v)])["outcomes"]["indirect"]["value"] == 1
    v["visited_node_ids"] = ["a", "c", "b"]
    with pytest.raises(ValueError):
        answer(b, v)


def test_issue_and_language():
    b = block(
        "accessibility.issue",
        dict(task_block_id="task", capture_context=False, criterion_refs=["contrast"]),
    )
    answer(b, {"issues": []})
    with pytest.raises(ValueError):
        answer(
            b,
            {
                "issues": [
                    {
                        "description": {"text": "bad", "language": "en"},
                        "impact": "blocked",
                        "criterion_ref": "fake",
                    }
                ]
            },
        )
    b = block(
        "language.review",
        dict(
            source_asset_ref={"asset_id": ASSET, "asset_version": 1},
            source_text="original text",
            source_language="en",
            target_language="en",
            rubric_version="v1",
            dimensions=[{"id": "accuracy", "min": 1, "max": 5}],
        ),
    )
    v = dict(
        ratings=[{"dimension_id": "accuracy", "value": 3}],
        issues=[{"quote": "original", "explanation": {"text": "note", "language": "en"}}],
    )
    answer(b, v)
    v["issues"][0]["quote"] = "fake"
    with pytest.raises(ValueError):
        answer(b, v)


def test_unknown_properties_and_renderer_gate():
    with pytest.raises(ValueError):
        block("survey.ranking", {"options": OPTIONS, "rank_count": 2, "script": "bad"})
    b = click()
    assert "first_click.recorded" in methods.EVENTS[b.type]


def test_click_heatmap_all_points_not_only_success():
    b = click()
    b.evaluation = None
    value = click_value()
    value.update(x=1.0, y=1.0)
    result = reduce_block(b, [answer(b, value)])["input_modes"]["pointer"]
    assert result["success"]["status"] == "not_configured"
    assert result["heatmap"]["distribution"]["9:9"]["numerator"] == 1


def test_asset_version_rejects_boolean():
    v = click_value()
    v["asset_version"] = True
    with pytest.raises(ValueError):
        answer(click(), v)


def test_tree_cycle_rejected():
    data = tree().model_dump(mode="json")
    data["config"]["nodes"][1]["parent_id"] = "c"
    data["config"]["nodes"][2]["parent_id"] = "b"
    with pytest.raises(ValueError):
        methods.parse_block(data)


def test_overlapping_aois_one_success_denominator():
    b = click()
    a = b.evaluation.aois[0].model_copy(update={"id": "overlap"})
    b.evaluation.aois.append(a)
    result = reduce_block(b, [answer(b, click_value())])["input_modes"]["pointer"]
    assert result["success"]["numerator"] == result["success"]["denominator"] == 1
    assert sum(m["numerator"] for m in result["aoi_hits"].values()) == 2


def test_tree_gave_up_preserves_explicit_null():
    b = tree()
    a = answer(
        b, dict(visited_node_ids=["a"], selected_node_id=None, outcome="gave_up", elapsed_ms=12)
    )
    assert "selected_node_id" in a["value"] and a["value"]["selected_node_id"] is None
    assert reduce_block(b, [a])["outcomes"]["failed"]["numerator"] == 1


def test_actual_frontend_exports_match_gate():
    import re
    from pathlib import Path

    source = (Path(__file__).parents[2] / "frontend" / "AdvancedMethods.jsx").read_text()
    exported = re.search(r"export const ADVANCED_METHOD_TYPES = \[(.*?)\]", source).group(1)
    types = set(re.findall(r"'([^']+)'", exported))
    assert types == set(advanced.VALUES)
    assert types <= methods.RENDERERS
    assert "export function AdvancedMethods(" in source
