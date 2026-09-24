import asyncio
import hashlib
import io
import os
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from research_support import document, png, policy, upload
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.auth.models import Membership, Workspace
from app.auth.security import utcnow
from app.common import privacy
from app.common.errors import DomainError
from app.common.privacy_models import Asset, ConsentReceipt, PrivacyRequest, UploadIntent
from app.common.privacy_schemas import PrivacyBody
from app.common.private_storage import PrivateStorage, validate_content
from app.jobs.models import Job
from app.jobs.runner import JobRunner

pytestmark = pytest.mark.db


@pytest.fixture
def scope(research_app):
    client, app, actor = research_app
    headers, user_id, workspace_id = actor()
    return client, app, actor, headers, user_id, workspace_id, f"/api/v1/workspaces/{workspace_id}"


def test_consent_immutable_locales_digest_and_optional_refusal(scope, db_engine):
    client, _, _, headers, user_id, workspace_id, base = scope
    doc = document(client, base, headers, "ai_processing")
    other = document(client, base, headers, "ai_processing", "ar", doc["document_key"])
    assert other["id"] != doc["id"]
    payload = {
        "document_id": doc["id"],
        "presented_digest": doc["digest"],
        "decision": "declined",
        "receipt_key": "once",
    }
    assert (
        client.post(
            base + "/consent-receipts",
            headers=headers,
            json=payload | {"presented_digest": "a" * 64},
        ).status_code
        == 409
    )
    first = client.post(base + "/consent-receipts", headers=headers, json=payload)
    assert first.status_code == 201
    assert (
        client.post(base + "/consent-receipts", headers=headers, json=payload).json()
        == first.json()
    )
    assert (
        client.post(
            base + "/consent-receipts", headers=headers, json=payload | {"decision": "granted"}
        ).status_code
        == 409
    )
    with Session(db_engine) as session:
        assert not privacy.consent_granted(session, workspace_id, user_id, "ai_processing")
        assert not privacy.restricted(session, workspace_id, user_id)
    with Session(db_engine) as session, pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE consent_documents SET body = 'changed' WHERE id = :id"), {"id": doc["id"]}
        )
    with Session(db_engine) as session, pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE consent_receipts SET decision = 'granted' WHERE id = :id"),
            {"id": first.json()["id"]},
        )
    assert len(client.get(base + "/consent-documents", headers=headers).json()["items"]) == 2
    assert len(client.get(base + "/consent-receipts", headers=headers).json()["items"]) == 1


@pytest.mark.parametrize("role", ["owner", "admin", "researcher", "reviewer", "viewer"])
def test_privacy_role_matrix(scope, role):
    client, _, actor, _, _, workspace_id, base = scope
    headers, _, _ = actor(workspace_id, role)
    result = client.post(
        base + "/retention-policies",
        headers=headers,
        json={
            "policy_key": "p",
            "version": 1,
            "raw_days": 1,
            "media_days": 1,
            "derived_days": 1,
            "export_days": 1,
            "legal_basis": "test",
        },
    )
    assert result.status_code == (201 if role in {"owner", "admin"} else 403)


def test_private_upload_quarantine_download_and_replay(scope):
    client, _, _, headers, _, _, base = scope
    result = upload(client, base, headers, complete=False)
    aid, uid = result["asset"]["id"], result["upload_id"]
    assert "storage_key" not in str(result)
    assert client.get(base + f"/assets/{aid}/content", headers=headers).status_code == 409
    first = client.post(base + f"/upload-intents/{uid}/complete", headers=headers)
    assert first.status_code == 200 and first.json()["width"] == 2
    assert (
        client.post(base + f"/upload-intents/{uid}/complete", headers=headers).json()
        == first.json()
    )
    download = client.get(base + f"/assets/{aid}/content", headers=headers)
    assert download.content == png() and "attachment" in download.headers["content-disposition"]
    assert client.get(base + f"/assets/{aid}/content").status_code == 401
    assert client.get(base + f"/assets/{aid}", headers=headers).status_code == 200


def test_cross_tenant_and_revoked_asset_link(scope, db_engine):
    client, _, actor, headers, _, workspace_id, base = scope
    aid = upload(client, base, headers)["asset"]["id"]
    outsider, _, other_workspace = actor()
    assert client.get(base + f"/assets/{aid}/content", headers=outsider).status_code == 404
    assert (
        client.get(
            f"/api/v1/workspaces/{other_workspace}/assets/{aid}", headers=outsider
        ).status_code
        == 404
    )
    reader, reader_id, _ = actor(workspace_id, "viewer")
    assert client.get(base + f"/assets/{aid}/content", headers=reader).status_code == 404
    with Session(db_engine) as session:
        member = session.scalar(select(Membership).where(Membership.user_id == reader_id))
        member_id = str(member.id)
    result = client.post(
        base + f"/assets/{aid}/links", headers=headers, json={"membership_id": member_id}
    )
    assert result.status_code == 201
    assert client.get(base + f"/assets/{aid}/content", headers=reader).status_code == 200
    assert (
        client.delete(
            base + f"/assets/{aid}/links/{result.json()['id']}", headers=headers
        ).status_code
        == 204
    )
    assert client.get(base + f"/assets/{aid}/content", headers=reader).status_code == 404


