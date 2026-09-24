import secrets
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from study_fixtures import blocks, ready_study

from app.auth.models import User
from app.auth.security import token_hash, utcnow
from app.collection.models import AnswerRevision, CollectionSession
from app.common.privacy_models import ConsentDocument
from app.jobs.models import Job
from app.recruiting.models import (
    Candidate,
    Invitation,
    PanelConsent,
    ParticipantProfile,
    RecruitmentConfig,
)
from app.studies.models import Launch

pytestmark = pytest.mark.db


@pytest.fixture
def collected(research_app, db_engine, request):
    client, app, actor = research_app
    owner_headers, _, workspace_id = actor()
    selected = [blocks(str(uuid4()))[0], blocks(str(uuid4()))[3]]
    selected[0]["branches"] = [
        {"source": "single", "operator": "eq", "value": "no", "target": None}
    ]
    if getattr(request, "param", None) == "methods":
        selected = None
    fixture = ready_study(client, f"/api/v1/workspaces/{workspace_id}", owner_headers, selected)
    response = client.post(
        fixture["endpoint"] + "/publish", headers=owner_headers, json={"expected_revision": 2}
    )
    assert response.status_code == 200, response.text
    raw = secrets.token_urlsafe(32)
    with Session(db_engine) as session, session.begin():
        user = User(
            email=f"participant-{uuid4().hex}@example.test",
            password_hash="synthetic",
            verified_at=utcnow(),
        )
        session.add(user)
        session.flush()
        participant_headers = {
            "Authorization": "Bearer " + app.state.auth._new_login(session, user)["access_token"]
        }
        profile = ParticipantProfile(user_id=user.id)
        session.add(profile)
        session.flush()
        session.add(
            PanelConsent(
                profile_id=profile.id,
                decision="granted",
                document_version="1",
                document_digest="a" * 64,
                request_digest="a" * 64,
                receipt_key=uuid4().hex,
            )
        )
        launch = session.scalar(
            select(Launch).where(Launch.version_id == UUID(fixture["version_id"]))
        )
        session.add(
            RecruitmentConfig(
                workspace_id=workspace_id,
                launch_id=launch.id,
                capacity=5,
                budget_millimes=0,
                reward_millimes=0,
            )
        )
        candidate = Candidate(
            workspace_id=workspace_id,
            launch_id=launch.id,
            subject_id=user.id,
            source_kind="public",
            source_id=profile.id,
            status="eligible",
            attributes_json={},
        )
        session.add(candidate)
        session.flush()
        session.add(
            Invitation(
                workspace_id=workspace_id,
                candidate_id=candidate.id,
                token_hash=token_hash(raw),
                expires_at=utcnow() + timedelta(hours=1),
            )
        )
        document = session.get(ConsentDocument, UUID(fixture["body"]["consent_documents"]["fr"]))
        body = {
            "invitation_token": raw,
            "capability": secrets.token_urlsafe(32),
            "locale": "fr",
            "document_id": str(document.id),
            "presented_digest": document.digest,
            "consent": "granted",
        }
    response = client.post("/api/v1/collection/sessions", headers=participant_headers, json=body)
    assert response.status_code == 201, response.text
    result = response.json()
    return (
        client,
        "/api/v1/collection/sessions/" + result["session_id"],
        {"X-Session-Token": body["capability"]},
        result,
        participant_headers,
        body,
    )


