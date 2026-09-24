"""Full HTTP and real PostgreSQL contracts; only dedicated guarded test DB."""

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from study_fixtures import ready_study
from test_evaluation import dataset_body

from app.auth.models import Membership
from app.common.errors import DomainError
from app.evaluation import privacy, service
from app.evaluation.models import EvaluationAssignment, EvaluationDataset, EvaluationOutcome
from app.evaluation.schemas import AssignmentBody, OutcomeBody
from app.studies.models import StudyGrant

pytestmark = [pytest.mark.db, pytest.mark.api]


@pytest.fixture
def evaluation(research_app, db_engine):
    client, app, actor = research_app
    headers, owner, wid = actor()
    base = f"/api/v1/workspaces/{wid}"
    study = ready_study(client, base, headers)
    sid = UUID(study["study_id"])
    reviewers = []
    for _ in range(4):
        h, uid, _ = actor(wid, "reviewer")
        with Session(db_engine) as s, s.begin():
            member = s.scalar(
                select(Membership).where(Membership.workspace_id == wid, Membership.user_id == uid)
            )
            s.add(
                StudyGrant(
                    workspace_id=wid,
                    study_id=sid,
                    membership_id=member.id,
                    capabilities=["read", "review"],
                )
            )
        reviewers.append((h, uid))
    root = base + "/evaluation"
    body = dataset_body(sid)
    r = client.post(root + "/datasets", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return client, root, headers, owner, wid, sid, reviewers, r.json(), body


def assign_api(e, index, kind="independent"):
    client, root, headers, owner, wid, sid, reviewers, ds, body = e
    r = client.post(
        root + f"/datasets/{ds['id']}/assignments",
        headers=headers,
        json={
            "item_id": ds["items"][0]["id"],
            "reviewer_id": str(reviewers[index][1]),
            "kind": kind,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def submit_api(e, index, assignment, label=True):
    client, root, _, _, _, _, reviewers, _, _ = e
    r = client.post(
        root + f"/assignments/{assignment}/outcome",
        headers=reviewers[index][0],
        json={
            "reason": {"text": "Reviewed independently", "language": "fr"},
            "annotations": [{"label_id": "yes"}] if label else [],
        },
    )
    assert r.status_code == 201, r.text
    return r


def test_http_independence_adjudication_reviewed_export(evaluation):
    e = evaluation
    client, root, h, owner, wid, sid, reviewers, ds, body = e
    first = assign_api(e, 0)
    # No read by owner, other reviewer, or unauthenticated caller.
    assert client.get(root + f"/assignments/{first}", headers=h).status_code == 403
    assert client.get(root + f"/assignments/{first}").status_code == 401
    before = client.get(root + f"/assignments/{first}", headers=reviewers[0][0]).json()
    assert "originals" not in before
    submit_api(e, 0, first)
    second = assign_api(e, 1)
    other = client.get(root + f"/assignments/{second}", headers=reviewers[1][0]).json()
    assert "originals" not in other and other["outcome"] is None
    submit_api(e, 1, second, False)
    assert (
        client.post(
            root + f"/datasets/{ds['id']}/assignments",
            headers=h,
            json={
                "item_id": ds["items"][0]["id"],
                "reviewer_id": str(reviewers[0][1]),
                "kind": "adjudication",
            },
        ).status_code
        == 409
    )
    assert client.get(root + f"/datasets/{ds['id']}/export", headers=h).status_code == 409
    third = assign_api(e, 2, "adjudication")
    assert (
        len(client.get(root + f"/assignments/{third}", headers=reviewers[2][0]).json()["originals"])
        == 2
    )
    submit_api(e, 2, third)
    r = client.post(
        root + f"/datasets/{ds['id']}/export-review",
        headers=h,
        json={"reason": {"text": "Rights and originals reviewed", "language": "fr"}},
    )
    assert r.status_code == 201, r.text
    exported = client.get(root + f"/datasets/{ds['id']}/export", headers=h)
    assert exported.status_code == 200, exported.text
    assert len(exported.json()["items"][0]["labels"]) == 3
    assert exported.json()["rights"] == body["rights"]
    report = client.get(root + f"/datasets/{ds['id']}/report", headers=h).json()
    assert (
        report["independently_double_labeled_items"] == 1 and report["exact_agreement_items"] == 0
    )
    assert report["winner"] is None
    assert (
        client.post(
            root + f"/assignments/{first}/outcome",
            headers=reviewers[0][0],
            json={"reason": {"text": "overwrite", "language": "en"}},
        ).status_code
        == 409
    )


def test_source_partition_dedupe_across_versions_and_uuids(evaluation):
    client, root, h, _, _, _, _, ds, body = evaluation
    body["version"] = 2
    body["items"][0]["key"] = uuid4().hex
    body["items"][0]["partition"] = "train"
    assert client.post(root + "/datasets", headers=h, json=body).status_code == 409
    body["key"] = "new-dataset"
    body["version"] = 1
    assert client.post(root + "/datasets", headers=h, json=body).status_code == 409
    body["items"][0]["partition"] = "evaluation"
    assert client.post(root + "/datasets", headers=h, json=body).status_code == 201


def test_assignment_and_submission_races(evaluation, db_engine):
    e = evaluation
    _, _, _, owner, wid, _, reviewers, ds, _ = e

    def create(_):
        try:
            with Session(db_engine) as s, s.begin():
                service.assign(
                    s,
                    wid,
                    owner,
                    UUID(ds["id"]),
                    AssignmentBody(item_id=ds["items"][0]["id"], reviewer_id=reviewers[0][1]),
                )
            return "ok"
        except DomainError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(create, range(2))) == ["conflict", "ok"]
    with Session(db_engine) as s:
        aid = s.scalar(
            select(EvaluationAssignment.id).where(
                EvaluationAssignment.item_id == UUID(ds["items"][0]["id"])
            )
        )

    def submit(_):
        try:
            with Session(db_engine) as s, s.begin():
                service.submit(
                    s,
                    wid,
                    reviewers[0][1],
                    aid,
                    OutcomeBody(reason={"text": "Human", "language": "en"}),
                )
            return "ok"
        except DomainError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, range(2))) == ["ok", "ok"]
    with Session(db_engine) as s:
        assert (
            len(
                s.scalars(
                    select(EvaluationOutcome).where(EvaluationOutcome.assignment_id == aid)
                ).all()
            )
            == 1
        )


