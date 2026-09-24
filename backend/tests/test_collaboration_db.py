"""Real HTTP/DB security; run only in lead-granted exclusive database window."""

from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_collection_db import collected as collected_fixture
from test_longitudinal_db import longitudinal as longitudinal_fixture
from test_longitudinal_db import slot_body

from app.auth.models import Membership
from app.collaboration import webhooks
from app.collaboration.models import APIKey, WebhookDelivery
from app.jobs import service as jobs

pytestmark = pytest.mark.db


def test_scoped_key_never_broad_auth_revocation_tenant(research_app, db_engine):
    client, app, actor = research_app
    headers, uid, wid = actor()
    other, _, owid = actor()
    base = f"/api/v1/workspaces/{wid}/collaboration"
    r = client.post(base + "/api-keys", headers=headers, json={"scopes": ["reports:read"]})
    assert r.status_code == 201, r.text
    key = r.json()
    with Session(db_engine) as s:
        row = s.get(APIKey, UUID(key["id"]))
        assert key["key"] not in row.token_hash and len(row.token_hash) == 64
    assert (
        client.get(
            "/api/v1/templates", headers={"Authorization": "Bearer " + key["key"]}
        ).status_code
        == 401
    )
    assert (
        client.post(base + "/api-keys", headers=headers, json={"scopes": ["admin"]}).status_code
        == 422
    )
    assert client.delete(base + "/api-keys/" + key["id"], headers=other).status_code == 404
    assert (
        client.get(
            base + "/api/templates/" + str(uuid4()), headers={"X-API-Key": key["key"]}
        ).status_code
        == 404
    )
    assert client.delete(base + "/api-keys/" + key["id"], headers=headers).status_code == 204
    assert (
        client.get(
            base + "/api/reports/" + str(uuid4()), headers={"X-API-Key": key["key"]}
        ).status_code
        == 404
    )


def test_webhook_disabled_duplicate_authority_and_no_payload(research_app, db_engine):
    client, app, actor = research_app
    headers, uid, wid = actor()
    base = f"/api/v1/workspaces/{wid}/collaboration"
    url = "https://hooks.example.com/events"
    assert (
        client.post(base + "/integrations", headers=headers, json={"destination": url}).status_code
        == 404
    )
    app.state.settings.collaboration_integration_mode = "mock"
    app.state.settings.collaboration_webhook_destinations = [url]
    app.state.settings.collaboration_webhook_secret = SecretStr("operator-approved-secret-" * 3)
    r = client.post(base + "/integrations", headers=headers, json={"destination": url})
    assert r.status_code == 201, r.text
    iid = r.json()["id"]
    body = {"command_key": str(uuid4())}
    endpoint = base + "/integrations/" + iid + "/deliveries"
    first = client.post(endpoint, headers=headers, json=body)
    assert first.status_code == 202, first.text
    assert client.post(endpoint, headers=headers, json=body).json() == first.json()
    with Session(db_engine) as s, s.begin():
        job = s.get(jobs.Job, UUID(first.json()["job_id"]))
        assert job.payload == {} and job.replay_safe
        assert webhooks.authorize_job(s, job)
        member = s.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.user_id == uid)
        )
        member.role = "viewer"
        s.flush()
        assert not webhooks.authorize_job(s, job)
    with Session(db_engine) as s, s.begin():
        job = s.get(jobs.Job, UUID(first.json()["job_id"]))
        member = s.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.user_id == uid)
        )
        member.role = "owner"
        s.flush()
    assert client.delete(base + "/integrations/" + iid, headers=headers).status_code == 204
    with Session(db_engine) as s:
        job = s.get(jobs.Job, UUID(first.json()["job_id"]))
        assert not webhooks.authorize_job(s, job)
        assert s.get(WebhookDelivery, job.target_id).command_key == UUID(body["command_key"])


def test_preferences_and_tenant_boundary(research_app, db_engine):
    from app.collaboration.service import notification_allowed

    client, app, actor = research_app
    headers, uid, wid = actor()
    base = f"/api/v1/workspaces/{wid}/collaboration"
    outsider, _, _ = actor()
    assert client.get(base + "/notification-preferences", headers=outsider).status_code == 404
    assert (
        client.put(
            base + "/notification-preferences", headers=outsider, json={"reminders": False}
        ).status_code
        == 404
    )
    assert (
        client.put(
            base + "/notification-preferences", headers=headers, json={"reminders": False}
        ).status_code
        == 200
    )
    with Session(db_engine) as s:
        assert not notification_allowed(s, wid, uid)
    assert (
        client.put(
            base + "/notification-preferences", headers=headers, json={"reminders": True}
        ).status_code
        == 200
    )
    with Session(db_engine) as s:
        assert notification_allowed(s, wid, uid)