@pytest.mark.parametrize("collected", ["methods"], indirect=True)
def test_preferences_exposure_and_private_assets(collected):
    from study_fixtures import answer

    client, url, headers, result, _, _ = collected
    for _ in range(4):
        block = client.get(url, headers=headers).json()["block"]
        body = {
            "schema_version": 1,
            "expected_revision": 0,
            "client_event_id": str(uuid4()),
            **answer(block),
        }
        response = client.put(url + "/answers/" + block["block_key"], headers=headers, json=body)
        assert response.status_code == 200, response.text
    block = client.get(url, headers=headers).json()["block"]
    assert block["type"] == "preference"
    assert client.get(url, headers=headers).json()["block"] == block
    asset_id = block["config"]["variants"][0]["asset_ref"]["asset_id"]
    # Fixture reuses the timed stimulus; reuse must not defeat concealment.
    assert client.get(url + "/assets/" + asset_id, headers=headers).status_code == 404
    body = {
        "schema_version": 1,
        "expected_revision": 0,
        "client_event_id": str(uuid4()),
        **answer(block),
    }
    forged = dict(body, value=body["value"] | {"assignment_id": "forged"})
    assert client.put(url + "/answers/preference", headers=headers, json=forged).status_code == 422
    assert client.put(url + "/answers/preference", headers=headers, json=body).status_code == 200
    assert "asset_ref" not in client.get(url, headers=headers).json()["block"]["config"]
    attempt = client.post(url + "/attempts/exposure", headers=headers).json()
    assert attempt["asset_ref"]
    assert client.get(url + "/assets/" + asset_id, headers=headers).status_code == 200
    replay = client.post(url + "/attempts/exposure", headers=headers).json()
    assert replay["attempt_id"] == attempt["attempt_id"] and replay["asset_ref"] is None
    event = {
        "version_id": result["version_id"],
        "events": [
            {
                "block_key": "exposure",
                "event": {
                    "kind": "exposure.interrupted",
                    "client_event_id": str(uuid4()),
                    "sequence": 0,
                    "elapsed_ms": 1200,
                    "metadata": {"attempt_id": attempt["attempt_id"]},
                },
            }
        ],
    }
    assert client.post(url + "/events", headers=headers, json=event).status_code == 200
    assert client.get(url + "/assets/" + asset_id, headers=headers).status_code == 404
    value = {"attempt_id": attempt["attempt_id"], "visible_ms": 1200, "interrupted": True}
    body = {
        "schema_version": 1,
        "expected_revision": 0,
        "client_event_id": str(uuid4()),
        "status": "responded",
        "value": value,
    }
    assert client.put(url + "/answers/exposure", headers=headers, json=body).status_code == 200


def put(client, url, headers, value="yes", revision=0, key=None):
    body = {
        "schema_version": 1,
        "expected_revision": revision,
        "client_event_id": key or str(uuid4()),
        "status": "responded",
        "value": {"option_id": value},
    }
    return client.put(url + "/answers/single", headers=headers, json=body), body


def test_real_nonmember_resume_revision_branch_submit_once(collected, db_engine):
    client, url, headers, result, auth, start = collected
    assert client.post("/api/v1/collection/sessions", headers=auth, json=start).status_code == 201
    response, body = put(client, url, headers)
    assert response.status_code == 200, response.text
    assert client.put(url + "/answers/single", headers=headers, json=body).json() == response.json()
    assert put(client, url, headers)[0].status_code == 409
    text_body = {
        "schema_version": 1,
        "expected_revision": 0,
        "client_event_id": str(uuid4()),
        "status": "responded",
        "value": {"text": "عربي clair", "language": "fr"},
    }
    assert client.put(url + "/answers/text", headers=headers, json=text_body).status_code == 200
    changed, _ = put(client, url, headers, "no", 1)
    assert changed.json()["invalidated"] == ["text"]
    assert (
        client.put(
            url + "/answers/text",
            headers=headers,
            json=text_body | {"client_event_id": str(uuid4()), "expected_revision": 1},
        ).status_code
        == 409
    )
    submit = {"version_id": result["version_id"], "expected_revision": 3}
    response = client.post(url + "/submit", headers=headers, json=submit)
    assert response.status_code == 200, response.text
    assert client.post(url + "/submit", headers=headers, json=submit).json() == response.json()
    assert put(client, url, headers, "yes", 2)[0].status_code == 409
    with Session(db_engine) as session:
        row = session.get(CollectionSession, UUID(result["session_id"]))
        assert set(row.submitted_snapshot) == {"single"}
        assert (
            session.scalar(select(func.count()).select_from(Job).where(Job.target_id == row.id))
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(AnswerRevision)
                .where(AnswerRevision.session_id == row.id)
            )
            == 3
        )


def test_capability_incomplete_events_and_withdraw(collected):
    client, url, headers, result, _, _ = collected
    assert client.get(url, headers={"X-Session-Token": "x" * 43}).status_code == 404
    assert (
        client.post(
            url + "/submit",
            headers=headers,
            json={"version_id": result["version_id"], "expected_revision": 0},
        ).status_code
        == 409
    )
    event = {
        "version_id": result["version_id"],
        "events": [
            {
                "block_key": "single",
                "event": {
                    "kind": "block.rendered",
                    "client_event_id": str(uuid4()),
                    "sequence": 0,
                    "elapsed_ms": 0,
                },
            }
        ],
    }
    response = client.post(url + "/events", headers=headers, json=event)
    assert response.status_code == 200, response.text
    assert client.post(url + "/events", headers=headers, json=event).json() == response.json()
    event["events"][0]["event"].update(client_event_id=str(uuid4()), sequence=2)
    assert client.post(url + "/events", headers=headers, json=event).status_code == 409
    assert client.post(url + "/withdraw", headers=headers).status_code == 200
    assert client.get(url, headers=headers).status_code == 403