def test_db_immutable_and_privacy_cascades(evaluation, db_engine):
    e = evaluation
    _, _, _, owner, wid, sid, reviewers, ds, _ = e
    aid = assign_api(e, 0)
    submit_api(e, 0, aid)
    for table, ident, column, value in [
        ("evaluation_datasets", ds["id"], "key", "'mutated'"),
        ("evaluation_items", ds["items"][0]["id"], "source", "'{}'::jsonb"),
        ("evaluation_assignments", aid, "candidate_order", "'[1,0]'::jsonb"),
    ]:
        with pytest.raises(DBAPIError), Session(db_engine) as s, s.begin():
            s.execute(text(f"UPDATE {table} SET {column}={value} WHERE id=:id"), {"id": ident})
    with Session(db_engine) as s, s.begin():
        assert (
            privacy.subject_data(s, wid, reviewers[0][1])[0]["outcome"]["provenance"]
            == "authenticated_human"
        )
        from app.common.privacy_models import PrivacyRestriction

        s.add(PrivacyRestriction(workspace_id=wid, subject_id=reviewers[0][1]))
        s.flush()
        assert privacy.purge_subject(s, wid, reviewers[0][1]) == 1
        assert s.get(EvaluationAssignment, UUID(aid)) is None
        assert not s.scalar(
            select(EvaluationOutcome.id).where(EvaluationOutcome.assignment_id == UUID(aid))
        )
        s.add(PrivacyRestriction(workspace_id=wid, subject_id=owner))
        s.flush()
        assert privacy.purge_studies(s, wid, [sid]) == 1
        assert s.get(EvaluationDataset, UUID(ds["id"])) is None