collected = collected_fixture
longitudinal = longitudinal_fixture


def test_calendar_revision_cancel_and_reminder_preferences(longitudinal, db_engine):
    from app.longitudinal.models import Notification
    from app.longitudinal.service import reminder_job_allowed

    client, root, staff, participant, wid, vid, _ = longitudinal
    r = client.post(root + "/slots", headers=staff, json=slot_body(vid))
    assert r.status_code == 200, r.text
    b = client.post(
        "/api/v1/participant/longitudinal/bookings",
        headers=participant,
        json={"slot_id": r.json()["id"], "request_key": str(uuid4())},
    )
    assert b.status_code == 200, b.text
    bid = b.json()["id"]
    url = "/api/v1/participant/bookings/" + bid + "/calendar.ics"
    r = client.get(url, headers=participant, params={"revision": 0})
    assert r.status_code == 200 and "STATUS:CONFIRMED" in r.text and "private-secret" not in r.text
    assert client.get(url, headers=staff, params={"revision": 0}).status_code == 404
    assert (
        client.put(
            f"/api/v1/workspaces/{wid}/collaboration/notification-preferences",
            headers=participant,
            json={"reminders": False},
        ).status_code
        == 200
    )
    with Session(db_engine) as s:
        note = s.scalar(select(Notification).where(Notification.booking_id == UUID(bid)))
        assert not reminder_job_allowed(s, s.get(jobs.Job, note.job_id))
    assert (
        client.post(
            "/api/v1/participant/longitudinal/bookings/" + bid + "/cancel",
            headers=participant,
            json={"expected_revision": 0},
        ).status_code
        == 200
    )
    assert client.get(url, headers=participant, params={"revision": 0}).status_code == 409
    r = client.get(url, headers=participant, params={"revision": 1})
    assert r.status_code == 200 and "STATUS:CANCELLED" in r.text and "SEQUENCE:1" in r.text


def test_comments_raw_only_grants_summary_and_stale_issuer(collected, research_app, db_engine):
    from test_analytics_db import context

    from app.analytics import service as reports
    from app.auth.models import User

    client, _, _, result, _, _ = collected
    _, app, actor = research_app
    with Session(db_engine) as s, s.begin():
        row, study, uid = context(s, result)
        wid = row.workspace_id
        owner = s.get(User, uid)
        headers = {"Authorization": "Bearer " + app.state.auth._new_login(s, owner)["access_token"]}
        snapshot = reports.freeze(s, wid, uid, study.id, row.version_id)
        report = reports.create_report(s, wid, uid, snapshot.id)
        rid = report["id"]
        reports.approve(s, wid, uid, UUID(rid), 1)
    viewer, vuid, _ = actor(workspace_id=wid, role="viewer")
    base = f"/api/v1/workspaces/{wid}/collaboration/reports/{rid}"
    r = client.post(
        base + "/comments", headers=headers, json={"text": "RAW ANSWER secret quotation"}
    )
    assert r.status_code == 201, r.text
    assert client.get(base + "/comments", headers=viewer).status_code == 403
    r = client.post(base + "/grants", headers=headers, json={"recipient_id": str(vuid)})
    assert r.status_code == 201, r.text
    r = client.get(base + "/granted", headers=viewer)
    assert r.status_code == 200 and "RAW ANSWER" not in r.text and "quotation" not in r.text
    with Session(db_engine) as s, s.begin():
        member = s.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.user_id == uid)
        )
        member.role = "viewer"
    assert client.get(base + "/granted", headers=viewer).status_code in (403, 404)


