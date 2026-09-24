from uuid import uuid4

import pytest
from study_fixtures import blocks

from app.studies.methods import validate_structure


@pytest.mark.parametrize(
    "key,rule",
    [
        ("text", {"min_text_length": 20}),
        ("prototype", {"min_elapsed_ms": 1000}),
    ],
)
def test_pinned_quality_thresholds_are_supported(key, rule):
    definitions = blocks(str(uuid4()))
    assert validate_structure(definitions, ["fr", "ar"], {key: rule})


@pytest.mark.parametrize(
    "key,rule",
    [
        ("text", {"min_text_length": True}),
        ("text", {"min_text_length": 0}),
        ("text", {"min_text_length": 10001}),
        ("text", {"min_elapsed_ms": 1000}),
        ("prototype", {"min_elapsed_ms": -1}),
        ("prototype", {"min_elapsed_ms": "1000"}),
        ("prototype", {"min_elapsed_ms": 3600001}),
        ("single", {"min_text_length": 20}),
    ],
)
def test_quality_thresholds_reject_wrong_types_methods_and_bounds(key, rule):
    with pytest.raises(ValueError):
        validate_structure(blocks(str(uuid4())), ["fr", "ar"], {key: rule})
