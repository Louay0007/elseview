"""Authenticated diary recovery, persisted replay and lock-boundary regressions."""

import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_collection_db import collected  # noqa: F401
from test_longitudinal_db import longitudinal  # noqa: F401

from app.auth.security import utcnow
from app.collection import service as collection
from app.collection.models import CollectionSession, ResponseEvent
from app.common.errors import DomainError
from app.longitudinal import service
from app.longitudinal.schemas import DiaryRecoverBody
from app.recruiting.models import Candidate

pytestmark = pytest.mark.db


@pytest.fixture
def diary(longitudinal, collected, db_engine):  # noqa: F811
    client, root, staff, participant, wid, vid, result = longitudinal
    _, base_url, base_cap, _, _, _ = collected
    now = utcnow().replace(tzinfo=None)
    response = client.post(
        root + "/diary-schedules",
        headers=staff,
        json={
            "base_session_id": result["session_id"],
            "timezone": "UTC",
            "windows": [
                {
                    "opens": {"local": (now - timedelta(minutes=1)).isoformat()},
                    "due": {"local": (now + timedelta(minutes=10)).isoformat()},
                    "grace": {"local": (now + timedelta(minutes=20)).isoformat()},
                }
            ],
        },
    )
    assert response.status_code == 200
    oid = response.json()[0]["id"]
    answer = client.put(
        base_url + "/answers/single",
        headers=base_cap,
        json={
            "schema_version": 1,
            "expected_revision": 0,
            "client_event_id": str(uuid4()),
            "status": "responded",
            "value": {"option_id": "no"},
        },
    )
    assert answer.status_code == 200
    assert (
        client.post(
            base_url + "/submit",
            headers=base_cap,
            json={
                "version_id": str(vid),
                "expected_revision": 1,
            },
        ).status_code
        == 200
    )
    endpoint = f"/api/v1/participant/longitudinal/diary-occurrences/{oid}"
    original = secrets.token_urlsafe(32)
    started = client.post(endpoint + "/start", headers=participant, json={"capability": original})
    assert started.status_code == 200
    sid = UUID(started.json()["session_id"])
    with Session(db_engine) as session:
        child = session.get(CollectionSession, sid)
        subject = child.subject_id
        initial = (child.expires_at, child.start_hash, child.assignments, child.last_sequence)
    return {
        "client": client,
        "headers": participant,
        "staff": staff,
        "endpoint": endpoint,
        "oid": UUID(oid),
        "sid": sid,
        "wid": wid,
        "vid": vid,
        "subject": subject,
        "original": original,
        "base_cap": base_cap,
        "initial": initial,
        "url": f"/api/v1/collection/sessions/{sid}",
    }


def recover(diary, body, headers=None):
    return diary["client"].post(
        diary["endpoint"] + "/recover", headers=headers or diary["headers"], json=body
    )


def rotation_count(engine, sid):
    with Session(engine) as session:
        return session.scalar(
            select(func.count())
            .select_from(ResponseEvent)
            .where(ResponseEvent.session_id == sid, ResponseEvent.kind == "session.recovered")
        )


def test_recovery_replays_after_answer_without_resetting_evidence(diary, db_engine):
    body = {"capability": secrets.token_urlsafe(32), "expected_revision": 0}
    response = recover(diary, body)
    assert response.status_code == 200
    assert response.json()["revision"] == 1 and response.json()["locale"] == "fr"
    assert response.headers["cache-control"] == "no-store"
    assert body["capability"] not in response.text
    assert (
        diary["client"]
        .get(diary["url"], headers={"X-Session-Token": diary["original"]})
        .status_code
        == 404
    )
    answer = diary["client"].put(
        diary["url"] + "/answers/single",
        headers={"X-Session-Token": body["capability"]},
        json={
            "schema_version": 1,
            "expected_revision": 0,
            "client_event_id": str(uuid4()),
            "status": "responded",
            "value": {"option_id": "no"},
        },
    )
    assert answer.status_code == 200
    replay = recover(diary, body)
    assert replay.status_code == 200 and replay.json()["revision"] == 2
    assert replay.json()["answers"]["single"]["revision"] == 1
    assert rotation_count(db_engine, diary["sid"]) == 1
    with Session(db_engine) as session:
        child = session.get(CollectionSession, diary["sid"])
        assert (
            child.expires_at,
            child.start_hash,
            child.assignments,
            child.last_sequence,
        ) == diary["initial"]
        event = session.scalar(
            select(ResponseEvent).where(
                ResponseEvent.session_id == child.id, ResponseEvent.kind == "session.recovered"
            )
        )
        assert event.payload == {}


@pytest.mark.parametrize("identical", [False, True])
def test_concurrent_recovery_serializes_and_counts_once(diary, db_engine, identical):
    first = DiaryRecoverBody(capability=secrets.token_urlsafe(32), expected_revision=0)
    second = (
        first
        if identical
        else DiaryRecoverBody(capability=secrets.token_urlsafe(32), expected_revision=0)
    )
    barrier = threading.Barrier(2)

    def run(body):
        barrier.wait(timeout=5)
        try:
            with Session(db_engine) as session, session.begin():
                service.recover_diary(session, diary["subject"], diary["oid"], body)
            return 200
        except DomainError as error:
            return error.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(run, [first, second]))
    assert results == ([200, 200] if identical else [200, 409])
    assert rotation_count(db_engine, diary["sid"]) == 1