@pytest.mark.parametrize(
    "filename,media_type,size",
    [
        ("../secret.png", "image/png", 10),
        ("file.svg", "image/png", 10),
        ("file.csv", "image/png", 10),
        ("file.png", "image/png", 9000000),
        ("file.png", "image/png", True),
    ],
)
def test_upload_rejects_path_type_size(scope, filename, media_type, size):
    client, _, _, headers, _, _, base = scope
    result = client.post(
        base + "/upload-intents",
        headers=headers,
        json={
            "upload_key": uuid4().hex,
            "filename": filename,
            "media_type": media_type,
            "purpose": "stimulus",
            "size_bytes": size,
            "checksum": "a" * 64,
            "retention_policy_id": policy(client, base, headers),
        },
    )
    assert result.status_code == 422


def test_invalid_content_and_partial_upload(scope):
    client, _, _, headers, _, _, base = scope
    result = upload(client, base, headers, content=b"not a png", complete=False)
    endpoint = base + "/upload-intents/" + result["upload_id"]
    assert client.post(endpoint + "/complete", headers=headers).status_code == 422
    payload = {
        "upload_key": uuid4().hex,
        "filename": "a.png",
        "media_type": "image/png",
        "purpose": "stimulus",
        "size_bytes": 20,
        "checksum": "a" * 64,
        "retention_policy_id": policy(client, base, headers),
    }
    intent = client.post(base + "/upload-intents", headers=headers, json=payload).json()
    endpoint = base + "/upload-intents/" + intent["upload_id"]
    assert (
        client.put(
            endpoint + "/content", headers=headers | {"content-type": "image/png"}, content=b"short"
        ).status_code
        == 422
    )
    assert client.post(endpoint + "/complete", headers=headers).status_code == 409
    intent = client.post(
        base + "/upload-intents", headers=headers, json=payload | {"upload_key": uuid4().hex}
    ).json()
    assert (
        client.put(
            base + f"/upload-intents/{intent['upload_id']}/content",
            headers=headers | {"content-type": "image/png"},
            content=b"x" * 21,
        ).status_code
        == 413
    )


def test_disk_full_and_symlink_boundaries(scope, tmp_path, monkeypatch):
    client, app, _, headers, _, _, base = scope

    def no_space(*args):
        raise OSError("sensitive disk detail")

    monkeypatch.setattr(PrivateStorage, "create", no_space)
    payload = {
        "upload_key": uuid4().hex,
        "filename": "a.png",
        "media_type": "image/png",
        "purpose": "stimulus",
        "size_bytes": len(png()),
        "checksum": hashlib.sha256(png()).hexdigest(),
        "retention_policy_id": policy(client, base, headers),
    }
    intent = client.post(base + "/upload-intents", headers=headers, json=payload).json()
    response = client.put(
        base + f"/upload-intents/{intent['upload_id']}/content",
        headers=headers | {"content-type": "image/png"},
        content=png(),
    )
    assert response.status_code == 507 and "sensitive" not in response.text
    root = tmp_path / "storage"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "assets").symlink_to(outside)
    with pytest.raises(OSError), PrivateStorage(root).directory():
        pass
    with pytest.raises(DomainError):
        PrivateStorage(app.state.settings.private_root).name("../../secret")


def test_recording_consent_and_revocation(scope):
    client, _, _, headers, _, _, base = scope
    output = io.BytesIO()
    with wave.open(output, "wb") as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(8000)
        recording.writeframes(b"\x00\x00" * 800)
    doc = document(client, base, headers, "recording")
    receipt = {
        "document_id": doc["id"],
        "presented_digest": doc["digest"],
        "decision": "granted",
        "receipt_key": "recording",
    }
    assert client.post(base + "/consent-receipts", headers=headers, json=receipt).status_code == 201
    result = upload(
        client,
        base,
        headers,
        content=output.getvalue(),
        media_type="audio/wav",
        extension="wav",
        purpose="recording",
    )
    assert result["asset"]["duration_ms"] == 100
    assert (
        client.post(
            base + "/consent-receipts",
            headers=headers,
            json=receipt | {"decision": "withdrawn", "receipt_key": "withdraw"},
        ).status_code
        == 201
    )
    assert client.get(
        base + f"/assets/{result['asset']['id']}/content", headers=headers
    ).status_code in {403, 409}


