from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from research_support import upload
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import utcnow
from app.common import privacy
from app.common.privacy_models import Asset, PrivacyRequest
from app.privacy_ops.models import Tombstone

pytestmark = pytest.mark.db


def test_retention_sweep_review_and_hold_gate(research_app, db_engine):
    from app.ai.models import AIRun
    from app.privacy_ops.models import LegalHold
    from app.privacy_ops.service import sweep_producers

    client, app, actor = research_app
    headers, uid, wid = actor()
    base = f"/api/v1/workspaces/{wid}/privacy-ops"
    policy = {
        "purpose": "derived",
        "version": 1,
        "days": 1,
        "reason": "synthetic retention review",
        "review_deadline": (utcnow() + timedelta(days=1)).isoformat(),
    }
    assert client.post(base + "/retention", headers=headers, json=policy).status_code == 201
    from research_support import policy as create_retention_policy

    from app.auth.models import Membership
    from app.studies.models import Study

    retention_id = UUID(create_retention_policy(client, f"/api/v1/workspaces/{wid}", headers))
    with app.state.database.sessions.begin() as session:
        owner = session.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.user_id == uid)
        )
        study = Study(
            workspace_id=wid,
            title="Synthetic retention study",
            owner_membership_id=owner.id,
            retention_policy_id=retention_id,
            ai_policy="assisted",
        )
        session.add(study)
        session.flush()
        row = AIRun(
            workspace_id=wid,
            study_id=study.id,
            requester_id=uid,
            command_key="retention-test",
            request_hash="a" * 64,
            cache_key="b" * 64,
            operation="study_helper",
            instruction="synthetic private instruction",
            privacy_epoch=0,
            state="draft",
            config={},
            coverage={},
            output={"text": "synthetic secret"},
            created_at=utcnow() - timedelta(days=2),
        )
        session.add(row)
        session.flush()
        rid = row.id
        hold = LegalHold(
            workspace_id=wid,
            subject_id=uid,
            reviewed_by=uid,
            reason="synthetic",
            review_deadline=utcnow() + timedelta(days=1),
        )
        session.add(hold)
        session.flush()
        assert sweep_producers(session, wid)["derived"] == 0
        assert row.output
        row.state = "invalidated"  # withdrawal retained evidence while held
        session.flush()
        hold.released_at = utcnow()
        session.flush()
        assert sweep_producers(session, wid)["derived"] == 1
        assert row.output is None and row.instruction == "" and row.state == "invalidated"
        assert sweep_producers(session, wid)["derived"] == 0
    with Session(db_engine) as session:
        assert session.get(AIRun, rid).output is None


def test_hold_restricts_export_preserves_file_then_retry_erases(research_app, db_engine):
    client, app, actor = research_app
    headers, uid, wid = actor()
    base = f"/api/v1/workspaces/{wid}"
    aid = upload(client, base, headers)["asset"]["id"]
    access = client.post(
        base + "/privacy-requests",
        headers=headers,
        json={"kind": "access", "request_key": "access"},
    ).json()
    hold = client.post(
        base + "/privacy-ops/holds",
        headers=headers,
        json={
            "subject_id": str(uid),
            "reason": "reviewed synthetic dispute",
            "review_deadline": (utcnow() + timedelta(days=1)).isoformat(),
        },
    )
    assert hold.status_code == 201, hold.text
    result = client.post(
        base + "/privacy-requests",
        headers=headers,
        json={"kind": "erasure", "request_key": "erase"},
    )
    assert result.status_code == 202, result.text
    rid = UUID(result.json()["id"])
    assert (
        client.get(base + f"/privacy-requests/{access['id']}/data", headers=headers).status_code
        == 403
    )
    with Session(db_engine) as session:
        task = SimpleNamespace(workspace_id=wid, target_id=rid)
        key = session.get(Asset, UUID(aid)).storage_key
    path = app.state.settings.private_root / "assets" / key
    assert path.exists()
    assert privacy.erase_files(app.state.database, app.state.settings, task) == {"status": "ok"}
    with app.state.database.sessions.begin() as session:
        privacy.finish_erasure(session, task)
        assert session.get(PrivacyRequest, rid).state != "completed"
        assert session.scalar(select(Tombstone.id).where(Tombstone.subject_id == uid))
    assert path.exists()
    # A held worker may finish its job while the erasure request stays pending.
    # Release must still permit a NEW durable job, not reuse the succeeded key.
    from app.jobs.models import Job

    with app.state.database.sessions.begin() as session:
        original_job = session.scalar(select(Job).where(Job.target_id == rid))
        original_job.state = "succeeded"
        original_job_id = original_job.id
    assert (
        client.post(
            base + f"/privacy-ops/holds/{hold.json()['id']}/release", headers=headers
        ).status_code
        == 200
    )
    retried = client.post(base + f"/privacy-requests/{rid}/retry", headers=headers)
    assert retried.status_code == 202, retried.text
    with Session(db_engine) as session:
        assert session.scalar(
            select(Job.id).where(
                Job.target_id == rid, Job.id != original_job_id, Job.state == "pending"
            )
        )
    # Missing physical file is an idempotent success, not a lost erasure.
    path.unlink()
    for _ in range(2):
        privacy.erase_files(app.state.database, app.state.settings, task)
        with app.state.database.sessions.begin() as session:
            privacy.finish_erasure(session, task)
    with Session(db_engine) as session:
        assert session.get(PrivacyRequest, rid).state == "completed"
        assert session.get(Asset, UUID(aid)).state == "purged"


def test_hold_scope_and_review_deadline(research_app):
    client, app, actor = research_app
    h, uid, wid = actor()
    other, _, _ = actor()
    url = f"/api/v1/workspaces/{wid}/privacy-ops/holds"
    body = {
        "subject_id": str(uid),
        "reason": "review",
        "review_deadline": (utcnow() + timedelta(days=1)).isoformat(),
    }
    assert client.post(url, headers=other, json=body).status_code in (403, 404)
    assert (
        client.post(
            url,
            headers=h,
            json=body | {"review_deadline": (utcnow() - timedelta(seconds=1)).isoformat()},
        ).status_code
        == 422
    )


def test_erasure_io_failure_stays_retryable(research_app, db_engine, monkeypatch):
    from app.common.private_storage import PrivateStorage

    client, app, actor = research_app
    headers, uid, wid = actor()
    base = f"/api/v1/workspaces/{wid}"
    upload(client, base, headers)
    result = client.post(
        base + "/privacy-requests",
        headers=headers,
        json={"kind": "erasure", "request_key": "io-retry"},
    )
    assert result.status_code == 202
    task = SimpleNamespace(workspace_id=wid, target_id=UUID(result.json()["id"]))
    original = PrivateStorage.delete

    def broken(*args):
        raise OSError("synthetic store unavailable")

    monkeypatch.setattr(PrivateStorage, "delete", broken)
    with pytest.raises(OSError):
        privacy.erase_files(app.state.database, app.state.settings, task)
    with Session(db_engine) as session:
        assert session.get(PrivacyRequest, task.target_id).state != "completed"
        assert privacy.restricted(session, wid, uid)
    monkeypatch.setattr(PrivateStorage, "delete", original)
    privacy.erase_files(app.state.database, app.state.settings, task)
    with app.state.database.sessions.begin() as session:
        privacy.finish_erasure(session, task)
        assert session.get(PrivacyRequest, task.target_id).state == "completed"
