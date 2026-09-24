"""Offline restore protocol. No server is started and no production writes allowed.

Snapshots are NOT encrypted here: operators must supply encrypted storage/transport.
HMAC authenticates metadata; it is not encryption. UUIDs remain pseudonymous data.
"""

import argparse
import hashlib
import hmac
import json
import os
import shutil
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


def verify_isolation(source_url, restore_url, source_files, restore_files):
    source, target = make_url(source_url), make_url(restore_url)
    if (
        not target.database
        or not target.database.endswith("_restore")
        or target.database == source.database
    ):
        raise ValueError("Restore requires a distinct database ending _restore")
    src, dst = Path(source_files), Path(restore_files)
    for path in (src, dst):
        if any(part.is_symlink() for part in [path, *path.parents]):
            raise ValueError("Symlinks are forbidden")
    src, dst = src.resolve(), dst.resolve()
    if src == dst or src in dst.parents or dst in src.parents or not dst.name.endswith("_restore"):
        raise ValueError("Restore requires a separate *_restore files directory")
    return dst


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def export_tombstones(session, path, signing_key):
    from app.privacy_ops.account_models import AccountErasure
    from app.privacy_ops.lifecycle_models import ContactHold
    from app.privacy_ops.models import LegalHold, RestoreEvent, Tombstone

    if len(signing_key) < 32:
        raise ValueError("Use an operator-provided signing key of at least 32 bytes")
    rows = session.scalars(select(Tombstone).order_by(Tombstone.id)).all()
    manifest = {
        "version": 3,
        "accounts": [
            {"subject_id": str(row.subject_id), "workspace_ids": sorted(row.workspace_ids)}
            for row in session.scalars(select(AccountErasure).order_by(AccountErasure.subject_id))
        ],
        "contact_holds": [
            {"workspace_id": str(wid), "contact_id": str(cid)}
            for wid, cid in session.execute(
                select(ContactHold.workspace_id, ContactHold.contact_id)
                .where(ContactHold.released_at.is_(None))
                .distinct()
                .order_by(ContactHold.workspace_id, ContactHold.contact_id)
            )
        ],
        "events": [
            dict(
                id=str(r.id),
                workspace_id=str(r.workspace_id),
                action=r.action,
                resource_id=str(r.resource_id),
            )
            for r in session.scalars(
                select(RestoreEvent).order_by(RestoreEvent.created_at, RestoreEvent.id)
            )
        ],
        "holds": [
            {"workspace_id": str(wid), "subject_id": str(sid)}
            for wid, sid in session.execute(
                select(LegalHold.workspace_id, LegalHold.subject_id)
                .where(LegalHold.released_at.is_(None))
                .distinct()
                .order_by(LegalHold.workspace_id, LegalHold.subject_id)
            )
        ],
        "tombstones": [
            dict(
                id=str(r.id),
                workspace_id=str(r.workspace_id),
                subject_id=str(r.subject_id),
                purpose=r.purpose,
            )
            for r in rows
        ],
    }
    payload = _canonical(manifest)
    envelope = {
        "manifest": manifest,
        "digest": hashlib.sha256(payload).hexdigest(),
        "signature": hmac.new(signing_key, payload, hashlib.sha256).hexdigest(),
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(_canonical(envelope))
        stream.flush()
        os.fsync(stream.fileno())
    return envelope["digest"]


def read_manifest(path, signing_key, expected_digest):
    if len(signing_key) < 32:
        raise ValueError("Use an operator-provided signing key of at least 32 bytes")
    envelope = json.loads(Path(path).read_bytes())
    manifest = envelope["manifest"]
    payload = _canonical(manifest)
    digest = hashlib.sha256(payload).hexdigest()
    if (
        not expected_digest
        or not hmac.compare_digest(digest, expected_digest)
        or not hmac.compare_digest(
            envelope["signature"], hmac.new(signing_key, payload, hashlib.sha256).hexdigest()
        )
    ):
        raise ValueError("Manifest authentication or latest digest mismatch")
    version = manifest.get("version")
    expected_keys = {"version", "tombstones", "holds", "contact_holds", "events", "accounts"}
    if set(manifest) != expected_keys or version != 3:
        raise ValueError("Unsupported manifest")
    from app.privacy_ops.events import ACTIONS

    for account in manifest["accounts"]:
        if set(account) != {"subject_id", "workspace_ids"} or not isinstance(
            account["workspace_ids"], list
        ):
            raise ValueError("Invalid account restriction scope")
        UUID(account["subject_id"])
        for workspace_id in account["workspace_ids"]:
            UUID(workspace_id)
    for event in manifest["events"]:
        if (
            set(event) != {"id", "workspace_id", "action", "resource_id"}
            or event["action"] not in ACTIONS
        ):
            raise ValueError("Invalid event scope")
        for name in ("id", "workspace_id", "resource_id"):
            UUID(event[name])
    for hold in manifest["contact_holds"]:
        if set(hold) != {"workspace_id", "contact_id"}:
            raise ValueError("Invalid contact hold scope")
        UUID(hold["workspace_id"])
        UUID(hold["contact_id"])
    for hold in manifest.get("holds", []):
        if set(hold) != {"workspace_id", "subject_id"}:
            raise ValueError("Invalid hold scope")
        UUID(hold["workspace_id"])
        UUID(hold["subject_id"])
    for row in manifest["tombstones"]:
        if set(row) != {"id", "workspace_id", "subject_id", "purpose"} or row["purpose"] not in {
            "erasure",
            "restriction",
        }:
            raise ValueError("Invalid tombstone")
        for name in ("id", "workspace_id", "subject_id"):
            UUID(row[name])
    return manifest


def copy_files(source, target):
    # No archives are extracted. Reject symlinks anywhere before copying.
    source, target = Path(source), Path(target)
    for root in (source, target):
        if any(p.is_symlink() for p in (root, *root.parents)):
            raise ValueError("Symlinks are forbidden")
    if source.resolve() == target.resolve() or source.resolve() in target.resolve().parents:
        raise ValueError("Snapshot source and destination must be disjoint")
    if target.exists() and any(target.iterdir()):
        raise ValueError("Restore files must be empty")
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("Snapshot contains symlink")
    shutil.copytree(
        source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".privacy-ready")
    )
    os.chmod(target, 0o700)
    for path in target.rglob("*"):
        os.chmod(path, 0o700 if path.is_dir() else 0o600)


