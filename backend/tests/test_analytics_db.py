"""Real PostgreSQL integration; run only in the lead's exclusive DB window."""

from uuid import UUID

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_collection_db import put
from test_reviews_db import collected as collected_fixture

from app.analytics import service
from app.analytics.models import AnalysisSnapshot, ReportShare, SnapshotSource
from app.auth.models import Membership
from app.collection.models import CollectionSession
from app.common.errors import DomainError
from app.studies.models import Study, StudyVersion

collected = collected_fixture
pytestmark = pytest.mark.db


def context(session, result):
    row = session.get(CollectionSession, UUID(result["session_id"]))
    version = session.get(StudyVersion, row.version_id)
    study = session.get(Study, version.study_id)
    owner = session.get(Membership, study.owner_membership_id)
    return row, study, owner.user_id


def test_snapshot_exclusions_immutability_tenant_and_purge(collected, db_engine):
    _, _, _, result, _, _ = collected
    with Session(db_engine) as session, session.begin():
        row, study, actor = context(session, result)
        snapshot = service.freeze(session, row.workspace_id, actor, study.id, row.version_id)
        assert snapshot.metrics["included"] == 0
        assert snapshot.metrics["excluded"] == {"not_submitted": 1}
        source = session.scalar(
            select(SnapshotSource).where(SnapshotSource.snapshot_id == snapshot.id)
        )
        assert source.revisions == {}
        with pytest.raises(DBAPIError), session.begin_nested():
            session.execute(
                text("UPDATE analysis_snapshots SET metrics='{}' WHERE id=:id"), {"id": snapshot.id}
            )
        with pytest.raises(DBAPIError), session.begin_nested():
            session.execute(
                text("UPDATE snapshot_sources SET revisions='{}' WHERE id=:id"), {"id": source.id}
            )
        report = service.create_report(session, row.workspace_id, actor, snapshot.id)
        service.approve(session, row.workspace_id, actor, UUID(report["id"]), 1)
        share = service.create_share(session, row.workspace_id, actor, UUID(report["id"]), 60)
        stored = session.get(ReportShare, UUID(share["id"]))
        assert stored.token_hash != share["token"]
        assert service.read_share(session, share["token"])["sample_size_band"] == "suppressed"
        service.invalidate_session(session, row.workspace_id, row.id)
        with pytest.raises(DomainError):
            service.snapshot_view(session, row.workspace_id, actor, snapshot.id)
        with pytest.raises(DomainError):
            service.read_share(session, share["token"])
        with pytest.raises(DBAPIError), session.begin_nested():
            session.execute(
                text("UPDATE report_shares SET revoked_at=NULL WHERE id=:id"), {"id": stored.id}
            )
        assert service.purge_sessions(session, row.workspace_id, [row.id]) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(SnapshotSource)
                .where(SnapshotSource.snapshot_id == snapshot.id)
            )
            == 0
        )


def test_live_withdrawal_without_epoch_invalidates_every_access(collected, db_engine):
    client, url, headers, result, _, _ = collected
    assert put(client, url, headers, "no")[0].status_code == 200
    assert (
        client.post(
            url + "/submit",
            headers=headers,
            json={"version_id": result["version_id"], "expected_revision": 1},
        ).status_code
        == 200
    )
    with Session(db_engine) as session, session.begin():
        row, study, actor = context(session, result)
        snapshot = service.freeze(session, row.workspace_id, actor, study.id, row.version_id)
        assert snapshot.metrics["excluded"] == {"not_accepted": 1}
        report = service.create_report(session, row.workspace_id, actor, snapshot.id)
        report_id = UUID(report["id"])
        service.approve(session, row.workspace_id, actor, report_id, 1)
        share = service.create_share(session, row.workspace_id, actor, report_id, 60)
        export = service.create_export(
            session, row.workspace_id, actor, report_id, "json", "summary"
        )
        # Deliberately bypass hook to prove access guards do not trust epoch/invalidation alone.
        row.state = "withdrawn"
        session.flush()
        for access in (
            lambda: service.snapshot_view(session, row.workspace_id, actor, snapshot.id),
            lambda: service.source_access_summary(session, row.workspace_id, actor, snapshot.id),
            lambda: service.report_view(session, row.workspace_id, actor, report_id),
            lambda: service.download_export(session, row.workspace_id, actor, UUID(export["id"])),
            lambda: service.read_share(session, share["token"]),
        ):
            with pytest.raises(DomainError):
                access()


