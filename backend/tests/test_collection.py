from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.collection.schemas import AnswerBody, StartBody
from app.collection.service import digest, path, project
from app.studies.methods import parse_block, validate_answer


def block(key="first", branches=None, required=True):
    return parse_block(
        {
            "block_key": key,
            "schema_version": 1,
            "type": "survey.single",
            "required": required,
            "prompt": {"fr": "Question"},
            "branches": branches or [],
            "config": {
                "options": [
                    {"id": "yes", "label": {"fr": "Oui"}},
                    {"id": "no", "label": {"fr": "Non"}},
                ]
            },
        }
    )


def test_path_stops_before_hidden_answers_and_branch_edits():
    blocks = [
        block(branches=[{"source": "first", "operator": "eq", "value": "yes", "target": "last"}]),
        block("hidden"),
        block("last"),
    ]
    assert path(blocks, {}) == (["first"], "first")
    answers = {"first": {"value": {"option_id": "yes"}}, "hidden": {"value": {"option_id": "no"}}}
    assert path(blocks, answers) == (["first", "last"], "last")
    answers["first"]["value"]["option_id"] = "no"
    assert path(blocks, answers) == (["first", "hidden", "last"], "last")


def test_safe_projection_never_leaks_branch_condition():
    row = SimpleNamespace(locale="fr")
    projected = project(
        row, block(branches=[{"source": "first", "operator": "eq", "value": "yes", "target": None}])
    )
    assert "branches" not in projected
    assert projected["prompt"] == "Question"
    assert projected["config"]["options"][0]["label"] == "Oui"


def test_canonical_answer_schema_and_strict_revision():
    body = {
        "schema_version": 1,
        "expected_revision": 0,
        "client_event_id": str(uuid4()),
        "status": "responded",
        "value": {"option_id": "yes"},
    }
    assert AnswerBody.model_validate(body).answer["status"] == "responded"
    for extra in ({"expected_revision": "0"}, {"assignment": "forged"}, {"schema_version": 2}):
        with pytest.raises(ValidationError):
            AnswerBody.model_validate(body | extra)


@pytest.mark.parametrize(
    "status,reason,valid",
    [("skipped", None, False), ("unable", "technical", True), ("unable", None, False)],
)
def test_required_skip_is_not_inability(status, reason, valid):
    data = {"status": status, "value": None, "reason_code": reason}
    if valid:
        assert validate_answer(block(), data, ["fr"])["status"] == status
    else:
        with pytest.raises(ValueError):
            validate_answer(block(), data, ["fr"])


@pytest.mark.parametrize("text,valid", [("عربي café", True), ("\ud800", False), ("  ", False)])
def test_unicode_boundary(text, valid):
    b = parse_block(
        {
            "block_key": "text",
            "schema_version": 1,
            "type": "survey.text",
            "required": True,
            "prompt": {"fr": "Text"},
            "config": {"min_length": 1, "max_length": 50},
        }
    )
    data = {"status": "responded", "value": {"text": text, "language": "fr"}}
    if valid:
        assert validate_answer(b, data, ["fr"])["value"]["text"] == text
    else:
        with pytest.raises(ValueError):
            validate_answer(b, data, ["fr"])


def test_digests_are_canonical_and_do_not_store_secrets():
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})
    assert len(digest("secret")) == 64


def test_capability_requires_long_urlsafe_secret():
    body = {
        "invitation_token": "x" * 32,
        "capability": "x" * 43,
        "locale": "fr",
        "document_id": str(uuid4()),
        "presented_digest": "a" * 64,
        "consent": "granted",
    }
    StartBody.model_validate(body)
    with pytest.raises(ValidationError):
        StartBody.model_validate(body | {"capability": "short"})
