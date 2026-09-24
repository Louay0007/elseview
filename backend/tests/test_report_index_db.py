"""Report index acceptance on the disposable PostgreSQL runner only."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from study_fixtures import blocks, ready_study
from test_analytics_db import collected as collected_fixture
from test_analytics_db import context

from app.analytics import service
from app.analytics.models import AnalysisSnapshot, Report, ReportVersion
from app.auth.models import Membership, User, Workspace
from app.auth.security import utcnow
from app.collection.models import CollectionSession
from app.common.privacy_models import PrivacyRestriction
from app.studies.models import StudyGrant

collected = collected_fixture
pytestmark = pytest.mark.db


@pytest.fixture
def report_index(collected, research_app, db_engine):
    client, _, _, result, _, _ = collected
    _, app, actor = research_app
    with Session(db_engine) as session, session.begin():
        source, study, owner = context(session, result)
        snapshot = service.freeze(session, source.workspace_id, owner, study.id, source.version_id)
        reports = [
            UUID(service.create_report(session, source.workspace_id, owner, snapshot.id)["id"])
            for _ in range(3)
        ]
        headers = {
            "Authorization": "Bearer "
            + app.state.auth._new_login(session, session.get(User, owner))["access_token"]
        }
        return {
            "client": client,
            "actor": actor,
            "headers": headers,
            "owner": owner,
            "wid": source.workspace_id,
            "study": study.id,
            "source": source.id,
            "subject": source.subject_id,
            "snapshot": snapshot.id,
            "reports": sorted(reports),
            "url": f"/api/v1/workspaces/{source.workspace_id}/analytics/reports",
        }


def fetch(index, **params):
    return index["client"].get(index["url"], headers=index["headers"], params=params)


def test_index_exact_projection_stable_pages_empty_and_no_store(report_index, db_engine):
    index = report_index
    with Session(db_engine) as session, session.begin():
        service.approve(session, index["wid"], index["owner"], index["reports"][1], 1)
        # All reports were inserted in one transaction, so creation timestamps tie.
        rows = session.scalars(select(Report).where(Report.workspace_id == index["wid"])).all()
        assert len({row.created_at for row in rows}) == 1
    first = fetch(index, limit=1)
    assert first.status_code == 200, first.text
    assert first.headers["cache-control"] == "no-store"
    assert first.json() == {
        "items": [{"id": str(index["reports"][0]), "revision": 1, "state": "draft"}],
        "has_more": True,
    }
    assert fetch(index, limit=1).json() == first.json()
    assert fetch(index, limit=1, offset=1).json() == {
        "items": [{"id": str(index["reports"][1]), "revision": 1, "state": "approved"}],
        "has_more": True,
    }
    assert fetch(index, limit=1, offset=2).json() == {
        "items": [{"id": str(index["reports"][2]), "revision": 1, "state": "draft"}],
        "has_more": False,
    }
    assert fetch(index, offset=3).json() == {"items": [], "has_more": False}
    assert set(fetch(index).json()) == {"items", "has_more"}
    assert all(set(item) == {"id", "revision", "state"} for item in fetch(index).json()["items"])


def test_index_ineligible_versions_do_not_consume_offsets_or_has_more(report_index, db_engine):
    index = report_index
    with Session(db_engine) as session, session.begin():
        for report_id in (index["reports"][0], index["reports"][2]):
            version = session.scalar(
                select(ReportVersion).where(ReportVersion.report_id == report_id)
            )
            version.state = "invalidated"
    assert fetch(index, limit=1).json() == {
        "items": [{"id": str(index["reports"][1]), "revision": 1, "state": "draft"}],
        "has_more": False,
    }
    assert fetch(index, limit=1, offset=1).json() == {"items": [], "has_more": False}
    with Session(db_engine) as session, session.begin():
        latest = service.revise(
            session, index["wid"], index["owner"], index["reports"][1], index["snapshot"], 1
        )
    assert fetch(index).json()["items"] == [{"id": latest["id"], "revision": 2, "state": "draft"}]
    with Session(db_engine) as session, session.begin():
        session.get(ReportVersion, UUID(latest["version_id"])).state = "invalidated"
    # A valid historical version cannot substitute for an ineligible latest version.
    assert fetch(index).json() == {"items": [], "has_more": False}


@pytest.mark.parametrize(
    "change",
    [
        "withdrawn",
        "source_restriction",
        "snapshot_invalidated",
        "owner_revoked",
        "owner_disabled",
        "owner_restricted",
    ],
)
def test_index_live_source_and_owner_eligibility(report_index, db_engine, change):
    index = report_index
    viewer_headers, viewer_id, _ = index["actor"](index["wid"], role="viewer")
    with Session(db_engine) as session, session.begin():
        member = session.scalar(
            select(Membership).where(
                Membership.user_id == viewer_id, Membership.workspace_id == index["wid"]
            )
        )
        session.add(
            StudyGrant(
                workspace_id=index["wid"],
                study_id=index["study"],
                membership_id=member.id,
                capabilities=["read"],
            )
        )
    index["headers"] = viewer_headers
    assert len(fetch(index).json()["items"]) == 3
    with Session(db_engine) as session, session.begin():
        if change == "withdrawn":
            # No epoch bump/invalidation hook: the read must validate live sources.
            session.get(CollectionSession, index["source"]).state = "withdrawn"
        elif change == "source_restriction":
            session.add(PrivacyRestriction(workspace_id=index["wid"], subject_id=index["subject"]))
        elif change == "snapshot_invalidated":
            session.get(AnalysisSnapshot, index["snapshot"]).state = "invalidated"
        elif change == "owner_disabled":
            session.get(User, index["owner"]).status = "disabled"
        elif change == "owner_restricted":
            session.add(PrivacyRestriction(workspace_id=index["wid"], subject_id=index["owner"]))
        else:
            session.scalar(
                select(Membership).where(
                    Membership.workspace_id == index["wid"], Membership.user_id == index["owner"]
                )
            ).status = "revoked"
    response = fetch(index)
    assert response.status_code == 200, response.text
    assert response.json() == {"items": [], "has_more": False}
    assert response.headers["cache-control"] == "no-store"


def test_index_workspace_membership_does_not_grant_study_summary(report_index, db_engine):
    index = report_index
    headers, viewer, _ = index["actor"](index["wid"], role="viewer")
    index["headers"] = headers
    assert fetch(index).json() == {"items": [], "has_more": False}
    with Session(db_engine) as session, session.begin():
        member = session.scalar(
            select(Membership).where(
                Membership.workspace_id == index["wid"], Membership.user_id == viewer
            )
        )
        grant = StudyGrant(
            workspace_id=index["wid"],
            study_id=index["study"],
            membership_id=member.id,
            capabilities=["raw"],
        )
        session.add(grant)
        session.flush()
        grant_id = grant.id
    assert fetch(index).json() == {"items": [], "has_more": False}
    with Session(db_engine) as session, session.begin():
        session.get(StudyGrant, grant_id).capabilities = ["read"]
    assert len(fetch(index).json()["items"]) == 3
    # Summary visibility never confers raw/export capability.
    denied = index["client"].post(
        index["url"] + f"/{index['reports'][0]}/exports",
        headers=headers,
        json={"format": "json", "scope": "raw"},
    )
    assert denied.status_code == 403
    with Session(db_engine) as session, session.begin():
        session.get(StudyGrant, grant_id).revoked_at = utcnow()
    assert fetch(index).json() == {"items": [], "has_more": False}


def test_index_foreign_study_and_workspace_are_not_disclosed(report_index, db_engine):
    index = report_index
    other_headers, other_owner, _ = index["actor"](index["wid"], role="owner")
    fixture = ready_study(
        index["client"],
        f"/api/v1/workspaces/{index['wid']}",
        other_headers,
        [blocks(str(uuid4()))[0]],
    )
    assert (
        index["client"]
        .post(
            fixture["endpoint"] + "/publish", headers=other_headers, json={"expected_revision": 2}
        )
        .status_code
        == 200
    )
    with Session(db_engine) as session, session.begin():
        snapshot = service.freeze(
            session,
            index["wid"],
            other_owner,
            UUID(fixture["study_id"]),
            UUID(fixture["version_id"]),
        )
        foreign = service.create_report(session, index["wid"], other_owner, snapshot.id)
    assert fetch(index, limit=3).json()["has_more"] is False
    assert foreign["id"] not in str(fetch(index).json())
    assert index["client"].get(index["url"], headers=other_headers).json() == {
        "items": [{"id": foreign["id"], "revision": 1, "state": "draft"}],
        "has_more": False,
    }
    foreign_headers, _, foreign_wid = index["actor"]()
    assert index["client"].get(index["url"], headers=foreign_headers).status_code == 404
    assert (
        index["client"]
        .get(f"/api/v1/workspaces/{foreign_wid}/analytics/reports", headers=index["headers"])
        .status_code
        == 404
    )
    empty = index["client"].get(
        f"/api/v1/workspaces/{foreign_wid}/analytics/reports", headers=foreign_headers
    )
    assert empty.status_code == 200 and empty.json() == {"items": [], "has_more": False}


def test_index_authentication_privacy_restriction_and_workspace_hold(report_index, db_engine):
    index = report_index
    assert index["client"].get(index["url"]).status_code == 401
    assert (
        index["client"].get(index["url"], headers={"Authorization": "Bearer invalid"}).status_code
        == 401
    )
    with Session(db_engine) as session, session.begin():
        session.add(PrivacyRestriction(workspace_id=index["wid"], subject_id=index["owner"]))
    assert fetch(index).status_code == 403
    with Session(db_engine) as session, session.begin():
        session.get(Workspace, index["wid"]).status = "suspended"
    assert fetch(index).status_code == 404


@pytest.mark.parametrize(
    "query", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001}, {"limit": "invalid"}]
)
def test_index_http_pagination_bounds(report_index, query):
    response = fetch(report_index, **query)
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"


def test_index_scan_budget_returns_no_partial_metadata(report_index, monkeypatch):
    monkeypatch.setattr(service, "MAX_REPORT_INDEX_CANDIDATES", 2)
    limited = fetch(report_index)
    assert limited.status_code == 422
    assert limited.headers["cache-control"] == "no-store"
    assert "REPORT_INDEX_LIMIT" in limited.text
    assert all(str(report_id) not in limited.text for report_id in report_index["reports"])
    smaller = fetch(report_index, limit=1)
    assert smaller.status_code == 200 and smaller.json()["has_more"] is True
