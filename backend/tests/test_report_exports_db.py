"""Real PostgreSQL acceptance. Run only through the parent's isolated DB runner."""

import csv
import io
import json
import re
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import UUID, uuid4
from xml.etree import ElementTree

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker
from test_analytics_db import collected as collected_fixture
from test_analytics_db import context
from test_analytics_db import reviewed_analytics as reviewed_fixture
from test_report_exports import local_pdf_font as pdf_fixture
from test_reviews_db import decisions

from app.analytics import service
from app.analytics.models import Export
from app.collection.models import CollectionSession
from app.common.errors import DomainError
from app.studies.models import StudyVersion

collected = collected_fixture
reviewed_analytics = reviewed_fixture
local_pdf_font = pdf_fixture
pytestmark = pytest.mark.db


def report(session, fixture):
    wid, sid, owner, reviewers, _ = fixture
    decisions(session, wid, sid, owner, reviewers)
    row = session.get(CollectionSession, sid)
    study_id = session.get(StudyVersion, row.version_id).study_id
    snapshot = service.freeze(session, wid, owner, study_id, row.version_id)
    created = service.create_report(session, wid, owner, snapshot.id)
    rid = UUID(created["id"])
    service.approve(session, wid, owner, rid, 1)
    return row, snapshot, rid


def decoded_rows(content, format):
    if format == "json":
        return json.loads(content)
    if format == "pdf":
        for stream in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", content, re.DOTALL):
            try:
                data = json.loads(zlib.decompress(stream))
                if "metrics" in data:
                    return data
            except (zlib.error, UnicodeDecodeError, json.JSONDecodeError):
                pass
        raise AssertionError("PDF original snapshot attachment missing")
    if format == "csv":
        return dict(list(csv.reader(io.StringIO(content)))[1:])
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        strings = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
        strings = [node.text or "" for node in strings.findall(".//s:t", ns)]
        sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        result = {}
        for row in sheet.findall(".//s:row", ns)[1:]:
            values = []
            for cell in row.findall("s:c", ns):
                value = cell.find("s:v", ns).text
                values.append(strings[int(value)] if cell.get("t") == "s" else value)
            result[values[0]] = values[2]
        return result


