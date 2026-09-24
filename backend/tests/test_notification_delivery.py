from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from test_recruiting import configure, optin, recruitment  # noqa: F401

from app.auth.models import Membership, User, Workspace
from app.auth.outbox import capability
from app.auth.security import token_hash, utcnow
from app.collaboration import mail
from app.collaboration.models import NotificationDelivery
from app.common.errors import DomainError
from app.recruiting.models import Invitation

pytestmark = pytest.mark.db


@pytest.fixture
def queued(recruitment):  # noqa: F811
    client, app, actor, staff, issuer, wid, base, root, launch = recruitment
    configure(client, staff, root)
    participant, uid, _ = actor()
    profile, consent = optin(client, participant)
    app.state.settings.job_runner_enabled = True
    response = client.post(
        root + "/invitations",
        headers=staff,
        json={"source_kind": "public", "source_id": profile, "delivery": "email"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["invitation_token"] is None
    assert response.json()["delivery"] == "queued"
    iid = UUID(response.json()["invitation_id"])
    with app.state.database.sessions() as s:
        did = s.scalar(
            select(NotificationDelivery.id).where(NotificationDelivery.invitation_id == iid)
        )
    return client, app, staff, participant, uid, issuer, wid, base, root, iid, did, consent


def dispatch(queued, did=None, sender=None):
    _, app, *rest = queued
    return mail.dispatch_one(
        app.state.database, app.state.settings, did or queued[10], sender or (lambda *args: None)
    )


def test_local_email_is_captured_privately_without_returning_capability(queued):
    import json

    client, app, staff, _, _, _, _, base, _, iid, did, _ = queued
    app.state.settings.job_runner_enabled = False
    response = client.post(base + f"/recruiting/invitations/{iid}/delivery", headers=staff)
    assert response.status_code == 202
    captures = [
        json.loads(path.read_text())
        for path in (app.state.settings.private_root / "dev-mail").glob("*.json")
    ]
    messages = [capture for capture in captures if capture["purpose"] == "recruitment_invite"]
    assert len(messages) == 1
    assert messages[0]["token"] == capability(app.state.settings, "recruitment_invite", iid)
    assert messages[0]["token"] not in response.text
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, did).state == "sent"


def test_source_only_storage_and_stable_explicit_resend(queued):
    client, app, staff, _, _, _, _, base, _, iid, did, _ = queued
    delivered = []
    assert dispatch(queued, sender=lambda *args: delivered.append(args))
    raw = capability(app.state.settings, "recruitment_invite", iid)
    assert delivered[0][1:] == ("recruitment_invite", raw)
    with app.state.database.sessions.begin() as s:
        assert s.get(Invitation, iid).token_hash == token_hash(raw)
        assert s.get(NotificationDelivery, did).state == "sent"
        s.get(NotificationDelivery, did).created_at = utcnow() - timedelta(minutes=2)
        assert not {"email", "token", "payload", "payload_json"} & set(
            NotificationDelivery.__table__.columns.keys()
        )
    response = client.post(base + f"/recruiting/invitations/{iid}/delivery", headers=staff)
    assert response.status_code == 202, response.text
    with app.state.database.sessions() as s:
        rows = s.scalars(
            select(NotificationDelivery).where(NotificationDelivery.invitation_id == iid)
        ).all()
        assert len(rows) == 2
        newer = next(r.id for r in rows if r.id != did)
    assert dispatch(queued, newer, lambda *args: delivered.append(args))
    assert delivered[0] == delivered[1]
    assert (
        client.get("/api/v1/recruiting/invitation", headers={"X-Invitation-Token": raw}).status_code
        == 200
    )


@pytest.mark.parametrize(
    "change", ["issuer", "recipient", "membership", "revoked", "redeemed", "key", "epoch"]
)
def test_claim_reauthorizes_every_source(queued, change):
    _, app, _, _, uid, issuer, wid, _, _, iid, did, _ = queued
    with app.state.database.sessions.begin() as s:
        if change in {"issuer", "recipient"}:
            s.get(User, issuer if change == "issuer" else uid).status = "disabled"
        elif change == "membership":
            member = s.scalar(
                select(Membership).where(
                    Membership.workspace_id == wid, Membership.user_id == issuer
                )
            )
            member.role = "viewer"
        elif change in {"revoked", "redeemed"}:
            setattr(s.get(Invitation, iid), change + "_at", utcnow())
        elif change == "epoch":
            s.get(Workspace, wid).privacy_epoch += 1
        else:
            app.state.settings.secret_key = SecretStr(
                "different-key-for-delivery-regression-000000000000000000000"
            )
    calls = []
    assert dispatch(queued, sender=lambda *args: calls.append(args))
    assert not calls
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, did).state == "cancelled"