def test_pairwise_blind_stable_ties_and_no_fake_votes(evaluation):
    e = evaluation
    client, root, h, owner, wid, sid, reviewers, ds, body = e
    body["key"] = "pairwise"
    body["schema"].update(
        task="pairwise",
        dimensions=[{"id": "quality", "min": 1, "max": 5}],
        rubric_version="v1",
        language_basis="French readability",
    )
    body["items"][0]["source"].update(
        testcase="Approved fictional greeting",
        candidates=[
            {"text": "Bonjour", "model_revision": "secret-model-A"},
            {"text": "Salut", "model_revision": "secret-model-B"},
        ],
    )
    r = client.post(root + "/datasets", headers=h, json=body)
    assert r.status_code == 201, r.text
    ds = r.json()
    e = (client, root, h, owner, wid, sid, reviewers, ds, body)
    aid = assign_api(e, 0)
    url = root + f"/assignments/{aid}"
    one = client.get(url, headers=reviewers[0][0])
    two = client.get(url, headers=reviewers[0][0])
    assert one.json() == two.json()
    assert "secret-model" not in one.text and "candidate_order" not in one.text
    payload = {
        "reason": {"text": "Equivalent", "language": "fr"},
        "choice": "tie",
        "ratings": [
            {"candidate_id": c, "dimension_id": "quality", "value": 3} for c in ["left", "right"]
        ],
    }
    assert (
        client.post(
            url + "/outcome", headers=reviewers[0][0], json=payload | {"provenance": "ai"}
        ).status_code
        == 422
    )
    assert client.post(url + "/outcome", headers=reviewers[0][0], json=payload).status_code == 201
    report = client.get(root + f"/datasets/{ds['id']}/report", headers=h).json()
    assert (
        report["independent_choices"]["tie"] == 1
        and report["judged_decisions"] == 1
        and report["winner"] is None
    )


def test_live_role_revocation_and_foreign_workspace(evaluation, db_engine, research_app):
    e = evaluation
    client, root, h, owner, wid, sid, reviewers, ds, body = e
    aid = assign_api(e, 0)
    _, _, actor = research_app
    foreign, _, _ = actor()
    assert client.get(root + f"/datasets/{ds['id']}", headers=foreign).status_code in {403, 404}
    with Session(db_engine) as s, s.begin():
        member = s.scalar(
            select(Membership).where(
                Membership.workspace_id == wid, Membership.user_id == reviewers[0][1]
            )
        )
        grant = s.scalar(
            select(StudyGrant).where(
                StudyGrant.study_id == sid, StudyGrant.membership_id == member.id
            )
        )
        from app.auth.security import utcnow

        grant.revoked_at = utcnow()
    assert client.get(root + f"/assignments/{aid}", headers=reviewers[0][0]).status_code == 404


@pytest.mark.parametrize(
    "task,bad",
    [
        ("classification", {"annotations": [{"label_id": "missing"}]}),
        ("classification", {"annotations": [{"label_id": "yes"}] * 2}),
        ("text_spans", {"annotations": [{"label_id": "yes", "start": 0, "end": 99}]}),
        ("text_spans", {"annotations": [{"label_id": "yes", "start": True, "end": 2}]}),
        ("classification", {"choice": "tie"}),
        ("classification", {"ai_vote": True}),
    ],
)
def test_http_rejects_invalid_outcomes(evaluation, task, bad):
    e = evaluation
    client, root, h, owner, wid, sid, reviewers, ds, body = e
    body["key"] = "invalid-" + task
    body["schema"]["task"] = task
    r = client.post(root + "/datasets", headers=h, json=body)
    assert r.status_code == 201, r.text
    e = (client, root, h, owner, wid, sid, reviewers, r.json(), body)
    aid = assign_api(e, 0)
    r = client.post(
        root + f"/assignments/{aid}/outcome",
        headers=reviewers[0][0],
        json={"reason": {"text": "Human rationale", "language": "fr"}} | bad,
    )
    assert r.status_code == 422, r.text