def replay(
    source_url,
    restore_url,
    source_files,
    restore_files,
    manifest_path,
    signing_key,
    expected_digest,
):
    target = verify_isolation(source_url, restore_url, source_files, restore_files)
    # Revalidation failure must invalidate an earlier receipt as well. Never
    # leave a previously ready restored copy serving after a failed replay.
    marker = target / ".privacy-ready"
    marker.unlink(missing_ok=True)
    manifest = read_manifest(manifest_path, signing_key, expected_digest)
    if manifest["version"] != 3:
        raise ValueError("Restore requires a current manifest including active holds")
    from importlib import import_module

    for module in (
        "auth",
        "ai",
        "analytics",
        "billing",
        "collaboration",
        "collection",
        "evaluation",
        "jobs",
        "longitudinal",
        "recruiting",
        "reviews",
        "studies",
        "templates",
        "privacy_ops",
    ):
        import_module("app." + module + ".models")
    from app.auth.models import User, Workspace
    from app.common.privacy import lock_workspace, restricted, run_erasure_handlers
    from app.common.privacy_models import Asset, PrivacyRestriction
    from app.common.private_storage import PrivateStorage
    from app.longitudinal.service import recording_assets
    from app.privacy_ops.lifecycle_models import ContactHold
    from app.privacy_ops.service import tombstone, workspace_held

    engine = create_engine(restore_url, hide_parameters=True)
    from uuid import uuid4

    nonce = str(uuid4())
    try:
        with sessionmaker(engine).begin() as session:
            if session.scalar(text("select current_database()")) != make_url(restore_url).database:
                raise ValueError("Connected database differs from restore target")
            # A backup cannot know about later legal holds. Refuse all destructive
            # replay until those reviewed decisions are imported by an authorized
            # operator; never fabricate reviewer attribution or a review deadline.
            from app.privacy_ops.models import LegalHold

            restored_holds = set(
                session.execute(
                    select(LegalHold.workspace_id, LegalHold.subject_id).where(
                        LegalHold.released_at.is_(None)
                    )
                )
            )
            current_holds = {
                (UUID(h["workspace_id"]), UUID(h["subject_id"])) for h in manifest["holds"]
            }
            if restored_holds != current_holds:
                raise ValueError("Current and restored holds differ; reconcile before replay")
            restored_contact_holds = set(
                session.execute(
                    select(ContactHold.workspace_id, ContactHold.contact_id).where(
                        ContactHold.released_at.is_(None)
                    )
                )
            )
            current_contact_holds = {
                (UUID(h["workspace_id"]), UUID(h["contact_id"])) for h in manifest["contact_holds"]
            }
            if restored_contact_holds != current_contact_holds:
                raise ValueError(
                    "Current and restored contact holds differ; reconcile before replay"
                )
            from app.privacy_ops.account import affected_workspaces

            # Old snapshots can contain scopes removed after the snapshot; union
            # these with the current request, never trust only one side.
            account_scope_union = set()
            for account in manifest["accounts"]:
                sid = UUID(account["subject_id"])
                scopes = {UUID(wid) for wid in account["workspace_ids"]}
                if session.get(User, sid) is not None:
                    scopes.update(affected_workspaces(session, sid))
                account_scope_union.update(scopes)
                if any(workspace_held(session, wid) for wid in scopes) or session.scalar(
                    select(LegalHold.id)
                    .where(LegalHold.subject_id == sid, LegalHold.released_at.is_(None))
                    .limit(1)
                ):
                    raise ValueError(
                        "Account restriction conflicts with current hold; reconcile before replay"
                    )
            for wid in sorted(account_scope_union, key=str):
                if session.get(Workspace, wid) is not None:
                    lock_workspace(session, wid)
            from app.privacy_ops.events import apply_event, record_event

            for event in manifest["events"]:
                wid, rid = UUID(event["workspace_id"]), UUID(event["resource_id"])
                if session.get(Workspace, wid) is None:
                    continue
                lock_workspace(session, wid)
                record_event(session, wid, event["action"], rid)
                apply_event(session, wid, event["action"], rid, PrivateStorage(target))
            for row in manifest["tombstones"]:
                wid, sid = UUID(row["workspace_id"]), UUID(row["subject_id"])
                if session.get(Workspace, wid) is None or session.get(User, sid) is None:
                    continue  # subject created after the snapshot has no restored content
                workspace = lock_workspace(session, wid)
                if not restricted(session, wid, sid):
                    session.add(PrivacyRestriction(workspace_id=wid, subject_id=sid))
                workspace.privacy_epoch += 1
                tombstone(session, wid, sid, row["purpose"])
                assets = list(
                    session.scalars(
                        select(Asset).where(Asset.workspace_id == wid, Asset.owner_id == sid)
                    )
                )
                assets.extend(recording_assets(session, wid, sid))
                for asset in assets:
                    asset.state = "blocked"
                from app.collaboration.privacy import invalidate_subject as invalidate_collaboration
                from app.collection.privacy import withdraw_subject

                if not workspace_held(session, wid):
                    withdraw_subject(session, wid, sid)
                from app.privacy_ops.service import invalidate_subject_safely

                invalidate_subject_safely(session, wid, sid)
                invalidate_collaboration(session, wid, sid)
                session.flush()
                if row["purpose"] == "erasure" and not workspace_held(session, wid):
                    for asset in assets:
                        PrivateStorage(target).delete(asset.storage_key)
                    run_erasure_handlers(session, wid, sid)
            from app.privacy_ops.account import apply_account_restriction

            account_scopes = sorted(
                {UUID(wid) for account in manifest["accounts"] for wid in account["workspace_ids"]},
                key=str,
            )
            for wid in account_scopes:
                if session.get(Workspace, wid) is not None:
                    lock_workspace(session, wid)
            for account in manifest["accounts"]:
                sid = UUID(account["subject_id"])
                if session.get(User, sid) is not None:
                    apply_account_restriction(session, sid)
            session.flush()
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS privacy_restore_receipt (singleton integer PRIMARY KEY CHECK (singleton=1), nonce text NOT NULL, digest text NOT NULL)"
                )
            )
            # Recovery acceptance includes the journal, not only data visibility.
            # A missing/imbalanced transaction must never obtain a serving marker.
            if session.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM ledger_transactions t "
                    "LEFT JOIN ledger_entries e ON e.transaction_id=t.id AND e.workspace_id=t.workspace_id "
                    "GROUP BY t.id HAVING count(e.id)<2 OR coalesce(sum(e.amount_millimes),0)<>0)"
                )
            ):
                raise ValueError("Restored journal is incomplete or unbalanced")
            session.execute(
                text(
                    "INSERT INTO privacy_restore_receipt VALUES (1,:nonce,:digest) ON CONFLICT (singleton) DO UPDATE SET nonce=excluded.nonce,digest=excluded.digest"
                ),
                {"nonce": nonce, "digest": expected_digest},
            )
        # Marker written ONLY after committed replay. App lead gates restore readiness.
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(
                json.dumps(
                    {"database": engine.url.database, "nonce": nonce, "digest": expected_digest}
                )
            )
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url-env", default="DATABASE_URL")
    parser.add_argument("--restore-url-env", default="RESTORE_DATABASE_URL")
    parser.add_argument("--source-files", required=True)
    parser.add_argument("--restore-files", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--latest-digest", required=True)
    parser.add_argument("--key-file", required=True)
    args = parser.parse_args()
    replay(
        os.environ[args.source_url_env],
        os.environ[args.restore_url_env],
        args.source_files,
        args.restore_files,
        args.manifest,
        Path(args.key_file).read_bytes(),
        args.latest_digest,
    )


if __name__ == "__main__":
    main()


def restore_ready(engine, private_root):
    """Restore deployments are offline until replay commits and writes its marker."""
    if not (engine.url.database or "").endswith("_restore"):
        return True
    root = Path(private_root)
    marker = root / ".privacy-ready"
    try:
        if (
            not root.name.endswith("_restore")
            or any(p.is_symlink() for p in (root, *root.parents))
            or marker.is_symlink()
            or not marker.is_file()
        ):
            return False
        value = json.loads(marker.read_text())
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT nonce,digest FROM privacy_restore_receipt WHERE singleton=1")
            ).one()
        return value == {"database": engine.url.database, "nonce": row.nonce, "digest": row.digest}
    except Exception:
        return False
