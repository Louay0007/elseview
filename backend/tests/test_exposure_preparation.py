"""Non-database protocol regressions; API boundaries use explicit service doubles."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.auth.security import utcnow
from app.collection import router, service
from app.collection.schemas import BatchBody, PrepareExposureBody, StartExposureBody
from app.common.errors import DomainError
from app.studies.methods import parse_block


@pytest.fixture
def exposure(monkeypatch):
    row = SimpleNamespace(
        id=uuid4(),
        version_id=uuid4(),
        state="active",
        last_sequence=-1,
        locale="en",
        assignments={},
        revision=0,
        diary_occurrence_id=None,
        submitted_at=None,
    )
    block = parse_block(
        {
            "block_key": "exposure",
            "schema_version": 1,
            "type": "five_second",
            "required": True,
            "prompt": {"en": "Look once"},
            "config": {
                "asset_ref": {"asset_id": str(uuid4()), "asset_version": 1},
                "exposure_ms": 5000,
                "interruption_policy": "invalidate",
                "recall_block_ids": ["recall"],
            },
        }
    )
    monkeypatch.setattr(service, "definition", lambda *_: (None, [block]))
    monkeypatch.setattr(service, "current_answers", lambda *_: {})
    session = MagicMock()
    session.scalar.return_value = None
    session.flush.side_effect = lambda: [
        setattr(call.args[0], "id", uuid4())
        for call in session.add.call_args_list
        if getattr(call.args[0], "id", None) is None
    ]
    body = PrepareExposureBody(protocol_version=2, version_id=row.version_id, capability="a" * 64)
    receipt = service.prepare_exposure(session, row, "exposure", body)
    attempt = session.add.call_args.args[0]
    session.scalar.return_value = attempt
    return session, row, block, body, attempt, receipt


def test_prepare_is_bounded_and_start_waits_for_single_asset_claim(exposure, monkeypatch):
    session, row, block, body, attempt, receipt = exposure
    assert receipt["state"] == "preparing" and receipt["asset_ref"]
    assert attempt.started_at is None
    assert attempt.preparation_hash != body.capability
    assert attempt.preparation_expires_at - attempt.prepared_at == timedelta(seconds=30)
    assert (
        service.prepare_exposure(session, row, "exposure", body)["attempt_id"]
        == receipt["attempt_id"]
    )
    assert service.exposure_asset_allowed(attempt, body.capability)
    assert not service.exposure_asset_allowed(attempt, "wrong")
    start = StartExposureBody(**body.model_dump(), attempt_id=attempt.id)
    with pytest.raises(DomainError, match="PREPARATION_EXPIRED"):
        service.begin_exposure(session, row, "exposure", start)
    attempt.asset_claimed_at = utcnow()
    assert not service.exposure_asset_allowed(attempt, body.capability)
    assert service.prepare_exposure(session, row, "exposure", body)["asset_ref"] is None
    now = attempt.prepared_at + timedelta(seconds=12)
    monkeypatch.setattr(service, "utcnow", lambda: now)
    first = service.begin_exposure(session, row, "exposure", start)
    assert first["state"] == "started" and not first["replay"]
    assert attempt.started_at == now
    assert service.begin_exposure(session, row, "exposure", start)["replay"]
    assert attempt.started_at == now
    assert not service.exposure_asset_allowed(attempt, body.capability)


def test_prepare_cannot_be_reclaimed_or_downgraded(exposure):
    session, row, block, body, attempt, receipt = exposure
    with pytest.raises(DomainError, match="ATTEMPT_FINAL"):
        service.prepare_exposure(
            session, row, "exposure", body.model_copy(update={"capability": "b" * 64})
        )
    assert service.start_attempt(session, row, "exposure")["asset_ref"] is None
    assert attempt.state == "preparing"
    assert not service.exposure_asset_allowed(
        attempt, body.capability, attempt.preparation_expires_at
    )
    attempt.asset_claimed_at = utcnow()
    attempt.preparation_expires_at = utcnow() - timedelta(seconds=1)
    with pytest.raises(DomainError, match="PREPARATION_EXPIRED"):
        service.begin_exposure(
            session, row, "exposure", StartExposureBody(**body.model_dump(), attempt_id=attempt.id)
        )


@pytest.mark.parametrize("state", ["preparing", "started"])
def test_resume_interrupts_without_inventing_visible_time(exposure, state):
    session, row, block, body, attempt, receipt = exposure
    attempt.state = state
    response = service.resume(session, row)
    assert response["block"]["attempt_state"] == "interrupted"
    assert response["block"]["visible_ms"] is None
    assert "asset_ref" not in response["block"]["config"]
    assert "preparation_hash" not in response["block"]
    assert not service.exposure_asset_allowed(attempt, body.capability)
    assert service.prepare_exposure(session, row, "exposure", body)["asset_ref"] is None


def test_legacy_protocol_retains_five_second_asset_window(exposure):
    session, row, block, body, attempt, receipt = exposure
    attempt.protocol_version = 1
    attempt.state = "started"
    attempt.started_at = utcnow()
    assert service.exposure_asset_allowed(attempt)
    assert not service.exposure_asset_allowed(
        attempt, now=attempt.started_at + timedelta(seconds=6)
    )
    service.resume(session, row)
    assert attempt.state == "started"


def event_body(row, attempt, kind, elapsed):
    return BatchBody(
        version_id=row.version_id,
        events=[
            {
                "block_key": "exposure",
                "event": {
                    "kind": kind,
                    "metadata": {"attempt_id": str(attempt.id)},
                    "elapsed_ms": elapsed,
                    "sequence": row.last_sequence + 1,
                    "client_event_id": str(uuid4()),
                },
            }
        ],
    )


@pytest.mark.parametrize(
    "kind,elapsed,state,expected",
    [
        ("exposure.interrupted", 0, "preparing", "interrupted"),
        ("exposure.ended", 5000, "started", "completed"),
        ("exposure.interrupted", 5300, "started", "interrupted"),
    ],
)
def test_event_finalization_and_exact_replay(exposure, kind, elapsed, state, expected):
    session, row, block, body, attempt, receipt = exposure
    attempt.state = state
    attempt.started_at = utcnow() - timedelta(seconds=6)
    batch = event_body(row, attempt, kind, elapsed)
    session.scalar.side_effect = [attempt, None, None]
    result = service.batch_events(session, row, batch)
    assert attempt.state == expected and attempt.visible_ms == elapsed
    saved = session.add.call_args.args[0]
    session.scalar.side_effect = [attempt, saved]
    assert service.batch_events(session, row, batch) == result
    assert row.last_sequence == 0
    session.scalar.side_effect = [attempt, None, saved]
    with pytest.raises(DomainError, match="ATTEMPT_FINAL"):
        service.batch_events(session, row, event_body(row, attempt, kind, elapsed))


@pytest.mark.parametrize("elapsed,server_seconds", [(0, 6), (5300, 6), (5000, 1), (5000, 31)])
def test_clean_completion_rejects_out_of_window_timing(exposure, elapsed, server_seconds):
    session, row, block, body, attempt, receipt = exposure
    attempt.state = "started"
    attempt.started_at = utcnow() - timedelta(seconds=server_seconds)
    session.scalar.side_effect = [attempt, None, None]
    with pytest.raises(DomainError, match="INVALID_EXPOSURE_TIME"):
        service.batch_events(session, row, event_body(row, attempt, "exposure.ended", elapsed))


def test_v2_protocol_version_is_explicit_and_strict():
    for version in (1, True, "2", 2.0):
        with pytest.raises(ValidationError):
            PrepareExposureBody(protocol_version=version, version_id=uuid4(), capability="a" * 64)


def test_api_prepare_start_body_and_session_header(monkeypatch):
    app = FastAPI()
    app.include_router(router.router)
    app.state.database = SimpleNamespace(sessions=MagicMock())
    monkeypatch.setattr(router, "guard", lambda *_: None)
    monkeypatch.setattr(service, "authorize", lambda *_: SimpleNamespace())
    prepare = MagicMock(return_value={"protocol_version": 2, "state": "preparing"})
    begin = MagicMock(return_value={"protocol_version": 2, "state": "started"})
    monkeypatch.setattr(service, "prepare_exposure", prepare)
    monkeypatch.setattr(service, "begin_exposure", begin)
    url = f"/api/v1/collection/sessions/{uuid4()}/attempts/exposure"
    body = {"protocol_version": 2, "version_id": str(uuid4()), "capability": "a" * 64}
    with TestClient(app) as client:
        assert client.post(url + "/prepare", json=body).status_code == 422
        headers = {"X-Session-Token": "s" * 64}
        assert client.post(url + "/prepare", headers=headers, json=body).status_code == 200
        assert client.post(url + "/start", headers=headers, json=body).status_code == 422
        assert (
            client.post(
                url + "/start", headers=headers, json=body | {"attempt_id": str(uuid4())}
            ).status_code
            == 200
        )
        assert (
            client.post(
                url + "/prepare", headers=headers, json=body | {"protocol_version": 1}
            ).status_code
            == 422
        )
    assert prepare.call_count == begin.call_count == 1