@pytest.mark.parametrize("format", ["json", "csv", "pdf", "xlsx"])
def test_formats_use_exact_frozen_values_and_live_permissions(
    reviewed_analytics, db_engine, local_pdf_font, format
):
    wid, _, owner, reviewers, subject = reviewed_analytics
    with Session(db_engine) as session, session.begin():
        row, snapshot, rid = report(session, reviewed_analytics)
        metric = snapshot.metrics["blocks"]["single"]["distribution"]["no"]
        assert metric["numerator"] == metric["denominator"] == 1
        item = service.create_export(session, wid, owner, rid, format, "raw")
        eid, sid = UUID(item["id"]), row.id
    sessions = sessionmaker(db_engine)
    content, kind = service.download_export(sessions, wid, owner, eid)
    data = decoded_rows(content, format)
    if format in {"json", "pdf"}:
        actual = data["metrics"]["blocks"]["single"]["distribution"]["no"]
        assert actual["numerator"] == actual["denominator"] == 1
        assert data["responses"][0]["answers"]["single"]["value"] == {"option_id": "no"}
    else:
        suffix = "metrics/blocks/single/distribution/no/denominator"
        assert any(key.endswith(suffix) and value == "1" for key, value in data.items())
    assert str(subject) not in str(data)
    assert kind in {
        "application/json",
        "text/csv",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    with pytest.raises(DomainError):
        service.download_export(sessions, wid, reviewers[0], eid)
    with pytest.raises(DomainError):
        service.download_export(sessions, uuid4(), owner, eid)
    with sessions.begin() as session:
        service.invalidate_session(session, wid, sid)
    with pytest.raises(DomainError):
        service.download_export(sessions, wid, owner, eid)
    with sessions.begin() as session:
        service.purge_sessions(session, wid, [sid])
        assert session.scalar(select(Export.id).where(Export.id == eid)) is None


@pytest.mark.parametrize("format", ["pdf", "xlsx"])
def test_render_releases_workspace_for_concurrent_autosave_and_withdrawal(
    collected, research_app, db_engine, monkeypatch, format
):
    from test_collection_db import put

    from app.auth.models import User

    client, url, capability, result, _, _ = collected
    _, app, _ = research_app
    with Session(db_engine) as session, session.begin():
        row, study, owner = context(session, result)
        wid = row.workspace_id
        snapshot = service.freeze(session, wid, owner, study.id, row.version_id)
        # This active source is excluded from metrics but still privacy-gated.
        assert snapshot.source_count == 1 and snapshot.metrics["included"] == 0
        rid = UUID(service.create_report(session, wid, owner, snapshot.id)["id"])
        service.approve(session, wid, owner, rid, 1)
        item = service.create_export(session, wid, owner, rid, format, "raw")
        headers = {
            "Authorization": "Bearer "
            + app.state.auth._new_login(session, session.get(User, owner))["access_token"]
        }
    with app.state.database.sessions.begin() as session:
        assert session.scalar(text("SHOW statement_timeout")) == "2s"
    rendering, release = Event(), Event()

    def render(*args):
        rendering.set()
        assert release.wait(10), "test did not release renderer"
        return b"private bytes must never escape"

    monkeypatch.setattr(service, "generate_document", render)
    with ThreadPoolExecutor(max_workers=2) as pool:
        download = pool.submit(
            client.get,
            f"/api/v1/workspaces/{wid}/analytics/exports/{item['id']}",
            headers=headers,
        )
        try:
            assert rendering.wait(5), "download did not reach renderer"
            saved, _ = pool.submit(put, client, url, capability).result(timeout=3)
            assert saved.status_code == 200, saved.text
            withdrawn = pool.submit(client.post, url + "/withdraw", headers=capability).result(
                timeout=3
            )
            assert withdrawn.status_code == 200, withdrawn.text
            assert not download.done(), "renderer must remain paused through withdrawal"
        finally:
            release.set()
        response = download.result(timeout=5)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "ANALYSIS_UNAVAILABLE"
    assert b"private bytes" not in response.content


@pytest.mark.parametrize("format", ["pdf", "xlsx"])
@pytest.mark.parametrize(
    "mutation",
    [
        "live_source",
        "workspace",
        "privacy_epoch",
        "actor",
        "export",
        "report",
        "actor_restricted",
        "source_restricted",
        "auth_version",
    ],
)
def test_finalization_rechecks_separate_committed_transaction(
    reviewed_analytics, db_engine, monkeypatch, format, mutation
):
    from app.analytics.models import ReportVersion
    from app.auth.models import User
    from app.common.privacy import lock_workspace
    from app.common.privacy_models import PrivacyRestriction

    wid, sid, owner, _, subject = reviewed_analytics
    sessions = sessionmaker(db_engine)
    with sessions.begin() as session:
        _, _, rid = report(session, reviewed_analytics)
        eid = UUID(service.create_export(session, wid, owner, rid, format, "raw")["id"])
    rendering, release = Event(), Event()

    def render(*args):
        rendering.set()
        assert release.wait(10), "test did not release renderer"
        return b"private bytes must never escape"

    monkeypatch.setattr(service, "generate_document", render)
    with ThreadPoolExecutor(max_workers=1) as pool:
        download = pool.submit(service.download_export, sessions, wid, owner, eid)
        try:
            assert rendering.wait(5), "download did not reach renderer"
            with sessions.begin() as session:
                session.execute(text("SET LOCAL statement_timeout = '2s'"))
                workspace = lock_workspace(session, wid)
                if mutation == "live_source":
                    # Bypass invalidation hooks to verify live source reauthorization.
                    session.get(CollectionSession, sid).state = "withdrawn"
                elif mutation == "workspace":
                    workspace.status = "suspended"
                elif mutation == "privacy_epoch":
                    workspace.privacy_epoch += 1
                elif mutation == "actor":
                    session.get(User, owner).status = "disabled"
                elif mutation == "auth_version":
                    session.get(User, owner).auth_version += 1
                elif mutation in {"actor_restricted", "source_restricted"}:
                    session.add(
                        PrivacyRestriction(
                            workspace_id=wid,
                            subject_id=owner if mutation == "actor_restricted" else subject,
                        )
                    )
                elif mutation == "export":
                    session.get(Export, eid).state = "invalidated"
                else:
                    item = session.get(Export, eid)
                    session.get(ReportVersion, item.report_version_id).state = "invalidated"
        finally:
            release.set()
        with pytest.raises(DomainError):
            download.result(timeout=5)


@pytest.mark.parametrize("format", ["pdf", "xlsx"])
def test_summary_documents_apply_complementary_suppression(
    reviewed_analytics, db_engine, local_pdf_font, format
):
    wid, _, owner, _, subject = reviewed_analytics
    with Session(db_engine) as session, session.begin():
        _, _, rid = report(session, reviewed_analytics)
        item = service.create_export(session, wid, owner, rid, format, "summary")
    content, _ = service.download_export(sessionmaker(db_engine), wid, owner, UUID(item["id"]))
    data = decoded_rows(content, format)
    assert "responses" not in str(data) and "option_id" not in str(data)
    assert str(subject) not in str(data)
    assert "numerator" not in str(data) and "denominator" not in str(data)
    assert "suppressed" in str(data)
