import csv
import io
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from study_fixtures import blocks

from app.analytics.metrics import (
    VERSION,
    compare_metrics,
    csv_document,
    digest,
    metric,
    redacted_metrics,
    reduce_block,
    safe_cell,
)
from app.analytics.router import ExportBody, ReviseBody, ShareBody
from app.analytics.service import safe_summary
from app.studies.methods import parse_block

pytestmark = pytest.mark.unit


def block(kind):
    return next(parse_block(b) for b in blocks(str(uuid4())) if b["type"] == kind)


def answered(value):
    return {"status": "responded", "value": value}


def test_single_denominator_missing_exclusions_and_version():
    result = reduce_block(
        block("survey.single"),
        [
            answered({"option_id": "yes"}),
            answered({"option_id": "no"}),
            {"status": "missing"},
            {"status": "unable"},
        ],
        {"not_accepted": 2},
    )
    yes = result["distribution"]["yes"]
    assert (yes["numerator"], yes["denominator"], yes["value"]) == (1, 2, 0.5)
    assert yes["source_unit"] == "session" and yes["metric_version"] == VERSION
    assert yes["exclusions"] == {"not_accepted": 2, "missing": 1, "unable": 1, "skipped": 0}
    assert result["missingness"]["value"] == 0.5
    assert result["response"]["value"] == 0.5


def test_multi_select_totals_can_exceed_one_hundred_percent():
    result = reduce_block(
        block("survey.multi"),
        [answered({"option_ids": ["yes", "no"]}), answered({"option_ids": ["yes", "no"]})],
    )
    assert sum(m["value"] for m in result["distribution"].values()) == 2
    assert all(m["denominator"] == 2 for m in result["distribution"].values())


@pytest.mark.parametrize(
    "values,expected", [([], None), ([1], 1), ([1, 3, 5], 3), ([1, 2, 4, 5], 3)]
)
def test_rating_median_even_odd_and_empty(values, expected):
    result = reduce_block(block("survey.rating"), [answered({"value": v}) for v in values])
    assert result["median"]["value"] == expected
    assert result["median"]["sample_n"] == len(values)
    assert result["median"]["aggregation"] == "median"


def test_preference_ties_and_none_are_explicit():
    result = reduce_block(
        block("preference"),
        [
            answered({"decision": "tie", "selected_variant_id": None}),
            answered({"decision": "none", "selected_variant_id": None}),
        ],
    )
    assert result["distribution"]["tie"]["value"] == 0.5
    assert result["distribution"]["none"]["value"] == 0.5


def test_completion_all_sessions_and_completed_time_only():
    result = reduce_block(
        block("prototype.task"),
        [
            answered({"outcome": "completed", "elapsed_ms": 10}),
            answered({"outcome": "completed", "elapsed_ms": 30}),
            answered({"outcome": "abandoned", "elapsed_ms": 90}),
            {"status": "missing"},
        ],
    )
    assert result["completion"]["denominator"] == 4
    assert result["completion"]["value"] == 0.5
    assert result["time_on_task"]["value"] == 20
    assert result["time_on_task"]["sample_n"] == 2
    assert result["time_on_task"]["provenance"] == "self_report"


def test_five_second_is_client_observed_not_verified():
    result = reduce_block(
        block("five_second"),
        [
            answered({"interrupted": False, "visible_ms": 5000}),
            answered({"interrupted": True, "visible_ms": 5000}),
        ],
    )
    assert result["timing_valid"]["value"] == 0.5
    assert "not_verified" in result["timing_valid"]["provenance"]


def test_text_is_not_copied_into_metrics():
    result = reduce_block(block("survey.text"), [answered({"text": "SECRET", "language": "fr"})])
    assert "SECRET" not in str(result)
    assert set(result) == {"type", "missingness", "response"}


def test_empty_metrics_null_not_zero():
    result = reduce_block(block("survey.single"), [])
    assert result["response"]["value"] is None
    assert result["distribution"]["yes"]["value"] is None


@pytest.mark.parametrize(
    "cell", ["=SUM(A1)", "+1", "-2", "@user", "  =1", "\tX", "\nX", "\rX", " \t=1"]
)
def test_csv_formula_safe(cell):
    assert safe_cell(cell).startswith("'")


