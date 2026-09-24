from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from app.auth import outbox
from app.auth.models import AuthDelivery, Membership, OneTimeToken, User, WorkspaceInvite
from app.auth.security import token_hash, utcnow
from app.auth.service import AuthService, create_workspace, invite_member
from app.common.errors import DomainError

pytestmark = pytest.mark.db


@pytest.fixture
def mail(db_engine, settings):
    settings.job_runner_enabled = True
    database = SimpleNamespace(
        engine=db_engine, sessions=sessionmaker(db_engine, expire_on_commit=False)
    )
    delivered = []
    auth = AuthService(database, settings, lambda *args: delivered.append(args))
    email = f"outbox-{uuid4().hex}@example.test"
    auth.register(email, "Synthetic-password-2026!", "Synthetic")
    with database.sessions() as session:
        user = session.scalar(select(User).where(User.email == email))
        delivery = session.scalar(
            select(AuthDelivery).join(OneTimeToken).where(OneTimeToken.user_id == user.id)
        )
        return database, settings, auth, delivered, user.id, delivery.id


def dispatch(mail, delivery_id=None, sender=None):
    db, settings, _, delivered, _, did = mail
    return outbox.dispatch_one(
        db, settings, delivery_id or did, sender or (lambda *args: delivered.append(args))
    )


def test_registration_enqueue_only_verifier_storage_and_domain_separation(mail):
    db, settings, _, delivered, uid, did = mail
    assert not delivered
    with db.sessions() as session:
        row = session.get(AuthDelivery, did)
        token = session.get(OneTimeToken, row.token_id)
        raw = outbox.capability(settings, "verify", token.id)
        assert token.token_hash == token_hash(raw)
        assert raw != outbox.capability(settings, "reset", token.id)
        assert raw != outbox.capability(settings, "verify", uuid4())
        assert set(AuthDelivery.__table__.columns.keys()).isdisjoint(
            {"email", "recipient", "token", "payload"}
        )
        assert row.state == "pending" and row.attempts == 0
    assert dispatch(mail)
    assert delivered[0][2] == raw
    with db.sessions() as session:
        assert session.get(AuthDelivery, did).state == "sent"


def test_newer_legacy_token_does_not_hide_recoverable_source(mail):
    db, settings, auth, delivered, uid, did = mail
    with db.sessions.begin() as session:
        row = session.get(AuthDelivery, did)
        source_id = row.token_id
        email = session.get(User, uid).email
        session.add(
            OneTimeToken(
                user_id=uid,
                purpose="verify",
                token_hash=token_hash("legacy-" + uuid4().hex),
                expires_at=utcnow() + timedelta(days=30),
            )
        )
    auth.request_token(email, "verify")
    with db.sessions() as session:
        tokens = session.scalars(select(OneTimeToken).where(OneTimeToken.user_id == uid)).all()
        rows = session.scalars(
            select(AuthDelivery).join(OneTimeToken).where(OneTimeToken.user_id == uid)
        ).all()
        assert len(tokens) == 2
        assert len(rows) == 1 and rows[0].token_id == source_id


def test_concurrent_request_and_claim_are_single_send(mail):
    db, settings, auth, delivered, uid, did = mail
    with db.sessions() as session:
        email = session.get(User, uid).email
    barrier = Barrier(2)

    def request():
        barrier.wait()
        auth.request_token(email, "verify")

    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda _: request(), range(2)))
    with db.sessions() as session:
        assert (
            len(
                session.scalars(
                    select(AuthDelivery).join(OneTimeToken).where(OneTimeToken.user_id == uid)
                ).all()
            )
            == 1
        )
    started, release = Event(), Event()

    def sender(*args):
        delivered.append(args)
        started.set()
        assert release.wait(5)

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(dispatch, mail, sender=sender)
        assert started.wait(5)
        second = pool.submit(dispatch, mail)
        try:
            assert second.result(5) is False
        finally:
            release.set()
        assert first.result(5)
    assert len(delivered) == 1


def test_resend_preserves_old_link_and_consumption_invalidates_all(mail):
    db, settings, auth, delivered, uid, did = mail
    assert dispatch(mail)
    old = delivered[0][2]
    with db.sessions.begin() as session:
        session.get(AuthDelivery, did).created_at = utcnow() - timedelta(minutes=2)
        email = session.get(User, uid).email
    auth.request_token(email, "verify")
    with db.sessions() as session:
        rows = session.scalars(
            select(AuthDelivery)
            .join(OneTimeToken)
            .where(OneTimeToken.user_id == uid)
            .order_by(AuthDelivery.created_at)
        ).all()
        assert len(rows) == 2 and rows[0].token_id == rows[1].token_id
        newer = rows[1].id
    assert dispatch(mail, newer)
    assert delivered[-1][2] == old
    # Legacy already-sent links survive introduction of recoverable HMAC sources.
    legacy = "legacy-" + uuid4().hex
    with db.sessions.begin() as session:
        session.add(
            OneTimeToken(
                user_id=uid,
                purpose="verify",
                token_hash=token_hash(legacy),
                expires_at=utcnow() + timedelta(minutes=10),
            )
        )
    auth.consume_token(legacy, "verify")
    with pytest.raises(DomainError):
        auth.consume_token(old, "verify")
    with db.sessions() as session:
        assert all(
            t.used_at
            for t in session.scalars(select(OneTimeToken).where(OneTimeToken.user_id == uid))
        )


