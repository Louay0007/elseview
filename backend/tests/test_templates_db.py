"""Every recipe exercises the real HTTP/DB path, never a synthetic production answer generator."""

import secrets
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from research_support import document, policy, upload
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from study_fixtures import answer
from test_templates import body_for

from app.analytics.models import AnalysisSnapshot
from app.auth.models import Membership, User
from app.auth.security import token_hash, utcnow
from app.common.privacy_models import ConsentDocument
from app.recruiting.models import (
    Candidate,
    Invitation,
    PanelConsent,
    ParticipantProfile,
    RecruitmentConfig,
)
from app.studies.models import Launch, StudyGrant, StudyVersion
from app.templates.catalogue import catalogue
from app.templates.models import TemplateInstance
from app.templates.schemas import InstantiateBody

pytestmark = pytest.mark.db


@pytest.mark.parametrize("recipe", catalogue(), ids=lambda r: r["key"])
def test_every_template_full_http_lifecycle(recipe, research_app, db_engine):
    client, app, actor = research_app
    owner_headers, owner, workspace_id = actor()
    base = f"/api/v1/workspaces/{workspace_id}"
    assert client.get("/api/v1/templates", headers=owner_headers).status_code == 200
    assert (
        client.get("/api/v1/templates/" + recipe["key"], headers=owner_headers).json()[
            "recipe_hash"
        ]
        == recipe["recipe_hash"]
    )
    retention = policy(client, base, owner_headers)
    assets = [
        upload(client, base, owner_headers, policy_id=retention)["asset"]["id"] for _ in range(2)
    ]
    if recipe["family"] == "localization":
        assets[0] = upload(
            client,
            base,
            owner_headers,
            content=b"Synthetic original",
            media_type="text/plain",
            extension="txt",
            policy_id=retention,
        )["asset"]["id"]
    consent_key = uuid4().hex
    documents = {
        loc: document(client, base, owner_headers, locale=loc, key=consent_key)["id"]
        for loc in recipe["locales"]
    }
    body = body_for(recipe, assets, documents, retention)
    endpoint = base + "/templates/" + recipe["key"] + "/instantiate"
    headers = owner_headers | {"Idempotency-Key": uuid4().hex}
    response = client.post(endpoint, headers=headers, json=body)
    assert response.status_code == 201, response.text
    fixture = response.json()
    assert client.post(endpoint, headers=headers, json=body).json() == fixture
    changed = dict(body, title="Conflicting retry")
    assert client.post(endpoint, headers=headers, json=changed).status_code == 409
    outsider, _, _ = actor()
    assert client.post(
        endpoint, headers=outsider | {"Idempotency-Key": uuid4().hex}, json=body
    ).status_code in (403, 404)
    study_endpoint = base + f"/studies/{fixture['study_id']}/versions/{fixture['version_id']}"
    response = client.post(
        study_endpoint + "/publish",
        headers=owner_headers,
        json={"expected_revision": fixture["revision"]},
    )
    assert response.status_code == 200, response.text
    with Session(db_engine) as session, session.begin():
        provenance = session.get(TemplateInstance, UUID(fixture["template_instance_id"]))
        assert provenance.inputs_snapshot == InstantiateBody(**body).model_dump(mode="json")
        version = session.get(StudyVersion, UUID(fixture["version_id"]))
        assert version.rules_json == {} and version.consent_documents == documents
        with pytest.raises(DBAPIError), session.begin_nested():
            session.execute(
                text("UPDATE template_instances SET template_version=2 WHERE id=:id"),
                {"id": provenance.id},
            )
    raw = secrets.token_urlsafe(32)
    with Session(db_engine) as session, session.begin():
        user = User(
            email=f"participant-{uuid4().hex}@example.test",
            password_hash="synthetic",
            verified_at=utcnow(),
        )
        session.add(user)
        session.flush()
        participant_headers = {
            "Authorization": "Bearer " + app.state.auth._new_login(session, user)["access_token"]
        }
        profile = ParticipantProfile(user_id=user.id)
        session.add(profile)
        session.flush()
        session.add(
            PanelConsent(
                profile_id=profile.id,
                decision="granted",
                document_version="1",
                document_digest="a" * 64,
                request_digest="a" * 64,
                receipt_key=uuid4().hex,
            )
        )
        launch = session.scalar(
            select(Launch).where(Launch.version_id == UUID(fixture["version_id"]))
        )
        session.add(
            RecruitmentConfig(
                workspace_id=workspace_id,
                launch_id=launch.id,
                capacity=5,
                budget_millimes=0,
                reward_millimes=0,
            )
        )
        candidate = Candidate(
            workspace_id=workspace_id,
            launch_id=launch.id,
            subject_id=user.id,
            source_kind="public",
            source_id=profile.id,
            status="eligible",
            attributes_json={},
        )
        session.add(candidate)
        session.flush()
        session.add(
            Invitation(
                workspace_id=workspace_id,
                candidate_id=candidate.id,
                token_hash=token_hash(raw),
                expires_at=utcnow() + timedelta(hours=1),
            )
        )
        consent_doc = session.get(ConsentDocument, UUID(documents[recipe["locales"][0]]))
        body = {
            "invitation_token": raw,
            "capability": secrets.token_urlsafe(32),
            "locale": recipe["locales"][0],
            "document_id": str(consent_doc.id),
            "presented_digest": consent_doc.digest,
            "consent": "granted",
        }
    response = client.post("/api/v1/collection/sessions", headers=participant_headers, json=body)
    assert response.status_code == 201, response.text
    result = response.json()
    url = "/api/v1/collection/sessions/" + result["session_id"]
    participant = {"X-Session-Token": body["capability"]}
    count = 0
    while True:
        state = client.get(url, headers=participant).json()
        block = state.get("block")
        if block is None:
            break
        assert "rules_json" not in block and "evaluation" not in block
        if block["type"] == "language.review":
            payload = {
                "status": "responded",
                "value": {
                    "ratings": [{"dimension_id": "clarity", "value": 4}],
                    "issues": [
                        {
                            "quote": "original",
                            "explanation": {
                                "text": "Synthetic note",
                                "language": recipe["locales"][0],
                            },
                        }
                    ],
                },
            }
        else:
            payload = (
                {
                    "status": "responded",
                    "value": {"ordered_option_ids": [o["id"] for o in block["config"]["options"]]},
                }
                if block["type"] == "survey.ranking"
                else answer(block, recipe["locales"][0])
            )
        response = client.put(
            url + "/answers/" + block["block_key"],
            headers=participant,
            json={
                "schema_version": 1,
                "expected_revision": 0,
                "client_event_id": str(uuid4()),
                **payload,
            },
        )
        assert response.status_code == 200, response.text
        count += 1
        assert count <= len(recipe["blocks"])
    assert count == len(recipe["blocks"])
    response = client.post(
        url + "/submit",
        headers=participant,
        json={"version_id": result["version_id"], "expected_revision": count},
    )
    assert response.status_code == 200, response.text
    for _ in range(2):
        review_headers, reviewer, _ = actor(workspace_id, role="reviewer")
        with Session(db_engine) as session, session.begin():
            member = session.scalar(
                select(Membership).where(
                    Membership.workspace_id == workspace_id, Membership.user_id == reviewer
                )
            )
            session.add(
                StudyGrant(
                    workspace_id=workspace_id,
                    study_id=UUID(fixture["study_id"]),
                    membership_id=member.id,
                    capabilities=["read", "review"],
                )
            )
        response = client.post(
            base + "/reviews/sessions/" + result["session_id"] + "/assignments",
            headers=owner_headers,
            json={"reviewer_id": str(reviewer), "kind": "independent"},
        )
        assert response.status_code == 201, response.text
        response = client.post(
            base + "/reviews/assignments/" + response.json()["id"] + "/decision",
            headers=review_headers,
            json={
                "command_key": str(uuid4()),
                "verdict": "accepted",
                "rationale": "Synthetic fixture reviewed",
                "evidence": ["clarity: final answer"],
            },
        )
        assert response.status_code == 200, response.text
    response = client.post(
        base + "/analytics/snapshots",
        headers=owner_headers,
        json={"study_id": fixture["study_id"], "version_id": fixture["version_id"]},
    )
    assert response.status_code == 201, response.text
    snapshot_id = response.json()["id"]
    with Session(db_engine) as session:
        metrics = session.get(AnalysisSnapshot, UUID(snapshot_id)).metrics
        assert metrics["included"] == 1
        assert metrics["blocks"]["clarity"]["distribution"]["4"]["numerator"] == 1
        if recipe["family"] == "localization":
            assert metrics["blocks"]["language"]["mean_rating"]["clarity"]["value"] == 4
            assert (
                metrics["blocks"]["language"]["reviewer_basis"]
                == "participant_self_report_unverified"
            )
        if "survey.ranking" in recipe["methods"]:
            assert metrics["blocks"]["comparison"]["mean_rank"]["option_0"]["value"] == 1
        if "preference" in recipe["methods"]:
            assert metrics["blocks"]["comparison"]["distribution"]["tie"]["numerator"] == 1
        if recipe["family"] != "localization":
            assert metrics["blocks"]["task_1"]["completion"]["numerator"] == 1
            assert metrics["blocks"]["task_1"]["completion"]["provenance"] == "self_report"
    response = client.post(
        base + "/analytics/reports", headers=owner_headers, json={"snapshot_id": snapshot_id}
    )
    assert response.status_code == 201, response.text
    report = base + "/analytics/reports/" + response.json()["id"]
    assert (
        client.post(
            report + "/approve", headers=owner_headers, json={"expected_revision": 1}
        ).status_code
        == 200
    )
    response = client.post(report + "/shares", headers=owner_headers, json={"ttl_seconds": 60})
    assert response.status_code == 201, response.text
    public = client.get("/api/v1/report-shares/" + response.json()["token"])
    assert public.status_code == 200, public.text
    assert public.json()["sample_size_band"] == "suppressed"
    assert "Clair" not in public.text and str(owner) not in public.text


