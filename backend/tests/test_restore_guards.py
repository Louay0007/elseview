"""Restore quarantine boundaries exercise actual API middleware and worker loop."""

import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine

from app.jobs.runner import JobRunner
from app.main import create_app
from app.privacy_ops.restore import restore_ready


def test_api_routes_fail_closed_before_restore_replay(settings, tmp_path):
    config = settings.model_copy(
        update={
            "database_url": SecretStr(
                "postgresql+psycopg://tester:synthetic@localhost/drill_restore"
            ),
            "private_root": tmp_path.resolve() / "files_restore",
        }
    )
    app = create_app(config)
    # No DB connection or readiness stub: absent physical marker is enough to
    # quarantine even unauthenticated API requests before route handling.
    with TestClient(app) as client:
        for path in ("/health/ready", "/api/v1/templates", "/api/v1/auth/me"):
            result = client.get(path)
            assert result.status_code == 503
            assert "RESTORE_QUARANTINED" in result.text


def test_worker_does_not_claim_jobs_until_restore_is_ready(settings, tmp_path, monkeypatch):
    from app.privacy_ops import restore

    engine = create_engine("postgresql+psycopg://tester:synthetic@localhost/drill_restore")
    config = settings.model_copy(update={"private_root": tmp_path.resolve() / "files_restore"})
    runner = JobRunner(SimpleNamespace(engine=engine), config)
    calls = []

    async def exercise():
        async def claim(*args, **kwargs):
            calls.append("claim")
            runner._stop.set()
            return None

        monkeypatch.setattr(runner, "_db", claim)
        checked = asyncio.Event()
        loop = asyncio.get_running_loop()

        def quarantine(*args):
            result = restore_ready(*args)
            assert result is False
            loop.call_soon_threadsafe(checked.set)
            return result

        monkeypatch.setattr(restore, "restore_ready", quarantine)
        await runner.start()
        await asyncio.wait_for(checked.wait(), timeout=2)
        await runner.stop()
        assert calls == []
        # Same worker loop resumes claiming only after readiness succeeds.
        monkeypatch.setattr(restore, "restore_ready", lambda *args: True)
        await runner.start()
        await asyncio.wait_for(runner._task, timeout=2)
        assert calls == ["claim"]

    try:
        asyncio.run(exercise())
    finally:
        engine.dispose()
