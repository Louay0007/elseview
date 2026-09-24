import asyncio
import hashlib
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from research_support import document, png, policy, upload
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from study_fixtures import blocks, ready_study

from app.auth.models import Membership
from app.auth.security import utcnow
from app.common import privacy
from app.common.privacy_models import (
    AssetLink,
    ConsentReceipt,
    PrivacyRequest,
    UploadIntent,
)
from app.common.privacy_router import upload_io
from app.common.privacy_schemas import UploadBody
from app.common.private_storage import PrivateStorage, validate_content
from app.jobs import service as jobs
from app.jobs.models import Job
from app.studies import methods, service
from app.studies.models import Study

pytestmark = pytest.mark.db


@pytest.fixture
def phase_scope(research_app):
    client, app, actor = research_app
    headers, user_id, workspace_id = actor()
    return client, app, actor, headers, user_id, workspace_id, f"/api/v1/workspaces/{workspace_id}"


def test_retention_and_document_idempotency_and_denied_fields(phase_scope):
    client, _, actor, headers, _, _, base = phase_scope
    retention_id = policy(client, base, headers)
    existing = client.get(base + "/retention-policies", headers=headers).json()["items"][0]
    body = {key: value for key, value in existing.items() if key != "id"}
    assert (
        client.post(base + "/retention-policies", headers=headers, json=body).json()["id"]
        == retention_id
    )
    assert (
        client.post(
            base + "/retention-policies", headers=headers, json=body | {"raw_days": 1}
        ).status_code
        == 409
    )
    doc = document(client, base, headers)
    data = {key: value for key, value in doc.items() if key not in {"id", "digest"}}
    assert client.post(base + "/consent-documents", headers=headers, json=data).json() == doc
    assert (
        client.post(
            base + "/consent-documents", headers=headers, json=data | {"body": "changed"}
        ).status_code
        == 409
    )
    outsider, _, _ = actor()
    assert client.get(base + "/consent-documents", headers=outsider).status_code == 404
    assert (
        client.get(base + "/retention-policies", headers=headers, params={"limit": 0}).status_code
        == 422
    )


def test_upload_idempotency_quota_race_and_wrong_mime(phase_scope, db_engine):
    client, app, _, headers, user_id, workspace_id, base = phase_scope
    retention = policy(client, base, headers)
    payload = {
        "upload_key": "once",
        "filename": "test.png",
        "media_type": "image/png",
        "purpose": "stimulus",
        "size_bytes": len(png()),
        "checksum": hashlib.sha256(png()).hexdigest(),
        "retention_policy_id": retention,
    }
    first = client.post(base + "/upload-intents", headers=headers, json=payload)
    assert first.status_code == 201
    assert (
        client.post(base + "/upload-intents", headers=headers, json=payload).json() == first.json()
    )
    assert (
        client.post(
            base + "/upload-intents", headers=headers, json=payload | {"checksum": "a" * 64}
        ).status_code
        == 409
    )
    endpoint = base + "/upload-intents/" + first.json()["upload_id"]
    assert (
        client.put(
            endpoint + "/content", headers=headers | {"content-type": "text/plain"}, content=png()
        ).status_code
        == 422
    )
    settings = app.state.settings.model_copy(update={"private_workspace_bytes": len(png()) * 2})

    def create(number):
        try:
            with Session(db_engine) as session, session.begin():
                privacy.create_upload(
                    session,
                    workspace_id,
                    user_id,
                    UploadBody(**(payload | {"upload_key": str(number)})),
                    settings,
                )
                return "ok"
        except Exception as error:
            return getattr(error, "code", type(error).__name__)

    with ThreadPoolExecutor(2) as executor:
        assert sorted(executor.map(create, range(2))) == ["STORAGE_QUOTA", "ok"]


def test_format_checksums_text_csv_and_png_bounds():
    for content, kind in [("Bonjour مرحبا".encode(), "text/plain"), (b"a,b\n1,2\n", "text/csv")]:
        assert validate_content(content, kind, hashlib.sha256(content).hexdigest())["width"] is None
    with pytest.raises(ValueError):
        validate_content(png(), "image/png", "a" * 64)
    corrupt = bytearray(png())
    corrupt[20] ^= 1
    with pytest.raises(ValueError):
        validate_content(bytes(corrupt), "image/png", hashlib.sha256(corrupt).hexdigest())


