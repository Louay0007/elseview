import asyncio
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.auth import outbox
from app.jobs import service
from app.jobs.runner import JobRunner


@pytest.mark.parametrize("queue", ["auth", "notification"])
@pytest.mark.parametrize("stop_early", [False, True])
def test_physical_mail_survives_timeout_stop_and_cannot_overlap(monkeypatch, stop_early, queue):
    started, release = Event(), Event()
    calls = []

    def blocking(*args):
        calls.append(1)
        started.set()
        assert release.wait(5)
        return True

    from app.collaboration import mail

    monkeypatch.setattr(outbox if queue == "auth" else mail, "dispatch_one", blocking)
    runner = JobRunner(
        None,
        SimpleNamespace(
            mail_mode="local",
            job_timeout_seconds=0.05 if not stop_early else 10,
            job_shutdown_seconds=0.05,
            job_poll_seconds=0.05,
        ),
    )
    runner._prefer_notification = queue == "notification"

    async def exercise():
        try:
            await runner.start()
            for _ in range(100):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            assert started.is_set()
            if not stop_early:
                await asyncio.sleep(0.15)
            await asyncio.wait_for(runner.stop(), 0.5)
            assert runner._quarantined
            assert runner._mail is not None and not runner._mail.done()
            old = runner._task
            await runner.start()
            assert runner._task is old and calls == [1]
            release.set()
            await runner.drain_mail()
            await runner.start()
            assert runner._task is old and calls == [1]
        finally:
            release.set()
            await runner.drain_mail()

    asyncio.run(exercise())


def test_timed_out_physical_privacy_job_also_fences_mail(monkeypatch):
    started, release = Event(), Event()
    calls = []

    def blocking(*args):
        started.set()
        assert release.wait(5)
        return {}

    runner = JobRunner(
        None, SimpleNamespace(mail_mode="local", job_timeout_seconds=0.05, job_poll_seconds=0.05)
    )
    runner._prefer_mail = False
    job = SimpleNamespace(kind="privacy.erase", id=uuid4(), lease_token=uuid4())

    async def db(*args):
        return job

    monkeypatch.setattr(runner, "_db", db)
    monkeypatch.setitem(service.REGISTRY, "privacy.erase", (blocking, True))
    monkeypatch.setattr(outbox, "dispatch_one", lambda *args: calls.append(1))

    async def exercise():
        try:
            await runner.start()
            for _ in range(100):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            assert started.is_set()
            await asyncio.sleep(0.15)
            await runner.stop()
            assert runner._quarantined
            assert not runner._handler.done()
            assert not calls
        finally:
            release.set()
            await runner.drain_mail()

    asyncio.run(exercise())


def test_queue_preference_alternates_and_empty_falls_back(monkeypatch):
    runner = JobRunner(None, SimpleNamespace())
    calls = []

    async def mail():
        calls.append("mail")
        return True

    async def claim(fn, *args):
        assert fn is service.claim
        calls.append("claim")
        return SimpleNamespace(id=uuid4())

    async def execute(job):
        calls.append("job")

    monkeypatch.setattr(runner, "_dispatch_mail", mail)
    monkeypatch.setattr(runner, "_db", claim)
    monkeypatch.setattr(runner, "_execute", execute)

    async def exercise():
        await runner._work()
        await runner._work()
        await runner._work()
        assert calls == ["mail", "claim", "job", "mail"]
        calls.clear()

        async def empty(*args):
            calls.append("empty")
            return None

        monkeypatch.setattr(runner, "_db", empty)
        await runner._work()
        assert calls == ["empty", "mail"]
        calls.clear()

        async def no_mail():
            calls.append("no-mail")
            return False

        monkeypatch.setattr(runner, "_dispatch_mail", no_mail)
        monkeypatch.setattr(runner, "_db", claim)
        await runner._work()
        assert calls == ["no-mail", "claim", "job"]

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "env,mode,enabled",
    [("production", "smtp", True), ("test", "local", True), ("test", "disabled", False)],
)
def test_immediate_dispatch_never_races_worker(monkeypatch, env, mode, enabled):
    calls = []
    monkeypatch.setattr(outbox, "dispatch_one", lambda *args: calls.append(1))
    outbox.dispatch_local(
        None,
        SimpleNamespace(app_env=env, mail_mode=mode, job_runner_enabled=enabled),
        uuid4(),
        None,
    )
    assert not calls


def test_restore_readiness_gates_both_queues(monkeypatch):
    from app.privacy_ops import restore

    calls = []
    runner = JobRunner(
        SimpleNamespace(engine=object()),
        SimpleNamespace(private_root="unused", job_poll_seconds=0.05),
    )
    monkeypatch.setattr(restore, "restore_ready", lambda *args: False)

    async def work():
        calls.append(1)

    monkeypatch.setattr(runner, "_work", work)

    async def exercise():
        await runner.start()
        await asyncio.sleep(0.12)
        await runner.stop()

    asyncio.run(exercise())
    assert not calls
