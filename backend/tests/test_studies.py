import copy
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from study_fixtures import answer, blocks, ready_study

from app.auth.models import Membership
from app.common.errors import DomainError
from app.studies import methods, service
from app.studies.models import Launch, Study, StudyVersion
from app.studies.schemas import VersionBody

pytestmark = pytest.mark.db


@pytest.fixture
def study_scope(research_app):
    client, app, actor = research_app
    headers, user_id, workspace_id = actor()
    base = f"/api/v1/workspaces/{workspace_id}"
    fixture = ready_study(client, base, headers)
    return client, app, actor, headers, user_id, workspace_id, base, fixture


def test_publish_immutable_version_new_draft_and_duplicate_commands(study_scope, db_engine):
    client, _, _, headers, _, _, base, fixture = study_scope
    endpoint = fixture["endpoint"]
    assert client.post(endpoint + "/validate", headers=headers).json()["valid"]
    result = client.post(endpoint + "/publish", headers=headers, json={"expected_revision": 2})
    assert result.status_code == 200, result.text
    assert len(result.json()["content_hash"]) == 64
    assert (
        client.post(endpoint + "/publish", headers=headers, json={"expected_revision": 2}).json()
        == result.json()
    )
    assert client.put(endpoint, headers=headers, json=fixture["body"]).status_code == 409
    with Session(db_engine) as session, pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE study_versions SET blocks_json = '[]' WHERE id = :id"),
            {"id": fixture["version_id"]},
        )
    with Session(db_engine) as session, pytest.raises(DBAPIError):
        session.execute(
            text("DELETE FROM study_versions WHERE id = :id"), {"id": fixture["version_id"]}
        )
    idem = headers | {"Idempotency-Key": uuid4().hex}
    draft = client.post(endpoint + "/new-draft", headers=idem)
    assert draft.status_code == 201
    assert client.post(endpoint + "/new-draft", headers=idem).json() == draft.json()
    assert draft.json()["number"] == 2
    assert (
        client.get(endpoint, headers=headers).json()["content_hash"]
        == result.json()["content_hash"]
    )
    assert client.get(base + "/studies", headers=headers).json()["items"][0]["status"] == "ready"
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Launch)
                .where(Launch.version_id == UUID(fixture["version_id"]))
            )
            == 1
        )


@pytest.mark.parametrize("locale", ["fr", "ar"])
def test_all_core_methods_preview_no_side_effects(study_scope, db_engine, locale):
    client, _, _, headers, _, workspace_id, _, fixture = study_scope
    with Session(db_engine) as session:
        before = {
            name: session.execute(
                text(f'SELECT count(*) FROM "{name}" WHERE workspace_id = :id'),
                {"id": workspace_id},
            ).scalar()
            for name in ("jobs", "study_versions", "launches", "privacy_requests")
        }
    response = client.post(
        fixture["endpoint"] + "/preview", headers=headers, json={"locale": locale}
    )
    assert response.status_code == 200, response.text
    token = {"X-Preview-Token": response.json()["preview_token"]}
    answers = {}
    visited = []
    while True:
        step = client.post("/api/v1/study-preview", headers=token, json={"answers": answers})
        assert step.status_code == 200, step.text
        assert (
            "expected_option" not in step.text
            and "rules_json" not in step.text
            and "branches" not in step.text
        )
        data = step.json()
        assert data["preview"] and not data["persisted"] and not data["rewards"]
        if data["complete"]:
            break
        block = data["block"]
        assert (
            client.post("/api/v1/study-preview", headers=token, json={"answers": answers}).json()
            == data
        )
        visited.append(block["type"])
        answers[block["block_key"]] = answer(block, locale)
    assert set(visited) == methods.RENDERERS - frozenset(methods.advanced.VALUES)
    assert (
        client.get(f"/api/v1/study-preview/assets/{fixture['asset_id']}", headers=token).status_code
        == 200
    )
    assert client.get(f"/api/v1/study-preview/assets/{uuid4()}", headers=token).status_code == 404
    with Session(db_engine) as session:
        after = {
            name: session.execute(
                text(f'SELECT count(*) FROM "{name}" WHERE workspace_id = :id'),
                {"id": workspace_id},
            ).scalar()
            for name in before
        }
    assert before == after


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_key",
        "cycle",
        "dangling",
        "forward_source",
        "missing_locale",
        "rules_leak",
        "consent_missing",
        "bad_recall",
    ],
)
def test_publish_rejects_invalid_study(study_scope, mutation):
    client, _, _, headers, _, _, _, fixture = study_scope
    body = copy.deepcopy(fixture["body"])
    if mutation == "duplicate_key":
        body["blocks_json"][1]["block_key"] = "single"
    elif mutation in {"cycle", "dangling", "forward_source"}:
        body["blocks_json"][0]["branches"] = [
            {
                "source": "multi" if mutation == "forward_source" else "single",
                "operator": "eq",
                "value": "yes",
                "target": "single"
                if mutation == "cycle"
                else "missing"
                if mutation == "dangling"
                else "rating",
            }
        ]
    elif mutation == "missing_locale":
        body["blocks_json"][0]["prompt"].pop("ar")
    elif mutation == "rules_leak":
        body["rules_json"]["single"]["unrecognized_secret"] = True
    elif mutation == "consent_missing":
        body["consent_documents"] = {}
    elif mutation == "bad_recall":
        body["blocks_json"][5]["config"]["recall_block_ids"] = ["single"]
    assert client.put(fixture["endpoint"], headers=headers, json=body).status_code == 200
    assert (
        client.post(
            fixture["endpoint"] + "/publish", headers=headers, json={"expected_revision": 3}
        ).status_code
        == 422
    )


