from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.evaluation.schemas import DatasetBody, OutcomeBody, Scenario, Schema
from app.evaluation.validation import content_identity, validate_outcome

pytestmark = pytest.mark.unit


def schema(task="classification", **kw):
    return Schema(
        task=task,
        instructions="Human instructions",
        instructions_version="v1",
        labels=[{"id": "yes", "label": "Yes"}],
        **kw,
    ).model_dump()


def outcome(**kw):
    return OutcomeBody(reason={"text": "Independent human rationale", "language": "fr"}, **kw)


def dataset_body(study_id=None, task="classification"):
    return {
        "study_id": str(study_id or uuid4()),
        "key": "dataset",
        "version": 1,
        "rights": {
            "owner": "Customer",
            "compensation_terms": "Agreed volunteer terms",
            "reuse_permission": True,
            "training_permission": True,
            "label_license": "Customer internal use",
            "consent_scope": "Fictional research only",
        },
        "schema": schema(task),
        "items": [
            {"key": "one", "source": {"text": "A😀بé", "language": "fr"}, "partition": "evaluation"}
        ],
    }


@pytest.mark.parametrize(
    "annotations",
    [
        [{"label_id": "unknown"}],
        [{"label_id": "yes"}, {"label_id": "yes"}],
        [{"label_id": "yes", "start": 0}],
        [{"label_id": "yes", "polygon": [[0, 0], [1, 0], [0, 1]]}],
    ],
)
def test_classification_invalid(annotations):
    with pytest.raises(ValueError):
        validate_outcome(schema(), {"text": "x"}, outcome(annotations=annotations))


def test_unicode_spans_exclusive_codepoints_and_overlap():
    source = {"text": "A😀بé"}
    validate_outcome(
        schema("text_spans"),
        source,
        outcome(annotations=[{"label_id": "yes", "start": 1, "end": 2}]),
    )
    for spans in [[(1, 5)], [(2, 2)], [(0, 2), (1, 3)]]:
        with pytest.raises(ValueError):
            validate_outcome(
                schema("text_spans"),
                source,
                outcome(annotations=[{"label_id": "yes", "start": a, "end": b} for a, b in spans]),
            )


@pytest.mark.parametrize(
    "polygon",
    [
        [[0, 0], [1, 1], [0, 1], [1, 0]],
        [[0, 0], [0, 0], [1, 1]],
        [[0, 0], [2, 0], [0, 1]],
        [[0, 0], [float("nan"), 0], [0, 1]],
        [[0, 0], [0.5, 0], [1, 0]],
    ],
)
def test_invalid_geometry(polygon):
    with pytest.raises(ValueError):
        validate_outcome(
            schema("image_polygons"),
            {},
            outcome(annotations=[{"label_id": "yes", "polygon": polygon}]),
        )


def test_contained_and_touching_polygons_rejected():
    for second in [[[0.1, 0.1], [0.2, 0.1], [0.1, 0.2]], [[0, 0], [0.2, 0], [0, 0.2]]]:
        with pytest.raises(ValueError):
            validate_outcome(
                schema("image_polygons"),
                {},
                outcome(
                    annotations=[
                        {"label_id": "yes", "polygon": [[0, 0], [1, 0], [0, 1]]},
                        {"label_id": "yes", "polygon": second},
                    ]
                ),
            )


@pytest.mark.parametrize("choice", ["left", "right", "tie", "both_bad", "cannot_judge"])
def test_pairwise_all_choices(choice):
    s = schema(
        "pairwise",
        dimensions=[{"id": "quality", "min": 1, "max": 5}],
        rubric_version="v1",
        language_basis="French fluency",
    )
    ratings = (
        []
        if choice == "cannot_judge"
        else [{"candidate_id": c, "dimension_id": "quality", "value": 3} for c in ["left", "right"]]
    )
    validate_outcome(s, {}, outcome(choice=choice, ratings=ratings))
    with pytest.raises(ValueError):
        validate_outcome(
            s,
            {},
            outcome(
                choice=choice,
                ratings=ratings + [{"candidate_id": "left", "dimension_id": "quality", "value": 6}],
            ),
        )


@pytest.mark.parametrize(
    "patch",
    [
        {"dimensions": [{"id": "q", "min": 2, "max": 1}]},
        {"dimensions": [{"id": "q", "min": 1, "max": 5}] * 2},
        {"dimensions": []},
        {"language_basis": None},
    ],
)
def test_rubric_validation(patch):
    with pytest.raises(ValidationError):
        Schema(
            task="pairwise",
            instructions="Instruction",
            instructions_version="v1",
            **(
                {
                    "dimensions": [{"id": "q", "min": 1, "max": 5}],
                    "rubric_version": "v1",
                    "language_basis": "French",
                }
                | patch
            ),
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]",
        "https://example.com/redirect",
        "file:///etc/passwd",
        "http://2130706433",
        "http://localhost",
        "https://user:pass@allowed.example",
    ],
)
def test_all_adapter_and_url_modes_disabled(url):
    with pytest.raises(ValidationError):
        Scenario(
            revision="v1",
            business_policy_version="v1",
            instructions="Fictional task",
            approved=True,
            fictional_inputs_only=True,
            mode="adapter",
            adapter_ref=url,
            max_turns=4,
            max_duration_ms=1000,
        )


def test_sandbox_limits_and_private_data():
    s = Scenario(
        revision="v1",
        business_policy_version="v1",
        instructions="Fictional task",
        approved=True,
        fictional_inputs_only=True,
        max_turns=2,
        max_duration_ms=1000,
        max_characters=100,
    ).model_dump()
    body = {
        "outcome": "infrastructure_failure",
        "turns": [{"role": "user", "text": "Fictional order", "language": "fr"}],
        "duration_ms": 500,
        "scenario_revision": "v1",
        "fictional_confirmation": True,
    }
    validate_outcome(schema("sandbox"), {"scenario": s}, outcome(**body))
    for patch in [
        {"duration_ms": 1001},
        {"scenario_revision": "v2"},
        {"fictional_confirmation": None},
        {"turns": []},
        {"turns": [{"role": "user", "text": "me@example.com", "language": "en"}]},
    ]:
        with pytest.raises(ValueError):
            validate_outcome(schema("sandbox"), {"scenario": s}, outcome(**(body | patch)))


def test_content_identity_not_caller_ids_versions_model_or_language():
    original = {"text": "café", "language": "fr", "key": str(uuid4()), "candidates": ["old"]}
    changed = {"text": "cafe\u0301", "language": "en", "key": str(uuid4()), "candidates": ["new"]}
    assert content_identity(original) == content_identity(changed)


@pytest.mark.parametrize(
    "patch",
    [
        {"min_annotations": True},
        {"max_annotations": 101},
        {"min_annotations": 4, "max_annotations": 3},
    ],
)
def test_strict_annotation_bounds(patch):
    with pytest.raises(ValidationError):
        schema(**patch)


def test_no_fake_human_or_extra_votes():
    with pytest.raises(ValidationError):
        OutcomeBody(
            reason={"text": "Generated", "language": "en"}, provenance="human", ai_vote=True
        )
    b = dataset_body()
    b["items"].append(deepcopy(b["items"][0]))
    with pytest.raises(ValidationError):
        DatasetBody.model_validate(b)