def test_template_explicit_same_workspace_grant_no_origin_inputs(
    collected, research_app, db_engine
):
    from test_analytics_db import context

    from app.auth.models import User
    from app.studies.schemas import StudyBody
    from app.studies.service import create_study
    from app.templates.catalogue import catalogue
    from app.templates.models import TemplateInstance

    client, _, _, result, _, _ = collected
    _, app, actor = research_app
    recipe = catalogue()[0]
    with Session(db_engine) as s, s.begin():
        row, study, uid = context(s, result)
        wid = row.workspace_id
        headers = {
            "Authorization": "Bearer "
            + app.state.auth._new_login(s, s.get(User, uid))["access_token"]
        }
        draft_study, draft_version = create_study(
            s,
            wid,
            uid,
            StudyBody(
                title="Shared template fixture", retention_policy_id=study.retention_policy_id
            ),
        )
        t = TemplateInstance(
            workspace_id=wid,
            study_id=draft_study.id,
            version_id=draft_version.id,
            template_key=recipe["key"],
            template_version=recipe["version"],
            recipe_hash="0" * 64,
            configuration_hash="1" * 64,
            recipe_snapshot={"private": "RAW ORIGIN"},
            inputs_snapshot={"private": "RAW ORIGIN"},
        )
        s.add(t)
        s.flush()
        iid = t.id
    viewer, vuid, _ = actor(workspace_id=wid, role="viewer")
    outside, ouid, _ = actor()
    base = f"/api/v1/workspaces/{wid}/collaboration/templates/{iid}"
    assert client.get(base + "/shared", headers=viewer).status_code == 404
    assert (
        client.post(base + "/grants", headers=headers, json={"recipient_id": str(ouid)}).status_code
        == 404
    )
    r = client.post(base + "/grants", headers=headers, json={"recipient_id": str(vuid)})
    assert r.status_code == 201, r.text
    grant = r.json()["id"]
    r = client.get(base + "/shared", headers=viewer)
    assert r.status_code == 200 and "RAW ORIGIN" not in r.text
    assert client.get(base + "/shared", headers=outside).status_code == 404
    assert (
        client.delete(
            f"/api/v1/workspaces/{wid}/collaboration/templates/grants/{grant}", headers=headers
        ).status_code
        == 204
    )
    assert client.get(base + "/shared", headers=viewer).status_code == 404


def test_webhook_lease_fenced_retry_terminal_and_mock_execute(research_app, db_engine):
    import asyncio
    from datetime import timedelta

    from app.auth.security import utcnow
    from app.jobs.models import Job

    client, app, actor = research_app
    headers, uid, wid = actor()
    app.state.settings.collaboration_integration_mode = "mock"
    app.state.settings.collaboration_webhook_destinations = ["https://hooks.example.com/events"]
    app.state.settings.collaboration_webhook_secret = SecretStr("operator-approved-secret-" * 3)
    base = f"/api/v1/workspaces/{wid}/collaboration"
    r = client.post(
        base + "/integrations",
        headers=headers,
        json={"destination": "https://hooks.example.com/events"},
    )
    assert r.status_code == 201, r.text
    r = client.post(
        base + "/integrations/" + r.json()["id"] + "/deliveries",
        headers=headers,
        json={"command_key": str(uuid4())},
    )
    assert r.status_code == 202, r.text
    jid = UUID(r.json()["job_id"])
    with Session(db_engine) as s, s.begin():
        # Avoid unrelated durable jobs from earlier fixtures competing for this claim.
        for row in s.scalars(select(Job).where(Job.state == "pending", Job.id != jid)):
            row.run_after = utcnow() + timedelta(days=1)
        job = jobs.claim(s)
        assert job.id == jid
        token = job.lease_token
        s.expunge(job)
    assert asyncio.run(webhooks.execute(app.state.database, app.state.settings, job)) == {
        "status": "ok"
    }
    with Session(db_engine) as s, s.begin():
        assert not jobs.fail_webhook(s, jid, uuid4(), True, 60)
        assert jobs.fail_webhook(s, jid, token, True, 60)
        row = s.get(Job, jid)
        assert row.state == "pending" and row.attempt_count == 1
        assert s.get(WebhookDelivery, row.target_id).state == "pending"
        row.run_after = utcnow() - timedelta(seconds=1)
    with Session(db_engine) as s, s.begin():
        job = jobs.claim(s)
        assert job.id == jid
        assert jobs.fail_webhook(s, jid, job.lease_token, False, 1)
        assert job.state == "failed"
        assert s.get(WebhookDelivery, job.target_id).state == "failed"


def test_comment_hold_invalidates_without_physical_purge(collected, research_app, db_engine):
    from test_analytics_db import context

    from app.analytics import service as reports
    from app.collaboration.models import ReportComment
    from app.collaboration.privacy import invalidate_subject, purge_subject

    _, _, _, result, _, _ = collected
    with Session(db_engine) as s, s.begin():
        row, study, uid = context(s, result)
        snapshot = reports.freeze(s, row.workspace_id, uid, study.id, row.version_id)
        report = reports.create_report(s, row.workspace_id, uid, snapshot.id)
        comment = ReportComment(
            workspace_id=row.workspace_id,
            report_id=UUID(report["id"]),
            author_id=uid,
            text="quoted participant sensitive source",
        )
        s.add(comment)
        s.flush()
        cid = comment.id
        wid = row.workspace_id
        subject = row.subject_id
        invalidate_subject(s, wid, subject)
        s.flush()
        s.refresh(comment)
        assert comment.restricted and comment.text == "quoted participant sensitive source"
    with Session(db_engine) as s, s.begin():
        purge_subject(s, wid, subject)
        assert s.get(ReportComment, cid) is None
