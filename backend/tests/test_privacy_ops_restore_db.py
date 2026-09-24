"""Physical PostgreSQL snapshot drill, never a migration/reset of the target.

The guarded test owner needs CREATEDB on the development cluster. TEMPLATE copies
real migrated tables, constraints and data; this is not a pg_dump format test.
Only a newly created, unpredictable *_restore database is ever dropped. Run
serially through app.test_runner, with no other sessions on the source *_test.
"""

import json
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from research_support import upload
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.analytics.models import Report
from app.auth.models import Membership
from app.auth.security import utcnow
from app.collaboration.models import ReportComment, ReportGrant
from app.common.privacy import restricted
from app.common.privacy_models import Asset
from app.privacy_ops.restore import copy_files, export_tombstones, replay, restore_ready
from app.reviews.models import LedgerAccount, LedgerEntry, LedgerTransaction
from app.reviews.service import post as post_ledger
from app.studies.models import Study

pytestmark = pytest.mark.db


def journal_snapshot(session, workspace_id):
    """Exact financial rows, including nonzero postings, not an empty balance sum."""
    transactions = session.execute(
        select(
            LedgerTransaction.id,
            LedgerTransaction.command_key,
            LedgerTransaction.currency,
            LedgerTransaction.reversal_of,
        )
        .where(LedgerTransaction.workspace_id == workspace_id)
        .order_by(LedgerTransaction.id)
    ).all()
    entries = session.execute(
        select(
            LedgerEntry.id,
            LedgerEntry.transaction_id,
            LedgerEntry.account_id,
            LedgerAccount.code,
            LedgerAccount.currency,
            LedgerEntry.amount_millimes,
        )
        .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
        .where(LedgerEntry.workspace_id == workspace_id)
        .order_by(LedgerEntry.id)
    ).all()
    assert len(transactions) == 1 and len(entries) == 2
    assert {(entry.code, entry.amount_millimes) for entry in entries} == {
        ("expense", 1750),
        ("payable", -1750),
    }
    for transaction in transactions:
        postings = [entry for entry in entries if entry.transaction_id == transaction.id]
        assert len(postings) == 2
        assert sum(entry.amount_millimes for entry in postings) == 0
        assert all(entry.currency == transaction.currency == "TND" for entry in postings)
    return transactions, entries


