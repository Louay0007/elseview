from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.analytics import service
from app.common.errors import DomainError

pytestmark = pytest.mark.unit


def listing(monkeypatch, counts):
    ids = [uuid4() for _ in counts]
    calls = []
    member = SimpleNamespace(id=uuid4())
    monkeypatch.setattr(service, "lock_workspace", lambda *args: None)
    monkeypatch.setattr(service, "require_workspace", lambda *args: member)
    monkeypatch.setattr(service, "require_unrestricted", lambda *args: None)
    session = SimpleNamespace(
        execute=lambda query: SimpleNamespace(all=lambda: list(zip(ids, counts, strict=True)))
    )

    def access(session, workspace_id, actor_id, report_id):
        calls.append(report_id)
        return SimpleNamespace(id=report_id), SimpleNamespace(number=2, state="draft"), None, None

    monkeypatch.setattr(service, "report_access", access)
    return session, ids, calls, access


def test_index_filters_before_offset_and_has_more(monkeypatch):
    session, ids, calls, access = listing(monkeypatch, [1] * 5)

    def guarded(*args):
        if args[-1] in ids[:2]:
            raise DomainError("ANALYSIS_UNAVAILABLE", "Unavailable", 409)
        return access(*args)

    monkeypatch.setattr(service, "report_access", guarded)
    page = service.list_reports(session, uuid4(), uuid4(), limit=1, offset=1)
    assert page == {
        "items": [{"id": str(ids[3]), "revision": 2, "state": "draft"}],
        "has_more": True,
    }
    assert calls == ids[2:]


def test_index_does_not_claim_more_from_ineligible_lookahead(monkeypatch):
    session, ids, _, access = listing(monkeypatch, [1, 1])

    def guarded(*args):
        if args[-1] == ids[1]:
            raise DomainError("PRIVACY_RESTRICTED", "Unavailable", 403)
        return access(*args)

    monkeypatch.setattr(service, "report_access", guarded)
    assert service.list_reports(session, uuid4(), uuid4(), limit=1)["has_more"] is False


@pytest.mark.parametrize("budget", ["candidates", "sources"])
def test_index_budget_fails_closed_before_unbounded_checks(monkeypatch, budget):
    session, ids, calls, _ = listing(monkeypatch, [2, 2, 2])
    monkeypatch.setattr(
        service, "MAX_REPORT_INDEX_CANDIDATES", 2 if budget == "candidates" else 1000
    )
    monkeypatch.setattr(
        service, "MAX_REPORT_INDEX_SOURCE_CHECKS", 4 if budget == "sources" else 10000
    )
    with pytest.raises(DomainError, match="REPORT_INDEX_LIMIT"):
        service.list_reports(session, uuid4(), uuid4(), limit=2)
    assert calls == ids[:2]


def test_index_unknown_errors_are_not_hidden_as_empty(monkeypatch):
    session, _, _, _ = listing(monkeypatch, [1])

    def unexpected(*args):
        raise DomainError("UNEXPECTED_GATE_FAILURE", "Unavailable", 503)

    monkeypatch.setattr(service, "report_access", unexpected)
    with pytest.raises(DomainError, match="UNEXPECTED_GATE_FAILURE"):
        service.list_reports(session, uuid4(), uuid4())


@pytest.mark.parametrize("limit,offset", [(0, 0), (101, 0), (25, -1), (25, 10001)])
def test_index_internal_pagination_is_bounded(limit, offset):
    with pytest.raises(DomainError, match="INVALID_PAGINATION"):
        service.list_reports(None, uuid4(), uuid4(), limit, offset)