def test_http_manual_sandbox_approval_revision_and_infrastructure(evaluation):
    e = evaluation
    client, root, h, owner, wid, sid, reviewers, ds, body = e
    body["key"] = "sandbox"
    body["schema"]["task"] = "sandbox"
    body["items"][0]["source"]["scenario"] = {
        "revision": "r1",
        "business_policy_version": "p1",
        "instructions": "Use fictional order only",
        "approved": True,
        "fictional_inputs_only": True,
        "max_turns": 2,
        "max_duration_ms": 1000,
    }
    r = client.post(root + "/datasets", headers=h, json=body)
    assert r.status_code == 201, r.text
    ds = r.json()
    e = (client, root, h, owner, wid, sid, reviewers, ds, body)
    payload = {
        "reason": {"text": "Simulator unavailable; not bot failure", "language": "en"},
        "outcome": "infrastructure_failure",
        "turns": [{"role": "user", "text": "Fictional order zero", "language": "en"}],
        "duration_ms": 100,
        "scenario_revision": "r1",
        "fictional_confirmation": True,
    }
    for n in range(3):
        aid = assign_api(e, n, "adjudication" if n == 2 else "independent")
        url = root + f"/assignments/{aid}/outcome"
        if n == 0:
            for patch in [
                {"scenario_revision": "r2"},
                {"duration_ms": 1001},
                {"turns": [{"role": "assistant", "text": "real@example.com", "language": "en"}]},
                {"fictional_confirmation": None},
            ]:
                assert (
                    client.post(url, headers=reviewers[n][0], json=payload | patch).status_code
                    == 422
                )
        r = client.post(url, headers=reviewers[n][0], json=payload)
        assert r.status_code == 201, r.text
        assert r.json()["body"]["transcript_provenance"] == "participant_supplied_unverified"
    report = client.get(root + f"/datasets/{ds['id']}/report", headers=h).json()
    assert (
        report["sandbox_evaluable_attempts"] == 0
        and report["sandbox_infrastructure_failures"] == 1
        and report["sandbox_reviewed_success"] == 0
    )
    for mode in ["adapter", "url"]:
        body["key"] = mode
        body["items"][0]["source"]["scenario"]["mode"] = mode
        body["items"][0]["source"]["scenario"]["adapter_ref"] = "http://169.254.169.254/"
        assert client.post(root + "/datasets", headers=h, json=body).status_code == 422


def test_http_png_scoped_identity_and_geometry(evaluation, research_app):
    from research_support import upload

    e = evaluation
    client, root, h, owner, wid, sid, reviewers, ds, body = e
    base = root.removesuffix("/evaluation")
    asset = upload(client, base, h)["asset"]["id"]
    body["key"] = "polygons"
    body["schema"]["task"] = "image_polygons"
    body["items"][0]["source"]["asset_ref"] = {"asset_id": asset, "asset_version": 1}
    r = client.post(root + "/datasets", headers=h, json=body)
    assert r.status_code == 201, r.text
    e = (client, root, h, owner, wid, sid, reviewers, r.json(), body)
    aid = assign_api(e, 0)
    image = client.get(root + f"/assignments/{aid}/image", headers=reviewers[0][0])
    assert image.status_code == 200 and image.headers["content-type"] == "image/png"
    assert (
        client.get(root + f"/assignments/{aid}/image", headers=reviewers[1][0]).status_code == 403
    )
    r = client.post(
        root + f"/assignments/{aid}/outcome",
        headers=reviewers[0][0],
        json={
            "reason": {"text": "Triangle identified", "language": "fr"},
            "annotations": [{"label_id": "yes", "polygon": [[0, 0], [1, 0], [0, 1]]}],
        },
    )
    assert r.status_code == 201, r.text
    # Separate uploaded asset ID, same PNG checksum, changed caption: still cannot leak split.
    duplicate = upload(client, base, h)["asset"]["id"]
    body["key"] = "new-image"
    body["items"][0]["key"] = uuid4().hex
    body["items"][0]["source"]["asset_ref"]["asset_id"] = duplicate
    body["items"][0]["source"]["text"] = "Changed caption"
    body["items"][0]["partition"] = "train"
    assert client.post(root + "/datasets", headers=h, json=body).status_code == 409


