"""AI audit regressions; DB cases require the exclusive integration window."""

import asyncio
from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_ai_db import claim_run
from test_ai_db import collected as collected_fixture
from test_analytics_db import context

from app.ai import service
from app.ai.models import AIAttempt, AIRun, UsageBudget
from app.ai.schemas import RunBody
from app.common.errors import DomainError
from app.jobs import service as jobs

collected = collected_fixture


@pytest.mark.unit
def test_cancel_during_authorization_releases_late_transferred_lease(monkeypatch, settings):
    from threading import Event

    from app.common import dispatch_gate

    entered, finish, released = Event(), Event(), Event()
    lease = SimpleNamespace(release=released.set)

    @contextmanager
    def begin():
        yield object()

    def prepare(session, settings, job, dispatch=True):
        if dispatch:
            entered.set()
            assert finish.wait(3)
        return [], {}, {}

    monkeypatch.setattr(service, "prepare", prepare)
    monkeypatch.setattr(dispatch_gate, "transfer", lambda *args: lease)

    async def scenario():
        task = asyncio.create_task(
            service.execute(
                SimpleNamespace(sessions=SimpleNamespace(begin=begin)),
                settings,
                SimpleNamespace(workspace_id="synthetic"),
            )
        )
        assert await asyncio.to_thread(entered.wait, 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        finish.set()
        assert await asyncio.to_thread(released.wait, 3)

    asyncio.run(scenario())


@pytest.mark.db
def test_transferred_send_gate_blocks_mutation_commit_not_response(collected, db_engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from app.common.dispatch_gate import transfer
    from app.common.privacy import lock_workspace

    with Session(db_engine) as session:
        row, _, _ = context(session, collected[3])
        wid = row.workspace_id
    lease = None
    with Session(db_engine) as session, session.begin():
        lock_workspace(session, wid)
        lease = transfer(session, wid)
    started, committed = Event(), Event()

    def mutation():
        started.set()
        with Session(db_engine) as session, session.begin():
            workspace = lock_workspace(session, wid)
            workspace.privacy_epoch += 1
        committed.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(mutation)
        try:
            assert started.wait(3)
            assert not committed.wait(0.1)
        finally:
            # Represents body.complete, not provider response completion.
            lease.release()
        pending.result(timeout=5)
        assert committed.is_set()


@pytest.mark.db
@pytest.mark.parametrize("change", ["cancel", "restriction"])
def test_actual_cancel_after_prepare_never_calls_provider(
    collected, db_engine, settings, monkeypatch, change
):
    from threading import Event

    with Session(db_engine) as session, session.begin():
        row, study, actor = context(session, collected[3])
        wid = row.workspace_id
        result = service.create(
            session,
            settings,
            wid,
            actor,
            RunBody(study_id=study.id, operation="study_helper", command_key="dispatch-cancel"),
        )
        run_id = UUID(result["id"])
    with Session(db_engine, expire_on_commit=False) as session, session.begin():
        job = claim_run(session, run_id)
        session.expunge(job)
    ready, proceed = Event(), Event()
    calls = []

    factory = sessionmaker(db_engine, expire_on_commit=False)
    first = True

    @contextmanager
    def begin():
        nonlocal first
        with factory.begin() as session:
            yield session
        if first:
            first = False
            ready.set()
            assert proceed.wait(5)

    async def generate(*args):
        calls.append(True)
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(service.adapter, "generate", generate)

    async def scenario():
        task = asyncio.create_task(
            service.execute(SimpleNamespace(sessions=SimpleNamespace(begin=begin)), settings, job)
        )
        try:
            assert await asyncio.to_thread(ready.wait, 5)

            def cancel():
                with factory.begin() as session:
                    if change == "cancel":
                        jobs.cancel(session, workspace_id=wid, user_id=actor, job_id=job.id)
                    else:
                        from app.common.privacy import lock_workspace
                        from app.common.privacy_models import PrivacyRestriction

                        lock_workspace(session, wid)
                        session.add(PrivacyRestriction(workspace_id=wid, subject_id=actor))

            await asyncio.to_thread(cancel)
        finally:
            proceed.set()
        with pytest.raises(DomainError):
            await task
        assert calls == []

    asyncio.run(scenario())
    with factory.begin() as session:
        run = session.get(AIRun, run_id)
        attempt = service.attempt_for(session, run)
        if change == "cancel":
            assert attempt.state == "released"
            assert attempt.error_code == "never_dispatched"
        else:
            assert attempt.state == "reserved"


@pytest.mark.unit
def test_real_http_transport_releases_gate_before_response():
    import tempfile

    import httpx2

    from app.ai import adapter
    from app.common.dispatch_gate import Lease, _Bucket

    async def scenario():
        received, respond = asyncio.Event(), asyncio.Event()

        async def server(reader, writer):
            headers = await reader.readuntil(b"\r\n\r\n")
            length = next(
                int(line.split(b":", 1)[1])
                for line in headers.split(b"\r\n")
                if line.lower().startswith(b"content-length:")
            )
            assert await reader.readexactly(length) == b"synthetic-private-source"
            received.set()
            await respond.wait()
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        directory = tempfile.TemporaryDirectory(dir="/tmp", prefix="ai-")
        socket_path = directory.name + "/provider.sock"
        listener = await asyncio.start_unix_server(server, socket_path)
        bucket = _Bucket()
        bucket.lock.acquire()
        lease = Lease(bucket)
        token = adapter.dispatch_lease.set(lease)
        try:
            async with httpx2.AsyncClient(
                trust_env=False,
                http2=False,
                transport=httpx2.AsyncHTTPTransport(uds=socket_path),
                event_hooks={"request": [adapter._dispatch_request_hook]},
            ) as client:
                sending = asyncio.create_task(
                    client.post("http://synthetic.invalid/", content=b"synthetic-private-source")
                )
                await asyncio.wait_for(received.wait(), 3)
                assert not sending.done()  # provider response is deliberately withheld
                assert lease.released
                assert bucket.lock.acquire(blocking=False)
                bucket.lock.release()
                respond.set()
                assert (await sending).status_code == 200
        finally:
            respond.set()
            lease.release()
            adapter.dispatch_lease.reset(token)
            listener.close()
            await listener.wait_closed()
            directory.cleanup()

    asyncio.run(scenario())


@pytest.mark.unit
def test_transport_gate_releases_body_not_headers():
    import httpx2

    from app.ai import adapter

    released = []

    async def scenario():
        token = adapter.dispatch_lease.set(SimpleNamespace(release=lambda: released.append(True)))
        try:
            request = httpx2.Request("POST", "https://synthetic.invalid", content=b"private")
            await adapter._dispatch_request_hook(request)
            trace = request.extensions["trace"]
            await trace("http11.send_request_headers.complete", {})
            assert not released
            await trace("http11.send_request_body.started", {})
            assert not released
            await trace("http11.send_request_body.complete", {})
            assert released == [True]
        finally:
            adapter.dispatch_lease.reset(token)

    asyncio.run(scenario())


@pytest.mark.unit
@pytest.mark.parametrize("reason", ["revoked", "cancelled"])
def test_change_after_prepare_prevents_provider_call(monkeypatch, settings, reason):
    from threading import Event

    prepared, changed = Event(), Event()
    calls = []

    @contextmanager
    def begin():
        yield object()

    def prepare(session, settings, job, dispatch=True):
        if not dispatch:
            prepared.set()
            assert changed.wait(3)
            return [], {}, {}
        assert changed.is_set()
        raise DomainError("AI_UNAVAILABLE", reason, 409)

    async def generate(*args):
        calls.append(True)

    monkeypatch.setattr(service, "prepare", prepare)
    monkeypatch.setattr(service.adapter, "generate", generate)

    async def scenario():
        task = asyncio.create_task(
            service.execute(
                SimpleNamespace(sessions=SimpleNamespace(begin=begin)), settings, object()
            )
        )
        assert await asyncio.to_thread(prepared.wait, 3)
        changed.set()
        with pytest.raises(DomainError):
            await task
        assert calls == []

    asyncio.run(scenario())


@pytest.mark.unit
@pytest.mark.parametrize("state,expected", [("reserved", "released"), ("sent", "uncertain")])
def test_failure_only_labels_provably_unsent_as_replaceable(monkeypatch, state, expected):
    from app.billing import service as billing

    attempt = SimpleNamespace(state=state, error_code=None, usage=None)
    run = SimpleNamespace(workspace_id="w", id="r", state="running")
    monkeypatch.setattr(service, "lock_workspace", lambda *args: None)
    monkeypatch.setattr(service, "attempt_for", lambda *args: attempt)
    monkeypatch.setattr(billing, "release_ai_addon", lambda *args: None)
    settlements = []
    monkeypatch.setattr(service, "settle", lambda *args: settlements.append(args[-1]))
    service.fail_job(
        SimpleNamespace(get=lambda *args: run), SimpleNamespace(kind="ai.generate", target_id="r")
    )
    assert attempt.state == expected
    assert settlements == ([Decimal(0)] if state == "reserved" else [])
    assert attempt.error_code == ("never_dispatched" if state == "reserved" else None)
    assert attempt.usage == ({"retry_after_seconds": 0} if state == "reserved" else None)


@pytest.mark.db
def test_cancel_unsent_allows_one_immediate_priced_replacement(collected, db_engine, settings):
    settings.llm_input_price_per_million = Decimal("1")
    settings.llm_output_price_per_million = Decimal("2")
    with Session(db_engine) as session, session.begin():
        row, study, actor = context(session, collected[3])
        wid = row.workspace_id
        body = RunBody(study_id=study.id, operation="study_helper", command_key="cancel-first")
        first = service.create(session, settings, wid, actor, body)
        run = session.get(AIRun, UUID(first["id"]))
        attempt = service.attempt_for(session, run)
        amount = attempt.reserved_cost
        assert amount > 0
        jobs.cancel(session, workspace_id=wid, user_id=actor, job_id=run.job_id)
        assert attempt.state == "released"
        assert attempt.error_code == "never_dispatched"
        assert attempt.usage == {"retry_after_seconds": 0}
        assert attempt.actual_cost == 0
        second = service.create(
            session, settings, wid, actor, body.model_copy(update={"command_key": "cancel-second"})
        )
        assert second["id"] != first["id"]
        replacement = session.get(AIRun, UUID(second["id"]))
        assert service.attempt_for(session, replacement).reserved_cost == amount
        ledger = session.scalars(select(UsageBudget).where(UsageBudget.workspace_id == wid)).all()
        assert len(ledger) == 2
        assert all(b.reserved == amount and b.spent == 0 for b in ledger)
        jobs.cancel(session, workspace_id=wid, user_id=actor, job_id=replacement.job_id)
        assert all(b.reserved == 0 and b.spent == 0 for b in ledger)
    with Session(db_engine) as session, session.begin():
        with pytest.raises(DomainError) as error:
            service.create(
                session,
                settings,
                wid,
                actor,
                body.model_copy(update={"command_key": "cancel-third"}),
            )
        assert error.value.code == "AI_RETRY_BLOCKED"
        assert (
            len(session.scalars(select(AIAttempt).where(AIAttempt.workspace_id == wid)).all()) == 2
        )
