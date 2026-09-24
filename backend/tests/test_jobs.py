import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.auth.models import Membership, User, Workspace
from app.common.errors import DomainError
from app.db import AppMetadata
from app.jobs import service
from app.jobs.models import Job, JobAttempt
from app.jobs.runner import JobRunner


@pytest.fixture
def scope(db_engine):
    sessions = sessionmaker(db_engine, expire_on_commit=False)
    uid, wid = uuid4(), uuid4()
    with sessions.begin() as s:
        s.add(
            User(
                id=uid,
                email=f"{uid}@example.test",
                password_hash="synthetic",
                verified_at=datetime.now(UTC),
            )
        )
        s.add(Workspace(id=wid, name="Synthetic jobs"))
        s.flush()
        s.add(Membership(user_id=uid, workspace_id=wid, role="owner"))
    yield sessions, uid, wid
    # Isolate claim tests from other tests without destructive global resets.
    with sessions.begin() as s:
        for job in s.scalars(select(Job).where(Job.workspace_id == wid)):
            if job.state in {"pending", "running"}:
                job.state = "cancelled"


def queued(scope, **kwargs):
    sessions, uid, wid = scope
    with sessions.begin() as s:
        return service.enqueue(
            s,
            requester_id=uid,
            workspace_id=wid,
            command_key=kwargs.pop("command_key", str(uuid4())),
            **kwargs,
        ).id


def claimed(scope):
    with scope[0].begin() as s:
        return service.claim(s)


@pytest.mark.db
def test_enqueue_atomic_and_duplicate_conflict(scope):
    sessions, uid, wid = scope
    with sessions() as s:
        job = service.enqueue(s, workspace_id=wid, requester_id=uid, command_key="rollback")
        jid = job.id
        s.rollback()
    with sessions() as s:
        assert s.get(Job, jid) is None
    jid = queued(scope, command_key="same")
    assert queued(scope, command_key="same") == jid
    with pytest.raises(DomainError):
        queued(scope, command_key="same", target_id=uuid4())


@pytest.mark.db
def test_concurrent_command_key(scope):
    with ThreadPoolExecutor(2) as pool:
        ids = list(pool.map(lambda _: queued(scope, command_key="race"), range(2)))
    assert ids[0] == ids[1]


@pytest.mark.db
def test_skip_locked_fifo_and_future(scope):
    first = queued(scope, run_after=datetime.now(UTC) - timedelta(seconds=20))
    second = queued(scope, run_after=datetime.now(UTC) - timedelta(seconds=10))
    queued(scope, run_after=datetime.now(UTC) + timedelta(hours=1))
    with scope[0]() as a, a.begin():
        assert service.claim(a).id == first
        with scope[0]() as b, b.begin():
            assert service.claim(b).id == second
    assert claimed(scope) is None


@pytest.mark.db
def test_completion_fencing_and_atomic_side_effect(scope):
    jid = queued(scope)
    job = claimed(scope)
    key = f"job-{jid}"

    def effect(s, _):
        s.add(AppMetadata(key=key, value={"synthetic": True}, is_synthetic=True))

    with scope[0]() as s:
        assert not service.complete(s, jid, uuid4(), {"status": "ok"}, effect)
        assert service.complete(s, jid, job.lease_token, {"status": "ok"}, effect)
        s.flush()
        s.rollback()
    with scope[0].begin() as s:
        assert s.get(AppMetadata, key) is None
        assert s.get(Job, jid).state == "running"
        assert service.complete(s, jid, job.lease_token, {"status": "ok"}, effect)
    with scope[0]() as s:
        assert s.get(AppMetadata, key)
        assert s.get(Job, jid).state == "succeeded"
        assert s.scalar(select(JobAttempt).where(JobAttempt.job_id == jid)).outcome == "succeeded"


