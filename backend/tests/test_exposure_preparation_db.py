"""Run only through the isolated database test runner; never reset a shared database."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_collection_db import collected as collected

from app.auth.security import utcnow
from app.collection.models import InteractionAttempt

pytestmark = pytest.mark.db


def advance_to_exposure(collected):
    from study_fixtures import answer

    client, url, headers, result, _, _ = collected
    for _ in range(5):
        block = client.get(url, headers=headers).json()["block"]
        response = client.put(
            url + "/answers/" + block["block_key"],
            headers=headers,
            json={
                "schema_version": 1,
                "expected_revision": 0,
                "client_event_id": str(uuid4()),
                **answer(block),
            },
        )
        assert response.status_code == 200, response.text
    body = {"protocol_version": 2, "version_id": result["version_id"], "capability": "a" * 64}
    response = client.post(url + "/attempts/exposure/prepare", headers=headers, json=body)
    assert response.status_code == 200, response.text
    return client, url, headers, body, response.json()


@pytest.mark.parametrize("collected", ["methods"], indirect=True)
def test_v2_single_use_asset_start_replay_completion_and_answer_revisions(collected, db_engine):
    client, url, headers, body, prepared = advance_to_exposure(collected)
    asset = url + "/assets/" + prepared["asset_ref"]["asset_id"]
    assert client.get(asset, headers=headers).status_code == 404
    asset_headers = headers | {"X-Exposure-Token": body["capability"]}
    response = client.get(asset, headers=asset_headers)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert client.get(asset, headers=asset_headers).status_code == 404
    assert (
        client.post(url + "/attempts/exposure/prepare", headers=headers, json=body).json()[
            "asset_ref"
        ]
        is None
    )
    start = body | {"attempt_id": prepared["attempt_id"]}
    first = client.post(url + "/attempts/exposure/start", headers=headers, json=start)
    assert first.status_code == 200 and not first.json()["replay"]
    assert client.post(url + "/attempts/exposure/start", headers=headers, json=start).json()[
        "replay"
    ]
    assert client.post(url + "/attempts/exposure", headers=headers).json()["asset_ref"] is None
    with Session(db_engine) as session, session.begin():
        attempt = session.get(InteractionAttempt, UUID(prepared["attempt_id"]))
        assert attempt.protocol_version == 2 and attempt.asset_claimed_at is not None
        attempt.started_at = utcnow() - timedelta(seconds=6)
    event = {
        "version_id": body["version_id"],
        "events": [
            {
                "block_key": "exposure",
                "event": {
                    "kind": "exposure.ended",
                    "metadata": {"attempt_id": prepared["attempt_id"]},
                    "sequence": 0,
                    "elapsed_ms": 5000,
                    "client_event_id": str(uuid4()),
                },
            }
        ],
    }
    response = client.post(url + "/events", headers=headers, json=event)
    assert response.status_code == 200, response.text
    assert client.post(url + "/events", headers=headers, json=event).json() == response.json()
    value = {"attempt_id": prepared["attempt_id"], "visible_ms": 5000, "interrupted": False}
    answer = {
        "version_id": body["version_id"],
        "schema_version": 1,
        "expected_revision": 0,
        "client_event_id": str(uuid4()),
        "status": "responded",
        "value": value,
    }
    saved = client.put(url + "/answers/exposure", headers=headers, json=answer)
    assert saved.status_code == 200, saved.text
    assert (
        client.put(url + "/answers/exposure", headers=headers, json=answer).json() == saved.json()
    )
    assert client.get(asset, headers=asset_headers).status_code == 404
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(InteractionAttempt)
                .where(InteractionAttempt.session_id == UUID(collected[3]["session_id"]))
            )
            == 1
        )


@pytest.mark.parametrize("collected", ["methods"], indirect=True)
@pytest.mark.parametrize("start_first", [False, True])
def test_reload_interruption_cannot_reprepare_or_fabricate_zero_timing(collected, start_first):
    client, url, headers, body, prepared = advance_to_exposure(collected)
    asset = url + "/assets/" + prepared["asset_ref"]["asset_id"]
    asset_headers = headers | {"X-Exposure-Token": body["capability"]}
    if start_first:
        assert client.get(asset, headers=asset_headers).status_code == 200
        assert (
            client.post(
                url + "/attempts/exposure/start",
                headers=headers,
                json=body | {"attempt_id": prepared["attempt_id"]},
            ).status_code
            == 200
        )
    resumed = client.get(url, headers=headers).json()["block"]
    assert resumed["attempt_state"] == "interrupted" and resumed["visible_ms"] is None
    assert client.get(asset, headers=asset_headers).status_code == 404
    assert (
        client.post(
            url + "/attempts/exposure/prepare",
            headers=headers,
            json=body | {"capability": "b" * 64},
        ).status_code
        == 409
    )
    fabricated = {
        "schema_version": 1,
        "expected_revision": 0,
        "client_event_id": str(uuid4()),
        "status": "responded",
        "value": {"attempt_id": prepared["attempt_id"], "visible_ms": 0, "interrupted": True},
    }
    assert (
        client.put(url + "/answers/exposure", headers=headers, json=fabricated).status_code == 422
    )
    unable = fabricated | {
        "client_event_id": str(uuid4()),
        "status": "unable",
        "value": None,
        "reason_code": "technical",
    }
    assert client.put(url + "/answers/exposure", headers=headers, json=unable).status_code == 200


@pytest.mark.parametrize("collected", ["methods"], indirect=True)
def test_expired_preparation_and_decode_failure_have_no_second_attempt(collected, db_engine):
    client, url, headers, body, prepared = advance_to_exposure(collected)
    with Session(db_engine) as session, session.begin():
        attempt = session.get(InteractionAttempt, UUID(prepared["attempt_id"]))
        attempt.preparation_expires_at = utcnow() - timedelta(seconds=1)
    asset = url + "/assets/" + prepared["asset_ref"]["asset_id"]
    assert (
        client.get(asset, headers=headers | {"X-Exposure-Token": body["capability"]}).status_code
        == 404
    )
    assert (
        client.post(
            url + "/attempts/exposure/start",
            headers=headers,
            json=body | {"attempt_id": prepared["attempt_id"]},
        ).status_code
        == 409
    )
    event = {
        "version_id": body["version_id"],
        "events": [
            {
                "block_key": "exposure",
                "event": {
                    "kind": "exposure.interrupted",
                    "metadata": {"attempt_id": prepared["attempt_id"]},
                    "sequence": 0,
                    "elapsed_ms": 0,
                    "client_event_id": str(uuid4()),
                },
            }
        ],
    }
    assert client.post(url + "/events", headers=headers, json=event).status_code == 200
    resumed = client.get(url, headers=headers).json()["block"]
    assert resumed["visible_ms"] == 0 and resumed["attempt_state"] == "interrupted"
    assert (
        client.post(url + "/attempts/exposure/prepare", headers=headers, json=body).json()[
            "asset_ref"
        ]
        is None
    )
