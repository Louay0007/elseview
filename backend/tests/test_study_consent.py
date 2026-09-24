from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session
from study_fixtures import ready_study

from app.common.privacy import consent_granted
from app.common.privacy_models import ConsentDocument

pytestmark = pytest.mark.db


def test_study_receipt_is_version_bound(research_app, db_engine):
    client, _, actor = research_app
    headers, user_id, workspace_id = actor()
    base = f"/api/v1/workspaces/{workspace_id}"
    first = ready_study(client, base, headers)
    second = ready_study(client, base, headers)
    with Session(db_engine) as session:
        document = session.get(ConsentDocument, UUID(first["body"]["consent_documents"]["fr"]))
        payload = {
            "document_id": str(document.id),
            "presented_digest": document.digest,
            "decision": "granted",
            "receipt_key": "study-consent",
        }
    assert client.post(base + "/consent-receipts", headers=headers, json=payload).status_code == 422
    assert (
        client.post(
            base + "/consent-receipts",
            headers=headers,
            json=payload | {"study_version_id": first["version_id"]},
        ).status_code
        == 409
    )
    for fixture in (first, second):
        assert (
            client.post(
                fixture["endpoint"] + "/publish", headers=headers, json={"expected_revision": 2}
            ).status_code
            == 200
        )
    assert (
        client.post(
            base + "/consent-receipts",
            headers=headers,
            json=payload | {"study_version_id": second["version_id"]},
        ).status_code
        == 409
    )
    response = client.post(
        base + "/consent-receipts",
        headers=headers,
        json=payload | {"study_version_id": first["version_id"]},
    )
    assert response.status_code == 201, response.text
    with Session(db_engine) as session:
        assert consent_granted(
            session, workspace_id, user_id, "study", study_version_id=UUID(first["version_id"])
        )
        assert not consent_granted(
            session, workspace_id, user_id, "study", study_version_id=UUID(second["version_id"])
        )
        assert not consent_granted(session, workspace_id, user_id, "study")
    withdrawn = payload | {
        "study_version_id": first["version_id"],
        "decision": "withdrawn",
        "receipt_key": uuid4().hex,
    }
    assert (
        client.post(base + "/consent-receipts", headers=headers, json=withdrawn).status_code == 201
    )
    with Session(db_engine) as session:
        assert not consent_granted(
            session, workspace_id, user_id, "study", study_version_id=UUID(first["version_id"])
        )
