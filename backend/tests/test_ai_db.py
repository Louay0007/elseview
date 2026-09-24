"""Exclusive lead DB window only. Synthetic drafts; no paid requests."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_analytics_db import context
from test_reviews_db import collected as collected_fixture
from test_reviews_db import decisions
from test_reviews_db import reviewed as reviewed_fixture

from app.ai import service
from app.ai.models import AIAttempt, AIRun, UsageBudget
from app.ai.schemas import ReconcileBody, RunBody
from app.common.errors import DomainError
from app.jobs import service as jobs
from app.jobs.models import Job
from app.jobs.runner import JobRunner

pytestmark = pytest.mark.db


@pytest.fixture
def collected(research_app, db_engine, request, monkeypatch):
    client = research_app[0]
    original = client.post

    def create_assisted(url, **kwargs):
        if url.endswith("/studies"):
            kwargs["json"] = kwargs["json"] | {"ai_policy": "assisted"}
        return original(url, **kwargs)

    monkeypatch.setattr(client, "post", create_assisted)
    return collected_fixture.__wrapped__(research_app, db_engine, request)


reviewed = reviewed_fixture


def claim_run(session, run_id):
    """Prioritize only this fixture's target; do not drain unrelated durable jobs."""
    run = session.get(AIRun, run_id)
    target = session.get(Job, run.job_id)
    target.run_after = jobs.now(session) - timedelta(days=1)
    session.flush()
    job = jobs.claim(session)
    assert job.id == target.id
    return job


def test_ai_mock_durable_cache_and_uncertainty(collected, db_engine, settings):
    _, _, _, result, _, _ = collected
    settings.llm_input_price_per_million = Decimal("1")
    settings.llm_output_price_per_million = Decimal("1")
    with Session(db_engine) as session, session.begin():
        row, study, actor = context(session, result)
        wid, sid = row.workspace_id, study.id
        body = RunBody(
            study_id=sid,
            operation="study_helper",
            command_key="mock-one",
            instruction="Draft a neutral usability question",
            researcher_text_approved=True,
        )
        view = service.create(session, settings, wid, actor, body)
        rid = UUID(view["id"])
        assert service.create(session, settings, wid, actor, body)["id"] == str(rid)
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, rid)
        assert job.kind == "ai.generate"
        prompt, sources, coverage = service.prepare(session, settings, job)
        jid, token = job.id, job.lease_token
    content, usage, request_id = asyncio.run(service.adapter.generate(settings, prompt))
    with Session(db_engine) as session, session.begin():
        from app.jobs.models import Job

        job = session.get(Job, jid)
        assert service.finish(session, settings, job, content, usage, request_id, sources, coverage)
        assert jobs.complete(session, jid, token, {"status": "ok"})
        assert service.view(session, wid, actor, rid)["state"] == "draft"
        assert session.scalar(select(AIAttempt).where(AIAttempt.run_id == rid)).state == "settled"
        assert all(
            b.reserved == 0
            for b in session.scalars(select(UsageBudget).where(UsageBudget.workspace_id == wid))
        )
    with Session(db_engine) as session, session.begin():
        body.command_key = "cache-repeat"
        assert service.create(session, settings, wid, actor, body)["id"] == str(rid)
        body.instruction = "Another question"
        body.command_key = "uncertain"
        second = service.create(session, settings, wid, actor, body)
        second_id = UUID(second["id"])
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, second_id)
        service.prepare(session, settings, job)
        jobs.fail(session, job.id, job.lease_token, "handler_timeout", True)
        attempt = session.scalar(select(AIAttempt).where(AIAttempt.run_id == second_id))
        assert attempt.state == "uncertain" and attempt.actual_cost is None
        assert all(
            b.reserved > 0
            for b in session.scalars(select(UsageBudget).where(UsageBudget.workspace_id == wid))
        )
    with Session(db_engine) as session, session.begin():
        body.command_key = "blind-repeat"
        with pytest.raises(DomainError), session.begin_nested():
            service.create(session, settings, wid, actor, body)
        service.reconcile(
            session,
            wid,
            actor,
            second_id,
            ReconcileBody(actual_cost=Decimal("0.002"), reference="synthetic-invoice"),
        )
        assert all(
            b.reserved == 0
            for b in session.scalars(select(UsageBudget).where(UsageBudget.workspace_id == wid))
        )
        service.invalidate_subject(session, wid, actor)
        assert session.get(AIRun, rid).output is None