@pytest.mark.db
@pytest.mark.parametrize("mutation", ["revoke", "suspend", "disable", "epoch", "role"])
@pytest.mark.parametrize("phase", ["claim", "complete"])
def test_authority_rechecked(scope, mutation, phase):
    sessions, uid, wid = scope
    jid = queued(scope)
    job = claimed(scope) if phase == "complete" else None
    with sessions.begin() as s:
        if mutation == "suspend":
            s.get(Workspace, wid).status = "suspended"
        elif mutation == "epoch":
            s.get(Workspace, wid).privacy_epoch += 1
        elif mutation == "disable":
            s.get(User, uid).status = "disabled"
        else:
            member = s.scalar(select(Membership).where(Membership.workspace_id == wid))
            if mutation == "role":
                member.role = "viewer"
            else:
                member.status = "revoked"
    with sessions.begin() as s:
        if job:
            assert not service.complete(s, jid, job.lease_token, {"status": "ok"})
        else:
            assert service.claim(s) is None
    with sessions() as s:
        assert s.get(Job, jid).state == "cancelled"


@pytest.mark.db
@pytest.mark.parametrize(
    "safe,max_attempts,expected",
    [(True, 3, "pending"), (True, 1, "failed"), (False, 3, "uncertain")],
)
def test_expired_lease(scope, safe, max_attempts, expected):
    jid = queued(scope, max_attempts=max_attempts)
    job = claimed(scope)
    with scope[0].begin() as s:
        row = s.get(Job, jid)
        row.replay_safe = safe
        row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with scope[0].begin() as s:
        assert not service.heartbeat(s, jid, job.lease_token)
        service.recover_expired(s)
        s.flush()
        assert s.get(Job, jid).state == expected
        if expected == "pending":
            assert service.claim(s) is None  # backoff, not an immediate retry
            s.get(Job, jid).run_after = datetime.now(UTC) - timedelta(seconds=1)
    if expected == "pending":
        fresh = claimed(scope)
        assert fresh.lease_token != job.lease_token
        with scope[0].begin() as s:
            assert not service.complete(s, jid, job.lease_token, {"status": "ok"})
            assert service.complete(s, jid, fresh.lease_token, {"status": "ok"})


@pytest.mark.db
def test_cancel_fences_worker(scope):
    sessions, uid, wid = scope
    jid = queued(scope)
    job = claimed(scope)
    with sessions.begin() as s:
        assert service.cancel(s, workspace_id=wid, user_id=uid, job_id=jid).state == "cancelled"
    with sessions.begin() as s:
        assert not service.complete(s, jid, job.lease_token, {"status": "ok"})


@pytest.mark.db
def test_unknown_handler_and_sanitized_error(scope):
    jid = queued(scope)
    with scope[0].begin() as s:
        s.get(Job, jid).kind = "not.allowed"
    assert claimed(scope) is None
    with scope[0]() as s:
        assert s.get(Job, jid).error_code == "unknown_handler"
    jid = queued(scope)
    job = claimed(scope)
    with scope[0].begin() as s:
        service.fail(s, jid, job.lease_token, "SECRET PII", False)
    with scope[0]() as s:
        assert s.get(Job, jid).error_code == "handler_error"


@pytest.mark.db
@pytest.mark.parametrize("role", ["viewer", "reviewer"])
def test_read_only_members_cannot_enqueue(scope, role):
    sessions, uid, wid = scope
    jid = queued(scope)
    with sessions.begin() as s:
        s.scalar(select(Membership).where(Membership.workspace_id == wid)).role = role
    with sessions() as s:
        assert service.get_job(s, wid, uid, jid).id == jid
        with pytest.raises(DomainError):
            service.enqueue(s, workspace_id=wid, requester_id=uid, command_key="forbidden")


@pytest.mark.unit
def test_strict_request_payload():
    from pydantic import ValidationError

    from app.jobs.router import JobCreate

    for body in [
        {"command_key": "x", "extra": 1},
        {"command_key": "x", "payload": {"email": "pii"}},
        {"command_key": 1},
        {"command_key": "x", "kind": "payments.send"},
    ]:
        with pytest.raises(ValidationError):
            JobCreate.model_validate(body)