@pytest.mark.parametrize(
    "code,final",
    [
        ("DELIVERY_UNAVAILABLE", "failed"),
        ("DELIVERY_REJECTED", "failed"),
        ("DELIVERY_UNCERTAIN", "uncertain"),
        ("UNEXPECTED", "uncertain"),
    ],
)
def test_only_known_predispatch_failure_retries_at_most_three(mail, code, final, caplog):
    db, _, _, _, _, did = mail
    calls = []

    def sender(*args):
        calls.append(1)
        raise DomainError(code, "private provider detail", 503)

    expected = 3 if code == "DELIVERY_UNAVAILABLE" else 1
    for attempt in range(expected):
        assert dispatch(mail, sender=sender)
        with db.sessions.begin() as session:
            row = session.get(AuthDelivery, did)
            assert row.attempts == attempt + 1
            if attempt + 1 < expected:
                assert row.state == "pending" and row.run_after > utcnow()
                row.run_after = utcnow() - timedelta(seconds=1)
    assert dispatch(mail, sender=sender) is False
    with db.sessions() as session:
        assert session.get(AuthDelivery, did).state == final
    assert len(calls) == expected and "private provider detail" not in caplog.text


def test_crash_after_acceptance_never_auto_replays(mail):
    db, _, _, delivered, _, did = mail

    class Crash(BaseException):
        pass

    def sender(*args):
        delivered.append(args)
        raise Crash()

    with pytest.raises(Crash):
        dispatch(mail, sender=sender)
    with db.sessions.begin() as session:
        row = session.get(AuthDelivery, did)
        assert row.state == "dispatching"
        row.lease_expires_at = utcnow() - timedelta(seconds=1)
    assert dispatch(mail) is False
    with db.sessions() as session:
        row = session.get(AuthDelivery, did)
        assert (row.state, row.outcome) == ("uncertain", "dispatch_expired")
    assert len(delivered) == 1


def test_restore_quarantines_pending_and_dispatching_but_fresh_request_recovers(mail):
    db, _, auth, delivered, uid, did = mail
    with db.sessions.begin() as session:
        user = session.get(User, uid)
        email = user.email
        reset = outbox.enqueue_auth(session, user, "reset", mail[1])
        session.get(AuthDelivery, reset).state = "dispatching"
        outbox.quarantine_restored(session)
    assert not dispatch(mail) and not dispatch(mail, reset)
    with db.sessions() as session:
        assert session.get(AuthDelivery, did).outcome == "restore_quarantine"
        assert session.get(AuthDelivery, reset).outcome == "restore_quarantine"
    auth.request_token(email, "verify")
    with db.sessions() as session:
        fresh = session.scalar(
            select(AuthDelivery)
            .join(OneTimeToken)
            .where(OneTimeToken.user_id == uid, AuthDelivery.state == "pending")
        )
        assert fresh.id != did
    assert dispatch(mail, fresh.id) and len(delivered) == 1


@pytest.mark.parametrize("mutation", ["used", "expired", "key", "purpose", "disabled"])
def test_claim_rechecks_source_and_user(mail, mutation):
    db, settings, _, _, uid, did = mail
    with db.sessions.begin() as session:
        row = session.get(AuthDelivery, did)
        token = session.get(OneTimeToken, row.token_id)
        if mutation == "used":
            token.used_at = utcnow()
        elif mutation == "expired":
            token.expires_at = utcnow() - timedelta(seconds=1)
        elif mutation == "key":
            token.token_hash = "0" * 64
        elif mutation == "purpose":
            token.purpose = "reset"
        else:
            session.get(User, uid).status = "disabled"
    assert dispatch(mail)
    assert not mail[3]
    with db.sessions() as session:
        assert session.get(AuthDelivery, did).state == "cancelled"


def test_source_delete_cascades_and_metadata_retention(mail):
    db, _, _, _, uid, did = mail
    with db.sessions.begin() as session:
        session.execute(delete(OneTimeToken).where(OneTimeToken.user_id == uid))
    with db.sessions() as session:
        assert session.get(AuthDelivery, did) is None


