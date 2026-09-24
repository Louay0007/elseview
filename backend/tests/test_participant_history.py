from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.recruiting.history import _rows


@pytest.mark.parametrize("offset,expected", [(0, 25), (99_975, 100_000), (100_000, None)])
def test_history_continuations_never_exceed_the_route_bound(offset, expected):
    session = SimpleNamespace(execute=lambda _: SimpleNamespace(all=lambda: list(range(26))))
    rows, next_offset = _rows(session, select(1), offset, 25)
    assert rows == list(range(25))
    assert next_offset == expected
