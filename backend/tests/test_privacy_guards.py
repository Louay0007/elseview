from uuid import UUID

import pytest
from research_support import document, policy, upload
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.auth.models import Membership

pytestmark = pytest.mark.db


@pytest.mark.parametrize("resource", ["document", "policy", "dimensions"])
def test_validated_privacy_records_are_immutable(research_app, db_engine, resource):
    client, _, actor = research_app
    headers, _, workspace_id = actor()
    base = f"/api/v1/workspaces/{workspace_id}"
    if resource == "document":
        identifier = document(client, base, headers)["id"]
        statement = "DELETE FROM consent_documents WHERE id = :id"
    elif resource == "policy":
        identifier = policy(client, base, headers)
        statement = "DELETE FROM retention_policies WHERE id = :id"
    else:
        identifier = upload(client, base, headers)["asset"]["id"]
        statement = "UPDATE assets SET width = 3 WHERE id = :id"
    with Session(db_engine) as session, pytest.raises(DBAPIError):
        session.execute(text(statement), {"id": UUID(identifier)})


def test_upload_rechecks_downgraded_role(research_app, db_engine):
    client, _, actor = research_app
    owner_headers, _, workspace_id = actor()
    headers, user_id, _ = actor(workspace_id, "researcher")
    base = f"/api/v1/workspaces/{workspace_id}"
    policy_id = policy(client, base, owner_headers)
    result = upload(client, base, headers, policy_id=policy_id, complete=False)
    with Session(db_engine) as session, session.begin():
        session.scalar(select(Membership).where(Membership.user_id == user_id)).role = "viewer"
    response = client.post(
        base + f"/upload-intents/{result['upload_id']}/complete", headers=headers
    )
    assert response.status_code == 403