def test_embedded_ai_runner(collected, db_engine, settings):
    _, _, _, result, _, _ = collected
    sessions = sessionmaker(db_engine, expire_on_commit=False)
    with sessions.begin() as session:
        row, study, actor = context(session, result)
        response = service.create(
            session,
            settings,
            row.workspace_id,
            actor,
            RunBody(study_id=study.id, operation="study_helper", command_key="runner-fixture"),
        )
        job_id = UUID(response["job_id"])
    settings.job_poll_seconds = 0.1
    runner = JobRunner(SimpleNamespace(sessions=sessions), settings)

    async def run():
        await runner.start()
        try:
            for _ in range(100):
                await asyncio.sleep(0.05)
                with sessions() as session:
                    if session.get(Job, job_id).state in jobs.TERMINAL:
                        break
        finally:
            await runner.stop()

    asyncio.run(run())
    with sessions() as session:
        assert session.get(Job, job_id).state == "succeeded"
        assert session.get(AIRun, UUID(response["id"])).state == "draft"


def test_ai_budget_failure_release_and_missing_usage(collected, db_engine, settings):
    _, _, _, result, _, _ = collected
    settings.llm_input_price_per_million = Decimal("100")
    settings.llm_output_price_per_million = Decimal("100")
    with Session(db_engine) as session, session.begin():
        row, study, actor = context(session, result)
        wid, sid = row.workspace_id, study.id
        body = RunBody(study_id=sid, operation="study_helper", command_key="budget")
        settings.llm_study_budget = Decimal("0.00001")
        with pytest.raises(DomainError), session.begin_nested():
            service.create(session, settings, wid, actor, body)
        settings.llm_study_budget = Decimal("2")
        first = service.create(session, settings, wid, actor, body)
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, UUID(first["id"]))
        service.prepare(session, settings, job)
        service.record_error(
            session,
            job,
            service.adapter.Failure("provider_http_429", False, 30),
            "synthetic-request",
        )
        jobs.fail(session, job.id, job.lease_token)
        assert all(
            b.reserved == 0
            for b in session.scalars(select(UsageBudget).where(UsageBudget.workspace_id == wid))
        )
    with Session(db_engine) as session, session.begin():
        body.command_key = "too-soon"
        with pytest.raises(DomainError), session.begin_nested():
            service.create(session, settings, wid, actor, body)
        body.instruction = "Different synthetic drafting input"
        body.researcher_text_approved = True
        second = service.create(session, settings, wid, actor, body)
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, UUID(second["id"]))
        prompt, sources, coverage = service.prepare(session, settings, job)
        content, _, _ = asyncio.run(service.adapter.generate(settings, prompt))
        service.finish(session, settings, job, content, None, "missing-usage", sources, coverage)
        jobs.complete(session, job.id, job.lease_token, {"status": "ok"})
        attempt = session.scalar(select(AIAttempt).where(AIAttempt.run_id == UUID(second["id"])))
        assert attempt.state == "uncertain" and attempt.actual_cost is None
        assert service.view(session, wid, actor, UUID(second["id"]))["state"] == "draft"


def test_snapshot_requires_exact_optional_consent_and_revocation_fence(
    reviewed, collected, db_engine, settings
):
    from uuid import uuid4

    from app.analytics import service as analytics
    from app.common.privacy_models import ConsentDocument, ConsentReceipt

    wid, sid, actor, reviewers, subject = reviewed
    with Session(db_engine) as session, session.begin():
        decisions(session, wid, sid, actor, reviewers)
        row, study, _ = context(session, collected[3])
        snapshot = analytics.freeze(session, wid, actor, study.id, row.version_id)
        assert snapshot.metrics["included"] == 1
        body = RunBody(
            study_id=study.id, snapshot_id=snapshot.id, operation="themes", command_key="consent"
        )
        with pytest.raises(DomainError), session.begin_nested():
            service.create(session, settings, wid, actor, body)
        doc = ConsentDocument(
            workspace_id=wid,
            document_key=uuid4().hex,
            version=1,
            locale=row.locale,
            purpose="ai_processing",
            body="Synthetic optional processing",
            digest="b" * 64,
        )
        session.add(doc)
        session.flush()
        receipt = ConsentReceipt(
            workspace_id=wid,
            subject_id=subject,
            document_id=doc.id,
            study_version_id=row.version_id,
            decision="granted",
            presented_digest=doc.digest,
            receipt_key=uuid4().hex,
        )
        session.add(receipt)
        session.flush()
        result = service.create(session, settings, wid, actor, body)
        run_id = UUID(result["id"])
        doc_id, doc_digest = doc.id, doc.digest
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, run_id)
        prompt, sources, coverage = service.prepare(session, settings, job)
        job_id, token = job.id, job.lease_token
    with Session(db_engine) as session, session.begin():
        row = session.get(
            __import__("app.collection.models", fromlist=["CollectionSession"]).CollectionSession,
            sid,
        )
        session.add(
            ConsentReceipt(
                workspace_id=wid,
                subject_id=subject,
                document_id=doc_id,
                study_version_id=row.version_id,
                decision="withdrawn",
                presented_digest=doc_digest,
                receipt_key=uuid4().hex,
            )
        )
    with Session(db_engine) as session, session.begin():
        job = session.get(Job, job_id)
        assert not service.authorize_job(session, job)
        assert not jobs.complete(session, job_id, token, {"status": "ok"})
        attempt = session.scalar(select(AIAttempt).where(AIAttempt.run_id == run_id))
        assert attempt.state == "uncertain"