@pytest.mark.db
def test_runner_timeout_is_bounded(scope, monkeypatch):
    async def hang(_):
        await asyncio.Event().wait()

    monkeypatch.setitem(service.REGISTRY, "system.check", (hang, True))
    jid = queued(scope, max_attempts=1)
    runner = JobRunner(
        SimpleNamespace(sessions=scope[0]),
        SimpleNamespace(job_poll_seconds=0.05, job_timeout_seconds=0.1, job_shutdown_seconds=0.1),
    )

    async def exercise():
        await runner.start()
        await asyncio.sleep(0.5)
        await runner.stop()

    asyncio.run(exercise())
    with scope[0]() as s:
        assert s.get(Job, jid).state == "failed"
        assert s.get(Job, jid).error_code == "handler_timeout"


@pytest.mark.unit
def test_runner_error_poll_and_shutdown(monkeypatch):
    runner = JobRunner(None, SimpleNamespace(job_poll_seconds=0.05, job_shutdown_seconds=0.05))
    calls = []

    async def broken(*args):
        calls.append(1)
        raise RuntimeError("synthetic")

    monkeypatch.setattr(runner, "_db", broken)

    async def exercise():
        await runner.start()
        await asyncio.sleep(0.18)
        await runner.stop()
        assert runner._task.done()

    asyncio.run(exercise())
    assert 1 <= len(calls) <= 5


@pytest.mark.db
def test_retry_exhaustion_and_attempt_history(scope):
    jid = queued(scope, max_attempts=2)
    for number in (1, 2):
        job = claimed(scope)
        assert job.attempt_count == number
        with scope[0].begin() as s:
            assert service.fail(s, jid, job.lease_token, "handler_timeout", True)
        with scope[0].begin() as s:
            row = s.get(Job, jid)
            assert row.state == ("pending" if number == 1 else "failed")
            row.run_after = datetime.now(UTC) - timedelta(seconds=1)
    with scope[0]() as s:
        assert len(s.scalars(select(JobAttempt).where(JobAttempt.job_id == jid)).all()) == 2
    assert claimed(scope) is None


@pytest.mark.db
def test_reader_cannot_access_other_requesters_job(scope):
    sessions, _, wid = scope
    jid = queued(scope)
    other = uuid4()
    with sessions.begin() as s:
        s.add(
            User(
                id=other,
                email=f"{other}@example.test",
                password_hash="synthetic",
                verified_at=datetime.now(UTC),
            )
        )
        s.flush()
        s.add(Membership(workspace_id=wid, user_id=other, role="researcher"))
    with sessions() as s:
        assert service.list_jobs(s, wid, other) == []
        with pytest.raises(DomainError):
            service.get_job(s, wid, other, jid)
        with pytest.raises(DomainError):
            service.cancel(s, workspace_id=wid, user_id=other, job_id=jid)


@pytest.mark.db
def test_runner_success(scope):
    jid = queued(scope)
    runner = JobRunner(SimpleNamespace(sessions=scope[0]), SimpleNamespace(job_poll_seconds=0.05))

    async def exercise():
        await runner.start()
        await asyncio.sleep(0.4)
        await runner.stop()

    asyncio.run(exercise())
    with scope[0]() as s:
        assert s.get(Job, jid).state == "succeeded"


@pytest.mark.unit
def test_shutdown_bounded_with_hung_handler(monkeypatch):
    runner = JobRunner(None, SimpleNamespace(job_shutdown_seconds=0.05))
    job = SimpleNamespace(id=uuid4(), kind="system.check", payload={}, lease_token=uuid4())
    started = None

    async def hang(_):
        started.set()
        await asyncio.Event().wait()

    async def db(*args):
        return job

    monkeypatch.setitem(service.REGISTRY, "system.check", (hang, True))
    monkeypatch.setattr(runner, "_db", db)

    async def exercise():
        nonlocal started
        started = asyncio.Event()
        await runner.start()
        await started.wait()
        await asyncio.wait_for(runner.stop(), timeout=0.3)
        assert runner._task.done()

    asyncio.run(exercise())


