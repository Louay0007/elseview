"""Fresh PostgreSQL only; synthetic inputs and mock provider transport."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from test_ai_db import claim_run, reviewed  # noqa: F401
from test_ai_db import collected as collected_fixture
from test_analytics_db import context
from test_reviews_db import decisions

from app.ai import orchestration as graph
from app.ai import service
from app.ai.models import AIAttempt, AICommand, AIRun, AIRunInput, AIStep, UsageBudget
from app.ai.schemas import EstimateBody, ReconcileBody, RunBody
from app.analytics import service as analytics
from app.auth.models import Membership, User, Workspace
from app.auth.security import utcnow
from app.billing.models import Usage
from app.collection.models import CollectionSession
from app.common.errors import DomainError
from app.common.privacy_models import ConsentDocument, ConsentReceipt
from app.jobs import service as jobs
from app.jobs.models import Job
from app.jobs.runner import JobRunner
from app.studies.models import Study, StudyGrant

pytestmark = pytest.mark.db


@pytest.fixture(autouse=True)
def enable_graphs(settings):
    settings.ai_orchestration_enabled = True


@pytest.fixture
def collected(research_app, db_engine, request, monkeypatch):
    from study_fixtures import blocks

    client = research_app[0]
    original = client.put

    def put_text(url, **kwargs):
        payload = kwargs.get("json", {})
        if "blocks_json" in payload:
            block = blocks(str(uuid4()))[3] | {"block_key": "single"}
            kwargs["json"] = payload | {"blocks_json": [block], "rules_json": {}}
        elif url.endswith("/answers/single"):
            kwargs["json"] = payload | {
                "value": {"text": "واجهة difficile 3lech", "language": "fr"}
            }
        return original(url, **kwargs)

    monkeypatch.setattr(client, "put", put_text)
    return collected_fixture.__wrapped__(research_app, db_engine, request, monkeypatch)


@pytest.fixture
def source(reviewed, collected, db_engine):  # noqa: F811
    wid, sid, actor, reviewers, subject = reviewed
    with Session(db_engine) as session, session.begin():
        decisions(session, wid, sid, actor, reviewers)
        row, study, _ = context(session, collected[3])
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
        session.add(
            ConsentReceipt(
                workspace_id=wid,
                subject_id=subject,
                document_id=doc.id,
                study_version_id=row.version_id,
                decision="granted",
                presented_digest=doc.digest,
                receipt_key=uuid4().hex,
            )
        )
        snapshot = analytics.freeze(session, wid, actor, study.id, row.version_id)
        from test_billing import rules

        from app.auth.security import utcnow
        from app.billing import service as billing
        from app.billing.schemas import ActivateBody, PlanBody

        plan = billing.create_plan(
            session, wid, actor, PlanBody(key="synthetic", version=1, reviewed=True, rules=rules())
        )
        billing.activate(
            session,
            wid,
            actor,
            ActivateBody(
                plan_id=plan.id,
                starts_at=utcnow() - timedelta(seconds=1),
                ends_at=utcnow() + timedelta(days=30),
            ),
        )
        return wid, actor, study.id, snapshot.id, sid


def confirmed(session, settings, source, key="graph", **updates):
    wid, actor, study, snapshot, _ = source
    body = EstimateBody(
        **(
            dict(study_id=study, snapshot_id=snapshot, operation="themes", profile_revision="2")
            | updates
        )
    )
    estimate = service.estimate(session, settings, wid, actor, body)
    request = RunBody(
        **body.model_dump(),
        command_key=key,
        plan_digest=estimate["plan_digest"],
        max_reserved_cost=estimate["reserved_cost"],
        currency=estimate["currency"],
    )
    return request, estimate


def make_run(db_engine, settings, source, **updates):
    with Session(db_engine) as session, session.begin():
        request, estimate = confirmed(session, settings, source, **updates)
        result = service.create(session, settings, source[0], source[1], request)
        return UUID(result["id"]), request, estimate


def answer(prepared):
    data = json.loads(prepared[0][1]["content"])
    findings = data.get("untrusted_intermediates")
    if findings is None:
        parts = data.get("untrusted_sources", [])
        findings = [
            {
                "text": "Synthetic finding",
                "evidence": [{"source_id": part["source_id"], "quote": part["text"]}],
            }
            for part in parts[:1]
        ]
    return json.dumps(
        {"findings": findings, "limitations": ["Synthetic"], "insufficient_evidence": not findings}
    )


def finish_one(db_engine, settings, run_id, *, usage=None, invalid=False):
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, run_id)
        prepared = graph.prepare(session, settings, job)
        jid = job.id
    with Session(db_engine) as session, session.begin():
        job = session.get(Job, jid)
        graph.finish(
            session,
            settings,
            job,
            "invalid" if invalid else answer(prepared),
            {"prompt_tokens": 1, "completion_tokens": 1} if usage is None else usage,
            "synthetic",
            prepared,
        )
        return jid


def test_estimate_confirmation_atomicity_and_cache_binding(source, db_engine, settings):
    settings.llm_input_price_per_million = Decimal("1")
    settings.llm_output_price_per_million = Decimal("1")
    tables = (AIRun, AIRunInput, AIStep, AIAttempt, AICommand, Job, UsageBudget, Usage)
    with Session(db_engine) as session, session.begin():
        before = [session.scalar(select(func.count()).select_from(table)) for table in tables]
        request, estimate = confirmed(session, settings, source)
        assert [
            session.scalar(select(func.count()).select_from(table)) for table in tables
        ] == before
        for update in ({"plan_digest": "0" * 64}, {"max_reserved_cost": "0"}, {"currency": "EUR"}):
            with (
                pytest.raises(DomainError, match="AI_CONFIRMATION_CHANGED"),
                session.begin_nested(),
            ):
                service.create(
                    session, settings, source[0], source[1], request.model_copy(update=update)
                )
        assert [
            session.scalar(select(func.count()).select_from(table)) for table in tables
        ] == before
        result = service.create(session, settings, source[0], source[1], request)
        rid = UUID(result["id"])
        assert result["planned_calls"] == 2
        assert Decimal(result["outstanding_reserved_cost"]) == Decimal(estimate["reserved_cost"])
    finish_one(db_engine, settings, rid)
    finish_one(db_engine, settings, rid)
    with Session(db_engine) as session, session.begin():
        output = service.view(session, source[0], source[1], rid)
        assert output["state"] == "draft" and output["completed_calls"] == 2
        assert output["draft"]["source_counts"] == [1]
        assert output["processed_coverage"]["source_included"] == 1
        assert output["processed_coverage"]["unique_source_chars"] == output["coverage"]["unique_source_chars"]
        assert Decimal(output["outstanding_reserved_cost"]) == 0
        units = session.scalars(select(Usage).where(Usage.source_id == rid)).all()
        assert len(units) == 1 and units[0].state == "consumed"
        cached = request.model_copy(update={"command_key": "cached-new-key"})
        assert service.create(session, settings, source[0], source[1], cached)["id"] == str(rid)
        assert (
            session.scalar(
                select(AICommand).where(AICommand.command_key == "cached-new-key")
            ).run_id
            == rid
        )
        with pytest.raises(DomainError, match="IDEMPOTENCY_CONFLICT"):
            service.create(
                session,
                settings,
                source[0],
                source[1],
                cached.model_copy(
                    update={"instruction": "Changed", "researcher_text_approved": True}
                ),
            )


@pytest.mark.parametrize("sent", [False, True])
def test_crash_recovery_never_resends_sent(source, db_engine, settings, sent):
    rid, _, _ = make_run(db_engine, settings, source)
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, rid)
        if sent:
            graph.prepare(session, settings, job)
        jid = job.id
        job.lease_expires_at = jobs.now(session) - timedelta(seconds=1)
    with Session(db_engine) as session, session.begin():
        assert jobs.recover_expired(session) >= 1
        job = session.get(Job, jid)
        run = session.get(AIRun, rid)
        states = [a.state for a in graph.attempts(session, run)]
        if sent:
            assert job.state == "uncertain" and run.state == "uncertain"
            assert sorted(states) == ["released", "uncertain"]
            with pytest.raises(DomainError):
                graph.prepare(session, settings, job)
        else:
            assert job.state == "pending" and states == ["reserved", "reserved"]


@pytest.mark.parametrize("stage", ["queued", "sent", "mapped"])
def test_cancel_releases_only_unsent_and_reconciles_exact_attempt(
    source, db_engine, settings, stage
):
    rid, _, _ = make_run(db_engine, settings, source)
    if stage == "mapped":
        finish_one(db_engine, settings, rid)
    with Session(db_engine) as session, session.begin():
        if stage == "sent":
            job = claim_run(session, rid)
            graph.prepare(session, settings, job)
            jid = job.id
        result = graph.cancel(session, source[0], source[1], rid)
        assert result["state"] == "cancelled"
        assert graph.cancel(session, source[0], source[1], rid)["state"] == "cancelled"
        assert result["unresolved_attempts"] == (1 if stage == "sent" else 0)
    if stage == "sent":
        with Session(db_engine) as session, session.begin():
            job = session.get(Job, jid)
            jobs._end(session, job, "cancelled")
            run = session.get(AIRun, rid)
            attempt = next(a for a in graph.attempts(session, run) if a.state == "uncertain")
            graph.reconcile(
                session,
                source[0],
                source[1],
                rid,
                attempt.id,
                ReconcileBody(actual_cost="0.01", reference="synthetic-invoice"),
            )
            assert attempt.state == "settled" and run.state == "cancelled"


@pytest.mark.parametrize("case", ["invalid", "unknown", "overrun"])
def test_settlement_failure_and_uncertainty(source, db_engine, settings, case):
    settings.llm_input_price_per_million = Decimal("1")
    settings.llm_output_price_per_million = Decimal("1")
    rid, _, _ = make_run(db_engine, settings, source)
    usage = (
        {}
        if case == "unknown"
        else {"prompt_tokens": 100000000 if case == "overrun" else 1, "completion_tokens": 1}
    )
    finish_one(db_engine, settings, rid, usage=usage, invalid=case == "invalid")
    with Session(db_engine) as session, session.begin():
        run = session.get(AIRun, rid)
        calls = graph.attempts(session, run)
        assert run.state == ("uncertain" if case == "unknown" else "failed")
        assert run.output is None and any(a.state == "released" for a in calls)
        used = next(a for a in calls if a.state != "released")
        assert used.state == ("uncertain" if case == "unknown" else "settled")
        if case == "overrun":
            assert (
                used.actual_cost > used.reserved_cost and used.error_code == "reservation_overrun"
            )
        unit = session.scalar(select(Usage).where(Usage.source_id == rid))
        assert unit.state == "released"


def test_midnight_stops_new_dispatch_and_releases_slots(source, db_engine, settings, monkeypatch):
    rid, _, _ = make_run(db_engine, settings, source)
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, rid)
        real = jobs.now(session)
        monkeypatch.setattr(jobs, "now", lambda session: real + timedelta(days=1))
        with pytest.raises(DomainError):
            graph.prepare(session, settings, job)
        # Recovery observes lease expiration; a new invocation fails before dispatch.
        jobs._end(session, job, "failed", "reservation_expired")
        assert all(a.state == "released" for a in graph.attempts(session, session.get(AIRun, rid)))


def test_embedded_each_invocation_has_one_call_and_atomic_completion(
    source, db_engine, settings, monkeypatch
):
    rid, _, _ = make_run(db_engine, settings, source)
    calls = []

    async def generate(config, prompt):
        calls.append(prompt)
        return answer((prompt,)), {"prompt_tokens": 0, "completion_tokens": 0}, "synthetic"

    monkeypatch.setattr(service.adapter, "generate", generate)
    database = SimpleNamespace(sessions=sessionmaker(db_engine, expire_on_commit=False))
    runner = JobRunner(database, settings)
    for expected in (1, 2):
        with database.sessions.begin() as session:
            job = claim_run(session, rid)
        asyncio.run(runner._execute(job))
        assert len(calls) == expected
        with database.sessions.begin() as session:
            assert session.get(Job, job.id).state == "succeeded"
            assert graph.view(session, source[0], source[1], rid)["completed_calls"] == expected
    # Replaying an already committed invocation cannot send or consume twice.
    with pytest.raises(DomainError):
        asyncio.run(graph.execute(database, settings, job))
    assert len(calls) == 2


def test_graph_immutability_scope_and_cardinality(source, db_engine, settings):
    rid, _, _ = make_run(db_engine, settings, source)
    with Session(db_engine) as session, session.begin():
        run = session.get(AIRun, rid)
        step = graph.steps(session, run)[0]
        attempt = session.scalar(select(AIAttempt).where(AIAttempt.step_id == step.id))
        for statement, params in [
            ("UPDATE ai_steps SET membership='{}' WHERE id=:id", {"id": step.id}),
            ("UPDATE ai_run_inputs SET role='right' WHERE run_id=:id", {"id": rid}),
            ("UPDATE ai_attempts SET step_id=NULL WHERE id=:id", {"id": attempt.id}),
            ("UPDATE ai_attempts SET reserved_cost=1 WHERE id=:id", {"id": attempt.id}),
            ("DELETE FROM ai_steps WHERE id=:id", {"id": step.id}),
            ("DELETE FROM ai_attempts WHERE id=:id", {"id": attempt.id}),
        ]:
            with pytest.raises(DBAPIError), session.begin_nested():
                session.execute(text(statement), params)
        with pytest.raises(DBAPIError), session.begin_nested():
            session.add(
                AIAttempt(
                    workspace_id=source[0],
                    run_id=rid,
                    step_id=step.id,
                    reserved_cost=0,
                    budget_day=attempt.budget_day,
                )
            )
            session.flush()


@pytest.mark.parametrize("state", ["pending", "sent", "mapped"])
def test_restore_quarantine_never_dispatches(source, db_engine, settings, state):
    rid, _, _ = make_run(db_engine, settings, source)
    if state == "mapped":
        finish_one(db_engine, settings, rid)
    with Session(db_engine) as session, session.begin():
        if state == "sent":
            graph.prepare(session, settings, claim_run(session, rid))
        graph.quarantine_restored(session)
        run = session.get(AIRun, rid)
        assert run.state == "uncertain"
        calls = graph.attempts(session, run)
        assert all(a.state in {"settled", "uncertain"} for a in calls)
        assert not graph.authorize_job(session, session.get(Job, run.job_id))
        assert any(a.error_code == "restored_work_quarantined" for a in calls)


def test_privacy_scrubs_intermediates_and_all_input_membership(source, db_engine, settings):
    rid, _, _ = make_run(db_engine, settings, source)
    finish_one(db_engine, settings, rid)
    with Session(db_engine) as session, session.begin():
        service.invalidate_sessions(session, source[0], [source[4]])
        session.flush()
        run = session.get(AIRun, rid)
        assert run.state == "invalidated" and run.coverage == {} and run.output is None
        assert not session.scalar(select(AIRunInput.id).where(AIRunInput.run_id == rid))
        assert all(s.membership == {} and s.result is None for s in graph.steps(session, run))
        assert all(a.state in {"settled", "released"} for a in graph.attempts(session, run))


def test_exact_epoch_and_consent_regrant_do_not_rebase_run(source, db_engine, settings):
    rid, _, _ = make_run(db_engine, settings, source)
    with Session(db_engine) as session, session.begin():
        session.get(Workspace, source[0]).privacy_epoch += 1
        with pytest.raises(DomainError):
            service.view(session, source[0], source[1], rid)


def test_same_key_concurrency_reserves_once(source, db_engine, settings):
    with Session(db_engine) as session, session.begin():
        body, _ = confirmed(session, settings, source)
    barrier = Barrier(2)

    def create(_):
        barrier.wait(timeout=5)
        with Session(db_engine) as session, session.begin():
            return service.create(session, settings, source[0], source[1], body)["id"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, range(2)))
    assert results[0] == results[1]
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AIAttempt)
                .where(AIAttempt.run_id == UUID(results[0]))
            )
            == 2
        )


def test_comparison_suppressed_zero_call_and_right_input_erasure(source, db_engine, settings):
    with Session(db_engine) as session, session.begin():
        left = session.get(
            __import__("app.analytics.models", fromlist=["AnalysisSnapshot"]).AnalysisSnapshot,
            source[3],
        )
        right = analytics.freeze(session, source[0], source[1], source[2], left.version_id)
        request, estimate = confirmed(
            session, settings, source, operation="comparison_report", right_snapshot_id=right.id
        )
        assert estimate["suppressed"] and estimate["planned_calls"] == 0
        result = service.create(session, settings, source[0], source[1], request)
        rid = UUID(result["id"])
        assert result["state"] == "draft" and result["planned_calls"] == 0
        assert (
            session.scalar(select(func.count()).select_from(Usage).where(Usage.source_id == rid))
            == 0
        )
        from app.privacy_ops.events import apply_event

        apply_event(session, source[0], "snapshot_delete", right.id)
        assert session.get(AIRun, rid).state == "invalidated"
        assert not session.scalar(select(AIRunInput.id).where(AIRunInput.run_id == rid))


def collaborator(session, source, capabilities):
    user = User(
        email=f"graph-{uuid4().hex}@example.test", password_hash="synthetic", verified_at=utcnow()
    )
    session.add(user)
    session.flush()
    member = Membership(workspace_id=source[0], user_id=user.id, role="researcher")
    session.add(member)
    session.flush()
    grant = StudyGrant(
        workspace_id=source[0],
        study_id=source[2],
        membership_id=member.id,
        capabilities=capabilities,
    )
    session.add(grant)
    session.flush()
    return user.id, grant


@pytest.mark.parametrize("capabilities", [["ai"], ["ai", "read"], ["raw", "read"]])
def test_text_requires_ai_and_raw_for_requester_and_reader(
    source, db_engine, settings, capabilities
):
    rid, _, _ = make_run(db_engine, settings, source)
    with Session(db_engine) as session, session.begin():
        actor, _ = collaborator(session, source, capabilities)
        with pytest.raises(DomainError):
            service.estimate(
                session,
                settings,
                source[0],
                actor,
                EstimateBody(
                    study_id=source[2],
                    snapshot_id=source[3],
                    operation="themes",
                    profile_revision="2",
                ),
            )
        with pytest.raises(DomainError):
            service.view(session, source[0], actor, rid)


def test_requester_raw_revocation_blocks_other_authorized_reader(source, db_engine, settings):
    with Session(db_engine) as session, session.begin():
        actor, grant = collaborator(session, source, ["ai", "read", "raw"])
        replacement = (source[0], actor, *source[2:])
        body, _ = confirmed(session, settings, replacement)
        rid = UUID(service.create(session, settings, source[0], actor, body)["id"])
        grant_id = grant.id
    with Session(db_engine) as session, session.begin():
        session.get(StudyGrant, grant_id).capabilities = ["ai", "read"]
        with pytest.raises(DomainError):
            service.view(session, source[0], source[1], rid)


@pytest.mark.parametrize("change", ["wrong_consent", "disabled"])
def test_current_processing_policy_stops_estimates_and_dispatch(
    source, db_engine, settings, change
):
    rid, _, _ = make_run(db_engine, settings, source)
    with Session(db_engine) as session, session.begin():
        job = claim_run(session, rid)
        if change == "wrong_consent":
            row = session.get(CollectionSession, source[4])
            receipt = session.scalar(
                select(ConsentReceipt).where(
                    ConsentReceipt.subject_id == row.subject_id,
                    ConsentReceipt.presented_digest == "b" * 64,
                )
            )
            # A later explicit denial is a real exact-version receipt, never a patched immutable record.
            session.add(
                ConsentReceipt(
                    workspace_id=source[0],
                    subject_id=row.subject_id,
                    document_id=receipt.document_id,
                    study_version_id=row.version_id,
                    decision="withdrawn",
                    presented_digest=receipt.presented_digest,
                    receipt_key=uuid4().hex,
                )
            )
        else:
            settings.ai_orchestration_enabled = False
        with pytest.raises(DomainError):
            confirmed(session, settings, source)
        with pytest.raises(DomainError):
            graph.prepare(session, settings, job)


def test_cache_bound_command_cannot_be_reused_through_revision1(source, db_engine, settings):
    rid, body, _ = make_run(db_engine, settings, source)
    finish_one(db_engine, settings, rid)
    finish_one(db_engine, settings, rid)
    with Session(db_engine) as session, session.begin():
        service.create(
            session,
            settings,
            source[0],
            source[1],
            body.model_copy(update={"command_key": "cache-bound"}),
        )
        with pytest.raises(DomainError, match="IDEMPOTENCY_CONFLICT"):
            service.create(
                session,
                settings,
                source[0],
                source[1],
                RunBody(study_id=source[2], operation="study_helper", command_key="cache-bound"),
            )


def test_whole_graph_budget_race_never_partially_reserves(source, db_engine, settings):
    settings.llm_input_price_per_million = Decimal("1")
    with Session(db_engine) as session, session.begin():
        bodies = [
            confirmed(
                session,
                settings,
                source,
                key=f"race-{i}",
                instruction=f"Synthetic {i}",
                researcher_text_approved=True,
            )[0]
            for i in range(2)
        ]
    settings.llm_study_budget = Decimal(bodies[0].max_reserved_cost) * Decimal("1.5")
    # Budget configuration is part of the confirmation, so reconfirm after the operator change.
    with Session(db_engine) as session, session.begin():
        bodies = [
            confirmed(
                session,
                settings,
                source,
                key=f"race-{i}",
                instruction=f"Synthetic {i}",
                researcher_text_approved=True,
            )[0]
            for i in range(2)
        ]
    barrier = Barrier(2)

    def create(body):
        barrier.wait(timeout=5)
        try:
            with Session(db_engine) as session, session.begin():
                return service.create(session, settings, source[0], source[1], body)["id"]
        except DomainError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, bodies))
    assert results.count("AI_BUDGET_EXHAUSTED") == 1
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count()).select_from(AIRun).where(AIRun.workspace_id == source[0])
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(AIAttempt)
                .where(AIAttempt.workspace_id == source[0])
            )
            == 2
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(Usage)
                .where(Usage.workspace_id == source[0], Usage.kind == "ai_addon")
            )
            == 1
        )


def test_downgrade_refuses_preserved_graph_history(source, db_engine, settings, monkeypatch):
    from importlib import import_module

    migration = import_module("migrations.versions.029_ai_orchestration")
    make_run(db_engine, settings, source)
    with Session(db_engine) as session, session.begin():
        monkeypatch.setattr(migration.op, "execute", lambda sql: session.execute(text(sql)))
        with (
            pytest.raises(DBAPIError, match="Revision-2 AI history exists"),
            session.begin_nested(),
        ):
            migration.downgrade()
        assert (
            session.scalar(
                select(func.count()).select_from(AIStep).where(AIStep.workspace_id == source[0])
            )
            == 2
        )


def test_held_intermediates_remain_inaccessible_then_erase(source, db_engine, settings):
    from app.privacy_ops.models import LegalHold

    rid, _, _ = make_run(db_engine, settings, source)
    finish_one(db_engine, settings, rid)
    with Session(db_engine) as session, session.begin():
        hold = LegalHold(
            workspace_id=source[0],
            subject_id=source[1],
            reason="Synthetic legal hold",
            reviewed_by=source[1],
            review_deadline=utcnow() + timedelta(days=1),
        )
        session.add(hold)
        session.flush()
        service.invalidate_sessions(session, source[0], [source[4]])
        run = session.get(AIRun, rid)
        assert graph.steps(session, run)[0].result is not None
        with pytest.raises(DomainError):
            service.view(session, source[0], source[1], rid)
        hold.released_at = utcnow()
        service._invalidate_runs(session, source[0], [run])
        assert all(
            step.result is None and not step.membership for step in graph.steps(session, run)
        )


def test_generic_job_payload_never_contains_prompts_or_answers(source, db_engine, settings):
    rid, _, _ = make_run(
        db_engine,
        settings,
        source,
        instruction="Private researcher text",
        researcher_text_approved=True,
    )
    with Session(db_engine) as session:
        run = session.get(AIRun, rid)
        job = session.get(Job, run.job_id)
        payload = json.dumps(job.payload)
        assert "Private" not in payload and "واجهة" not in payload


def test_human_only_study_cannot_enter_graph(source, db_engine, settings):
    with Session(db_engine) as session, session.begin():
        original = session.get(Study, source[2])
        study = Study(
            workspace_id=source[0],
            owner_membership_id=original.owner_membership_id,
            retention_policy_id=original.retention_policy_id,
            title="Synthetic human only",
            ai_policy="human_only",
        )
        session.add(study)
        session.flush()
        body = EstimateBody(
            study_id=study.id, snapshot_id=source[3], operation="themes", profile_revision="2"
        )
        with pytest.raises(DomainError, match="AI_DISABLED"):
            service.estimate(session, settings, source[0], source[1], body)


def test_invalidated_graph_does_not_block_next_job(source, db_engine, settings):
    rid, _, _ = make_run(db_engine, settings, source)
    with Session(db_engine) as session, session.begin():
        run = session.get(AIRun, rid)
        old_job = session.get(Job, run.job_id)
        old_job.run_after = jobs.now(session) - timedelta(days=2)
        service.invalidate_sessions(session, source[0], [source[4]])
        following = jobs.enqueue(session, workspace_id=source[0], requester_id=source[1], command_key="after-invalidated-graph", run_after=jobs.now(session) - timedelta(days=1))
        session.flush()
        assert jobs.claim(session).id == following.id
        assert old_job.state == "cancelled"
        jobs.complete(session, following.id, following.lease_token, {"status": "ok"})