def test_ai_http_worker_approval_and_access(collected, research_app, db_engine):
    from research_support import policy

    from app.auth.models import User

    client, app, make_actor = research_app
    with Session(db_engine) as session, session.begin():
        row, study, actor = context(session, collected[3])
        wid, study_id = row.workspace_id, study.id
        headers = {
            "Authorization": "Bearer "
            + app.state.auth._new_login(session, session.get(User, actor))["access_token"]
        }
    base = f"/api/v1/workspaces/{wid}"
    body = {"study_id": str(study_id), "operation": "study_helper", "command_key": "http-flow"}
    response = client.post(base + "/ai/runs", headers=headers, json=body)
    assert response.status_code == 202, response.text
    run_id = response.json()["id"]
    assert response.headers["cache-control"] == "no-store"
    viewer_headers, _, _ = make_actor(wid, "viewer")
    assert client.get(base + "/ai/runs/" + run_id, headers=viewer_headers).status_code in {403, 404}
    with app.state.database.sessions.begin() as session:
        job = claim_run(session, UUID(run_id))
    runner = JobRunner(app.state.database, app.state.settings)
    asyncio.run(runner._execute(job))
    path = base + "/ai/runs/" + run_id
    assert client.get(path, headers=headers).json()["state"] == "draft"
    assert client.post(path + "/approve", headers=headers).json()["state"] == "approved"
    assert client.post(path + "/approve", headers=headers).status_code == 409
    # This fixture deliberately creates assisted studies; original TestClient method bypasses
    # only that fixture convenience so production human_only creation is exercised.
    from fastapi.testclient import TestClient

    human = TestClient.post(
        client,
        base + "/studies",
        headers=headers | {"Idempotency-Key": "human-http"},
        json={
            "title": "Human only",
            "ai_policy": "human_only",
            "retention_policy_id": policy(client, base, headers),
        },
    )
    assert human.status_code == 201, human.text
    body.update(study_id=human.json()["study_id"], command_key="human-denied")
    assert client.post(base + "/ai/runs", headers=headers, json=body).status_code == 403


def test_concurrent_study_budget_reservations(collected, db_engine, settings):
    from threading import Barrier

    with Session(db_engine) as session:
        row, study, actor = context(session, collected[3])
        wid, sid = row.workspace_id, study.id
    settings.llm_input_price_per_million = Decimal("1")
    settings.llm_output_price_per_million = Decimal("1")
    amount = service.adapter.estimate(
        settings, service.adapter.messages("study_helper", "", [], {})
    )
    settings.llm_study_budget = amount * Decimal("1.5")
    gate = Barrier(2)

    def reserve(index):
        gate.wait(timeout=5)
        try:
            with Session(db_engine) as session, session.begin():
                result = service.create(
                    session,
                    settings,
                    wid,
                    actor,
                    RunBody(
                        study_id=sid,
                        operation="study_helper",
                        command_key=f"parallel-{index}",
                        instruction=str(index),
                        researcher_text_approved=True,
                    ),
                )
                return result["id"]
        except DomainError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, [0, 1]))
    assert results.count("AI_BUDGET_EXHAUSTED") == 1
    with Session(db_engine) as session, session.begin():
        budgets = session.scalars(select(UsageBudget).where(UsageBudget.workspace_id == wid)).all()
        assert len(budgets) == 2 and budgets[0].reserved == budgets[1].reserved
        assert budgets[0].reserved <= settings.llm_study_budget
        run_id = UUID(next(value for value in results if value != "AI_BUDGET_EXHAUSTED"))
        run = session.get(AIRun, run_id)
        jobs.cancel(session, workspace_id=wid, user_id=actor, job_id=run.job_id)
        assert all(b.reserved == 0 for b in budgets)