@pytest.mark.parametrize("kind", ["unknown", "survey.rating", "survey.single"])
def test_draft_rejects_unknown_or_invalid_method(study_scope, kind):
    client, _, _, headers, _, _, _, fixture = study_scope
    body = copy.deepcopy(fixture["body"])
    body["blocks_json"][0]["type"] = kind
    if kind == "survey.single":
        body["blocks_json"][0]["config"]["options"][1]["id"] = "yes"
    assert client.put(fixture["endpoint"], headers=headers, json=body).status_code == 422
    assert client.get(fixture["endpoint"], headers=headers).json()["revision"] == 2


def test_branch_routing_and_hidden_answer_rejection(study_scope):
    client, _, _, headers, _, _, _, fixture = study_scope
    body = copy.deepcopy(fixture["body"])
    body["blocks_json"][0]["branches"] = [
        {"source": "single", "operator": "eq", "value": "yes", "target": "rating"}
    ]
    assert client.put(fixture["endpoint"], headers=headers, json=body).status_code == 200
    token = client.post(
        fixture["endpoint"] + "/preview", headers=headers, json={"locale": "fr"}
    ).json()["preview_token"]
    preview_headers = {"X-Preview-Token": token}
    answers = {"single": {"status": "responded", "value": {"option_id": "yes"}}}
    assert (
        client.post(
            "/api/v1/study-preview", headers=preview_headers, json={"answers": answers}
        ).json()["block"]["block_key"]
        == "rating"
    )
    answers["multi"] = {"status": "responded", "value": {"option_ids": ["yes"]}}
    assert (
        client.post(
            "/api/v1/study-preview", headers=preview_headers, json={"answers": answers}
        ).status_code
        == 409
    )


@pytest.mark.parametrize("role", ["owner", "admin", "researcher", "reviewer", "viewer"])
def test_study_grant_role_matrix_and_revoke(study_scope, db_engine, role):
    client, _, actor, headers, _, workspace_id, base, fixture = study_scope
    target_headers, target_id, _ = actor(workspace_id, role)
    study_path = base + f"/studies/{fixture['study_id']}"
    assert client.get(study_path, headers=target_headers).status_code == 404
    with Session(db_engine) as session:
        member_id = str(
            session.scalar(select(Membership.id).where(Membership.user_id == target_id))
        )
    grant = client.post(
        study_path + "/grants",
        headers=headers,
        json={"membership_id": member_id, "capabilities": ["read"]},
    )
    assert grant.status_code == 201
    assert client.get(study_path, headers=target_headers).status_code == 200
    assert client.get(fixture["endpoint"], headers=target_headers).status_code in {403, 404}
    capabilities = client.post(
        study_path + "/grants",
        headers=headers,
        json={"membership_id": member_id, "capabilities": ["read", "edit", "preview"]},
    )
    assert capabilities.status_code == (201 if role in {"owner", "admin", "researcher"} else 403)
    assert (
        client.delete(study_path + f"/grants/{grant.json()['id']}", headers=headers).status_code
        == 204
    )
    assert client.get(study_path, headers=target_headers).status_code == 404


