"""Local unit guards; DB integration is deliberately separate."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.common.errors import DomainError
from app.privacy_ops import lifecycle


@pytest.fixture
def scoped(monkeypatch):
    session = MagicMock()
    workspace = SimpleNamespace(privacy_epoch=0)
    monkeypatch.setattr(lifecycle, "lock_workspace", lambda session, wid: workspace)
    monkeypatch.setattr("app.privacy_ops.service.workspace_held", lambda session, wid: False)
    monkeypatch.setattr("app.privacy_ops.events.record_event", lambda *args: None)
    return session, workspace


def test_unknown_action_fails_closed(scoped):
    session, _ = scoped
    with pytest.raises(ValueError, match="not implemented"):
        lifecycle.apply_lifecycle_event(session, uuid4(), "unsupported_delete", uuid4())
    session.delete.assert_not_called()


def test_missing_scoped_resource_is_idempotent(scoped):
    session, _ = scoped
    session.scalar.return_value = None
    lifecycle.apply_lifecycle_event(session, uuid4(), "contact_delete", uuid4())
    session.delete.assert_not_called()


def test_contact_hold_defers_without_scrubbing(scoped, monkeypatch):
    session, _ = scoped
    contact = SimpleNamespace(id=uuid4(), attributes_json={"private": "value"})
    session.scalar.return_value = contact
    monkeypatch.setattr(lifecycle, "contact_held", lambda *args: True)
    with pytest.raises(DomainError):
        lifecycle.apply_lifecycle_event(session, uuid4(), "contact_delete", contact.id)
    assert contact.attributes_json == {"private": "value"}
    session.flush.assert_not_called()


def test_contact_erasure_strips_only_scoped_recruitment_payload(scoped, monkeypatch):
    session, _ = scoped
    wid, cid = uuid4(), uuid4()
    contact = SimpleNamespace(
        id=cid, attributes_json={"private": "value"}, source="raw", status="active"
    )
    candidate = SimpleNamespace(
        id=uuid4(), attributes_json={"private": "value"}, source_id=cid, status="eligible"
    )
    invitation = SimpleNamespace(revoked_at=None)
    session.scalar.return_value = contact
    session.scalars.side_effect = [
        SimpleNamespace(all=lambda: [candidate]),
        SimpleNamespace(all=lambda: []),
        [invitation],
    ]
    monkeypatch.setattr("app.recruiting.service.release_reservation", lambda *args: None)
    monkeypatch.setattr(lifecycle, "contact_held", lambda *args: False)
    lifecycle.apply_lifecycle_event(session, wid, "contact_delete", cid)
    assert (contact.attributes_json, contact.source, contact.status) == ({}, "", "withdrawn")
    assert candidate.attributes_json == {} and candidate.source_id is None
    assert candidate.status == "withdrawn" and invitation.revoked_at is not None
    assert len(contact.contact_lookup_hash) == 64
    session.delete.assert_not_called()  # Financial/consent shells are retained.
    for call in session.scalars.call_args_list:
        sql = str(call.args[0])
        assert "workspace_id" in sql


def test_workspace_hold_prevents_all_sweep_mutations(scoped, monkeypatch):
    session, workspace = scoped
    monkeypatch.setattr("app.privacy_ops.service.workspace_held", lambda *args: True)
    assert not any(lifecycle.sweep_lifecycle(session, uuid4()).values())
    assert workspace.privacy_epoch == 0
    session.scalars.assert_not_called()


def test_sweep_limit_is_bounded_and_without_policy_only_contacts(scoped, monkeypatch):
    session, _ = scoped
    monkeypatch.setattr("app.privacy_ops.service.reviewed_cutoff", lambda *args: None)
    session.scalars.return_value.all.return_value = []
    lifecycle.sweep_lifecycle(session, uuid4(), limit=100000)
    query = session.scalars.call_args.args[0]
    assert query.compile().params["param_1"] == 100
    assert "private_contacts" in str(query)
    assert "privacy_contact_holds" in str(query)
    assert session.scalars.call_count == 1


@pytest.mark.db
def test_contact_hold_admin_scope_release_and_erasure_db(research_app, db_engine):
    from datetime import timedelta

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.auth.security import utcnow
    from app.privacy_ops.models import RestoreEvent
    from app.recruiting.models import PrivateContact

    client, app, actor = research_app
    headers, uid, wid = actor()
    other_headers, _, other_wid = actor()
    member_headers, _, _ = actor(wid, role="viewer")
    with Session(db_engine) as session, session.begin():
        contact = PrivateContact(
            workspace_id=wid,
            contact_lookup_hash=uuid4().hex * 2,
            attributes_json={"name": "synthetic"},
            source="synthetic",
            retention_until=utcnow() - timedelta(days=1),
        )
        session.add(contact)
        session.flush()
        cid = contact.id
    base = f"/api/v1/workspaces/{wid}/privacy-ops"
    body = {
        "contact_id": str(cid),
        "reason_code": "legal_review",
        "review_deadline": (utcnow() + timedelta(days=1)).isoformat(),
    }
    assert (
        client.post(base + "/contact-holds", headers=member_headers, json=body).status_code == 403
    )
    assert (
        client.post(
            f"/api/v1/workspaces/{other_wid}/privacy-ops/contact-holds",
            headers=other_headers,
            json=body,
        ).status_code
        == 404
    )
    hold = client.post(base + "/contact-holds", headers=headers, json=body)
    assert hold.status_code == 201, hold.text
    assert client.post(base + f"/contacts/{cid}/erase", headers=headers).status_code == 409
    with Session(db_engine) as session:
        assert session.get(PrivateContact, cid).attributes_json == {"name": "synthetic"}
    assert (
        client.post(
            base + f"/contact-holds/{hold.json()['id']}/release", headers=headers
        ).status_code
        == 200
    )
    erased = client.post(base + f"/contacts/{cid}/erase", headers=headers)
    assert erased.status_code == 200, erased.text
    with Session(db_engine) as session:
        assert session.get(PrivateContact, cid).attributes_json == {}
        assert session.scalar(
            select(RestoreEvent.id).where(
                RestoreEvent.workspace_id == wid,
                RestoreEvent.action == "contact_delete",
                RestoreEvent.resource_id == cid,
            )
        )


@pytest.mark.db
def test_contact_dataset_retention_scoped_bounded_db(research_app, db_engine):
    from datetime import timedelta

    from research_support import policy
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.auth.models import Membership
    from app.auth.security import utcnow
    from app.evaluation.models import EvaluationDataset
    from app.privacy_ops.models import RestoreEvent
    from app.recruiting.models import PrivateContact
    from app.studies.models import Study

    client, app, actor = research_app
    headers, uid, wid = actor()
    _, _, other_wid = actor()
    retention = policy(client, f"/api/v1/workspaces/{wid}", headers)
    base = f"/api/v1/workspaces/{wid}/privacy-ops"
    with Session(db_engine) as session, session.begin():
        member = session.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.user_id == uid)
        )
        study = Study(
            workspace_id=wid,
            title="Synthetic",
            owner_membership_id=member.id,
            retention_policy_id=UUID(retention),
        )
        session.add(study)
        session.flush()
        dataset = EvaluationDataset(
            workspace_id=wid,
            study_id=study.id,
            key="synthetic",
            version=1,
            creator_id=uid,
            rights={},
            schema={},
            created_at=utcnow() - timedelta(days=10),
        )
        contacts = [
            PrivateContact(
                workspace_id=w,
                contact_lookup_hash=uuid4().hex * 2,
                attributes_json={"raw": "synthetic"},
                source="synthetic",
                retention_until=utcnow() - timedelta(days=1),
            )
            for w in (wid, other_wid)
        ]
        session.add_all([dataset, *contacts])
        session.flush()
        did, cid, other_cid = dataset.id, contacts[0].id, contacts[1].id
    with Session(db_engine) as session, session.begin():
        counts = lifecycle.sweep_lifecycle(session, wid, limit=1)
        assert counts["contacts"] == 1 and sum(counts.values()) == 1
        assert session.get(EvaluationDataset, did) is not None  # no reviewed policy
    review = client.post(
        base + "/retention",
        headers=headers,
        json={
            "purpose": "raw",
            "version": 1,
            "days": 1,
            "reason": "synthetic review",
            "review_deadline": (utcnow() + timedelta(days=1)).isoformat(),
        },
    )
    assert review.status_code == 201, review.text
    with Session(db_engine) as session, session.begin():
        counts = lifecycle.sweep_lifecycle(session, wid, limit=1)
        assert counts["datasets"] == 1
    with Session(db_engine) as session:
        assert session.get(EvaluationDataset, did) is None
        assert session.get(PrivateContact, cid).attributes_json == {}
        assert session.get(PrivateContact, other_cid).attributes_json == {"raw": "synthetic"}
        assert session.scalar(
            select(RestoreEvent.id).where(
                RestoreEvent.workspace_id == wid,
                RestoreEvent.action == "dataset_delete",
                RestoreEvent.resource_id == did,
            )
        )


@pytest.mark.db
def test_study_event_removes_exact_study_and_template_not_same_owner_db(research_app, db_engine):
    from research_support import policy
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.auth.models import Membership
    from app.privacy_ops.events import apply_event, record_event
    from app.studies.models import Study, StudyVersion
    from app.templates.models import TemplateInstance

    client, app, actor = research_app
    headers, uid, wid = actor()
    retention = UUID(policy(client, f"/api/v1/workspaces/{wid}", headers))
    with Session(db_engine) as session, session.begin():
        member = session.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.user_id == uid)
        )
        studies = [
            Study(
                workspace_id=wid,
                title=f"Synthetic {n}",
                owner_membership_id=member.id,
                retention_policy_id=retention,
            )
            for n in range(2)
        ]
        session.add_all(studies)
        session.flush()
        from app.auth.security import utcnow

        version = StudyVersion(
            workspace_id=wid,
            study_id=studies[0].id,
            number=1,
        )
        session.add(version)
        session.flush()
        template = TemplateInstance(
            workspace_id=wid,
            study_id=studies[0].id,
            version_id=version.id,
            template_key="synthetic",
            template_version=1,
            recipe_hash="0" * 64,
            configuration_hash="0" * 64,
            recipe_snapshot={},
            inputs_snapshot={"synthetic": "raw"},
        )
        session.add(template)
        session.flush()
        version.state, version.published_at, version.content_hash = "published", utcnow(), "0" * 64
        session.flush()
        target, survivor, tid = studies[0].id, studies[1].id, template.id
    with Session(db_engine) as session, session.begin():
        apply_event(session, wid, "study_delete", target)
        record_event(session, wid, "study_delete", target)
    with Session(db_engine) as session:
        assert session.get(Study, target) is None
        assert session.get(TemplateInstance, tid) is None
        assert session.get(Study, survivor) is not None


@pytest.mark.db
def test_operational_retention_scrubs_payload_keeps_identifiers_db(research_app, db_engine):
    from datetime import timedelta

    from sqlalchemy.orm import Session

    from app.auth.models import AuditEvent
    from app.auth.security import utcnow
    from app.common.idempotency import IdempotencyRecord
    from app.privacy_ops.events import apply_event

    client, app, actor = research_app
    headers, uid, wid = actor()
    _, _, other_wid = actor()
    with Session(db_engine) as session, session.begin():
        audit = AuditEvent(
            workspace_id=wid, actor_id=uid, action="synthetic", details={"raw": "synthetic"}
        )
        record = IdempotencyRecord(
            workspace_id=wid,
            actor_id=uid,
            operation="synthetic",
            key_hash="0" * 64,
            request_hash="1" * 64,
            response={"raw": "synthetic"},
            expires_at=utcnow() + timedelta(days=1),
        )
        session.add_all([audit, record])
        session.flush()
        aid, rid = audit.id, record.id
    with Session(db_engine) as session, session.begin():
        apply_event(session, other_wid, "audit_scrub", aid)
        assert session.get(AuditEvent, aid).details == {"raw": "synthetic"}
        apply_event(session, wid, "audit_scrub", aid)
        apply_event(session, wid, "idempotency_scrub", rid)
    with Session(db_engine) as session:
        assert session.get(AuditEvent, aid).details == {}
        assert session.get(IdempotencyRecord, rid).response is None
        assert session.get(IdempotencyRecord, rid).key_hash == "0" * 64


@pytest.mark.db
def test_study_retention_minimizes_raw_preserving_reservation_db(research_app, db_engine):
    from datetime import timedelta

    from research_support import policy
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session

    from app.auth.models import Membership
    from app.auth.security import utcnow
    from app.privacy_ops.models import RestoreEvent
    from app.recruiting.models import Candidate, Reservation
    from app.studies.models import Launch, Study, StudyVersion
    from app.templates.models import TemplateInstance

    client, app, actor = research_app
    headers, uid, wid = actor()
    retention = UUID(policy(client, f"/api/v1/workspaces/{wid}", headers))
    with Session(db_engine) as session, session.begin():
        member = session.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.user_id == uid)
        )
        studies = [
            Study(
                workspace_id=wid,
                title="Synthetic raw title",
                owner_membership_id=member.id,
                retention_policy_id=retention,
                status="closed",
                created_at=utcnow() - timedelta(days=10),
            ),
            Study(
                workspace_id=wid,
                title="Sibling raw",
                owner_membership_id=member.id,
                retention_policy_id=retention,
            ),
        ]
        session.add_all(studies)
        session.flush()
        version = StudyVersion(
            workspace_id=wid,
            study_id=studies[0].id,
            number=1,
            blocks_json=[{"raw": "synthetic"}],
            rules_json={"raw": "synthetic"},
            consent_documents={"raw": "synthetic"},
        )
        session.add(version)
        session.flush()
        template = TemplateInstance(
            workspace_id=wid,
            study_id=studies[0].id,
            version_id=version.id,
            template_key="synthetic",
            template_version=1,
            recipe_hash="1" * 64,
            configuration_hash="2" * 64,
            recipe_snapshot={"raw": "synthetic"},
            inputs_snapshot={"raw": "synthetic"},
        )
        session.add(template)
        session.flush()
        version.state, version.published_at, version.content_hash = "published", utcnow(), "3" * 64
        session.flush()
        launch = Launch(workspace_id=wid, version_id=version.id)
        session.add(launch)
        session.flush()
        candidate = Candidate(
            workspace_id=wid,
            launch_id=launch.id,
            subject_id=uid,
            source_kind="public",
            source_id=uid,
            attributes_json={"raw": "synthetic"},
        )
        session.add(candidate)
        session.flush()
        reservation = Reservation(
            workspace_id=wid,
            launch_id=launch.id,
            candidate_id=candidate.id,
            state="consumed",
            expires_at=utcnow(),
            reward_millimes=12345,
        )
        session.add(reservation)
        session.flush()
        sid, sibling, vid, tid, rid = (
            studies[0].id,
            studies[1].id,
            version.id,
            template.id,
            reservation.id,
        )
    response = client.post(
        f"/api/v1/workspaces/{wid}/privacy-ops/retention",
        headers=headers,
        json={
            "purpose": "raw",
            "version": 1,
            "days": 1,
            "reason": "synthetic review",
            "review_deadline": (utcnow() + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    with Session(db_engine) as session, session.begin():
        assert lifecycle.sweep_lifecycle(session, wid)["studies"] == 1
    with Session(db_engine) as session, session.begin():
        assert lifecycle.sweep_lifecycle(session, wid)["studies"] == 0
        study, version, template, reservation = (
            session.get(Study, sid),
            session.get(StudyVersion, vid),
            session.get(TemplateInstance, tid),
            session.get(Reservation, rid),
        )
        assert study.title == "Erased study" and study.status == "archived"
        assert (
            version.blocks_json == []
            and version.rules_json == {}
            and version.consent_documents == {}
        )
        assert version.content_hash == "3" * 64
        assert template.inputs_snapshot == {} and template.recipe_snapshot == {}
        assert template.configuration_hash == "2" * 64
        assert reservation.reward_millimes == 12345 and reservation.state == "consumed"
        assert session.get(Study, sibling).title == "Sibling raw"
        assert (
            session.scalar(
                select(func.count())
                .select_from(RestoreEvent)
                .where(
                    RestoreEvent.workspace_id == wid,
                    RestoreEvent.action == "study_delete",
                    RestoreEvent.resource_id == sid,
                )
            )
            == 1
        )

    # The durable event permits only emptying; never a fresh arbitrary rewrite.
    from sqlalchemy.exc import DBAPIError

    with Session(db_engine) as session:
        with pytest.raises(DBAPIError):
            with session.begin():
                version = session.get(StudyVersion, vid)
                version.blocks_json = [{"raw": "must not be reintroduced"}]
                session.flush()
    with Session(db_engine) as session:
        with pytest.raises(DBAPIError):
            with session.begin():
                template = session.get(TemplateInstance, tid)
                template.inputs_snapshot = {"raw": "must not be reintroduced"}
                session.flush()