@pytest.mark.db
def test_jobs_migration_downgrade_upgrade(db_engine):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    path = Path(__file__).resolve().parents[1] / "migrations/versions/003_jobs.py"
    spec = importlib.util.spec_from_file_location("jobs_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    # Later collection/research rows reference durable jobs. Unwind them first,
    # just as Alembic does, instead of dropping an ancestor beneath live children.
    collection_path = path.parent / "007_collection.py"
    collection_spec = importlib.util.spec_from_file_location(
        "collection_migration", collection_path
    )
    collection_migration = importlib.util.module_from_spec(collection_spec)
    collection_spec.loader.exec_module(collection_migration)
    descendants = []
    for name in (
        "008_reviews",
        "009_analytics",
        "010_ai",
        "011_methods",
        "012_longitudinal",
        "013_evaluation",
        "014_templates",
        "015_billing",
        "016_collaboration",
        "017_privacy_ops",
        "018_billing_allowances",
        "019_privacy_events",
        "020_review_access",
        "021_privacy_lifecycle",
        "022_account_erasure",
    ):
        descendant_spec = importlib.util.spec_from_file_location(name, path.parent / f"{name}.py")
        descendant = importlib.util.module_from_spec(descendant_spec)
        descendant_spec.loader.exec_module(descendant)
        descendants.append(descendant)
    # Transactional DDL: rollback restores original data, even if an assertion fails.
    with db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Operations.context(MigrationContext.configure(connection)):
                for descendant in reversed(descendants):
                    descendant.downgrade()
                collection_migration.downgrade()
                migration.downgrade()
                assert not inspect(connection).has_table("jobs")
                assert not inspect(connection).has_table("idempotency_records")
                migration.upgrade()
                assert inspect(connection).has_table("job_attempts")
                assert inspect(connection).has_table("idempotency_records")
                collection_migration.upgrade()
                for descendant in descendants:
                    descendant.upgrade()
        finally:
            transaction.rollback()


@pytest.mark.unit
@pytest.mark.parametrize("suppress", [False, True])
def test_runner_drains_cancellation_and_quarantines(suppress, monkeypatch):
    runner = JobRunner(
        None,
        SimpleNamespace(job_timeout_seconds=0.05, job_shutdown_seconds=0.05, job_poll_seconds=0.05),
    )
    calls = []
    job = SimpleNamespace(id=uuid4(), kind="system.check", payload={}, lease_token=uuid4())

    async def exercise():
        release = asyncio.Event()
        errors = []
        loop = asyncio.get_running_loop()
        previous = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: errors.append(context))

        async def handler(_):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                if suppress:
                    await release.wait()
                raise RuntimeError("synthetic cancellation cleanup failure") from None

        async def db(function, *args):
            calls.append(function)
            if function is service.claim:
                return job if calls.count(service.claim) == 1 else None
            return True

        monkeypatch.setitem(service.REGISTRY, "system.check", (handler, True))
        monkeypatch.setattr(runner, "_db", db)
        try:
            await runner.start()
            await asyncio.sleep(0.25)
            if suppress:
                assert runner._quarantined
                assert runner._handler is not None and not runner._handler.done()
                assert service.fail not in calls
                assert calls.count(service.claim) == 1
                old_task = runner._task
                await runner.start()
                assert runner._task is old_task
            else:
                assert service.fail in calls
                assert runner._handler is None
            await runner.stop()
            release.set()
            if runner._handler:
                await asyncio.wait({runner._handler}, timeout=0.1)
            await asyncio.sleep(0)
            assert not errors
        finally:
            release.set()
            loop.set_exception_handler(previous)

    asyncio.run(exercise())