def test_wrong_version_dedupe_conflict_and_atomic_event_batch(collected, db_engine):
    from app.collection.models import ResponseEvent

    client, url, headers, result, _, _ = collected
    response, body = put(client, url, headers)
    assert response.status_code == 200
    assert (
        client.put(
            url + "/answers/single", headers=headers, json=body | {"value": {"option_id": "no"}}
        ).status_code
        == 409
    )
    assert (
        client.put(
            url + "/answers/single",
            headers=headers,
            json=body
            | {"client_event_id": str(uuid4()), "version_id": str(uuid4()), "expected_revision": 1},
        ).status_code
        == 409
    )
    items = [
        {
            "block_key": "single",
            "event": {
                "kind": "block.rendered",
                "client_event_id": str(uuid4()),
                "sequence": n,
                "elapsed_ms": 100,
            },
        }
        for n in [0, 2]
    ]
    assert (
        client.post(
            url + "/events",
            headers=headers,
            json={"version_id": result["version_id"], "events": items},
        ).status_code
        == 409
    )
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(ResponseEvent)
                .where(
                    ResponseEvent.session_id == UUID(result["session_id"]),
                    ResponseEvent.provenance == "client_observed",
                )
            )
            == 0
        )
        assert session.get(CollectionSession, UUID(result["session_id"])).last_sequence == -1


def test_quality_privacy_export_purge_and_database_guards(collected, db_engine):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from app.collection.privacy import purge_subject, subject_data
    from app.collection.quality import finish_quality, quality_job_allowed
    from app.common.privacy import lock_workspace

    client, url, headers, result, _, _ = collected
    assert put(client, url, headers, "no")[0].status_code == 200
    assert (
        client.post(
            url + "/submit",
            headers=headers,
            json={"version_id": result["version_id"], "expected_revision": 1},
        ).status_code
        == 200
    )
    row_id = UUID(result["session_id"])
    with Session(db_engine) as session, session.begin():
        row = session.get(CollectionSession, row_id)
        job = session.get(Job, row.quality_job_id)
        assert quality_job_allowed(session, job)
        summary = finish_quality(session, job)
        assert summary["decision"] is None
        assert row.quality_summary["status"] == "pending_human_review"
        assert subject_data(session, row.workspace_id, row.subject_id)[0]["revisions"][0]["answer"][
            "value"
        ] == {"option_id": "no"}
    with Session(db_engine) as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text("UPDATE answer_revisions SET payload = '{}' WHERE session_id = :id"),
                {"id": row_id},
            )
        session.rollback()
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "UPDATE collection_sessions SET assignments = '{\"forged\": true}' WHERE id = :id"
                ),
                {"id": row_id},
            )
        session.rollback()
    with Session(db_engine) as session, session.begin():
        row = session.get(CollectionSession, row_id)
        lock_workspace(session, row.workspace_id)
        purge_subject(session, row.workspace_id, row.subject_id)
        assert row.state == "erased"
        assert row.quality_summary is None
        assert not quality_job_allowed(session, session.get(Job, row.quality_job_id))
        assert (
            session.scalar(
                select(func.count())
                .select_from(AnswerRevision)
                .where(AnswerRevision.session_id == row_id)
            )
            == 0
        )


def test_concurrent_duplicate_submission_one_job(collected, db_engine):
    from concurrent.futures import ThreadPoolExecutor

    from app.collection import service
    from app.collection.schemas import SubmitBody

    client, url, headers, result, _, _ = collected
    assert put(client, url, headers, "no")[0].status_code == 200

    def submit(_):
        with Session(db_engine) as session, session.begin():
            row = service.authorize(session, UUID(result["session_id"]), headers["X-Session-Token"])
            return service.submit(
                session, row, SubmitBody(version_id=UUID(result["version_id"]), expected_revision=1)
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(submit, range(2))
    assert first == second
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Job)
                .where(Job.target_id == UUID(result["session_id"]))
            )
            == 1
        )


