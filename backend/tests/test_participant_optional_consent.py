from uuid import UUID, uuid4

import pytest
from research_support import document
from sqlalchemy.orm import Session
from test_collection_db import collected as collected_fixture

from app.collection.models import CollectionSession
from app.common.privacy import consent_granted

collected = collected_fixture
pytestmark = pytest.mark.db


def test_optional_context_exact_version_and_own_identity(collected, research_app, db_engine):
    client, url, _, result, participant, _ = collected
    _, _, actor = research_app
    with Session(db_engine) as session:
        row = session.get(CollectionSession, UUID(result["session_id"]))
        workspace_id, subject_id, version_id = row.workspace_id, row.subject_id, row.version_id
    admin, _, _ = actor(workspace_id=workspace_id, role="admin")
    other, _, _ = actor()
    doc = document(client, f"/api/v1/workspaces/{workspace_id}", admin, "accessibility_context")
    endpoint = url + "/optional-consent"
    assert (
        client.get(endpoint, headers=other, params={"purpose": "accessibility_context"}).status_code
        == 404
    )
    shown = client.get(endpoint, headers=participant, params={"purpose": "accessibility_context"})
    assert shown.status_code == 200
    assert shown.json()["study_version_id"] == str(version_id)
    body = {
        "purpose": "accessibility_context",
        "document_id": doc["id"],
        "presented_digest": doc["digest"],
        "decision": "granted",
        "receipt_key": uuid4().hex,
    }
    assert (
        client.post(
            endpoint, headers=participant, json=body | {"presented_digest": "0" * 64}
        ).status_code
        == 409
    )
    saved = client.post(endpoint, headers=participant, json=body)
    assert saved.status_code == 200, saved.text
    assert client.post(endpoint, headers=participant, json=body).json() == saved.json()
    assert (
        client.post(
            endpoint, headers=participant, json=body | {"decision": "withdrawn"}
        ).status_code
        == 409
    )
    with Session(db_engine) as session:
        assert consent_granted(
            session, workspace_id, subject_id, "accessibility_context", study_version_id=version_id
        )
        assert not consent_granted(
            session, workspace_id, subject_id, "accessibility_context", study_version_id=uuid4()
        )
    assert (
        client.post(
            endpoint,
            headers=participant,
            json=body | {"decision": "withdrawn", "receipt_key": uuid4().hex},
        ).status_code
        == 200
    )
    with Session(db_engine) as session:
        assert not consent_granted(
            session, workspace_id, subject_id, "accessibility_context", study_version_id=version_id
        )


def test_human_only_cannot_opt_into_ai(collected, research_app, db_engine):
    client, url, _, result, participant, _ = collected
    _, _, actor = research_app
    with Session(db_engine) as session:
        workspace_id = session.get(CollectionSession, UUID(result["session_id"])).workspace_id
    admin, _, _ = actor(workspace_id=workspace_id, role="admin")
    doc = document(client, f"/api/v1/workspaces/{workspace_id}", admin, "ai_processing")
    body = {
        "purpose": "ai_processing",
        "document_id": doc["id"],
        "presented_digest": doc["digest"],
        "decision": "granted",
        "receipt_key": uuid4().hex,
    }
    assert client.post(url + "/optional-consent", headers=participant, json=body).status_code == 403
    assert (
        client.post(
            url + "/optional-consent", headers=participant, json=body | {"decision": "declined"}
        ).status_code
        == 200
    )
