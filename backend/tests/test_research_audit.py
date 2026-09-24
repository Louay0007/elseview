"""P12/P13 regressions. Database execution requires the lead's isolated DB grant."""

import time

# ruff: noqa: F811
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from study_fixtures import ready_study
from test_collection_db import collected  # noqa: F401
from test_evaluation_db import assign_api, evaluation  # noqa: F401
from test_longitudinal_db import longitudinal, slot_body  # noqa: F401

from app.auth.models import Membership
from app.common.errors import DomainError
from app.evaluation.models import EvaluationRawExposure
from app.studies.models import StudyGrant

pytestmark = pytest.mark.db


def set_access(engine, wid, sid, uid, role, capabilities):
    with Session(engine) as s, s.begin():
        member = s.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.user_id == uid)
        )
        member.role = role
        grant = s.scalar(
            select(StudyGrant).where(
                StudyGrant.study_id == sid, StudyGrant.membership_id == member.id
            )
        )
        grant.capabilities = capabilities


@pytest.mark.parametrize("privilege", ["creator", "admin", "raw"])
def test_privileged_independent_denied(evaluation, db_engine, privilege):
    client, root, h, owner, wid, sid, reviewers, ds, _ = evaluation
    uid = reviewers[0][1]
    if privilege == "creator":
        uid = owner
    else:
        set_access(
            db_engine,
            wid,
            sid,
            uid,
            "admin" if privilege == "admin" else "researcher",
            ["read", "review", "raw"] if privilege == "raw" else ["read", "review"],
        )
    r = client.post(
        root + f"/datasets/{ds['id']}/assignments",
        headers=h,
        json={"item_id": ds["items"][0]["id"], "reviewer_id": str(uid), "kind": "independent"},
    )
    assert r.status_code == 403, r.text


def test_raw_first_read_irreversible_and_assignment_revalidated(evaluation, db_engine):
    client, root, h, _, wid, sid, reviewers, ds, _ = evaluation
    aid = assign_api(evaluation, 0)
    rh, uid = reviewers[0]
    assert client.get(root + f"/assignments/{aid}", headers=rh).status_code == 200
    set_access(db_engine, wid, sid, uid, "researcher", ["read", "review", "raw"])
    assert client.get(root + f"/assignments/{aid}", headers=rh).status_code == 403
    assert client.get(root + f"/datasets/{ds['id']}", headers=rh).status_code == 200
    set_access(db_engine, wid, sid, uid, "reviewer", ["read", "review"])
    assert client.get(root + f"/assignments/{aid}", headers=rh).status_code == 403
    r = client.post(
        root + f"/assignments/{aid}/outcome",
        headers=rh,
        json={
            "reason": {"text": "Independent", "language": "en"},
            "annotations": [{"label_id": "yes"}],
        },
    )
    assert r.status_code == 403, r.text
    with Session(db_engine) as s:
        assert s.scalar(
            select(EvaluationRawExposure.id).where(
                EvaluationRawExposure.dataset_id == UUID(ds["id"]),
                EvaluationRawExposure.actor_id == uid,
            )
        )


def test_unused_revoked_raw_grant_does_not_invent_exposure(evaluation, db_engine):
    _, _, _, _, wid, sid, reviewers, _, _ = evaluation
    uid = reviewers[0][1]
    set_access(db_engine, wid, sid, uid, "researcher", ["read", "review", "raw"])
    set_access(db_engine, wid, sid, uid, "reviewer", ["read", "review"])
    assign_api(evaluation, 0)


def test_crossworkspace_booking_independent_transactions(
    longitudinal, research_app, db_engine, monkeypatch
):
    from app.collection.models import CollectionSession
    from app.longitudinal import service
    from app.longitudinal.models import Booking
    from app.longitudinal.schemas import SlotBody

    client, root, staff, _, wid, vid, result = longitudinal
    h2, owner2, wid2 = research_app[2]()
    study2 = ready_study(client, f"/api/v1/workspaces/{wid2}", h2)
    published = client.post(
        study2["endpoint"] + "/publish", headers=h2, json={"expected_revision": 2}
    )
    assert published.status_code == 200, published.text
    with Session(db_engine) as s:
        base = s.get(CollectionSession, UUID(result["session_id"]))
        participant = base.subject_id
    # Only participation and reminder delivery are stubbed: both workers execute
    # the real booking overlap query, insert and commit on separate connections.
    monkeypatch.setattr(service, "participant_version", lambda *a: None)
    monkeypatch.setattr(service, "remind", lambda *a: None)
    first = client.post(root + "/slots", headers=staff, json=slot_body(vid))
    assert first.status_code == 200, first.text
    payload = slot_body(UUID(study2["version_id"]))
    payload["starts"] = slot_body(vid)["starts"]
    with Session(db_engine) as s, s.begin():
        second = service.create_slot(s, wid2, owner2, SlotBody.model_validate(payload))
        second_id = second["id"]
    barrier = Barrier(2)
    original_capacity = service.capacity

    def slow_capacity(*args, **kwargs):
        original_capacity(*args, **kwargs)
        time.sleep(0.2)  # Exposes the old check/insert race without serializing it.

    monkeypatch.setattr(service, "capacity", slow_capacity)

    def worker(slot_id):
        with Session(db_engine) as s:
            barrier.wait(timeout=5)
            try:
                with s.begin():
                    service.book(
                        s, participant, SimpleNamespace(slot_id=slot_id, request_key=str(uuid4()))
                    )
                return "success"
            except DomainError as exc:
                return exc.code

    ids = [UUID(first.json()["id"]), second_id]
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, ids))
    assert sorted(outcomes) == ["PARTICIPANT_OVERLAP", "success"]
    with Session(db_engine) as s:
        assert (
            len(
                s.scalars(
                    select(Booking).where(
                        Booking.subject_id == participant,
                        Booking.slot_id.in_(ids),
                        Booking.state == "booked",
                    )
                ).all()
            )
            == 1
        )


def test_legacy_unchecked_independent_fails_closed(evaluation, db_engine):
    from app.evaluation.models import EvaluationAssignment

    client, root, _, _, wid, _, reviewers, ds, _ = evaluation
    with Session(db_engine) as s, s.begin():
        legacy = EvaluationAssignment(
            workspace_id=wid,
            item_id=UUID(ds["items"][0]["id"]),
            reviewer_id=reviewers[0][1],
            kind="independent",
            candidate_order=[0, 1],
        )
        s.add(legacy)
        s.flush()
        aid = legacy.id
    assert client.get(root + f"/assignments/{aid}", headers=reviewers[0][0]).status_code == 403