def test_expired_reservation_blocks_submission_without_job(collected, db_engine):
    from app.recruiting.models import Reservation

    client, url, headers, result, _, _ = collected
    assert put(client, url, headers, "no")[0].status_code == 200
    with Session(db_engine) as session, session.begin():
        row = session.get(CollectionSession, UUID(result["session_id"]))
        reservation = session.scalar(
            select(Reservation).where(Reservation.candidate_id == row.candidate_id)
        )
        reservation.expires_at = utcnow() - timedelta(seconds=1)
    response = client.post(
        url + "/submit",
        headers=headers,
        json={"version_id": result["version_id"], "expected_revision": 1},
    )
    assert response.status_code == 409
    with Session(db_engine) as session:
        row = session.get(CollectionSession, UUID(result["session_id"]))
        assert row.state == "active" and row.quality_job_id is None


def test_nonmember_privacy_request_and_launch_purge(collected, db_engine):
    from app.collection.privacy import purge_launches
    from app.common.privacy import lock_workspace

    client, url, headers, result, auth, _ = collected
    with Session(db_engine) as session:
        row = session.get(CollectionSession, UUID(result["session_id"]))
        workspace_id, launch_id = row.workspace_id, row.launch_id
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/privacy-requests",
        headers=auth,
        json={"request_key": uuid4().hex, "kind": "access"},
    )
    assert response.status_code == 202, response.text
    with Session(db_engine) as session, session.begin():
        lock_workspace(session, workspace_id)
        purge_launches(session, workspace_id, [launch_id])
        assert session.get(CollectionSession, UUID(result["session_id"])) is None


@pytest.mark.parametrize("guard", ["capability_expired", "launch_closed", "source_withdrawn"])
def test_revoked_collection_authority(collected, db_engine, guard):
    client, url, headers, result, _, _ = collected
    assert put(client, url, headers, "no")[0].status_code == 200
    with Session(db_engine) as session, session.begin():
        row = session.get(CollectionSession, UUID(result["session_id"]))
        if guard == "capability_expired":
            row.expires_at = utcnow() - timedelta(seconds=1)
        elif guard == "launch_closed":
            session.get(Launch, row.launch_id).state = "closed"
        else:
            candidate = session.get(Candidate, row.candidate_id)
            session.get(ParticipantProfile, candidate.source_id).status = "withdrawn"
    response = client.post(
        url + "/submit",
        headers=headers,
        json={"version_id": result["version_id"], "expected_revision": 1},
    )
    assert response.status_code in {403, 409}
    with Session(db_engine) as session:
        assert session.get(CollectionSession, UUID(result["session_id"])).quality_job_id is None


def second_participation(collected, research_app, db_engine):
    from app.auth.models import Membership
    from app.studies.models import Study, StudyVersion

    client, _, _, first, participant_auth, _ = collected
    _, app, _ = research_app
    with Session(db_engine) as session, session.begin():
        row = session.get(CollectionSession, UUID(first["session_id"]))
        original = session.get(Candidate, row.candidate_id)
        version = session.get(StudyVersion, row.version_id)
        study = session.get(Study, version.study_id)
        owner = session.get(User, session.get(Membership, study.owner_membership_id).user_id)
        owner_auth = {
            "Authorization": "Bearer " + app.state.auth._new_login(session, owner)["access_token"]
        }
        workspace_id, subject_id, source_id = row.workspace_id, row.subject_id, original.source_id
    fixture = ready_study(
        client, f"/api/v1/workspaces/{workspace_id}", owner_auth, [blocks(str(uuid4()))[0]]
    )
    assert (
        client.post(
            fixture["endpoint"] + "/publish", headers=owner_auth, json={"expected_revision": 2}
        ).status_code
        == 200
    )
    raw = secrets.token_urlsafe(32)
    with Session(db_engine) as session, session.begin():
        launch = session.scalar(
            select(Launch).where(Launch.version_id == UUID(fixture["version_id"]))
        )
        session.add(
            RecruitmentConfig(
                workspace_id=workspace_id,
                launch_id=launch.id,
                capacity=5,
                budget_millimes=0,
                reward_millimes=0,
            )
        )
        candidate = Candidate(
            workspace_id=workspace_id,
            launch_id=launch.id,
            subject_id=subject_id,
            source_kind="public",
            source_id=source_id,
            status="eligible",
            attributes_json={},
        )
        session.add(candidate)
        session.flush()
        session.add(
            Invitation(
                workspace_id=workspace_id,
                candidate_id=candidate.id,
                token_hash=token_hash(raw),
                expires_at=utcnow() + timedelta(hours=1),
            )
        )
        document = session.get(ConsentDocument, UUID(fixture["body"]["consent_documents"]["fr"]))
        body = {
            "invitation_token": raw,
            "capability": secrets.token_urlsafe(32),
            "locale": "fr",
            "document_id": str(document.id),
            "presented_digest": document.digest,
            "consent": "granted",
        }
    response = client.post("/api/v1/collection/sessions", headers=participant_auth, json=body)
    assert response.status_code == 201, response.text
    return response.json(), {"X-Session-Token": body["capability"]}