def test_source_split_race_new_versions(evaluation, db_engine):
    from app.evaluation.schemas import DatasetBody

    e = evaluation
    _, _, _, owner, wid, sid, _, _, body = e

    def create(partition):
        from copy import deepcopy

        b = deepcopy(body)
        b["key"] = "racing-" + partition
        b["items"][0]["source"]["text"] = "brand new identical source"
        b["items"][0]["partition"] = partition
        try:
            with Session(db_engine) as s, s.begin():
                service.create_dataset(s, wid, owner, DatasetBody.model_validate(b))
            return "ok"
        except DomainError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(create, ["train", "evaluation"])) == ["conflict", "ok"]


def test_assignment_issuer_requires_administration(evaluation):
    client, root, h, owner, wid, sid, reviewers, ds, body = evaluation
    response = client.post(
        root + f"/datasets/{ds['id']}/assignments",
        headers=reviewers[0][0],
        json={"item_id": ds["items"][0]["id"], "reviewer_id": str(reviewers[0][1])},
    )
    assert response.status_code == 403


def test_exact_http_outcome_retry_before_and_after_export_seal(evaluation):
    e = evaluation
    client, root, h, owner, wid, sid, reviewers, ds, body = e
    aid = assign_api(e, 0)
    first = submit_api(e, 0, aid).json()
    assert submit_api(e, 0, aid).json() == first
    submit_api(e, 1, assign_api(e, 1))
    submit_api(e, 2, assign_api(e, 2, "adjudication"))
    response = client.post(
        root + f"/datasets/{ds['id']}/export-review",
        headers=h,
        json={"reason": {"text": "Reviewed all originals", "language": "en"}},
    )
    assert response.status_code == 201
    assert submit_api(e, 0, aid).json() == first


def test_creator_restriction_blocks_existing_snapshot_immediately(evaluation, db_engine):
    from app.common.privacy_models import PrivacyRestriction

    client, root, h, owner, wid, sid, reviewers, ds, body = evaluation
    aid = assign_api(evaluation, 0)
    with Session(db_engine) as session, session.begin():
        session.add(PrivacyRestriction(workspace_id=wid, subject_id=owner))
    assert client.get(root + f"/assignments/{aid}", headers=reviewers[0][0]).status_code == 403
    for suffix in ["", "/report", "/export"]:
        assert client.get(root + f"/datasets/{ds['id']}" + suffix, headers=h).status_code == 403


def test_export_approver_revoked_role_blocks_export(evaluation, db_engine, research_app):
    client, root, h, owner, wid, sid, reviewers, ds, body = evaluation
    for i in range(3):
        submit_api(
            evaluation, i, assign_api(evaluation, i, "adjudication" if i == 2 else "independent")
        )
    _, _, actor = research_app
    approval_headers, approver, _ = actor(wid, "admin")
    with Session(db_engine) as session, session.begin():
        member = session.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.user_id == approver)
        )
        session.add(
            StudyGrant(
                workspace_id=wid,
                study_id=sid,
                membership_id=member.id,
                capabilities=["read", "review", "export"],
            )
        )
    response = client.post(
        root + f"/datasets/{ds['id']}/export-review",
        headers=approval_headers,
        json={"reason": {"text": "Rights reviewed", "language": "en"}},
    )
    assert response.status_code == 201, response.text
    assert client.get(root + f"/datasets/{ds['id']}/export", headers=h).status_code == 200
    with Session(db_engine) as session, session.begin():
        member = session.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.user_id == approver)
        )
        member.role = "reviewer"
    assert client.get(root + f"/datasets/{ds['id']}/export", headers=h).status_code == 403


def test_db_direct_delete_without_privacy_is_rejected(evaluation, db_engine):
    aid = assign_api(evaluation, 0)
    result = submit_api(evaluation, 0, aid).json()
    for table, row_id in [
        ("evaluation_outcomes", result["id"]),
        ("evaluation_assignments", aid),
        ("evaluation_datasets", evaluation[7]["id"]),
    ]:
        with pytest.raises(DBAPIError), Session(db_engine) as session, session.begin():
            session.execute(text(f"DELETE FROM {table} WHERE id=:id"), {"id": row_id})