def test_cross_workspace_guess_clone_and_unauthenticated(study_scope):
    client, _, actor, headers, _, _, _, fixture = study_scope
    other_headers, _, other_workspace = actor()
    assert client.get(fixture["endpoint"], headers=other_headers).status_code == 404
    assert client.get(fixture["endpoint"]).status_code == 401
    assert (
        client.post(
            fixture["endpoint"] + "/clone",
            headers=other_headers | {"Idempotency-Key": uuid4().hex},
            json=fixture["study_body"],
        ).status_code
        == 404
    )
    idem = headers | {"Idempotency-Key": uuid4().hex}
    cloned = client.post(fixture["endpoint"] + "/clone", headers=idem, json=fixture["study_body"])
    assert cloned.status_code == 201
    assert (
        client.post(fixture["endpoint"] + "/clone", headers=idem, json=fixture["study_body"]).json()
        == cloned.json()
    )
    assert (
        client.post(
            f"/api/v1/workspaces/{other_workspace}/studies",
            headers=other_headers | {"Idempotency-Key": uuid4().hex},
            json=fixture["study_body"],
        ).status_code
        == 404
    )


def test_concurrent_edits_and_publish_single_result(study_scope, db_engine):
    _, _, _, _, user_id, workspace_id, _, fixture = study_scope

    def edit(_):
        try:
            with Session(db_engine) as session, session.begin():
                service.edit_version(
                    session,
                    workspace_id,
                    user_id,
                    UUID(fixture["study_id"]),
                    UUID(fixture["version_id"]),
                    VersionBody.model_validate(fixture["body"]),
                )
                return "ok"
        except DomainError as error:
            return error.code

    with ThreadPoolExecutor(2) as executor:
        assert sorted(executor.map(edit, range(2))) == ["REVISION_CONFLICT", "ok"]

    def publish(_):
        with Session(db_engine) as session, session.begin():
            return service.publish(
                session,
                workspace_id,
                user_id,
                UUID(fixture["study_id"]),
                UUID(fixture["version_id"]),
                3,
            ).content_hash

    with ThreadPoolExecutor(2) as executor:
        assert len(set(executor.map(publish, range(2)))) == 1


@pytest.mark.parametrize("change", ["draft", "withdrawal", "logout", "close"])
def test_preview_revocation(study_scope, change):
    client, _, _, headers, _, _, base, fixture = study_scope
    response = client.post(fixture["endpoint"] + "/preview", headers=headers, json={"locale": "fr"})
    token = {"X-Preview-Token": response.json()["preview_token"]}
    if change == "draft":
        assert (
            client.put(fixture["endpoint"], headers=headers, json=fixture["body"]).status_code
            == 200
        )
    elif change == "withdrawal":
        assert (
            client.post(
                base + "/privacy-requests",
                headers=headers,
                json={"kind": "withdrawal", "request_key": "withdraw"},
            ).status_code
            == 202
        )
    elif change == "logout":
        assert (
            client.post(
                "/api/v1/auth/logout", headers=headers | {"Origin": "http://localhost:8080"}
            ).status_code
            == 204
        )
    elif change == "close":
        assert (
            client.patch(
                base + f"/studies/{fixture['study_id']}/state",
                headers=headers,
                json={"status": "closed"},
            ).status_code
            == 200
        )
    assert client.post("/api/v1/study-preview", headers=token, json={}).status_code in {401, 403}


