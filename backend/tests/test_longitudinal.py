from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.common.errors import DomainError
from app.longitudinal.schemas import LocalTime, SlotBody, TranscriptBody
from app.longitudinal.service import local_utc


@pytest.mark.unit
def test_tunis_fixed_offset_and_explicit_fold():
    assert local_utc(LocalTime(local=datetime(2026, 7, 1, 10)), "Africa/Tunis") == datetime(
        2026, 7, 1, 9, tzinfo=UTC
    )
    early = local_utc(LocalTime(local=datetime(2026, 11, 1, 1, 30), fold=0), "America/New_York")
    late = local_utc(LocalTime(local=datetime(2026, 11, 1, 1, 30), fold=1), "America/New_York")
    assert (late - early).total_seconds() == 3600


@pytest.mark.unit
@pytest.mark.parametrize(
    "local,zone,fold",
    [
        ("2026-03-08T02:30:00", "America/New_York", None),
        ("2026-11-01T01:30:00", "America/New_York", None),
        ("2026-07-01T10:00:00", "invalid-zone", None),
        ("2026-07-01T10:00:00+01:00", "Africa/Tunis", None),
        ("2026-07-01T10:00:00", "Africa/Tunis", 1),
    ],
)
def test_invalid_local_choices(local, zone, fold):
    with pytest.raises(DomainError):
        local_utc(LocalTime(local=local, fold=fold), zone)


@pytest.mark.unit
def test_transcript_exactly_one_source_and_limits():
    with pytest.raises(ValidationError):
        TranscriptBody()
    with pytest.raises(ValidationError):
        TranscriptBody(text="hello", segments=[{"start_ms": 0, "end_ms": 1, "text": "hello"}])
    with pytest.raises(ValidationError):
        TranscriptBody(segments=[{"start_ms": True, "end_ms": 1, "text": "x"}])
    assert TranscriptBody(text="مرحبا").text == "مرحبا"


@pytest.mark.unit
def test_slot_strict_capacity_and_https():
    body = dict(
        version_id=uuid4(),
        timezone="Africa/Tunis",
        starts={"local": "2026-10-01T10:00:00"},
        ends={"local": "2026-10-01T10:30:00"},
        join_url="https://meeting.example.test/a",
    )
    assert SlotBody(**body).capacity == 1
    for value in [True, 0, 101, 1.1]:
        with pytest.raises(ValidationError):
            SlotBody(**body, capacity=value)
    body["join_url"] = "javascript:alert(1)"
    with pytest.raises(ValidationError):
        SlotBody(**body)