def test_stream_upload_cancellation_waits_for_descriptor_owner():
    entered = threading.Event()
    finished = threading.Event()

    def slow():
        entered.set()
        time.sleep(0.04)
        finished.set()

    async def run():
        operation = asyncio.create_task(upload_io(slow))
        while not entered.is_set():
            await asyncio.sleep(0.001)
        operation.cancel()
        with pytest.raises(asyncio.CancelledError):
            await operation
        assert finished.is_set()

    asyncio.run(run())


def test_privacy_erasure_retry_removes_published_study(phase_scope, db_engine, monkeypatch):
    client, app, _, headers, user_id, workspace_id, base = phase_scope
    fixture = ready_study(client, base, headers)
    assert (
        client.post(
            fixture["endpoint"] + "/publish", headers=headers, json={"expected_revision": 2}
        ).status_code
        == 200
    )
    result = client.post(
        base + "/privacy-requests",
        headers=headers,
        json={"kind": "erasure", "request_key": "erase"},
    ).json()
    assert client.get(fixture["endpoint"], headers=headers).status_code == 403
    with Session(db_engine) as session:
        job = session.scalar(select(Job).where(Job.target_id == UUID(result["id"])))
        session.expunge(job)
    with Session(db_engine) as session, session.begin():
        assert jobs._authority(session, job)
        with pytest.raises(Exception, match="PRIVACY_JOB_REQUIRED"):
            jobs.cancel(session, workspace_id=workspace_id, user_id=user_id, job_id=job.id)
    original = PrivateStorage.delete

    def failing(self, key):
        raise OSError("synthetic storage failure")

    monkeypatch.setattr(PrivateStorage, "delete", failing)
    with pytest.raises(OSError):
        privacy.erase_files(app.state.database, app.state.settings, job)
    with Session(db_engine) as session, session.begin():
        session.get(Job, job.id).state = "failed"
    assert (
        client.post(base + f"/privacy-requests/{result['id']}/retry", headers=headers).status_code
        == 202
    )
    assert (
        client.post(base + f"/privacy-requests/{result['id']}/retry", headers=headers).status_code
        == 202
    )
    monkeypatch.setattr(PrivateStorage, "delete", original)
    assert privacy.erase_files(app.state.database, app.state.settings, job) == {"status": "ok"}
    assert privacy.erase_files(app.state.database, app.state.settings, job) == {"status": "ok"}
    with Session(db_engine) as session, session.begin():
        privacy.finish_erasure(session, job)
    with Session(db_engine) as session:
        assert session.get(Study, UUID(fixture["study_id"])) is None
        assert session.get(PrivacyRequest, UUID(result["id"])).state == "completed"
        assert (
            len(session.scalars(select(Job).where(Job.target_id == UUID(result["id"]))).all()) == 2
        )


def test_source_withdrawal_hides_granted_studies_and_asset_content(phase_scope, db_engine):
    client, _, actor, headers, _, workspace_id, base = phase_scope
    fixture = ready_study(client, base, headers)
    reader, reader_id, _ = actor(workspace_id, "researcher")
    with Session(db_engine) as session:
        member_id = session.scalar(select(Membership.id).where(Membership.user_id == reader_id))
    result = client.post(
        base + f"/studies/{fixture['study_id']}/grants",
        headers=headers,
        json={"membership_id": str(member_id), "capabilities": ["read", "preview"]},
    )
    assert result.status_code == 201
    token_result = client.post(
        fixture["endpoint"] + "/preview", headers=reader, json={"locale": "fr"}
    )
    assert token_result.status_code == 200
    token = {"X-Preview-Token": token_result.json()["preview_token"]}
    assert (
        client.get(f"/api/v1/study-preview/assets/{fixture['asset_id']}", headers=token).status_code
        == 200
    )
    assert (
        client.post(
            base + "/privacy-requests",
            headers=headers,
            json={"kind": "withdrawal", "request_key": "withdraw"},
        ).status_code
        == 202
    )
    assert client.get(base + "/studies", headers=reader).json()["items"] == []
    assert client.post("/api/v1/study-preview", headers=token, json={}).status_code == 401


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("retention_policies", "raw_days", "0"),
        ("consent_documents", "version", "0"),
        ("assets", "state", "'public'"),
        ("assets", "storage_key", "'../escape'"),
        ("privacy_requests", "kind", "'arbitrary'"),
        ("study_versions", "revision", "0"),
        ("studies", "status", "'running'"),
        ("study_grants", "capabilities", "'[\"admin\"]'::jsonb"),
    ],
)
def test_model_checks_reject_invalid_updates(phase_scope, db_engine, table, field, value):
    client, _, actor, headers, _, workspace_id, base = phase_scope
    fixture = ready_study(client, base, headers)
    client.post(
        base + "/privacy-requests",
        headers=headers,
        json={"kind": "access", "request_key": "access"},
    )
    _, reader_id, _ = actor(workspace_id, "viewer")
    with Session(db_engine) as session:
        member_id = session.scalar(select(Membership.id).where(Membership.user_id == reader_id))
    assert (
        client.post(
            base + f"/studies/{fixture['study_id']}/grants",
            headers=headers,
            json={"membership_id": str(member_id), "capabilities": ["read"]},
        ).status_code
        == 201
    )
    with Session(db_engine) as session, pytest.raises(DBAPIError):
        session.execute(
            text(f'UPDATE "{table}" SET "{field}" = {value} WHERE workspace_id = :id'),
            {"id": workspace_id},
        )


