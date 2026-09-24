"""Private own-subject history never substitutes for staff or payment evidence."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_reviews_db import collected as collected
from test_reviews_db import decisions, payment
from test_reviews_db import reviewed as reviewed

from app.auth.security import utcnow
from app.collection.models import CollectionSession
from app.common.privacy_models import PrivacyRestriction
from app.longitudinal.models import Booking, ScheduleSlot
from app.recruiting.models import ParticipantProfile
from app.reviews import service
from app.reviews.models import RewardRecord

pytestmark = pytest.mark.db
ROOT = "/api/v1/participant/history"


def scope(db_engine, collected):
    with Session(db_engine) as session:
        row = session.get(CollectionSession, UUID(collected[3]["session_id"]))
        return row.workspace_id, row.subject_id, row.version_id


def seed_attendance(db_engine, wid, subject, version, owner, status="unknown"):
    with Session(db_engine) as session, session.begin():
        slot = ScheduleSlot(
            workspace_id=wid,
            version_id=version,
            host_id=owner,
            starts_at=utcnow() - timedelta(days=1),
            ends_at=utcnow() - timedelta(days=1) + timedelta(minutes=30),
            timezone="Africa/Tunis",
            capacity=1,
            join_url="https://example.test/private-interview-room",
        )
        session.add(slot)
        session.flush()
        booking = Booking(
            workspace_id=wid,
            slot_id=slot.id,
            subject_id=subject,
            request_key=uuid4(),
            attendance=status,
            attendance_actor_id=owner if status != "unknown" else None,
            attendance_at=utcnow() if status != "unknown" else None,
            attendance_note="Private staff attribution" if status != "unknown" else None,
        )
        session.add(booking)
        session.flush()
        return booking.id


def test_history_scope_is_own_participation_not_workspace_membership(
    collected, research_app, db_engine
):
    client, _, _, _, auth, _ = collected
    wid, _, _ = scope(db_engine, collected)
    assert client.get(ROOT).status_code == 401
    response = client.get(ROOT, headers=auth)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"items": [{"workspace_id": str(wid)}], "next_offset": None}
    assert client.get(f"{ROOT}/{wid}/responses", headers=auth).json() == {
        "items": [],
        "next_offset": None,
    }
    outsider, _, outsider_wid = research_app[2]()
    assert client.get(ROOT, headers=outsider).json()["items"] == []
    for suffix in ("responses", "rewards", "attendance"):
        assert client.get(f"{ROOT}/{wid}/{suffix}", headers=outsider).status_code == 404
        assert client.get(f"{ROOT}/{outsider_wid}/{suffix}", headers=auth).status_code == 404
        assert client.get(f"{ROOT}/{uuid4()}/{suffix}", headers=auth).status_code == 404


def test_response_history_uses_current_human_review_and_appeal(collected, reviewed, db_engine):
    client, _, _, result, auth, _ = collected
    wid, sid, owner, reviewers, subject = reviewed
    path = f"{ROOT}/{wid}/responses"
    response = client.get(path, headers=auth)
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert set(item) == {
        "session_id",
        "version_id",
        "occurrence_id",
        "locale",
        "submitted_at",
        "review_state",
        "appeal_state",
    }
    assert item["session_id"] == result["session_id"]
    assert item["submitted_at"] and item["review_state"] == "pending"
    assert item["appeal_state"] is None
    with Session(db_engine) as session, session.begin():
        decisions(session, wid, sid, owner, reviewers, ("rejected", "rejected"))
    assert client.get(path, headers=auth).json()["items"][0]["review_state"] == "rejected"
    response = client.post(
        f"/api/v1/workspaces/{wid}/reviews/sessions/{sid}/appeal",
        headers=auth,
        json={"command_key": str(uuid4()), "reason": "Please review my response evidence."},
    )
    assert response.status_code == 201, response.text
    item = client.get(path, headers=auth).json()["items"][0]
    assert item["review_state"] == "appealed" and item["appeal_state"] == "open"
    assert "evidence" not in item and str(subject) not in str(item)


def test_reward_payment_history_survives_restriction_without_staff_evidence(
    collected, reviewed, research_app, db_engine
):
    client, _, _, _, auth, _ = collected
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as session, session.begin():
        decisions(session, wid, sid, owner, reviewers)
        reward = session.scalar(select(RewardRecord).where(RewardRecord.subject_id == subject))
        rid = reward.id
        failed = service.payout(session, wid, owner, rid, payment(True))
        recorded = service.payout(session, wid, owner, rid, payment())
        failed_id, recorded_id = str(failed.id), str(recorded.id)
        session.add(PrivacyRestriction(workspace_id=wid, subject_id=subject))
    assert client.get(f"{ROOT}/{wid}/responses", headers=auth).status_code == 403
    assert client.get(f"{ROOT}/{wid}/attendance", headers=auth).status_code == 403
    response = client.get(f"{ROOT}/{wid}/rewards", headers=auth)
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert set(item) == {
        "id",
        "amount_millimes",
        "currency",
        "state",
        "created_at",
        "settled_at",
        "manual_record_only",
    }
    assert item["amount_millimes"] == 1000 and item["currency"] == "TND"
    assert item["state"] == "paid" and item["manual_record_only"] is True
    path = f"{ROOT}/{wid}/rewards/{rid}/payments"
    first = client.get(path + "?limit=1", headers=auth)
    assert first.status_code == 200, first.text
    assert first.json()["next_offset"] == 1
    second = client.get(path + "?limit=1&offset=1", headers=auth).json()
    assert second["next_offset"] is None
    entries = first.json()["items"] + second["items"]
    assert {entry["id"] for entry in entries} == {failed_id, recorded_id}
    assert {entry["state"] for entry in entries} == {"failed", "recorded"}
    assert all(
        set(entry) == {"id", "state", "created_at", "manual_record_only"} for entry in entries
    )
    assert first.headers["cache-control"] == "no-store"
    outsider, _, _ = research_app[2]()
    assert client.get(path, headers=outsider).status_code == 404
    assert client.get(f"{ROOT}/{wid}/rewards/{uuid4()}/payments", headers=auth).status_code == 404


@pytest.mark.parametrize("status", ["unknown", "attended", "absent"])
def test_attendance_history_is_attributed_not_inferred_and_hides_private_room(
    collected, reviewed, db_engine, status
):
    client, _, _, _, auth, _ = collected
    wid, _, owner, _, subject = reviewed
    _, _, version = scope(db_engine, collected)
    bid = seed_attendance(db_engine, wid, subject, version, owner, status)
    response = client.get(f"{ROOT}/{wid}/attendance", headers=auth)
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["id"] == str(bid) and item["attendance"] == status
    assert (item["attendance_at"] is None) is (status == "unknown")
    assert set(item) == {
        "id",
        "version_id",
        "state",
        "attendance",
        "attendance_at",
        "starts_at",
        "ends_at",
        "timezone",
    }
    assert "private-interview-room" not in response.text
    assert "Private staff attribution" not in response.text
    assert client.get(ROOT, headers=auth).json()["items"] == [{"workspace_id": str(wid)}]


@pytest.mark.parametrize("withdrawal", ["study", "source"])
def test_withdrawal_hides_response_and_attendance_history(
    collected, reviewed, db_engine, withdrawal
):
    client, url, capability, _, auth, _ = collected
    wid, _, owner, _, subject = reviewed
    _, _, version = scope(db_engine, collected)
    seed_attendance(db_engine, wid, subject, version, owner)
    assert len(client.get(f"{ROOT}/{wid}/responses", headers=auth).json()["items"]) == 1
    if withdrawal == "study":
        assert client.post(url + "/withdraw", headers=capability).status_code == 200
    else:
        with Session(db_engine) as session, session.begin():
            profile = session.scalar(
                select(ParticipantProfile).where(ParticipantProfile.user_id == subject)
            )
            profile.status = "withdrawn"
    for kind in ("responses", "attendance"):
        response = client.get(f"{ROOT}/{wid}/{kind}", headers=auth)
        assert response.status_code == 200, response.text
        assert response.json()["items"] == []


@pytest.mark.parametrize("query", ["limit=0", "limit=51", "offset=-1", "offset=100001"])
def test_history_pagination_is_bounded(collected, query):
    client, _, _, _, auth, _ = collected
    assert client.get(ROOT + "?" + query, headers=auth).status_code == 422
