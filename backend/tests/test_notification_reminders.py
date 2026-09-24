from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_collection_db import collected  # noqa: F401
from test_longitudinal_db import longitudinal, slot_body  # noqa: F401

from app.auth.models import Membership, User
from app.auth.security import utcnow
from app.collaboration import mail
from app.collaboration.models import NotificationDelivery
from app.collection.models import CollectionSession
from app.longitudinal.models import Notification

pytestmark = pytest.mark.db


def preference(client, wid, participant, **flags):
    response = client.put(
        f"/api/v1/workspaces/{wid}/collaboration/notification-preferences",
        headers=participant,
        json={"reminders": True, "email_reminders": True} | flags,
    )
    assert response.status_code == 200, response.text
    return response.json()


def booking(context):
    client, root, staff, participant, wid, vid, result = context
    slot = client.post(root + "/slots", headers=staff, json=slot_body(vid, hours=12))
    assert slot.status_code == 200, slot.text
    response = client.post(
        "/api/v1/participant/longitudinal/bookings",
        headers=participant,
        json={"slot_id": slot.json()["id"], "request_key": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


def delivery(app, wid):
    with app.state.database.sessions() as s:
        return s.scalar(
            select(NotificationDelivery).where(NotificationDelivery.workspace_id == wid)
        )


def send(app, did, calls):
    return mail.dispatch_one(
        app.state.database, app.state.settings, did, lambda *args: calls.append(args)
    )


def test_missing_preference_is_email_off(longitudinal, research_app):  # noqa: F811
    client, _, _, participant, wid, *_ = longitudinal
    response = client.get(
        f"/api/v1/workspaces/{wid}/collaboration/notification-preferences", headers=participant
    )
    assert response.json() == {"reminders": True, "email_reminders": False}
    booking(longitudinal)
    app = research_app[1]
    assert delivery(app, wid) is None
    preference(client, wid, participant)
    assert delivery(app, wid) is None  # Explicit opt-in does not backfill historical sources.


def test_opted_in_booking_email_does_not_depend_on_in_app_delivery(longitudinal, research_app):  # noqa: F811
    client, _, _, participant, wid, *_ = longitudinal
    preference(client, wid, participant)
    booking(longitudinal)
    app = research_app[1]
    row = delivery(app, wid)
    with app.state.database.sessions.begin() as s:
        s.get(Notification, row.notification_id).delivered_at = utcnow()
    calls = []
    assert send(app, row.id, calls)
    assert calls[0][1:] == ("interview_reminder", None)
    assert not send(app, row.id, calls)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "reason",
    ["email_optout", "master_optout", "cancel", "recipient", "issuer", "consent", "authority"],
)
def test_booking_pending_delivery_cancellation_and_rechecks(longitudinal, research_app, reason):  # noqa: F811
    client, _, _, participant, wid, *_ = longitudinal
    preference(client, wid, participant)
    booked = booking(longitudinal)
    app = research_app[1]
    row = delivery(app, wid)
    if reason.endswith("optout"):
        flags = {"email_reminders": False} if reason == "email_optout" else {"reminders": False}
        preference(client, wid, participant, **flags)
        assert delivery(app, wid).state == "cancelled"
        preference(client, wid, participant)
    elif reason == "cancel":
        response = client.post(
            "/api/v1/participant/longitudinal/bookings/" + booked["id"] + "/cancel",
            headers=participant,
            json={"expected_revision": 0},
        )
        assert response.status_code == 200, response.text
        assert delivery(app, wid).state == "cancelled"
    else:
        with app.state.database.sessions.begin() as s:
            if reason in {"recipient", "issuer"}:
                s.get(
                    User, row.recipient_id if reason == "recipient" else row.issuer_id
                ).status = "disabled"
            elif reason == "authority":
                member = s.scalar(
                    select(Membership).where(
                        Membership.workspace_id == wid, Membership.user_id == row.issuer_id
                    )
                )
                member.role = "viewer"
            else:
                from app.common.privacy_models import ConsentReceipt

                receipts = s.scalars(
                    select(ConsentReceipt).where(
                        ConsentReceipt.workspace_id == wid,
                        ConsentReceipt.subject_id == row.recipient_id,
                        ConsentReceipt.study_version_id.is_not(None),
                    )
                ).all()
                assert receipts
                receipt = receipts[0]
                s.add(
                    ConsentReceipt(
                        workspace_id=wid,
                        subject_id=row.recipient_id,
                        document_id=receipt.document_id,
                        study_version_id=receipt.study_version_id,
                        receipt_key=uuid4().hex,
                        presented_digest=receipt.presented_digest,
                        decision="withdrawn",
                    )
                )
    calls = []
    send(app, row.id, calls)
    assert not calls
    assert delivery(app, wid).state == "cancelled"


def test_reschedule_cancels_old_delivery_and_enqueues_current_revision(longitudinal, research_app):  # noqa: F811
    client, root, staff, participant, wid, vid, _ = longitudinal
    preference(client, wid, participant)
    booked = booking(longitudinal)
    app = research_app[1]
    old = delivery(app, wid)
    slot = client.post(root + "/slots", headers=staff, json=slot_body(vid, hours=14))
    assert slot.status_code == 200, slot.text
    response = client.post(
        "/api/v1/participant/longitudinal/bookings/" + booked["id"] + "/reschedule",
        headers=participant,
        json={"expected_revision": 0, "slot_id": slot.json()["id"]},
    )
    assert response.status_code == 200, response.text
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, old.id).state == "cancelled"
        newer = s.scalar(
            select(NotificationDelivery).where(
                NotificationDelivery.workspace_id == wid, NotificationDelivery.id != old.id
            )
        )
        assert newer and newer.state == "pending"
    calls = []
    assert not send(app, old.id, calls)
    assert send(app, newer.id, calls)
    assert len(calls) == 1