def test_revoked_source_asset_and_missing_renderer_deny_publication(study_scope, monkeypatch):
    client, _, _, headers, _, _, _, fixture = study_scope
    monkeypatch.setattr(methods, "RENDERERS", frozenset({"survey.single"}))
    assert (
        client.post(
            fixture["endpoint"] + "/publish", headers=headers, json={"expected_revision": 2}
        ).status_code
        == 422
    )


def test_db_rejects_cross_workspace_version_and_unpublished_launch(study_scope, db_engine):
    _, _, actor, _, _, workspace_id, _, fixture = study_scope
    _, _, other = actor()
    with Session(db_engine) as session, pytest.raises(DBAPIError):
        session.add(
            StudyVersion(workspace_id=other, study_id=UUID(fixture["study_id"]), number=100)
        )
        session.flush()
    with Session(db_engine) as session, pytest.raises(DBAPIError):
        session.add(Launch(workspace_id=workspace_id, version_id=UUID(fixture["version_id"])))
        session.flush()
    with Session(db_engine) as session:
        assert session.get(Study, UUID(fixture["study_id"])).status == "draft"


@pytest.mark.parametrize("method_index", range(8))
def test_each_method_config_answer_and_reducer(method_index):
    block = methods.parse_block(blocks(str(uuid4()))[method_index])
    value = answer(block.model_dump())
    accepted = methods.validate_answer(block, value, ["fr", "ar"], "assignment", "attempt")
    result = methods.reduce_answers(block, [accepted])
    assert result["responded"] == 1 and result["source_unit"] == "answer"
    assert methods.reduce_answers(block, [])["denominator"] == 0
    with pytest.raises(ValueError):
        methods.validate_answer(
            block, {"status": "skipped", "value": None}, ["fr"], "assignment", "attempt"
        )
    assert (
        methods.validate_answer(
            block, {"status": "unable", "value": None, "reason_code": "accessibility"}, ["fr"]
        )["status"]
        == "unable"
    )
    with pytest.raises(ValueError):
        methods.validate_answer(
            block,
            {"status": "responded", "value": {"unknown": True}},
            ["fr"],
            "assignment",
            "attempt",
        )


@pytest.mark.parametrize(
    "index,value",
    [
        (0, {"option_id": "unknown"}),
        (1, {"option_ids": ["yes", "yes"]}),
        (2, {"value": True}),
        (2, {"value": 99}),
        (3, {"text": " ", "language": "fr"}),
        (3, {"text": "\ud800", "language": "fr"}),
        (3, {"text": "valid", "language": "en"}),
        (
            4,
            {
                "assignment_id": "wrong",
                "decision": "tie",
                "selected_variant_id": None,
                "reason": {"text": "valid", "language": "fr"},
            },
        ),
        (5, {"attempt_id": "wrong", "visible_ms": 5000, "interrupted": False}),
        (7, {"outcome": "completed", "elapsed_ms": 1, "termination_reason": "timeout"}),
    ],
)
def test_invalid_values(index, value):
    block = methods.parse_block(blocks(str(uuid4()))[index])
    with pytest.raises(ValueError):
        methods.validate_answer(
            block, {"status": "responded", "value": value}, ["fr"], "assignment", "attempt"
        )


def test_external_prototype_authorization_and_no_claimed_instrumentation():
    block = blocks(str(uuid4()))[-1]
    block["config"]["target"] = {
        "mode": "external_link",
        "url": "https://example.com/prototype",
        "authorization_ref": "approved-test",
    }
    with pytest.raises(ValueError):
        methods.validate_structure([block], ["fr", "ar"], {})
    approved = {
        "prototype": {
            "authorization": {
                "reference": "approved-test",
                "build_revision": "build-1",
                "approved": True,
            }
        }
    }
    methods.validate_structure([block], ["fr", "ar"], approved)
    for url in (
        "http://example.com",
        "https://127.0.0.1",
        "https://localhost",
        "javascript:alert(1)",
    ):
        invalid = copy.deepcopy(block)
        invalid["config"]["target"]["url"] = url
        with pytest.raises(ValueError):
            methods.parse_block(invalid)
