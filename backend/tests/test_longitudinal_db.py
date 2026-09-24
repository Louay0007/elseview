"""Real HTTP/database longitudinal transactions; execute only in isolated DB window."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_collection_db import collected  # noqa: F401

from app.auth.models import Membership, User
from app.auth.security import utcnow
from app.collection.models import CollectionSession
from app.longitudinal.models import Booking, Notification
from app.studies.models import Study, StudyVersion

pytestmark = pytest.mark.db


@pytest.fixture
def longitudinal(collected, db_engine, research_app):  # noqa: F811
    client, url, cap, result, participant, start = collected
    app = research_app[1]
    with Session(db_engine) as session, session.begin():
        base = session.get(CollectionSession, UUID(result["session_id"]))
        version = session.get(StudyVersion, base.version_id)
        study = session.get(Study, version.study_id)
        member = session.get(Membership, study.owner_membership_id)
        owner = session.get(User, member.user_id)
        staff = {
            "Authorization": "Bearer " + app.state.auth._new_login(session, owner)["access_token"]
        }
        wid, vid = base.workspace_id, base.version_id
    root = f"/api/v1/workspaces/{wid}/longitudinal"
    return client, root, staff, participant, wid, vid, result


def slot_body(vid, hours=48):
    start = (utcnow() + timedelta(hours=hours)).replace(tzinfo=None, second=0, microsecond=0)
    return {
        "version_id": str(vid),
        "timezone": "UTC",
        "starts": {"local": start.isoformat()},
        "ends": {"local": (start + timedelta(minutes=30)).isoformat()},
        "capacity": 1,
        "join_url": "https://meeting.example.test/private-secret",
    }


def test_booking_private_link_revision_cancel_and_reminder(longitudinal, db_engine):
    client, root, staff, participant, wid, vid, _ = longitudinal
    r = client.post(root + "/slots", headers=staff, json=slot_body(vid))
    assert r.status_code == 200, r.text
    slot = r.json()
    endpoint = "/api/v1/participant/longitudinal"
    public = client.get(
        endpoint + "/slots",
        headers=participant,
        params={"workspace_id": str(wid), "version_id": str(vid)},
    )
    assert public.status_code == 200 and "private-secret" not in public.text
    payload = {"slot_id": slot["id"], "request_key": str(uuid4())}
    r = client.post(endpoint + "/bookings", headers=participant, json=payload)
    assert r.status_code == 200, r.text
    booking = r.json()
    assert booking["slot"]["join_url"].endswith("private-secret")
    repeat = client.post(endpoint + "/bookings", headers=participant, json=payload)
    assert repeat.json()["id"] == booking["id"]
    r = client.post(
        endpoint + "/bookings/" + booking["id"] + "/cancel",
        headers=participant,
        json={"expected_revision": 0},
    )
    assert r.status_code == 200, r.text
    assert "join_url" not in r.json()["slot"]
    r = client.post(
        endpoint + "/bookings/" + booking["id"] + "/cancel",
        headers=participant,
        json={"expected_revision": 0},
    )
    assert r.status_code == 409
    from app.jobs.models import Job
    from app.longitudinal.service import reminder_job_allowed

    with Session(db_engine) as session:
        note = session.scalar(
            select(Notification).where(Notification.booking_id == UUID(booking["id"]))
        )
        assert not reminder_job_allowed(session, session.get(Job, note.job_id))


def test_host_overlap_real_http_race(longitudinal, db_engine):
    client, root, staff, _, wid, vid, _ = longitudinal
    body = slot_body(vid)

    def publish(_):
        return client.post(root + "/slots", headers=staff, json=body).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(publish, range(2)))
    assert sorted(outcomes) == [200, 409]


def test_capacity_booking_real_http_race(longitudinal, db_engine):
    client, root, staff, participant, wid, vid, _ = longitudinal
    r = client.post(root + "/slots", headers=staff, json=slot_body(vid))
    assert r.status_code == 200, r.text
    slot = r.json()

    def book(_):
        return client.post(
            "/api/v1/participant/longitudinal/bookings",
            headers=participant,
            json={"slot_id": slot["id"], "request_key": str(uuid4())},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(book, range(2)))
    assert sorted(outcomes) == [200, 409]
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Booking)
                .where(Booking.slot_id == UUID(slot["id"]), Booking.state == "booked")
            )
            == 1
        )


def test_slot_invalid_time_duration_and_auth(longitudinal):
    client, root, staff, participant, wid, vid, _ = longitudinal
    body = slot_body(vid)
    assert client.post(root + "/slots", json=body).status_code == 401
    assert client.post(root + "/slots", headers=participant, json=body).status_code in {403, 404}
    body["ends"] = body["starts"]
    assert client.post(root + "/slots", headers=staff, json=body).status_code == 422
    body = slot_body(vid)
    body["timezone"] = "America/New_York"
    body["starts"] = {"local": "2027-03-14T02:30:00"}
    assert client.post(root + "/slots", headers=staff, json=body).status_code == 422


def test_multiday_diary_independent_sessions_and_grace(
    longitudinal,
    collected,  # noqa: F811
    db_engine,
    monkeypatch,  # noqa: F811
):
    import secrets

    from app.collection import service as collection_service
    from app.longitudinal import service
    from app.longitudinal.models import DiaryOccurrence
    from app.recruiting.models import Reservation

    client, root, staff, participant, wid, vid, result = longitudinal
    _, base_url, cap, _, _, _ = collected
    now = utcnow()
    windows = []
    for day in range(3):
        opens = (now + timedelta(days=day, minutes=-5)).replace(tzinfo=None)
        windows.append(
            {
                "opens": {"local": opens.isoformat()},
                "due": {"local": (opens + timedelta(minutes=10)).isoformat()},
                "grace": {"local": (opens + timedelta(minutes=20)).isoformat()},
            }
        )
    body = {"base_session_id": result["session_id"], "timezone": "UTC", "windows": windows}
    response = client.post(root + "/diary-schedules", headers=staff, json=body)
    assert response.status_code == 200, response.text
    occurrences = response.json()
    assert client.post(root + "/diary-schedules", headers=staff, json=body).json() == occurrences

    def complete(url, headers):
        r = client.put(
            url + "/answers/single",
            headers=headers,
            json={
                "schema_version": 1,
                "expected_revision": 0,
                "client_event_id": str(uuid4()),
                "status": "responded",
                "value": {"option_id": "no"},
            },
        )
        assert r.status_code == 200, r.text
        r = client.post(
            url + "/submit", headers=headers, json={"version_id": str(vid), "expected_revision": 1}
        )
        assert r.status_code == 200, r.text

    complete(base_url, cap)
    endpoint = "/api/v1/participant/longitudinal/diary-occurrences/"
    token = secrets.token_urlsafe(32)
    assert (
        client.post(
            endpoint + occurrences[1]["id"] + "/start",
            headers=participant,
            json={"capability": token},
        ).status_code
        == 409
    )
    ids = []
    for day, occurrence in enumerate(occurrences[:2]):
        clock = now + timedelta(days=day, minutes=7 if day else 0)
        monkeypatch.setattr(service, "utcnow", lambda clock=clock: clock)
        monkeypatch.setattr(collection_service, "utcnow", lambda clock=clock: clock)
        token = secrets.token_urlsafe(32)
        r = client.post(
            endpoint + occurrence["id"] + "/start", headers=participant, json={"capability": token}
        )
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        ids.append(sid)
        assert (
            client.post(
                endpoint + occurrence["id"] + "/start",
                headers=participant,
                json={"capability": token},
            ).json()["session_id"]
            == sid
        )
        complete("/api/v1/collection/sessions/" + sid, {"X-Session-Token": token})
    clock = now + timedelta(days=3)
    monkeypatch.setattr(service, "utcnow", lambda clock=clock: clock)
    assert (
        client.post(
            endpoint + occurrences[2]["id"] + "/start",
            headers=participant,
            json={"capability": secrets.token_urlsafe(32)},
        ).status_code
        == 409
    )
    assert len(set(ids + [result["session_id"]])) == 3
    with Session(db_engine) as session:
        base = session.get(CollectionSession, UUID(result["session_id"]))
        assert (
            session.scalar(
                select(func.count())
                .select_from(Reservation)
                .where(Reservation.candidate_id == base.candidate_id)
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(DiaryOccurrence)
                .where(DiaryOccurrence.base_session_id == base.id)
            )
            == 3
        )
        assert service.diary_reward_source(session, base) is None


def test_recording_exact_participant_consent_immutable_transcript_revoke(longitudinal, db_engine):
    import io
    import wave

    from research_support import document, upload

    from app.common.privacy_models import Asset
    from app.longitudinal.models import Recording, TranscriptSegment

    client, root, staff, participant, wid, vid, result = longitudinal
    base = f"/api/v1/workspaces/{wid}"
    doc = document(client, base, staff, "recording")
    receipt = {
        "document_id": doc["id"],
        "presented_digest": doc["digest"],
        "decision": "granted",
        "receipt_key": uuid4().hex,
    }
    assert client.post(base + "/consent-receipts", headers=staff, json=receipt).status_code == 201
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00" * 800)
    asset = upload(
        client,
        base,
        staff,
        content=stream.getvalue(),
        media_type="audio/wav",
        extension="wav",
        purpose="recording",
    )["asset"]
    with Session(db_engine) as session:
        subject = session.get(CollectionSession, UUID(result["session_id"])).subject_id
    response = client.post(
        "/api/v1/collection/sessions/" + result["session_id"] + "/optional-consent",
        headers=participant,
        json=receipt | {"purpose": "recording", "receipt_key": uuid4().hex},
    )
    assert response.status_code == 200, response.text
    participant_receipt = response.json()
    body = {
        "asset_id": asset["id"],
        "version_id": str(vid),
        "subject_id": str(subject),
        "consent_receipt_id": participant_receipt["id"],
    }
    response = client.post(root + "/recordings", headers=staff, json=body)
    assert response.status_code == 200, response.text
    rid = response.json()["id"]
    url = root + "/recordings/" + rid
    assert client.get(url, headers=participant).status_code in {403, 404}
    bad = {"segments": [{"start_ms": 0, "end_ms": 101, "text": "outside recording"}]}
    assert client.post(url + "/transcript", headers=staff, json=bad).status_code == 422
    payload = {
        "segments": [{"start_ms": 0, "end_ms": 100, "text": "مرحبا", "speaker": "participant"}]
    }
    response = client.post(url + "/transcript", headers=staff, json=payload)
    assert response.status_code == 200, response.text
    assert client.post(url + "/transcript", headers=staff, json=payload).json() == response.json()
    assert (
        client.post(url + "/transcript", headers=staff, json={"text": "changed"}).status_code == 409
    )
    response = client.post(
        "/api/v1/collection/sessions/" + result["session_id"] + "/optional-consent",
        headers=participant,
        json=receipt
        | {"purpose": "recording", "decision": "withdrawn", "receipt_key": uuid4().hex},
    )
    assert response.status_code == 200, response.text
    assert client.get(url, headers=staff).status_code == 403
    with Session(db_engine) as session:
        assert session.get(Recording, UUID(rid)).revoked
        assert (
            session.scalar(
                select(func.count())
                .select_from(TranscriptSegment)
                .where(TranscriptSegment.recording_id == UUID(rid))
            )
            == 0
        )
        assert session.get(Asset, UUID(asset["id"])).state == "blocked"


def test_owner_purge_cascades_diary_shells(longitudinal, collected, db_engine):  # noqa: F811
    from app.collection.privacy import purge_launches
    from app.common.privacy import lock_workspace
    from app.longitudinal import service
    from app.longitudinal.models import DiaryOccurrence

    client, root, staff, participant, wid, vid, result = longitudinal
    opens = (utcnow() - timedelta(minutes=1)).replace(tzinfo=None)
    body = {
        "base_session_id": result["session_id"],
        "timezone": "UTC",
        "windows": [
            {
                "opens": {"local": opens.isoformat()},
                "due": {"local": (opens + timedelta(minutes=5)).isoformat()},
                "grace": {"local": (opens + timedelta(minutes=10)).isoformat()},
            }
        ],
    }
    assert client.post(root + "/diary-schedules", headers=staff, json=body).status_code == 200
    with Session(db_engine) as session, session.begin():
        lock_workspace(session, wid)
        base = session.get(CollectionSession, UUID(result["session_id"]))
        study = session.get(StudyVersion, vid).study_id
        launch = base.launch_id
        service.purge_studies(session, wid, [study])
        purge_launches(session, wid, [launch])
        assert (
            session.scalar(
                select(func.count())
                .select_from(DiaryOccurrence)
                .where(DiaryOccurrence.workspace_id == wid)
            )
            == 0
        )


def test_transcript_cross_workspace_and_wrong_subject_denied(longitudinal, db_engine):
    from app.common.errors import DomainError
    from app.longitudinal.schemas import RecordingBody
    from app.longitudinal.service import create_recording

    _, _, _, _, wid, vid, result = longitudinal
    with Session(db_engine) as session, session.begin():
        base = session.get(CollectionSession, UUID(result["session_id"]))
        with pytest.raises(DomainError):
            create_recording(
                session,
                wid,
                base.subject_id,
                RecordingBody(
                    asset_id=uuid4(), version_id=vid, subject_id=uuid4(), consent_receipt_id=uuid4()
                ),
            )


def test_reminder_durable_complete_inbox_and_no_repeat(longitudinal, db_engine):
    from app.jobs import service as jobs
    from app.jobs.models import Job

    client, root, staff, participant, wid, vid, _ = longitudinal
    slot = client.post(root + "/slots", headers=staff, json=slot_body(vid, hours=2)).json()
    response = client.post(
        "/api/v1/participant/longitudinal/bookings",
        headers=participant,
        json={"slot_id": slot["id"], "request_key": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    bid = UUID(response.json()["id"])
    with Session(db_engine) as session, session.begin():
        note = session.scalar(select(Notification).where(Notification.booking_id == bid))
        job = session.get(Job, note.job_id)
        job.run_after = utcnow() - timedelta(days=3650)
    with Session(db_engine) as session, session.begin():
        claimed = jobs.claim(session)
        assert claimed and claimed.kind == "longitudinal.reminder"
        jid, token = claimed.id, claimed.lease_token
    with Session(db_engine) as session, session.begin():
        assert jobs.complete(session, jid, token, {"status": "ok"})
    with Session(db_engine) as session, session.begin():
        assert not jobs.complete(session, jid, token, {"status": "ok"})
    inbox = client.get(
        "/api/v1/participant/longitudinal/notifications",
        headers=participant,
        params={"workspace_id": str(wid)},
    )
    assert inbox.status_code == 200, inbox.text
    assert len([n for n in inbox.json() if n["booking"]["id"] == str(bid)]) == 1


def test_metrics_empty_denominators_and_authorization(longitudinal):
    client, root, staff, participant, wid, vid, _ = longitudinal
    response = client.get(root + "/metrics", headers=staff, params={"version_id": str(vid)})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["interviews"] == {"ended_noncancelled": 0, "attended": 0, "absent": 0, "unknown": 0}
    assert body["diary"]["due_occurrences"] == body["diary"]["submitted"] == 0
    assert body["diary"]["participants_with_due_occurrences"] == 0
    assert client.get(
        root + "/metrics", headers=participant, params={"version_id": str(vid)}
    ).status_code in {403, 404}


def test_attendance_persists_actor_and_server_time(longitudinal, db_engine, monkeypatch):
    from app.longitudinal import service

    client, root, staff, participant, wid, vid, _ = longitudinal
    slot = client.post(root + "/slots", headers=staff, json=slot_body(vid, hours=2)).json()
    booking = client.post(
        "/api/v1/participant/longitudinal/bookings",
        headers=participant,
        json={"slot_id": slot["id"], "request_key": str(uuid4())},
    ).json()
    now = utcnow() + timedelta(hours=3)
    monkeypatch.setattr(service, "utcnow", lambda: now)
    response = client.post(
        root + "/bookings/" + booking["id"] + "/attendance",
        headers=staff,
        json={
            "expected_revision": 0,
            "attendance": "attended",
            "note": "Host observed participant in interview.",
        },
    )
    assert response.status_code == 200, response.text
    with Session(db_engine) as session:
        row = session.get(Booking, UUID(booking["id"]))
        assert row.attendance_actor_id is not None
        assert row.attendance_at == now