def test_actual_postgresql_snapshot_replays_latest_erasure(
    migrated_database, research_app, db_engine, tmp_path, tmp_path_factory, monkeypatch
):
    client, app, actor = research_app
    headers, uid, wid = actor()
    _, recipient, _ = actor(wid, "viewer")
    base = f"/api/v1/workspaces/{wid}"
    aid = UUID(upload(client, base, headers)["asset"]["id"])
    with Session(db_engine) as session, session.begin():
        asset = session.get(Asset, aid)
        storage_key = asset.storage_key
        owner = session.scalar(select(Membership).where(Membership.user_id == uid))
        study = Study(
            workspace_id=wid,
            title="Synthetic restore drill",
            owner_membership_id=owner.id,
            retention_policy_id=asset.retention_policy_id,
        )
        session.add(study)
        session.flush()
        report = Report(workspace_id=wid, study_id=study.id)
        session.add(report)
        session.flush()
        grant = ReportGrant(
            workspace_id=wid, report_id=report.id, issuer_id=uid, recipient_id=recipient, revision=1
        )
        comment = ReportComment(
            workspace_id=wid,
            report_id=report.id,
            author_id=uid,
            text="synthetic raw snapshot content",
        )
        session.add_all([grant, comment])
        session.flush()
        grant_id, comment_id = grant.id, comment.id
        # Use the real journal service (which creates accounts and paired entries).
        # This proves financial retention, not a new participant reward award.
        post_ledger(
            session, wid, "restore-retained-journal", [("expense", 1750), ("payable", -1750)]
        )
    with Session(db_engine) as session:
        journal_before = journal_snapshot(session, wid)

    source = make_url(migrated_database)
    assert source.database.endswith("_test")
    assert (
        source.database
        != make_url(app.state.settings.migration_database_url.get_secret_value()).database
    )
    name = "p17_" + uuid4().hex + "_restore"
    target_url = source.set(database=name)
    source_files = app.state.settings.private_root.resolve()
    target_files = tmp_path_factory.mktemp("snapshot").resolve() / "files_restore"
    copy_files(source_files, target_files)
    assert (target_files / "assets" / storage_key).is_file()
    # No fixture or live app pool may keep the template open during the copy.
    app.state.database.engine.dispose()
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
        with Session(target) as session:
            assert not restricted(session, wid, uid)
            assert session.get(Asset, aid).state == "ready"
            assert not session.get(ReportGrant, grant_id).revoked
            assert session.get(ReportComment, comment_id).text
            assert journal_snapshot(session, wid) == journal_before
        assert not restore_ready(target, target_files)

        # Contact holds have no account subject and must independently block
        # readiness for both post-snapshot additions and stale restored holds.
        from app.privacy_ops.lifecycle_models import ContactHold

        contact_id = uuid4()
        with Session(db_engine) as session, session.begin():
            contact_hold = ContactHold(
                workspace_id=wid,
                contact_id=contact_id,
                reason_code="synthetic-dispute",
                reviewed_by=uid,
                review_deadline=utcnow() + timedelta(days=1),
            )
            session.add(contact_hold)
            session.flush()
            contact_hold_id = contact_hold.id
        contact_key = b"synthetic-contact-hold-signing-key"
        contact_manifest = tmp_path / "contact-hold.json"
        with Session(db_engine) as session:
            contact_digest = export_tombstones(session, contact_manifest, contact_key)
        with pytest.raises(ValueError, match="contact holds differ"):
            replay(
                source,
                target_url,
                source_files,
                target_files,
                contact_manifest,
                contact_key,
                contact_digest,
            )
        assert not restore_ready(target, target_files)
        assert (target_files / "assets" / storage_key).is_file()
        with Session(db_engine) as session, session.begin():
            session.get(ContactHold, contact_hold_id).released_at = utcnow()
        with Session(target) as session, session.begin():
            stale_contact = ContactHold(
                workspace_id=wid,
                contact_id=contact_id,
                reason_code="synthetic-old-dispute",
                reviewed_by=uid,
                review_deadline=utcnow() + timedelta(days=1),
            )
            session.add(stale_contact)
            session.flush()
            stale_contact_id = stale_contact.id
        contact_released = tmp_path / "contact-released.json"
        with Session(db_engine) as session:
            released_digest = export_tombstones(session, contact_released, contact_key)
        with pytest.raises(ValueError, match="contact holds differ"):
            replay(
                source,
                target_url,
                source_files,
                target_files,
                contact_released,
                contact_key,
                released_digest,
            )
        assert not restore_ready(target, target_files)
        assert (target_files / "assets" / storage_key).is_file()
        with Session(target) as session, session.begin():
            session.get(ContactHold, stale_contact_id).released_at = utcnow()

        # A reviewed hold created after the snapshot must stop replay before
        # any destructive work; the snapshot cannot supply its attribution.
        key = b"synthetic-restore-test-key-32-bytes"
        hold = client.post(
            base + "/privacy-ops/holds",
            headers=headers,
            json={
                "subject_id": str(uid),
                "reason": "synthetic post-snapshot legal review",
                "review_deadline": (utcnow() + timedelta(days=1)).isoformat(),
            },
        )
        assert hold.status_code == 201, hold.text
        held_manifest = tmp_path / "held.json"
        with Session(db_engine) as session:
            held_digest = export_tombstones(session, held_manifest, key)
        held_payload = json.loads(held_manifest.read_text())["manifest"]
        assert held_payload["version"] == 3
        assert {"workspace_id": str(wid), "subject_id": str(uid)} in held_payload["holds"]
        marker = target_files / ".privacy-ready"
        marker.write_text("stale receipt must be removed on failure")
        with pytest.raises(ValueError, match="holds differ"):
            replay(source, target_url, source_files, target_files, held_manifest, key, held_digest)
        assert not marker.exists()
        assert not restore_ready(target, target_files)
        assert (target_files / "assets" / storage_key).read_bytes() == (
            source_files / "assets" / storage_key
        ).read_bytes()
        with Session(target) as session:
            assert session.get(Asset, aid).state == "ready"
            assert session.get(ReportComment, comment_id).text == "synthetic raw snapshot content"
            assert not session.get(ReportGrant, grant_id).revoked
        released = client.post(
            base + f"/privacy-ops/holds/{hold.json()['id']}/release", headers=headers
        )
        assert released.status_code == 200, released.text

        # The inverse mismatch is equally unsafe: a released hold remains in
        # an old snapshot and would otherwise silently suppress deletion.
        from app.privacy_ops.models import LegalHold

        with Session(target) as session, session.begin():
            stale = LegalHold(
                workspace_id=wid,
                subject_id=uid,
                reviewed_by=uid,
                reason="old snapshot hold",
                review_deadline=utcnow() + timedelta(days=1),
            )
            session.add(stale)
            session.flush()
            stale_id = stale.id
        no_hold_manifest = tmp_path / "released.json"
        with Session(db_engine) as session:
            no_hold_digest = export_tombstones(session, no_hold_manifest, key)
        with pytest.raises(ValueError, match="holds differ"):
            replay(
                source,
                target_url,
                source_files,
                target_files,
                no_hold_manifest,
                key,
                no_hold_digest,
            )
        assert not restore_ready(target, target_files)
        with Session(target) as session, session.begin():
            session.get(LegalHold, stale_id).released_at = utcnow()

        # New erasure comes AFTER the physical snapshot, through the real API.
        response = client.post(
            base + "/privacy-requests",
            headers=headers,
            json={"kind": "erasure", "request_key": "post-snapshot"},
        )
        assert response.status_code == 202, response.text
        manifest = tmp_path / "latest.json"
        with Session(db_engine) as session:
            assert restricted(session, wid, uid)
            digest = export_tombstones(session, manifest, key)
        assert len(json.loads(manifest.read_text())["manifest"]["tombstones"]) >= 1

        def run():
            replay(source, target_url, source_files, target_files, manifest, key, digest)

        # A storage failure must not publish a receipt, then missing files and
        # repeated erasure must be safe. Real registry callbacks remain installed.
        from app.common.private_storage import PrivateStorage

        original = PrivateStorage.delete

        def fail_delete(*args):
            raise OSError("synthetic storage unavailable")

        with monkeypatch.context() as patch:
            patch.setattr(PrivateStorage, "delete", fail_delete)
            with pytest.raises(OSError):
                run()
        assert not restore_ready(target, target_files)
        # A committed DB replay without a durable filesystem marker is still
        # quarantined; retry must finish despite already-deleted asset bytes.
        from app.privacy_ops import restore

        real_open = restore.os.open

        def fail_marker(path, *args, **kwargs):
            if str(path) == str(target_files / ".privacy-ready"):
                raise OSError("synthetic marker write unavailable")
            return real_open(path, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(restore.os, "open", fail_marker)
            with pytest.raises(OSError):
                run()
        assert not restore_ready(target, target_files)
        run()
        assert restore_ready(target, target_files)
        assert not (target_files / "assets" / storage_key).exists()
        with Session(target) as session:
            assert journal_snapshot(session, wid) == journal_before
        receipt = (target_files / ".privacy-ready").read_bytes()
        run()  # Physical asset is already missing.
        assert restore_ready(target, target_files)
        assert receipt != (target_files / ".privacy-ready").read_bytes()
        with Session(target) as session:
            assert restricted(session, wid, uid)
            asset = session.get(Asset, aid)
            assert asset is None or asset.state == "purged"
            grant = session.get(ReportGrant, grant_id)
            assert grant is None or grant.revoked
            assert session.get(ReportComment, comment_id) is None
            # Repeated replay must neither erase nor duplicate balanced money rows.
            assert journal_snapshot(session, wid) == journal_before
        # Snapshot replay must never delete the source's private bytes.
        assert (source_files / "assets" / storage_key).exists()
        with pytest.raises(ValueError):
            replay(source, target_url, source_files, target_files, manifest, key, "0" * 64)
        assert not restore_ready(target, target_files)
        assert PrivateStorage.delete is original
    finally:
        target.dispose()
        if created:
            with admin.connect() as conn:
                quote = conn.dialect.identifier_preparer.quote_identifier
                conn.exec_driver_sql(f"DROP DATABASE {quote(name)}")
        admin.dispose()


from test_collection_db import collected  # noqa: E402,F401


@pytest.mark.parametrize("decision", ["withdraw", "retention", "optional_consent"])
def test_snapshot_before_scoped_session_decision(
    decision,
    collected,  # noqa: F811
    research_app,
    migrated_database,
    db_engine,
    tmp_path,
    tmp_path_factory,
):
    from app.auth.models import Membership
    from app.collection.models import AnswerRevision, CollectionSession
    from app.privacy_ops.models import RestoreEvent, ReviewedRetention
    from app.privacy_ops.service import sweep_producers

    client, url, headers, result, participant_headers, _ = collected
    _, app, _ = research_app
    sid = UUID(result["session_id"])
    response = client.put(
        url + "/answers/single",
        headers=headers,
        json={
            "schema_version": 1,
            "expected_revision": 0,
            "client_event_id": str(uuid4()),
            "status": "responded",
            "value": {"option_id": "yes"},
        },
    )
    assert response.status_code == 200, response.text
    with Session(db_engine) as session, session.begin():
        row = session.get(CollectionSession, sid)
        wid = row.workspace_id
        if decision == "optional_consent":
            from app.common.privacy_models import ConsentDocument, ConsentReceipt

            doc = ConsentDocument(
                workspace_id=wid,
                document_key="optional-audit",
                version=1,
                locale="fr",
                purpose="accessibility_context",
                body="synthetic",
                digest="a" * 64,
            )
            session.add(doc)
            session.flush()
            doc_id = doc.id
            session.add(
                ConsentReceipt(
                    workspace_id=wid,
                    subject_id=row.subject_id,
                    document_id=doc.id,
                    study_version_id=row.version_id,
                    receipt_key="prior-grant",
                    decision="granted",
                    presented_digest=doc.digest,
                )
            )
        row.created_at = utcnow() - timedelta(days=3)
        owner_id = session.scalar(
            select(Membership.user_id).where(
                Membership.workspace_id == wid, Membership.role == "owner"
            )
        )
        session.add(
            ReviewedRetention(
                workspace_id=wid,
                purpose="raw",
                version=1,
                days=1,
                reason="synthetic reviewed expiry",
                reviewed_by=owner_id,
                review_deadline=utcnow() + timedelta(days=1),
            )
        )
    source = make_url(migrated_database)
    assert source.database.endswith("_test")
    name = "scoped_" + uuid4().hex + "_restore"
    target_url = source.set(database=name)
    source_files = app.state.settings.private_root.resolve()
    target_files = tmp_path_factory.mktemp("scoped_snapshot") / "files_restore"
    copy_files(source_files, target_files)
    app.state.database.engine.dispose()
    db_engine.dispose()
    admin = create_engine(source, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    target = create_engine(target_url, poolclass=NullPool)
    created = False
    try:
        with admin.connect() as conn:
            quote = conn.dialect.identifier_preparer.quote_identifier
            conn.exec_driver_sql(f"CREATE DATABASE {quote(name)} TEMPLATE {quote(source.database)}")
            created = True
        if decision == "withdraw":
            assert client.post(url + "/withdraw", headers=headers).status_code == 200
        elif decision == "optional_consent":
            response = client.post(
                url + "/optional-consent",
                headers=participant_headers,
                json={
                    "purpose": "accessibility_context",
                    "document_id": str(doc_id),
                    "presented_digest": "a" * 64,
                    "decision": "withdrawn",
                    "receipt_key": "withdraw-audit",
                },
            )
            assert response.status_code == 200, response.text
        else:
            with Session(db_engine) as session, session.begin():
                assert sweep_producers(session, wid)["raw"] == 1
        action = {
            "withdraw": "session_withdraw",
            "retention": "session_delete",
            "optional_consent": "consent_revoke",
        }[decision]
        key = b"scoped-synthetic-manifest-key-32bytes"
        manifest = tmp_path / "latest.json"
        with Session(db_engine) as session:
            assert session.scalar(
                select(RestoreEvent.id).where(
                    RestoreEvent.workspace_id == wid,
                    *([RestoreEvent.resource_id == sid] if decision != "optional_consent" else []),
                    RestoreEvent.action == action,
                )
            )
            digest = export_tombstones(session, manifest, key)
        with Session(target) as session:
            assert session.get(CollectionSession, sid).state == "active"
        for _ in range(2):
            replay(source, target_url, source_files, target_files, manifest, key, digest)
            assert restore_ready(target, target_files)
            with Session(target) as session:
                row = session.get(CollectionSession, sid)
                assert (
                    row.state
                    == {
                        "withdraw": "withdrawn",
                        "retention": "erased",
                        "optional_consent": "active",
                    }[decision]
                )
                if decision == "optional_consent":
                    from app.common.privacy import consent_granted

                    assert not consent_granted(
                        session,
                        wid,
                        row.subject_id,
                        "accessibility_context",
                        study_version_id=row.version_id,
                    )
                remaining = session.scalars(
                    select(AnswerRevision).where(AnswerRevision.session_id == sid)
                ).all()
                assert len(remaining) == (0 if decision == "retention" else 1)
                assert not restricted(session, wid, row.subject_id)  # no account-wide escalation
    finally:
        target.dispose()
        if created:
            with admin.connect() as conn:
                conn.exec_driver_sql(
                    f"DROP DATABASE {conn.dialect.identifier_preparer.quote_identifier(name)}"
                )
        admin.dispose()


@pytest.mark.parametrize("later_hold", [False, True])
def test_global_account_request_after_snapshot_restricts_without_fabricated_receipt(
    migrated_database, research_app, db_engine, tmp_path, tmp_path_factory, later_hold
):
    from app.auth.models import Membership, OneTimeToken, RefreshToken, User
    from app.auth.security import password_hasher
    from app.privacy_ops.account_models import AccountErasure
    from app.privacy_ops.models import LegalHold
    from app.recruiting.models import ParticipantProfile, Qualification

    client, app, actor = research_app
    _, owner_id, wid = actor()
    password = "synthetic-account-restore-password"
    email = "snapshot-" + uuid4().hex + "@example.test"
    with Session(db_engine) as session, session.begin():
        user = User(
            email=email,
            password_hash=password_hasher.hash(password),
            display_name="Synthetic private name",
            verified_at=utcnow(),
        )
        session.add(user)
        session.flush()
        uid = user.id
        credentials = app.state.auth._new_login(session, user)
        profile = ParticipantProfile(user_id=uid, attributes_json={"private": "synthetic"})
        session.add(profile)
        session.flush()
        pid = profile.id
        session.add(
            Qualification(
                profile_id=pid,
                language="fr",
                assessment_version="1",
                passed=True,
                expires_at=utcnow() + timedelta(days=1),
            )
        )
        session.add(
            OneTimeToken(
                user_id=uid,
                purpose="reset",
                token_hash="a" * 64,
                expires_at=utcnow() + timedelta(hours=1),
            )
        )
        assert not session.scalars(select(Membership).where(Membership.user_id == uid)).all()
    source = make_url(migrated_database)
    assert source.database.endswith("_test")
    name = "account_" + uuid4().hex + "_restore"
    target_url = source.set(database=name)
    source_files = app.state.settings.private_root.resolve()
    target_files = tmp_path_factory.mktemp("account_snapshot") / "files_restore"
    copy_files(source_files, target_files)
    app.state.database.engine.dispose()
    db_engine.dispose()
    admin = create_engine(source, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    target = create_engine(target_url, poolclass=NullPool)
    created = False
    try:
        with admin.connect() as conn:
            quote = conn.dialect.identifier_preparer.quote_identifier
            conn.exec_driver_sql(f"CREATE DATABASE {quote(name)} TEMPLATE {quote(source.database)}")
            created = True
        response = client.post(
            "/api/v1/account/erasure",
            headers={"authorization": "Bearer " + credentials["access_token"]},
            json={
                "request_key": str(uuid4()),
                "current_password": password,
                "confirmation": "ERASE MY ACCOUNT",
                "status_capability": "b" * 64,
            },
        )
        assert response.status_code == 202, response.text
        with Session(db_engine) as session:
            record = session.scalar(select(AccountErasure).where(AccountErasure.subject_id == uid))
            assert record.workspace_ids == [] and record.state == "pending"
        if later_hold:
            # Equal hold sets must not authorize global minimization: a hold
            # created after the request still preserves this subject's profile.
            for engine in (db_engine, target):
                with Session(engine) as session, session.begin():
                    session.add(
                        LegalHold(
                            workspace_id=wid,
                            subject_id=uid,
                            reviewed_by=owner_id,
                            reason="synthetic later dispute",
                            review_deadline=utcnow() + timedelta(days=1),
                        )
                    )
        key = b"synthetic-account-restore-key-32bytes"
        manifest = tmp_path / "account-manifest.json"
        with Session(db_engine) as session:
            digest = export_tombstones(session, manifest, key)
        payload = json.loads(manifest.read_text())["manifest"]
        assert [row for row in payload["accounts"] if row["subject_id"] == str(uid)] == [
            {"subject_id": str(uid), "workspace_ids": []}
        ]
        assert email not in manifest.read_text() and "capability" not in manifest.read_text()
        if later_hold:
            with pytest.raises(ValueError, match="Account restriction conflicts"):
                replay(source, target_url, source_files, target_files, manifest, key, digest)
            assert not restore_ready(target, target_files)
            with Session(target) as session:
                assert session.get(User, uid).email == email
                assert session.get(ParticipantProfile, pid).attributes_json == {
                    "private": "synthetic"
                }
            return
        for _ in range(2):
            replay(source, target_url, source_files, target_files, manifest, key, digest)
            assert restore_ready(target, target_files)
            with Session(target) as session:
                user = session.get(User, uid)
                assert user.email == f"erased-{uid}@invalid.example"
                assert user.status == "disabled" and user.password_hash == "!account-erased"
                assert user.display_name == "" and user.verified_at is None
                assert user.auth_version == 1
                profile = session.get(ParticipantProfile, pid)
                assert profile.status == "withdrawn" and profile.attributes_json == {}
                assert not session.scalars(
                    select(Qualification).where(Qualification.profile_id == pid)
                ).all()
                assert not session.scalars(
                    select(OneTimeToken).where(OneTimeToken.user_id == uid)
                ).all()
                tokens = session.scalars(
                    select(RefreshToken).where(RefreshToken.user_id == uid)
                ).all()
                assert tokens and all(token.revoked_at is not None for token in tokens)
                assert (
                    session.scalar(select(AccountErasure).where(AccountErasure.subject_id == uid))
                    is None
                )
    finally:
        target.dispose()
        if created:
            with admin.connect() as conn:
                conn.exec_driver_sql(
                    f"DROP DATABASE {conn.dialect.identifier_preparer.quote_identifier(name)}"
                )
        admin.dispose()
