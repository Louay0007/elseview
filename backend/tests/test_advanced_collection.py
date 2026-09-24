"""Service latch/replay tests with inert sessions; DB constraints tested in lead window."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.collection import service
from app.collection.schemas import BatchBody
from app.common.errors import DomainError
from app.studies import methods


def setup(monkeypatch, prior=None, latch=None):
    asset, version, sid = uuid4(), uuid4(), uuid4()
    block = methods.parse_block(
        dict(
            block_key="click",
            schema_version=1,
            type="first_click",
            required=True,
            prompt={"en": "Click"},
            config=dict(
                asset_ref={"asset_id": str(asset), "asset_version": 1},
                asset_width=100,
                asset_height=100,
                coordinate_space="normalized_asset",
                input_modes=["pointer"],
            ),
        )
    )
    value = dict(
        asset_id=str(asset), asset_version=1, x=0.2, y=0.3, elapsed_ms=20, input_mode="pointer"
    )
    event = dict(
        kind="first_click.recorded",
        client_event_id=str(uuid4()),
        sequence=1,
        elapsed_ms=20,
        metadata=value,
    )
    body = BatchBody.model_validate(
        dict(version_id=version, events=[dict(block_key="click", event=event)])
    )
    row = SimpleNamespace(id=sid, version_id=version, state="active", last_sequence=0)
    session = MagicMock()
    session.scalar.side_effect = [None, prior, None]
    monkeypatch.setattr(service, "definition", lambda *a: (None, [block]))
    monkeypatch.setattr(service, "current_answers", lambda *a: {})
    monkeypatch.setattr(service, "first_click", lambda *a: latch)
    return session, row, body, block, event


def test_first_click_stored_exactly_once(monkeypatch):
    session, row, body, block, event = setup(monkeypatch)
    result = service.batch_events(session, row, body)
    saved = session.add.call_args.args[0]
    assert saved.kind == "first_click.recorded"
    assert saved.payload["metadata"] == event["metadata"]
    assert result["last_sequence"] == 1
    assert session.add.call_count == 1


def test_latched_second_click_denied(monkeypatch):
    session, row, body, _, _ = setup(monkeypatch, latch=object())
    with pytest.raises(DomainError) as error:
        service.batch_events(session, row, body)
    assert error.value.code == "FIRST_CLICK_FINAL"
    session.add.assert_not_called()


def test_identical_retry_acknowledged_without_insert(monkeypatch):
    session, row, body, block, event = setup(monkeypatch)
    prior = SimpleNamespace(payload=methods.validate_event(block, event), block_key="click")
    session.scalar.side_effect = [None, prior]
    row.last_sequence = 1
    assert service.batch_events(session, row, body)["accepted"] == [event["client_event_id"]]
    session.add.assert_not_called()


def test_changed_retry_conflicts(monkeypatch):
    session, row, body, block, event = setup(monkeypatch)
    prior = SimpleNamespace(payload=methods.validate_event(block, event), block_key="click")
    prior.payload["metadata"]["x"] = 0.9
    session.scalar.side_effect = [None, prior]
    with pytest.raises(DomainError) as error:
        service.batch_events(session, row, body)
    assert error.value.code == "IDEMPOTENCY_CONFLICT"
    session.add.assert_not_called()


@pytest.mark.parametrize("latched,mutated", [(False, False), (True, True)])
def test_answer_requires_exact_latch(monkeypatch, latched, mutated):
    from app.collection.schemas import AnswerBody

    session, row, _, block, event = setup(monkeypatch)
    row.locale = "en"
    row.assignments = {}
    value = dict(event["metadata"])
    if mutated:
        value["x"] = 0.9
    body = AnswerBody.model_validate(
        dict(
            version_id=row.version_id,
            schema_version=1,
            expected_revision=0,
            client_event_id=uuid4(),
            status="responded",
            value=value,
        )
    )
    session.scalar.side_effect = [None, None, None]
    monkeypatch.setattr(
        service, "first_click", lambda *a: SimpleNamespace(payload=event) if latched else None
    )
    with pytest.raises(DomainError) as error:
        service.save_answer(session, row, "click", body)
    assert error.value.code == "INVALID_ANSWER"
    session.add.assert_not_called()