def test_empty_snapshot_owner_cleanup(collected, db_engine):
    _, _, _, result, _, _ = collected
    with Session(db_engine) as session, session.begin():
        row, study, actor = context(session, result)
        row.state = "withdrawn"
        session.flush()
        snapshot = service.freeze(session, row.workspace_id, actor, study.id, row.version_id)
        assert snapshot.source_count == 0
        service.create_report(session, row.workspace_id, actor, snapshot.id)
        assert service.purge_studies(session, row.workspace_id, [study.id]) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(AnalysisSnapshot)
                .where(AnalysisSnapshot.study_id == study.id)
            )
            == 0
        )


@pytest.fixture
def reviewed_analytics(collected, db_engine):
    from test_reviews_db import reviewed

    # Reuse the exact P08 participant/reviewer contract fixture without database mocks.
    return reviewed.__wrapped__(collected, db_engine)


def test_accepted_snapshot_revision_digest_exports_review_drift(reviewed_analytics, db_engine):

    from test_reviews_db import decisions

    wid, sid, owner, reviewers, subject = reviewed_analytics
    with Session(db_engine) as session, session.begin():
        decisions(session, wid, sid, owner, reviewers)
        row = session.get(CollectionSession, sid)
        study_id = session.get(StudyVersion, row.version_id).study_id
        snapshot = service.freeze(session, wid, owner, study_id, row.version_id)
        assert snapshot.metrics["included"] == 1
        assert snapshot.metrics["blocks"]["single"]["distribution"]["no"]["numerator"] == 1
        manifest = service.source_access_summary(session, wid, owner, snapshot.id)
        assert len(manifest["sources"][0]["revision_ids"]) == 1
        assert manifest["sources"][0]["decision"]["version"] > 0
        report = service.create_report(session, wid, owner, snapshot.id)
        rid = UUID(report["id"])
        service.approve(session, wid, owner, rid, 1)
        export = service.create_export(session, wid, owner, rid, "json", "raw")
        content, kind = service.download_export(session, wid, owner, UUID(export["id"]))
        assert kind == "application/json" and "option_id" in content
        assert str(subject) not in content
        with pytest.raises(DomainError):
            service.create_export(session, wid, reviewers[0], rid, "json", "raw")
        share = service.create_share(session, wid, owner, rid, 60)
        assert "option_id" not in str(service.read_share(session, share["token"]))
        service.invalidate_session(session, wid, sid)
        with pytest.raises(DomainError):
            service.download_export(session, wid, owner, UUID(export["id"]))
        with pytest.raises(DomainError):
            service.read_share(session, share["token"])


def test_share_expiry_revoke_issuer_and_report_revisions(
    reviewed_analytics, db_engine, monkeypatch
):
    from datetime import timedelta

    from test_reviews_db import decisions

    from app.auth.models import User

    wid, sid, owner, reviewers, _ = reviewed_analytics
    with Session(db_engine) as session, session.begin():
        decisions(session, wid, sid, owner, reviewers)
        row = session.get(CollectionSession, sid)
        study_id = session.get(StudyVersion, row.version_id).study_id
        snapshot = service.freeze(session, wid, owner, study_id, row.version_id)
        report = service.create_report(session, wid, owner, snapshot.id)
        rid = UUID(report["id"])
        with pytest.raises(DomainError):
            service.create_share(session, wid, owner, rid, 60)
        service.approve(session, wid, owner, rid, 1)
        share = service.create_share(session, wid, owner, rid, 60)
        with pytest.raises(DomainError):
            service.read_share(session, share["token"][:-2] + "XX")
        now = service.utcnow()
        with monkeypatch.context() as patch:
            patch.setattr(service, "utcnow", lambda: now + timedelta(seconds=61))
            with pytest.raises(DomainError):
                service.read_share(session, share["token"])
        issuer = session.get(User, owner)
        issuer.status = "disabled"
        session.flush()
        with pytest.raises(DomainError):
            service.read_share(session, share["token"])
        issuer.status = "active"
        session.flush()
        assert service.read_share(session, share["token"])["status"] == "approved"
        service.revoke_share(session, wid, owner, UUID(share["id"]))
        with pytest.raises(DomainError):
            service.read_share(session, share["token"])
        with pytest.raises(DomainError):
            service.revise(session, wid, owner, rid, snapshot.id, 2)
        revised = service.revise(session, wid, owner, rid, snapshot.id, 1)
        assert revised["revision"] == 2 and revised["state"] == "draft"
        assert service.report_view(session, wid, owner, rid, 1)["state"] == "approved"
        service.approve(session, wid, owner, rid, 2)
        assert service.purge_studies(session, wid, [study_id]) == 1
        assert (
            session.scalar(
                select(func.count()).select_from(ReportShare).where(ReportShare.workspace_id == wid)
            )
            == 0
        )