def test_withdrawal_immediate_and_erasure_runner(scope, db_engine):
    client, app, _, headers, user_id, workspace_id, base = scope
    result = upload(client, base, headers)
    aid = result["asset"]["id"]
    with Session(db_engine) as session:
        key = session.get(Asset, UUID(aid)).storage_key
    access = client.post(
        base + "/privacy-requests",
        headers=headers,
        json={"kind": "access", "request_key": "access"},
    ).json()
    assert (
        client.get(base + f"/privacy-requests/{access['id']}/data", headers=headers).json()[
            "assets"
        ][0]["id"]
        == aid
    )
    body = {"kind": "erasure", "request_key": "erase"}
    request = client.post(base + "/privacy-requests", headers=headers, json=body)
    assert request.status_code == 202
    assert (
        client.post(base + "/privacy-requests", headers=headers, json=body).json() == request.json()
    )
    assert client.get(base + f"/assets/{aid}/content", headers=headers).status_code == 403

    async def run():
        runner = JobRunner(
            app.state.database, app.state.settings.model_copy(update={"job_poll_seconds": 0.05})
        )
        with Session(db_engine) as session:
            job = session.scalar(select(Job).where(Job.target_id == UUID(request.json()["id"])))
            job_id = job.id
        from app.jobs.service import claim

        with app.state.database.sessions.begin() as session:
            claimed = claim(session)
            assert claimed.id == job_id
        await runner._execute(claimed)

    asyncio.run(run())
    assert not (app.state.settings.private_root / "assets" / key).exists()
    assert (
        client.get(base + f"/privacy-requests/{request.json()['id']}", headers=headers).json()[
            "state"
        ]
        == "completed"
    )
    with Session(db_engine) as session:
        assert session.get(Asset, UUID(aid)).state == "purged"
        assert privacy.restricted(session, workspace_id, user_id)


def test_privacy_race_and_tenant_constraint(scope, db_engine):
    _, _, actor, _, user_id, workspace_id, _ = scope
    _, _, other_workspace = actor()

    def request(_):
        with Session(db_engine) as session, session.begin():
            return privacy.create_request(
                session, workspace_id, user_id, PrivacyBody(kind="withdrawal", request_key="same")
            ).id

    with ThreadPoolExecutor(2) as executor:
        assert len(set(executor.map(request, range(2)))) == 1
    with Session(db_engine) as session, session.begin():
        assert session.get(Workspace, workspace_id).privacy_epoch == 1
        assert (
            session.scalar(
                select(PrivacyRequest).where(PrivacyRequest.workspace_id == workspace_id)
            ).state
            == "completed"
        )
    with Session(db_engine) as session, pytest.raises(DBAPIError):
        session.add(
            ConsentReceipt(
                workspace_id=other_workspace,
                subject_id=user_id,
                document_id=uuid4(),
                receipt_key="wrong",
                decision="granted",
                presented_digest="a" * 64,
            )
        )
        session.flush()


def test_abandoned_upload_cleanup_and_immutable_asset(scope, db_engine):
    client, _, _, headers, _, _, base = scope
    result = upload(client, base, headers, complete=False)
    with Session(db_engine) as session, session.begin():
        session.get(UploadIntent, UUID(result["upload_id"])).expires_at = utcnow() - timedelta(
            seconds=1
        )
    assert client.post(base + "/assets/retention-sweep", headers=headers).json() == {"purged": 1}
    with Session(db_engine) as session, pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE assets SET checksum = :hash WHERE id = :id"),
            {"hash": "b" * 64, "id": result["asset"]["id"]},
        )


@pytest.mark.parametrize(
    "content,kind",
    [
        (b"<html>x</html>", "image/png"),
        (png()[:-3], "image/png"),
        (b"a,b\n1\n", "text/csv"),
        (b"\x00", "text/plain"),
        (b"bad", "audio/wav"),
    ],
)
def test_invalid_file_formats(content, kind):
    with pytest.raises((ValueError, wave.Error, EOFError)):
        validate_content(content, kind, hashlib.sha256(content).hexdigest())


def test_storage_file_symlink_and_private_modes(tmp_path):
    storage = PrivateStorage(tmp_path, minimum_free=0)
    key = uuid4().hex
    descriptor = storage.create(key, 1)
    os.write(descriptor, b"x")
    os.close(descriptor)
    assert (tmp_path / "assets" / key).stat().st_mode & 0o777 == 0o600
    assert storage.read(key, 1) == b"x"
    storage.delete(key)
    storage.delete(key)
    outside = tmp_path / "external"
    outside.write_text("private")
    (tmp_path / "assets" / key).symlink_to(outside)
    with pytest.raises(OSError):
        storage.read(key, 100)
    storage.delete(key)
    assert outside.read_text() == "private"