@pytest.fixture
def invitations(mail):
    db, settings, _, _, uid, _ = mail
    with db.sessions.begin() as session:
        session.get(User, uid).verified_at = utcnow()
        recipient = User(
            email=f"recipient-{uuid4().hex}@example.test",
            password_hash="synthetic",
            verified_at=utcnow(),
        )
        session.add(recipient)
        session.flush()
        ws = create_workspace(session, uid, "Mail scope")
        record, did = invite_member(session, uid, ws.id, recipient.email, "viewer", settings)
        return ws.id, recipient.id, record.id, did


def test_invitation_exact_reuse_role_change_replaces_and_cancels(mail, invitations):
    db, settings, _, _, uid, _ = mail
    wid, recipient, iid, did = invitations
    with db.sessions.begin() as session:
        email = session.get(User, recipient).email
        same, repeated = invite_member(session, uid, wid, email, "viewer", settings)
        assert same.id == iid and repeated == did
        changed, changed_delivery = invite_member(session, uid, wid, email, "researcher", settings)
        assert changed.id != iid and changed_delivery != did
    with db.sessions() as session:
        assert session.get(AuthDelivery, did).state == "cancelled"
        assert session.get(WorkspaceInvite, iid).revoked_at
    assert not dispatch(mail, did)
    assert dispatch(mail, changed_delivery)


@pytest.mark.parametrize(
    "mutation",
    [
        "role",
        "inviter_disabled",
        "inviter_restricted",
        "recipient_disabled",
        "recipient_restricted",
        "workspace",
    ],
)
def test_invitation_claim_reauthorizes(mail, invitations, mutation):
    from app.auth.models import Workspace
    from app.common.privacy_models import PrivacyRestriction

    db, _, _, _, uid, _ = mail
    wid, recipient, _, did = invitations
    with db.sessions.begin() as session:
        if mutation == "role":
            session.scalar(
                select(Membership).where(Membership.workspace_id == wid, Membership.user_id == uid)
            ).role = "viewer"
        elif mutation == "workspace":
            session.get(Workspace, wid).status = "suspended"
        elif mutation.endswith("disabled"):
            session.get(
                User, uid if mutation.startswith("inviter") else recipient
            ).status = "disabled"
        else:
            session.add(
                PrivacyRestriction(
                    workspace_id=wid,
                    subject_id=uid if mutation.startswith("inviter") else recipient,
                )
            )
    assert dispatch(mail, did)
    assert not mail[3]
    with db.sessions() as session:
        assert session.get(AuthDelivery, did).state == "cancelled"


def test_recovery_commits_before_owner_lock_and_account_cascade(mail, monkeypatch):
    db, settings, _, _, uid, did = mail
    recovered, user_locked = Event(), Event()
    with db.sessions.begin() as session:
        row = session.get(AuthDelivery, did)
        row.state = "dispatching"
        row.lease_expires_at = utcnow() - timedelta(seconds=1)
        reset_id = outbox.enqueue_auth(session, session.get(User, uid), "reset", settings)
    original = outbox.recover

    def recover(session):
        original(session)
        session.flush()
        recovered.set()
        assert user_locked.wait(5)

    def erase():
        assert recovered.wait(5)
        with db.sessions.begin() as session:
            session.scalar(select(User).where(User.id == uid).with_for_update())
            user_locked.set()
            session.execute(delete(OneTimeToken).where(OneTimeToken.user_id == uid))

    monkeypatch.setattr(outbox, "recover", recover)
    with ThreadPoolExecutor(2) as pool:
        deleting = pool.submit(erase)
        sending = pool.submit(dispatch, mail, reset_id)
        assert sending.result(8) is False
        deleting.result(8)
    assert not mail[3]


def test_changed_inviter_replaces_invitation(mail, invitations):
    db, settings, _, _, uid, _ = mail
    wid, recipient, iid, did = invitations
    with db.sessions.begin() as session:
        other = User(
            email=f"other-inviter-{uuid4().hex}@example.test",
            password_hash="synthetic",
            verified_at=utcnow(),
        )
        session.add(other)
        session.flush()
        session.add(Membership(workspace_id=wid, user_id=other.id, role="admin"))
        session.flush()
        changed, new_delivery = invite_member(
            session, other.id, wid, session.get(User, recipient).email, "viewer", settings
        )
        assert changed.id != iid and new_delivery != did
    with db.sessions() as session:
        assert session.get(AuthDelivery, did).state == "cancelled"
        assert session.get(WorkspaceInvite, iid).revoked_at


def test_internal_aggregates_expose_only_bounded_metadata(mail):
    db, _, _, _, uid, did = mail
    with db.sessions() as session:
        rows = outbox.aggregates(session)
    assert rows and all(
        set(row) == {"state", "outcome", "count", "oldest_age_seconds"} for row in rows
    )
    assert all(row["count"] >= 1 and row["oldest_age_seconds"] >= 0 for row in rows)