def test_source_manifest_is_final_revision_and_review_identity_drift(
    reviewed_analytics, db_engine, monkeypatch
):
    from test_reviews_db import decisions

    from app.collection.models import AnswerRevision

    wid, sid, actor, reviewers, _ = reviewed_analytics
    with Session(db_engine) as session, session.begin():
        decisions(session, wid, sid, actor, reviewers)
        row = session.get(CollectionSession, sid)
        study_id = session.get(StudyVersion, row.version_id).study_id
        snapshot = service.freeze(session, wid, actor, study_id, row.version_id)
        assert snapshot.source_count == 1 and snapshot.metrics["included"] == 1
        assert snapshot.metrics["blocks"]["single"]["distribution"]["no"]["numerator"] == 1
        assert snapshot.metrics["blocks"]["single"]["distribution"]["yes"]["numerator"] == 0
        source = session.scalar(
            select(SnapshotSource).where(SnapshotSource.snapshot_id == snapshot.id)
        )
        final = session.get(AnswerRevision, UUID(source.revisions["single"]))
        assert final.revision == row.submitted_snapshot["single"]["revision"]
        assert service.compare(session, wid, actor, snapshot.id, snapshot.id)["suppressed"]
        changed = dict(source.decision, version=source.decision["version"] + 1)
        monkeypatch.setattr(service, "decision_snapshot", lambda *args: changed)
        with pytest.raises(DomainError):
            service.snapshot_view(session, wid, actor, snapshot.id)


def test_tenant_scope_snapshot_bound_and_sql_manifest_guards(collected, db_engine, monkeypatch):
    from uuid import uuid4

    _, _, _, result, _, _ = collected
    with Session(db_engine) as session, session.begin():
        row, study, actor = context(session, result)
        with monkeypatch.context() as patch:
            patch.setattr(service, "MAX_SOURCES", 0)
            with pytest.raises(DomainError) as error:
                service.freeze(session, row.workspace_id, actor, study.id, row.version_id)
            assert error.value.code == "SNAPSHOT_LIMIT"
        snapshot = service.freeze(session, row.workspace_id, actor, study.id, row.version_id)
        with pytest.raises(DomainError):
            service.snapshot_view(session, uuid4(), actor, snapshot.id)
        source = session.scalar(
            select(SnapshotSource).where(SnapshotSource.snapshot_id == snapshot.id)
        )
        for statement in (
            "UPDATE analysis_snapshots SET manifest_digest=repeat('b',64) WHERE id=:id",
            "UPDATE analysis_snapshots SET state='building' WHERE id=:id",
            "DELETE FROM analysis_snapshots WHERE id=:id",
        ):
            with pytest.raises(DBAPIError), session.begin_nested():
                session.execute(text(statement), {"id": snapshot.id})
        with pytest.raises(DBAPIError), session.begin_nested():
            session.execute(
                text("UPDATE snapshot_sources SET digest=repeat('c',64) WHERE id=:id"),
                {"id": source.id},
            )