def test_withdraw_capability_is_session_scoped(collected, research_app, db_engine):
    from app.common.privacy_models import ConsentReceipt
    from app.recruiting.models import Reservation

    client, url, headers, first, _, _ = collected
    second, second_headers = second_participation(collected, research_app, db_engine)
    for _ in range(2):
        assert client.post(url + "/withdraw", headers=headers).status_code == 200
    assert (
        client.get(
            "/api/v1/collection/sessions/" + second["session_id"], headers=second_headers
        ).status_code
        == 200
    )
    with Session(db_engine) as session:
        row = session.get(CollectionSession, UUID(second["session_id"]))
        assert row.state == "active"
        assert session.get(ConsentReceipt, row.consent_receipt_id).decision == "granted"
        assert (
            session.scalar(
                select(Reservation).where(Reservation.candidate_id == row.candidate_id)
            ).state
            == "held"
        )


@pytest.mark.parametrize("withdraw", [False, True])
def test_fenced_quality_completion(collected, db_engine, withdraw):
    from sqlalchemy import update

    from app.jobs import service as jobs

    client, url, headers, result, _, _ = collected
    assert put(client, url, headers, "no")[0].status_code == 200
    response = client.post(
        url + "/submit",
        headers=headers,
        json={"version_id": result["version_id"], "expected_revision": 1},
    )
    assert response.status_code == 200
    target = UUID(response.json()["quality_job_id"])
    with Session(db_engine) as session, session.begin():
        session.execute(
            update(Job)
            .where(Job.id != target, Job.state == "pending")
            .values(run_after=utcnow() + timedelta(days=1))
        )
        job = jobs.claim(session, 30)
        assert job.id == target
        lease = job.lease_token
    if withdraw:
        assert client.post(url + "/withdraw", headers=headers).status_code == 200
    with Session(db_engine) as session, session.begin():
        assert jobs.complete(session, target, lease, {"status": "ok"}) is (not withdraw)
    with Session(db_engine) as session:
        row = session.get(CollectionSession, UUID(result["session_id"]))
        assert session.get(Job, target).state == ("cancelled" if withdraw else "succeeded")
        assert (row.quality_summary is None) is withdraw


def test_randomized_choices_persist(collected, db_engine):
    client, url, headers, result, auth, body = collected
    first = client.get(url, headers=headers).json()["block"]["config"]["options"]
    assert (
        client.post("/api/v1/collection/sessions", headers=auth, json=body).json()["block"][
            "config"
        ]["options"]
        == first
    )
    with Session(db_engine) as session:
        row = session.get(CollectionSession, UUID(result["session_id"]))
        assert row.assignments["single"]["order"] == [option["id"] for option in first]


def test_db_final_insert_resurrection_and_cross_session(collected, research_app, db_engine):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    client, url, headers, first, _, _ = collected
    second, _ = second_participation(collected, research_app, db_engine)
    assert put(client, url, headers, "no")[0].status_code == 200
    with Session(db_engine) as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO answer_revisions SELECT :new_id, :other, answer_id, 2, :event, request_hash, payload, status, value, reason_code, receipt, created_at FROM answer_revisions WHERE session_id = :first"
                ),
                {
                    "new_id": uuid4(),
                    "other": UUID(second["session_id"]),
                    "event": uuid4(),
                    "first": UUID(first["session_id"]),
                },
            )
        session.rollback()
    assert (
        client.post(
            url + "/submit",
            headers=headers,
            json={"version_id": first["version_id"], "expected_revision": 1},
        ).status_code
        == 200
    )
    for command in [
        "UPDATE collection_sessions SET state = 'active' WHERE id = :id",
        "INSERT INTO response_events (id,session_id,kind,provenance,payload) VALUES (:new_id,:id,'block.rendered','client_observed','{}')",
        "INSERT INTO collection_answers (id,session_id,block_key,occurrence,current_revision,active) VALUES (:new_id,:id,'forged',0,0,true)",
    ]:
        with Session(db_engine) as session:
            with pytest.raises(DBAPIError):
                session.execute(text(command), {"id": UUID(first["session_id"]), "new_id": uuid4()})
            session.rollback()
