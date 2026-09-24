"""Schema/projection boundaries independent of database services."""

from copy import deepcopy
from typing import get_args

import pytest
from pydantic import ValidationError

from app.recruiting.assessment_schemas import Language, SubmitBody, VersionBody
from app.recruiting.assessments import CONSENT_DIGEST, CONSENT_DOCUMENT
from app.recruiting.schemas import Filters
from app.recruiting.service import digest, matches


def content(*, synthetic=True, language="french", key="text-fixture", version=1):
    return dict(
        assessment_key=key,
        version=version,
        language=language,
        synthetic=synthetic,
        limitations="Synthetic engineering fixture; not validated language content.",
        tasks=[
            dict(
                id="choice",
                kind="single_choice",
                prompt="Synthetic choice?",
                choices=[dict(id="a", label="One"), dict(id="b", label="Two")],
                criteria={"accuracy": "Correct choice"},
            ),
            dict(
                id="text",
                kind="text",
                prompt="Synthetic bounded text",
                criteria={"clarity": "Clear text"},
            ),
        ],
        material=dict(
            answer_keys={"choice": "b"},
            rubric={
                "choice": {"accuracy": "KEY_CANARY_private_review"},
                "text": {"clarity": "RUBRIC_CANARY_private_review"},
            },
        ),
    )


def test_distinct_vocabulary_and_no_inference():
    assert set(get_args(Language)) == {"tunisianArabic", "formalArabic", "french", "arabizi"}
    for language in get_args(Language):
        assert not matches(
            {"languages": [language], "verified_languages": [language, "ar"]},
            {"reviewed_language": language},
        )
        assert matches({"reviewed_languages": [language]}, {"reviewed_language": language})
        for other in set(get_args(Language)) - {language}:
            assert not matches({"reviewed_languages": [other]}, {"reviewed_language": language})
    with pytest.raises(ValidationError):
        Filters(reviewed_language="ar")
    assert CONSENT_DIGEST == digest(CONSENT_DOCUMENT)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda b: b["material"]["answer_keys"].clear(),
        lambda b: b["material"]["answer_keys"].update(choice="unknown"),
        lambda b: b["material"]["rubric"]["text"].update(extra="secret"),
        lambda b: b["tasks"].append(deepcopy(b["tasks"][0])),
        lambda b: b.update(language="ar"),
        lambda b: b.update(synthetic="false"),
        lambda b: b.update(policy={"cooldown_hours": 0}),
        lambda b: b["tasks"][0].update(prompt="x" * 2001),
    ],
)
def test_invalid_assessment_content(mutation):
    body = content()
    mutation(body)
    with pytest.raises(ValidationError):
        VersionBody.model_validate(body)


def test_response_bounds_and_valid_fixture():
    VersionBody.model_validate(content())
    with pytest.raises(ValidationError):
        SubmitBody(command_key="submit", responses={"text": "x" * 4001})


def test_authority_settings_default_disabled_and_validate_language_scopes(settings):
    from uuid import uuid4

    from app.config import Settings

    assert settings.language_assessment_authority_workspace_id is None
    assert settings.language_assessment_reviewers == {}
    uid, wid = uuid4(), uuid4()
    values = settings.model_dump()
    configured = Settings(
        **(
            values
            | dict(
                language_assessment_authority_workspace_id=str(wid),
                language_assessment_reviewers={str(uid): ["french", "arabizi"]},
            )
        )
    )
    assert configured.language_assessment_authority_workspace_id == wid
    assert configured.language_assessment_reviewers == {uid: ["french", "arabizi"]}
    for reviewers in ({str(uid): ["ar"]}, {"not-a-uuid": ["french"]}):
        with pytest.raises(ValidationError):
            Settings(**(values | dict(language_assessment_reviewers=reviewers)))


@pytest.mark.parametrize("mutation", ["old", "missing", "raw", "wrong_type"])
def test_authenticated_manifest_rejects_missing_or_nonidentifier_revocations(tmp_path, mutation):
    import hashlib
    import hmac
    import json
    from uuid import uuid4

    from app.privacy_ops.restore import read_manifest

    manifest = dict(
        version=4,
        assessment_revocations=[],
        tombstones=[],
        holds=[],
        contact_holds=[],
        accounts=[],
        events=[],
    )
    if mutation == "old":
        manifest["version"] = 3
        del manifest["assessment_revocations"]
    elif mutation == "missing":
        del manifest["assessment_revocations"]
    elif mutation == "wrong_type":
        manifest["assessment_revocations"] = {}
    else:
        manifest["assessment_revocations"] = [
            dict(profile_id=str(uuid4()), grant_id=str(uuid4()), rationale="forbidden")
        ]
    key = b"synthetic-manifest-validation-key-32"
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    path = tmp_path / "signed-invalid.json"
    path.write_text(
        json.dumps(
            dict(manifest=manifest, signature=hmac.new(key, payload, hashlib.sha256).hexdigest())
        )
    )
    with pytest.raises(ValueError):
        read_manifest(path, key, hashlib.sha256(payload).hexdigest())


def test_all_new_routes_have_explicit_success_schemas():
    from app.recruiting.assessment_router import router

    for route in router.routes:
        assert route.response_model, route.path