def test_withdraw_then_reoptin_does_not_revive_mail(queued):
    client, app, _, participant, _, _, _, _, _, _, did, consent = queued
    body = consent | {"decision": "withdrawn", "receipt_key": uuid4().hex}
    assert client.put("/api/v1/panel/profile", headers=participant, json=body).status_code == 200
    assert (
        client.put(
            "/api/v1/panel/profile",
            headers=participant,
            json=consent | {"receipt_key": uuid4().hex},
        ).status_code
        == 200
    )
    assert not dispatch(queued)
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, did).state == "cancelled"


@pytest.mark.parametrize(
    "code,expected,state",
    [
        ("DELIVERY_UNAVAILABLE", 3, "failed"),
        ("DELIVERY_REJECTED", 1, "failed"),
        ("DELIVERY_UNCERTAIN", 1, "uncertain"),
        ("OTHER", 1, "uncertain"),
    ],
)
def test_retry_only_predispatch_unavailability(queued, code, expected, state, caplog):
    app, did = queued[1], queued[10]
    calls = []

    def sender(*args):
        calls.append(1)
        raise DomainError(code, "private recipient and provider details", 503)

    for index in range(expected):
        assert dispatch(queued, sender=sender)
        with app.state.database.sessions.begin() as s:
            row = s.get(NotificationDelivery, did)
            assert row.attempts == index + 1
            if index + 1 < expected:
                assert row.run_after > utcnow()
                row.run_after = utcnow() - timedelta(seconds=1)
    assert not dispatch(queued, sender=sender)
    assert len(calls) == expected and "private recipient" not in caplog.text
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, did).state == state


def test_crash_after_acceptance_never_replays(queued):
    app, did = queued[1], queued[10]
    accepted = []

    class ProcessCrash(BaseException):
        pass

    def sender(*args):
        accepted.append(1)
        raise ProcessCrash()

    with pytest.raises(ProcessCrash):
        dispatch(queued, sender=sender)
    with app.state.database.sessions.begin() as s:
        row = s.get(NotificationDelivery, did)
        assert row.state == "dispatching"
        row.lease_expires_at = utcnow() - timedelta(seconds=1)
    assert not dispatch(queued, sender=sender)
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, did).state == "uncertain"
    assert accepted == [1]


def test_concurrent_enqueue_and_physical_claim(queued):
    client, app, staff, _, _, _, _, base, _, iid, did, _ = queued
    endpoint = base + f"/recruiting/invitations/{iid}/delivery"
    with ThreadPoolExecutor(2) as pool:
        responses = list(
            pool.map(lambda _: client.post(endpoint, headers=staff).status_code, range(2))
        )
    assert responses == [202, 202]
    with app.state.database.sessions() as s:
        assert (
            len(
                s.scalars(
                    select(NotificationDelivery).where(NotificationDelivery.invitation_id == iid)
                ).all()
            )
            == 1
        )
    started, release = Event(), Event()
    calls = []

    def sender(*args):
        calls.append(1)
        started.set()
        assert release.wait(5)

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(dispatch, queued, sender=sender)
        assert started.wait(5)
        try:
            assert pool.submit(dispatch, queued, sender=sender).result(5) is False
        finally:
            release.set()
        assert first.result(5)
    assert calls == [1]


def test_restore_quarantine_explicit_reissue_and_retention(queued):
    client, app, staff, _, _, _, _, base, _, iid, did, _ = queued
    with app.state.database.sessions.begin() as s:
        mail.quarantine_restored(s)
        assert s.get(NotificationDelivery, did).outcome == "restore_quarantine"
    assert not dispatch(queued)
    assert (
        client.post(base + f"/recruiting/invitations/{iid}/delivery", headers=staff).status_code
        == 202
    )
    with app.state.database.sessions.begin() as s:
        rows = s.scalars(
            select(NotificationDelivery).where(NotificationDelivery.invitation_id == iid)
        ).all()
        assert len(rows) == 2
        s.get(NotificationDelivery, did).expires_at = utcnow() - timedelta(days=8)
        s.flush()
        mail.recover(s)
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, did) is None
        assert all(
            set(row) == {"state", "outcome", "count", "oldest_age_seconds"}
            for row in mail.aggregates(s)
        )


