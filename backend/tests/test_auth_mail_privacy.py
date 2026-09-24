from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event

import pytest
import test_auth_outbox as fixtures
from sqlalchemy import select

from app.auth import outbox
from app.auth.models import AuthDelivery, OneTimeToken, User, Workspace, WorkspaceInvite
from app.auth.security import utcnow
from app.common.privacy import lock_workspace

pytestmark = pytest.mark.db
mail = fixtures.mail
invitations = fixtures.invitations
dispatch = fixtures.dispatch


@pytest.mark.parametrize("subject", ["inviter", "recipient"])
def test_scoped_restriction_cancels_invites_not_global_auth(mail, invitations, subject):
    db, _, _, _, uid, global_delivery = mail
    wid, recipient, iid, did = invitations
    with db.sessions.begin() as session:
        lock_workspace(session, wid)
        outbox.restrict_subject(session, wid, uid if subject == "inviter" else recipient)
    with db.sessions() as session:
        assert session.get(AuthDelivery, did).state == "cancelled"
        assert session.get(WorkspaceInvite, iid).revoked_at
        assert session.get(AuthDelivery, global_delivery).state == "pending"
        assert session.get(User, uid).status == "active"


@pytest.mark.parametrize("subject", ["inviter", "recipient"])
def test_global_erasure_cancels_invites_and_cascades_auth(mail, invitations, subject):
    from app.privacy_ops.account import affected_workspaces, apply_account_restriction

    db, settings, _, _, uid, global_delivery = mail
    wid, recipient, iid, did = invitations
    sid = uid if subject == "inviter" else recipient
    with db.sessions.begin() as session:
        if subject == "recipient":
            global_delivery = outbox.enqueue_auth(
                session, session.get(User, sid), "reset", settings
            )
        for scope in affected_workspaces(session, sid):
            lock_workspace(session, scope)
        apply_account_restriction(session, sid)
    with db.sessions() as session:
        assert session.get(AuthDelivery, did).state == "cancelled"
        assert session.get(WorkspaceInvite, iid).revoked_at
        assert session.get(AuthDelivery, global_delivery) is None
        assert not session.scalars(select(OneTimeToken).where(OneTimeToken.user_id == sid)).all()
        assert session.get(User, sid).status == "disabled"


def test_privacy_waits_for_physical_send_and_completion_never_deadlocks(mail, invitations):
    db, _, _, _, uid, _ = mail
    wid, recipient, iid, did = invitations
    started, release, restricting = Event(), Event(), Event()

    def sender(*args):
        # Dispatch authorization has committed; SMTP does not hold a workspace SQL lock.
        with db.sessions.begin() as session:
            assert session.scalar(
                select(Workspace).where(Workspace.id == wid).with_for_update(nowait=True)
            )
        started.set()
        assert release.wait(5)

    def restrict():
        restricting.set()
        with db.sessions.begin() as session:
            lock_workspace(session, wid)
            outbox.restrict_subject(session, wid, recipient)

    with ThreadPoolExecutor(2) as pool:
        send = pool.submit(dispatch, mail, did, sender)
        assert started.wait(5)
        restriction = pool.submit(restrict)
        try:
            assert restricting.wait(5)
            assert not restriction.done()
        finally:
            release.set()
        assert send.result(5)
        restriction.result(5)
    with db.sessions() as session:
        # Already committed dispatch cannot be recalled by later cancellation.
        assert session.get(AuthDelivery, did).state == "sent"
        assert session.get(WorkspaceInvite, iid).revoked_at


def test_terminal_metadata_pruned_without_deleting_source(mail):
    db, _, _, _, _, did = mail
    assert dispatch(mail)
    with db.sessions.begin() as session:
        row = session.get(AuthDelivery, did)
        token_id = row.token_id
        row.expires_at = utcnow() - timedelta(days=8)
    with db.sessions.begin() as session:
        outbox.prune(session)
    with db.sessions() as session:
        assert session.get(AuthDelivery, did) is None
        assert session.get(OneTimeToken, token_id) is not None


def test_spool_expiry_independent_of_database_retention(settings):
    import os
    import time

    from app.auth.delivery import cleanup_local, deliver_local

    deliver_local(settings, "synthetic@example.test", "reset", "synthetic-code")
    capture = next((settings.private_root / "dev-mail").glob("*.json"))
    os.utime(capture, (time.time() - 86401, time.time() - 86401))
    cleanup_local(settings)
    assert not capture.exists()


def test_restored_presend_snapshot_cannot_replay_postsnapshot_accepted_mail(mail, db_engine):
    from uuid import uuid4

    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    from app.auth.delivery import deliver_local
    from app.privacy_ops.restore import copy_files, export_tombstones, replay, restore_ready

    db, settings, _, _, uid, did = mail
    source = db_engine.url
    assert source.database.endswith("_test")
    name = "mail_" + uuid4().hex + "_restore"
    target_url = source.set(database=name)
    source_files = settings.private_root.resolve()
    target_files = source_files.parent / ("mail_" + uuid4().hex + "_restore")
    deliver_local(settings, "synthetic@example.test", "reset", "snapshot-code")
    copy_files(source_files, target_files)
    db_engine.dispose()
    admin = create_engine(
        source, isolation_level="AUTOCOMMIT", poolclass=NullPool, hide_parameters=True
    )
    target = create_engine(target_url, poolclass=NullPool, hide_parameters=True)
    created = False
    try:
        with admin.connect() as conn:
            quote = conn.dialect.identifier_preparer.quote_identifier
            conn.exec_driver_sql(f"CREATE DATABASE {quote(name)} TEMPLATE {quote(source.database)}")
            created = True
        assert dispatch(mail)
        with db.sessions() as session:
            assert session.get(AuthDelivery, did).state == "sent"
            path = source_files / "mail-manifest.json"
            key = b"synthetic-restore-key-at-least-32-bytes"
            digest = export_tombstones(session, path, key)
        assert not restore_ready(target, target_files)
        replay(
            source.render_as_string(hide_password=False),
            target_url.render_as_string(hide_password=False),
            source_files,
            target_files,
            path,
            key,
            digest,
        )
        assert restore_ready(target, target_files)
        from sqlalchemy.orm import Session

        with Session(target) as session:
            restored = session.get(AuthDelivery, did)
            assert (restored.state, restored.outcome) == ("uncertain", "restore_quarantine")
        assert not list((target_files / "dev-mail").glob("*.json"))
    finally:
        target.dispose()
        if created:
            with admin.connect() as conn:
                quote = conn.dialect.identifier_preparer.quote_identifier
                conn.exec_driver_sql(f"DROP DATABASE {quote(name)}")
        admin.dispose()