def test_template_invalid_inputs_are_atomic(research_app, db_engine):
    from sqlalchemy import func

    from app.studies.models import Study

    client, _, actor = research_app
    headers, _, wid = actor()
    base = f"/api/v1/workspaces/{wid}"
    recipe = catalogue()[0]
    retention = policy(client, base, headers)
    key = uuid4().hex
    documents = {
        loc: document(client, base, headers, locale=loc, key=key)["id"] for loc in recipe["locales"]
    }
    body = body_for(recipe, consent=documents, retention=retention)
    endpoint = base + "/templates/" + recipe["key"] + "/instantiate"
    with Session(db_engine) as session:
        before = session.scalar(
            select(func.count()).select_from(Study).where(Study.workspace_id == wid)
        )
    # Well-shaped but nonexistent assets cannot leave a partially created study.
    response = client.post(endpoint, headers=headers | {"Idempotency-Key": uuid4().hex}, json=body)
    assert response.status_code == 404, response.text
    body["inputs"]["prompts"].clear()
    assert (
        client.post(
            endpoint, headers=headers | {"Idempotency-Key": uuid4().hex}, json=body
        ).status_code
        == 422
    )
    with Session(db_engine) as session:
        assert (
            session.scalar(select(func.count()).select_from(Study).where(Study.workspace_id == wid))
            == before
        )
    viewer, _, _ = actor(wid, role="viewer")
    assert (
        client.post(
            endpoint, headers=viewer | {"Idempotency-Key": uuid4().hex}, json=body
        ).status_code
        == 403
    )