def test_model_cross_tenant_relationships_and_receipt_integrity(phase_scope, db_engine):
    client, _, actor, headers, user_id, workspace_id, base = phase_scope
    result = upload(client, base, headers)
    doc = document(client, base, headers)
    _, other_user, other_workspace = actor()
    with Session(db_engine) as session:
        member_id = session.scalar(select(Membership.id).where(Membership.user_id == user_id))
    records = [
        AssetLink(
            workspace_id=other_workspace,
            asset_id=UUID(result["asset"]["id"]),
            owner_membership_id=member_id,
            purpose="stimulus",
        ),
        UploadIntent(
            workspace_id=other_workspace,
            asset_id=UUID(result["asset"]["id"]),
            uploader_id=other_user,
            upload_key="attack",
            expires_at=utcnow() + timedelta(hours=1),
        ),
        ConsentReceipt(
            workspace_id=workspace_id,
            subject_id=user_id,
            document_id=UUID(doc["id"]),
            receipt_key="bad-digest",
            decision="granted",
            presented_digest="b" * 64,
        ),
    ]
    for record in records:
        with Session(db_engine) as session, pytest.raises(DBAPIError):
            session.add(record)
            session.flush()


@pytest.mark.parametrize("index", range(8))
def test_method_event_contracts(index):
    block = methods.parse_block(blocks(str(uuid4()))[index])
    for kind in methods.EVENTS[block.type]:
        metadata = (
            {"attempt_id": "attempt"}
            if kind.startswith("exposure.")
            else {"visibility": "visible", "attempt_id": "attempt"}
            if kind == "visibility.changed"
            else {"variant_id": "one"}
            if kind == "variant.rendered"
            else {"step_index": 0}
            if kind == "prototype.step_reported"
            else {}
        )
        event = {
            "kind": kind,
            "client_event_id": str(uuid4()),
            "sequence": 1,
            "elapsed_ms": 100,
            "metadata": metadata,
        }
        assert methods.validate_event(block, event, "attempt")["provenance"] == "client_observed"
        with pytest.raises(ValueError):
            methods.validate_event(
                block, event | {"metadata": {"email": "private@example.test"}}, "attempt"
            )
    with pytest.raises(ValueError):
        methods.validate_event(
            block,
            {
                "kind": "server.success",
                "client_event_id": str(uuid4()),
                "sequence": 0,
                "elapsed_ms": 0,
            },
        )


def test_human_only_policy_denies_ai(phase_scope, db_engine):
    client, _, _, headers, user_id, workspace_id, base = phase_scope
    fixture = ready_study(client, base, headers)
    with Session(db_engine) as session, pytest.raises(Exception, match="AI_DISABLED"):
        service.authorize(session, workspace_id, user_id, UUID(fixture["study_id"]), "ai")


def test_new_migrations_round_trip_on_guarded_database(db_engine, monkeypatch):
    monkeypatch.setenv("MIGRATION_DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    configuration = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.downgrade(configuration, "003_jobs")
    with db_engine.connect() as connection:
        assert connection.scalar(text("SELECT to_regclass('public.assets')")) is None
        assert connection.scalar(text("SELECT to_regclass('public.jobs')")) is not None
    command.upgrade(configuration, "004_privacy")
    with db_engine.connect() as connection:
        assert connection.scalar(text("SELECT to_regclass('public.assets')")) is not None
        assert connection.scalar(text("SELECT to_regclass('public.studies')")) is None
    command.upgrade(configuration, "head")
    command.check(configuration)
    from app.db import REVISION

    with db_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == REVISION