def test_concurrent_freeze_withdrawal_has_no_accessible_stale_snapshot(collected, db_engine):
    from concurrent.futures import ThreadPoolExecutor

    from app.collection.privacy import withdraw_session

    _, _, _, result, _, _ = collected
    with Session(db_engine) as session:
        row, study, actor = context(session, result)
        wid, sid, study_id, version_id = row.workspace_id, row.id, study.id, row.version_id

    def freeze():
        with Session(db_engine) as session, session.begin():
            return service.freeze(session, wid, actor, study_id, version_id).id

    def withdraw():
        with Session(db_engine) as session, session.begin():
            from app.common.privacy import lock_workspace

            lock_workspace(session, wid)
            withdraw_session(session, session.get(CollectionSession, sid))

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(freeze)
        second = pool.submit(withdraw)
        snapshot_id = first.result()
        second.result()
    with Session(db_engine) as session, session.begin():
        snapshot = session.get(AnalysisSnapshot, snapshot_id)
        if snapshot.source_count:
            with pytest.raises(DomainError):
                service.snapshot_view(session, wid, actor, snapshot_id)
        else:
            assert service.snapshot_view(session, wid, actor, snapshot_id)["metrics"]["blocks"]


def test_http_approved_report_exports_shares_and_authority(
    reviewed_analytics, research_app, db_engine
):
    from test_reviews_db import decisions

    from app.auth.models import User

    wid, sid, owner, reviewers, _ = reviewed_analytics
    client, app, _ = research_app
    with Session(db_engine) as session, session.begin():
        decisions(session, wid, sid, owner, reviewers)
        row = session.get(CollectionSession, sid)
        study_id = session.get(StudyVersion, row.version_id).study_id
        version_id = row.version_id
        headers = {
            "Authorization": "Bearer "
            + app.state.auth._new_login(session, session.get(User, owner))["access_token"]
        }
        reviewer_headers = {
            "Authorization": "Bearer "
            + app.state.auth._new_login(session, session.get(User, reviewers[0]))["access_token"]
        }
    base = f"/api/v1/workspaces/{wid}/analytics"
    response = client.post(
        base + "/snapshots",
        headers=headers,
        json={"study_id": str(study_id), "version_id": str(version_id)},
    )
    assert response.status_code == 201, response.text
    snapshot_id = response.json()["id"]
    assert client.get(base + f"/snapshots/{snapshot_id}", headers=headers).status_code == 200
    assert (
        client.get(base + f"/snapshots/{snapshot_id}/sources", headers=headers).status_code == 200
    )
    assert (
        client.get(base + f"/snapshots/{snapshot_id}/sources", headers=reviewer_headers).status_code
        == 403
    )
    assert client.get(
        base + "/comparisons",
        headers=headers,
        params={"left_id": snapshot_id, "right_id": snapshot_id},
    ).json()["suppressed"]
    response = client.post(base + "/reports", headers=headers, json={"snapshot_id": snapshot_id})
    assert response.status_code == 201, response.text
    report_id = response.json()["id"]
    report = base + "/reports/" + report_id
    assert (
        client.post(report + "/approve", headers=headers, json={"expected_revision": 1}).status_code
        == 200
    )
    assert client.get(report, headers=headers).json()["state"] == "approved"
    for format in ("json", "csv"):
        response = client.post(report + "/exports", headers=headers, json={"format": format})
        assert response.status_code == 201, response.text
        response = client.get(base + "/exports/" + response.json()["id"], headers=headers)
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert (
        client.post(
            report + "/exports", headers=reviewer_headers, json={"format": "json", "scope": "raw"}
        ).status_code
        == 403
    )
    response = client.post(report + "/shares", headers=headers, json={"ttl_seconds": 60})
    assert response.status_code == 201, response.text
    share = response.json()
    public = "/api/v1/report-shares/" + share["token"]
    assert client.get(public).status_code == 200
    assert client.delete(base + "/shares/" + share["id"], headers=headers).status_code == 200
    assert client.get(public).status_code == 404
    response = client.post(
        report + "/revise",
        headers=headers,
        json={"snapshot_id": snapshot_id, "expected_revision": 1},
    )
    assert response.status_code == 201 and response.json()["revision"] == 2