def test_master_optout_does_not_prevent_booking(longitudinal, research_app):  # noqa: F811
    client, _, _, participant, wid, *_ = longitudinal
    preference(client, wid, participant, reminders=False)
    booking(longitudinal)
    assert delivery(research_app[1], wid) is None


def test_legacy_preference_update_preserves_email_choice(longitudinal):  # noqa: F811
    client, _, _, participant, wid, *_ = longitudinal
    preference(client, wid, participant)
    response = client.put(
        f"/api/v1/workspaces/{wid}/collaboration/notification-preferences",
        headers=participant,
        json={"reminders": True},
    )
    assert response.json() == {"reminders": True, "email_reminders": True}


def diary(context):
    client, root, staff, _, _, _, result = context
    now = utcnow().replace(tzinfo=None)
    response = client.post(
        root + "/diary-schedules",
        headers=staff,
        json={
            "base_session_id": result["session_id"],
            "timezone": "UTC",
            "windows": [
                {
                    "opens": {"local": (now - timedelta(minutes=5)).isoformat()},
                    "due": {"local": (now + timedelta(hours=1)).isoformat()},
                    "grace": {"local": (now + timedelta(hours=2)).isoformat()},
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()[0]


@pytest.mark.parametrize(
    "reason", ["valid", "expired", "base_erased", "child_submitted", "restored"]
)
def test_diary_mail_is_bounded_by_current_window_and_participation(
    longitudinal,  # noqa: F811
    research_app,
    reason,
    collected,  # noqa: F811
    monkeypatch,
):
    client, _, _, participant, wid, vid, result = longitudinal
    _, base_url, cap, _, _, _ = collected
    response = client.put(
        base_url + "/answers/single",
        headers=cap,
        json={
            "schema_version": 1,
            "expected_revision": 0,
            "client_event_id": str(uuid4()),
            "status": "responded",
            "value": {"option_id": "no"},
        },
    )
    assert response.status_code == 200, response.text
    response = client.post(
        base_url + "/submit", headers=cap, json={"version_id": str(vid), "expected_revision": 1}
    )
    assert response.status_code == 200, response.text
    preference(client, wid, participant)
    occurrence = diary(longitudinal)
    app = research_app[1]
    row = delivery(app, wid)
    if reason in {"base_erased", "expired", "restored"}:
        with app.state.database.sessions.begin() as s:
            if reason == "base_erased":
                s.get(CollectionSession, UUID(result["session_id"])).state = "erased"
            elif reason == "expired":
                expired_clock = row.expires_at + timedelta(seconds=1)
                monkeypatch.setattr(mail, "utcnow", lambda: expired_clock)
            else:
                mail.quarantine_restored(s)
    if reason == "child_submitted":
        endpoint = (
            "/api/v1/participant/longitudinal/diary-occurrences/" + occurrence["id"] + "/start"
        )
        response = client.post(
            endpoint, headers=participant, json={"capability": uuid4().hex + uuid4().hex}
        )
        assert response.status_code == 200, response.text
        with app.state.database.sessions.begin() as s:
            s.get(CollectionSession, UUID(response.json()["session_id"])).state = "submitted"
    calls = []
    send(app, row.id, calls)
    assert len(calls) == (1 if reason == "valid" else 0)
    if calls:
        assert calls[0][1:] == ("diary_reminder", None)