def test_csv_unicode_quotes_newlines_and_keys_roundtrip():
    data = {"=evil": '"عربي,café\ntext"', "ordinary": '=HYPERLINK("bad")'}
    rows = list(csv.reader(io.StringIO(csv_document(data))))
    assert rows[1][0] == "'=evil"
    assert rows[1][1] == data["=evil"]
    assert rows[2][1].startswith("'=HYPERLINK")


def test_digest_canonical_and_nan_rejected():
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})
    with pytest.raises(ValueError):
        digest({"value": float("nan")})


def test_comparisons_suppress_both_groups_and_median_difference():
    assert compare_metrics({}, {}, 100, 4)["suppressed"]
    left = {"median": metric(5, 5, {}) | {"value": 10}}
    right = {"median": metric(5, 5, {}) | {"value": 30}}
    assert compare_metrics(left, right, 5, 5)["differences"]["median"] == 20


def test_complementary_suppression_entire_distribution_and_counts():
    data = {
        "included": 100,
        "excluded": {"pending": 1},
        "blocks": {
            "q": {
                "distribution": {"rare": metric(1, 100, {}), "common": metric(99, 100, {})},
                "response": metric(99, 100, {}),
            }
        },
    }
    result = redacted_metrics(data)
    assert "included" not in result and "excluded" not in result
    assert result["blocks"]["q"]["distribution"]["suppressed"]
    assert result["blocks"]["q"]["response"]["suppressed"]
    assert "99" not in str(result)


def test_public_summary_strict_allowlist_ignores_injected_metadata():
    result = safe_summary(
        SimpleNamespace(metrics={"included": 3, "secret": "leak", "blocks": {"quote": "leak"}})
    )
    assert set(result) == {
        "metric_version",
        "source_unit",
        "sample_size_band",
        "sampling",
        "status",
        "measures",
    }
    assert result["sample_size_band"] == "suppressed"
    assert "leak" not in str(result)


@pytest.mark.parametrize(
    "body",
    [
        {"format": "xlsx"},
        {"format": "pdf"},
        {"format": "json", "scope": "contacts"},
        {"format": "json", "extra": True},
    ],
)
def test_only_existing_csv_json_export_contract(body):
    with pytest.raises(ValidationError):
        ExportBody.model_validate(body)


def test_share_expiry_and_revision_bounds():
    for ttl in (0, 59, 2592001):
        with pytest.raises(ValidationError):
            ShareBody(ttl_seconds=ttl)
    with pytest.raises(ValidationError):
        ReviseBody(expected_revision=0, snapshot_id=uuid4())


def test_overlapping_release_history_suppresses_both_including_invalidated():
    from app.analytics.metrics import metric
    from app.analytics.service import release_metrics, release_suppressed

    a, b, wid, study = (uuid4() for _ in range(4))
    population = [uuid4() for _ in range(21)]

    def snapshot(id, total):
        return SimpleNamespace(
            id=id,
            workspace_id=wid,
            study_id=study,
            definition_digest="a" * 64,
            state="invalidated" if id == a else "ready",
            metrics={
                "included": total,
                "blocks": {
                    "q": {
                        "distribution": {
                            "yes": metric(total - 10, total, {}),
                            "no": metric(10, total, {}),
                        }
                    }
                },
            },
        )

    left, right = snapshot(a, 20), snapshot(b, 21)

    class Result(list):
        def all(self):
            return self

    class Session:
        def __init__(self, current):
            self.current = current
            self.calls = 0

        def scalars(self, query):
            self.calls += 1
            if self.calls % 2:
                # All stored history, deliberately no state predicate in gate query.
                assert "analysis_snapshots.state" not in str(query)
                return Result([b if self.current == a else a])
            return Result(
                [
                    SimpleNamespace(snapshot_id=id, session_id=p)
                    for id, count in ((a, 20), (b, 21))
                    for p in population[:count]
                ]
            )

    assert release_suppressed(Session(a), left)
    assert release_suppressed(Session(b), right)
    assert release_metrics(Session(a), left)["suppressed"]
    assert release_metrics(Session(b), right)["suppressed"]
    assert "numerator" not in str(release_metrics(Session(b), right))