@pytest.mark.parametrize("role", ["recipient", "issuer"])
def test_scoped_privacy_cancels_recipient_or_issuer(queued, role):
    from app.privacy_ops.service import invalidate_subject_safely

    app, uid, issuer, wid, did = queued[1], queued[4], queued[5], queued[6], queued[10]
    with app.state.database.sessions.begin() as s:
        invalidate_subject_safely(s, wid, uid if role == "recipient" else issuer)
    assert not dispatch(queued)
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, did).state == "cancelled"


def test_source_cascade_and_cross_workspace_fk(queued):
    app, iid, did = queued[1], queued[9], queued[10]
    with app.state.database.sessions.begin() as s:
        row = s.get(NotificationDelivery, did)
        foreign = s.scalar(select(Workspace.id).where(Workspace.id != row.workspace_id))
        with pytest.raises(IntegrityError), s.begin_nested():
            row.workspace_id = foreign
            s.flush()
        s.execute(delete(Invitation).where(Invitation.id == iid))
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, did) is None


def test_private_contact_email_is_rejected_without_creating_candidate(recruitment):  # noqa: F811
    from research_support import document

    from app.recruiting.models import Candidate

    client, app, actor, staff, issuer, wid, base, root, _ = recruitment
    configure(client, staff, root)
    doc = document(client, base, staff, purpose="private_panel")
    response = client.post(
        base + "/recruiting/contacts/import",
        headers=staff,
        json={
            "rows": [{"mail": "synthetic-private@example.test"}],
            "mapping": {"email": "mail"},
            "source": "synthetic opt-in",
            "document_id": doc["id"],
            "consent_confirmed": True,
            "retention_until": (utcnow() + timedelta(days=30)).isoformat(),
            "preview": False,
        },
    )
    assert response.status_code == 200, response.text
    contact = response.json()["contact_ids"][0]
    response = client.post(
        root + "/invitations",
        headers=staff,
        json={"source_kind": "private", "source_id": contact, "delivery": "email"},
    )
    assert response.status_code == 409, response.text
    with app.state.database.sessions() as s:
        assert not s.scalars(select(Candidate).where(Candidate.workspace_id == wid)).all()
    response = client.post(
        root + "/invitations", headers=staff, json={"source_kind": "private", "source_id": contact}
    )
    assert response.status_code == 201 and response.json()["delivery"] == "manual"


@pytest.mark.parametrize("role", ["recipient", "issuer"])
def test_global_erasure_cancels_pending_optional_mail(queued, role):
    from app.common.privacy import lock_workspace
    from app.privacy_ops.account import affected_workspaces, apply_account_restriction

    app, uid, issuer, did = queued[1], queued[4], queued[5], queued[10]
    subject = uid if role == "recipient" else issuer
    with app.state.database.sessions.begin() as s:
        for scope in affected_workspaces(s, subject):
            lock_workspace(s, scope)
        apply_account_restriction(s, subject)
    assert not dispatch(queued)
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, did).state == "cancelled"


def test_privacy_waits_for_physical_send_without_completion_deadlock(queued):
    from app.common.privacy import lock_workspace

    app, uid, wid, did = queued[1], queued[4], queued[6], queued[10]
    started, release, restricting = Event(), Event(), Event()

    def sender(*args):
        with app.state.database.sessions.begin() as s:
            assert s.scalar(
                select(Workspace).where(Workspace.id == wid).with_for_update(nowait=True)
            )
        started.set()
        assert release.wait(5)

    def restrict():
        restricting.set()
        with app.state.database.sessions.begin() as s:
            lock_workspace(s, wid)
            mail.cancel_subject(s, uid, wid)

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(dispatch, queued, sender=sender)
        assert started.wait(5)
        second = pool.submit(restrict)
        try:
            assert restricting.wait(5)
            assert not second.done()
        finally:
            release.set()
        assert first.result(5)
        second.result(5)
    with app.state.database.sessions() as s:
        assert s.get(NotificationDelivery, did).state == "sent"


def test_legacy_capability_cannot_be_reconstructed(queued):
    client, app, staff, _, _, _, _, base, _, iid, _, _ = queued
    with app.state.database.sessions.begin() as s:
        s.get(Invitation, iid).token_hash = token_hash("old-manual-capability")
    response = client.post(base + f"/recruiting/invitations/{iid}/delivery", headers=staff)
    assert response.status_code == 409
    assert (
        client.get(
            "/api/v1/recruiting/invitation", headers={"X-Invitation-Token": "old-manual-capability"}
        ).status_code
        == 200
    )
