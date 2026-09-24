"""Narrow P19 workflows: real HTTP collection, PostgreSQL, synthetic AI only."""

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_ai_db import claim_run
from test_ai_db import collected as collected_fixture
from test_analytics_db import context
from test_collection_db import put
from test_reviews_db import decisions
from test_reviews_db import reviewed as reviewed_fixture

from app.ai import service as ai
from app.ai.models import AIRun
from app.ai.schemas import RunBody
from app.analytics import service as analytics
from app.collection.models import AnswerRevision, CollectionSession
from app.common.errors import DomainError
from app.common.privacy_models import ConsentDocument, ConsentReceipt
from app.jobs import service as jobs
from app.jobs.models import Job
from app.reviews.models import RewardRecord

pytestmark = pytest.mark.db
collected = collected_fixture
reviewed = reviewed_fixture


def test_accepted_answer_review_reward_report_mock_ai(reviewed, collected, db_engine, settings):
    assert settings.ai_mode == "mock"
    # reviewed submits a real HTTP answer and creates independent human reviewers.
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as session, session.begin():
        assignments = decisions(session, wid, sid, owner, reviewers)
        assert len({a.reviewer_id for a in assignments}) == 2
        reward = session.scalars(
            select(RewardRecord).where(RewardRecord.subject_id == subject)
        ).one()
        assert reward.amount_millimes == 1000 and reward.state == "earned"
        row, study, _ = context(session, collected[3])
        snapshot = analytics.freeze(session, wid, owner, study.id, row.version_id)
        assert snapshot.metrics["included"] == 1
        assert snapshot.metrics["blocks"]["single"]["distribution"]["no"]["numerator"] == 1
        report = analytics.create_report(session, wid, owner, snapshot.id)
        analytics.approve(session, wid, owner, UUID(report["id"]), 1)
        share = analytics.create_share(session, wid, owner, UUID(report["id"]), 60)
        assert analytics.read_share(session, share["token"])["sample_size_band"] == "suppressed"
        with pytest.raises(DomainError):
            analytics.snapshot_view(session, uuid4(), owner, snapshot.id)
        # Researcher-only assistance is deliberately not participant-source analysis.
        body = RunBody(study_id=study.id, operation="study_helper", command_key="acceptance")
        run = ai.create(session, settings, wid, owner, body)
        rid = UUID(run["id"])
        assert ai.create(session, settings, wid, owner, body)["id"] == str(rid)
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, rid)
        prompt, sources, coverage = ai.prepare(session, settings, job)
        jid, token = job.id, job.lease_token
    content, usage, request_id = asyncio.run(ai.adapter.generate(settings, prompt))
    with Session(db_engine) as session, session.begin():
        job = session.get(Job, jid)
        assert ai.finish(session, settings, job, content, usage, request_id, sources, coverage)
        assert jobs.complete(session, jid, token, {"status": "ok"})
        assert ai.view(session, wid, owner, rid)["state"] == "draft"
        with pytest.raises(DomainError):
            ai.view(session, uuid4(), owner, rid)


def test_network_replay_preserves_one_answer_and_submission(collected, db_engine):
    client, url, headers, result, auth, start = collected
    resumed = client.post("/api/v1/collection/sessions", headers=auth, json=start)
    assert resumed.status_code == 201
    assert resumed.json()["session_id"] == result["session_id"]
    response, body = put(client, url, headers, "no")
    assert response.status_code == 200
    replay = client.put(url + "/answers/single", headers=headers, json=body)
    assert replay.status_code == 200 and replay.json() == response.json()
    assert put(client, url, headers, "yes")[0].status_code == 409
    submit = {"version_id": result["version_id"], "expected_revision": 1}
    response = client.post(url + "/submit", headers=headers, json=submit)
    assert response.status_code == 200
    replay = client.post(url + "/submit", headers=headers, json=submit)
    assert replay.status_code == 200 and replay.json() == response.json()
    with Session(db_engine) as session:
        sid = UUID(result["session_id"])
        assert (
            len(
                session.scalars(
                    select(AnswerRevision).where(AnswerRevision.session_id == sid)
                ).all()
            )
            == 1
        )
        assert len(session.scalars(select(Job).where(Job.target_id == sid)).all()) == 1
        assert set(session.get(CollectionSession, sid).submitted_snapshot) == {"single"}


def test_withdrawal_between_ai_prepare_and_final_write(reviewed, collected, db_engine, settings):
    """Exercise the cloud-result persistence boundary without a cloud request."""
    assert settings.ai_mode == "mock"
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as session, session.begin():
        decisions(session, wid, sid, owner, reviewers)
        row, study, _ = context(session, collected[3])
        snapshot = analytics.freeze(session, wid, owner, study.id, row.version_id)
        doc = ConsentDocument(
            workspace_id=wid,
            document_key=uuid4().hex,
            version=1,
            locale=row.locale,
            purpose="ai_processing",
            body="Synthetic optional AI consent",
            digest="b" * 64,
        )
        session.add(doc)
        session.flush()
        receipt = dict(
            workspace_id=wid,
            subject_id=subject,
            document_id=doc.id,
            study_version_id=row.version_id,
            presented_digest=doc.digest,
        )
        session.add(ConsentReceipt(**receipt, decision="granted", receipt_key=uuid4().hex))
        session.flush()
        run = ai.create(
            session,
            settings,
            wid,
            owner,
            RunBody(
                study_id=study.id,
                snapshot_id=snapshot.id,
                operation="themes",
                command_key="privacy",
            ),
        )
        rid = UUID(run["id"])
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, rid)
        prompt, sources, coverage = ai.prepare(session, settings, job)
        jid = job.id
    content, usage, request_id = asyncio.run(ai.adapter.generate(settings, prompt))
    # A separately committed revocation arrives while the synthetic provider is in flight.
    with Session(db_engine) as session, session.begin():
        session.add(ConsentReceipt(**receipt, decision="withdrawn", receipt_key=uuid4().hex))
    with Session(db_engine) as session, session.begin():
        assert not ai.finish(
            session, settings, session.get(Job, jid), content, usage, request_id, sources, coverage
        )
    with Session(db_engine) as session:
        run = session.get(AIRun, rid)
        assert not run.output and run.state not in {"draft", "approved"}
        reward = session.scalars(
            select(RewardRecord).where(RewardRecord.subject_id == subject)
        ).one()
        assert reward.state == "earned" and reward.amount_millimes == 1000