def test_stale_recovery_cannot_restore_previous_token(diary):
    first = {"capability": secrets.token_urlsafe(32), "expected_revision": 0}
    assert recover(diary, first).status_code == 200
    second = {"capability": secrets.token_urlsafe(32), "expected_revision": 1}
    assert recover(diary, second).status_code == 200
    assert recover(diary, first).status_code == 409
    assert (
        diary["client"]
        .get(diary["url"], headers={"X-Session-Token": first["capability"]})
        .status_code
        == 404
    )
    assert (
        diary["client"]
        .get(diary["url"], headers={"X-Session-Token": second["capability"]})
        .status_code
        == 200
    )


@pytest.mark.parametrize("allow_withdrawn", [False, True])
def test_old_capability_waiting_at_workspace_lock_is_rechecked(
    diary, db_engine, monkeypatch, allow_withdrawn
):
    checked, proceed = threading.Event(), threading.Event()
    local = threading.local()
    original_lock = collection.lock_workspace

    def gate(session, wid):
        if getattr(local, "old_request", False):
            checked.set()
            assert proceed.wait(timeout=10)
        return original_lock(session, wid)

    monkeypatch.setattr(collection, "lock_workspace", gate)

    def old_request():
        local.old_request = True
        try:
            with Session(db_engine) as session, session.begin():
                collection.authorize(
                    session, diary["sid"], diary["original"], allow_withdrawn=allow_withdrawn
                )
            return 200
        except DomainError as error:
            return error.status

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(old_request)
        try:
            assert checked.wait(timeout=5)
            assert (
                recover(
                    diary, {"capability": secrets.token_urlsafe(32), "expected_revision": 0}
                ).status_code
                == 200
            )
        finally:
            proceed.set()
        assert future.result(timeout=10) == 404


@pytest.mark.parametrize(
    "case", ["owner", "withdrawn", "expired", "closed", "submitted", "missing"]
)
def test_recovery_rejects_invalid_owner_or_lifecycle(diary, db_engine, monkeypatch, case):
    with Session(db_engine) as session, session.begin():
        child = session.get(CollectionSession, diary["sid"])
        if case in {"withdrawn", "submitted"}:
            child.state = case
        elif case == "expired":
            child.expires_at = utcnow() - timedelta(seconds=1)
        elif case == "closed":
            before_open = utcnow() - timedelta(days=1)
            monkeypatch.setattr(service, "utcnow", lambda: before_open)
        elif case == "missing":
            diary["endpoint"] = f"/api/v1/participant/longitudinal/diary-occurrences/{uuid4()}"
    response = recover(
        diary,
        {"capability": secrets.token_urlsafe(32), "expected_revision": 0},
        diary["staff"] if case == "owner" else None,
    )
    assert response.status_code in {403, 404, 409}
    assert rotation_count(db_engine, diary["sid"]) == 0


def test_collision_and_failed_projection_roll_back_rotation(diary, db_engine, monkeypatch):
    collision = {"capability": diary["base_cap"]["X-Session-Token"], "expected_revision": 0}
    assert recover(diary, collision).status_code == 409
    original_resume = collection.resume

    def fail_projection(*args):
        raise DomainError("TEST_PROJECTION", "Synthetic projection failure.", 409)

    monkeypatch.setattr(collection, "resume", fail_projection)
    assert (
        recover(
            diary, {"capability": secrets.token_urlsafe(32), "expected_revision": 0}
        ).status_code
        == 409
    )
    monkeypatch.setattr(collection, "resume", original_resume)
    assert (
        diary["client"]
        .get(diary["url"], headers={"X-Session-Token": diary["original"]})
        .status_code
        == 200
    )
    assert rotation_count(db_engine, diary["sid"]) == 0
    with Session(db_engine) as session:
        assert session.get(CollectionSession, diary["sid"]).revision == 0


@pytest.mark.parametrize("answer_first", [False, True])
def test_answer_rotation_order_and_old_mutations(diary, answer_first):
    headers = {"X-Session-Token": diary["original"]}
    answer = {
        "schema_version": 1,
        "expected_revision": 0,
        "client_event_id": str(uuid4()),
        "status": "responded",
        "value": {"option_id": "no"},
    }
    if answer_first:
        response = diary["client"].put(
            diary["url"] + "/answers/single", headers=headers, json=answer
        )
        assert response.status_code == 200
    rotated = recover(diary, {"capability": secrets.token_urlsafe(32), "expected_revision": 0})
    assert rotated.status_code == (409 if answer_first else 200)
    if not answer_first:
        commands = [
            ("put", "/answers/single", answer),
            ("post", "/submit", {"version_id": str(diary["vid"]), "expected_revision": 1}),
            (
                "post",
                "/events",
                {
                    "version_id": str(diary["vid"]),
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
                },
            ),
            ("post", "/withdraw", None),
        ]
        for method, path, body in commands:
            response = getattr(diary["client"], method)(
                diary["url"] + path, headers=headers, **({"json": body} if body else {})
            )
            assert response.status_code == 404


def test_source_withdrawal_rolls_back_provisional_rotation(diary, db_engine, monkeypatch):
    def no_reservation(*args):
        raise AssertionError("Recovery must not reserve another response")

    monkeypatch.setattr("app.billing.service.reserve_response", no_reservation)
    with Session(db_engine) as session, session.begin():
        child = session.get(CollectionSession, diary["sid"])
        candidate = session.get(Candidate, child.candidate_id)
        candidate.status = "withdrawn"
    response = recover(diary, {"capability": secrets.token_urlsafe(32), "expected_revision": 0})
    assert response.status_code == 403
    with Session(db_engine) as session, session.begin():
        child = session.get(CollectionSession, diary["sid"])
        assert child.revision == 0 and child.capability_hash == collection.digest(diary["original"])
        session.get(Candidate, child.candidate_id).status = "eligible"
    response = recover(diary, {"capability": secrets.token_urlsafe(32), "expected_revision": 0})
    assert response.status_code == 200
    assert rotation_count(db_engine, diary["sid"]) == 1
