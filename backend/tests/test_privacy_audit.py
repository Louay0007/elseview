"""Scoped replay metadata and bounded deletion regression coverage."""

import hashlib
import hmac
import json
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from research_support import upload
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import utcnow
from app.common.privacy import sweep_storage
from app.common.privacy_models import Asset
from app.privacy_ops.models import LegalHold, RestoreEvent
from app.privacy_ops.restore import read_manifest


@pytest.mark.parametrize("mutation", ["action", "resource", "content", "old"])
def test_v3_rejects_authenticated_invalid_event_scopes(tmp_path, mutation):
    event = dict(
        id=str(uuid4()), workspace_id=str(uuid4()), resource_id=str(uuid4()), action="asset_delete"
    )
    value = dict(version=3, tombstones=[], holds=[], contact_holds=[], accounts=[], events=[event])
    if mutation == "action":
        event["action"] = "account_delete"
    elif mutation == "resource":
        event["resource_id"] = "../private"
    elif mutation == "content":
        event["raw"] = "not allowed"
    else:
        value["version"] = 2
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    key = b"x" * 32
    digest = hashlib.sha256(payload).hexdigest()
    path = tmp_path / "manifest"
    path.write_text(
        json.dumps(
            dict(manifest=value, signature=hmac.new(key, payload, hashlib.sha256).hexdigest())
        )
    )
    with pytest.raises(ValueError):
        read_manifest(path, key, digest)


@pytest.mark.db
def test_asset_sweep_passes_101_held_rows_and_commits_event_before_disk(
    research_app, db_engine, monkeypatch
):
    client, app, actor = research_app
    headers, uid, wid = actor()
    _, held_uid, _ = actor(wid, "viewer")
    aid = UUID(upload(client, f"/api/v1/workspaces/{wid}", headers)["asset"]["id"])
    with Session(db_engine) as session, session.begin():
        original = session.get(Asset, aid)
        # Immutable upload policy stays untouched; reviewed retention shortens it.
        from app.privacy_ops.models import ReviewedRetention

        original.created_at = utcnow() - timedelta(days=2)
        session.add(
            ReviewedRetention(
                workspace_id=wid,
                purpose="media",
                version=1,
                days=1,
                reason="synthetic expiry review",
                reviewed_by=uid,
                review_deadline=utcnow() + timedelta(days=1),
            )
        )
        session.add(
            LegalHold(
                workspace_id=wid,
                subject_id=held_uid,
                reviewed_by=uid,
                reason="synthetic",
                review_deadline=utcnow() + timedelta(days=1),
            )
        )
        for _ in range(101):
            session.add(
                Asset(
                    workspace_id=wid,
                    owner_id=held_uid,
                    retention_policy_id=original.retention_policy_id,
                    storage_key=uuid4().hex,
                    checksum="a" * 64,
                    media_type="image/png",
                    extension="png",
                    purpose="stimulus",
                    size_bytes=10,
                    state="ready",
                    created_at=utcnow() - timedelta(days=3),
                    retention_until=utcnow() - timedelta(days=2),
                )
            )
    from app.common.private_storage import PrivateStorage

    real_delete = PrivateStorage.delete
    seen = []

    def checked_delete(storage, key):
        with Session(db_engine) as session:
            assert session.scalar(
                select(RestoreEvent.id).where(
                    RestoreEvent.workspace_id == wid,
                    RestoreEvent.resource_id == aid,
                    RestoreEvent.action == "asset_delete",
                )
            )
        seen.append(key)
        return real_delete(storage, key)

    monkeypatch.setattr(PrivateStorage, "delete", checked_delete)
    assert sweep_storage(app.state.database, app.state.settings, wid, uid) == 1
    assert len(seen) == 1
    with Session(db_engine) as session:
        assert session.get(Asset, aid).state == "purged"
        assert (
            len(
                session.scalars(
                    select(Asset).where(Asset.owner_id == held_uid, Asset.state == "ready")
                ).all()
            )
            == 101
        )


@pytest.mark.parametrize(
    "scope",
    [
        {"workspace_id": str(uuid4()), "subject_id": str(uuid4())},
        {"workspace_id": str(uuid4()), "contact_id": "bad"},
    ],
)
def test_v3_rejects_invalid_contact_hold_scope(tmp_path, scope):
    value = dict(version=3, tombstones=[], holds=[], contact_holds=[scope], accounts=[], events=[])
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    key = b"x" * 32
    digest = hashlib.sha256(payload).hexdigest()
    path = tmp_path / "manifest"
    path.write_text(
        json.dumps(
            dict(manifest=value, signature=hmac.new(key, payload, hashlib.sha256).hexdigest())
        )
    )
    with pytest.raises(ValueError):
        read_manifest(path, key, digest)
