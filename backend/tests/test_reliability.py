"""Local single-process benchmark, not a production capacity or restart claim."""

import asyncio
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_analytics_db import context
from test_collection_db import collected as collection_fixture

from app.ai import service as ai
from app.ai.schemas import RunBody
from app.collection.models import AnswerRevision, CollectionSession
from app.common.errors import DomainError
from app.common.private_storage import PrivateStorage
from app.jobs.models import Job
from app.jobs.runner import JobRunner
from app.reliability_probe import (
    hardware,
    peak_rss_bytes,
    percentile,
    validate_load_environment,
    write_metrics,
)


def test_low_disk_guard_recovers_without_partial_file(tmp_path, monkeypatch):
    storage = PrivateStorage(tmp_path, minimum_free=32)
    key = uuid4().hex
    with monkeypatch.context() as patch:
        patch.setattr(
            "app.common.private_storage.shutil.disk_usage", lambda _: SimpleNamespace(free=32)
        )
        with pytest.raises(DomainError) as error:
            storage.create(key, 1)
        assert error.value.code == "STORAGE_FULL"
        assert not (tmp_path / "assets" / key).exists()
    descriptor = storage.create(key, 1)
    os.write(descriptor, b"x")
    os.close(descriptor)
    assert storage.read(key, 1) == b"x"
    storage.delete(key)


def test_percentiles_are_nearest_rank():
    assert percentile([4, 1, 3, 2], 50) == 2
    assert percentile(list(range(1, 101)), 95) == 95


@pytest.fixture
def load_context(request, monkeypatch):
    # Gate before requesting any fixture that migrates or connects to PostgreSQL.
    if os.environ.get("TEST_ALLOW_LOAD") != "1":
        pytest.skip("Explicit TEST_ALLOW_LOAD=1 required")
    _, output = validate_load_environment()
    research_app = request.getfixturevalue("research_app")
    db_engine = request.getfixturevalue("db_engine")
    client = research_app[0]
    original = client.post

    def assisted(url, **kwargs):
        if url.endswith("/studies"):
            kwargs["json"] = kwargs["json"] | {"ai_policy": "assisted"}
        return original(url, **kwargs)

    monkeypatch.setattr(client, "post", assisted)
    fixtures = [collection_fixture.__wrapped__(research_app, db_engine, request) for _ in range(4)]
    return research_app, fixtures, output


@pytest.mark.db
@pytest.mark.load
def test_parallel_autosaves_during_blocked_mock_inference(load_context, monkeypatch):
    (client, app, _), fixtures, output = load_context
    database = app.state.database
    sessions = database.sessions
    settings = app.state.settings.model_copy(
        update={
            "job_poll_seconds": 0.05,
            "job_timeout_seconds": 90,
            "job_shutdown_seconds": 2,
        }
    )
    entered, release = threading.Event(), threading.Event()
    original_generate = ai.adapter.generate
    delay = []

    async def blocked_generate(config, prompt):
        assert config.ai_mode == "mock"
        start = time.perf_counter()
        entered.set()
        while not release.is_set():
            await asyncio.sleep(0.01)
        delay.append(time.perf_counter() - start)
        return await original_generate(config, prompt)

    monkeypatch.setattr(ai.adapter, "generate", blocked_generate)
    with sessions.begin() as session:
        row, study, actor = context(session, fixtures[0][3])
        view = ai.create(
            session,
            settings,
            row.workspace_id,
            actor,
            RunBody(study_id=study.id, operation="study_helper", command_key="p18"),
        )
        ai_job_id = UUID(view["job_id"])
    runner = JobRunner(database, settings)
    latencies, payload_sizes, queue_ages, pool_samples = [], [], [], []
    barrier = threading.Barrier(4, timeout=10)
    rss_before = peak_rss_bytes()
    start = time.perf_counter()
    client.portal.call(runner.start)
    try:
        assert entered.wait(15), "mock inference did not start"

        def writer(fixture):
            _, url, headers, result, _, _ = fixture
            barrier.wait()
            for revision in range(12):
                body = {
                    "schema_version": 1,
                    "expected_revision": revision,
                    "client_event_id": str(uuid4()),
                    "status": "responded",
                    "value": {"option_id": "no"},
                }
                tick = time.perf_counter()
                response = client.put(url + "/answers/single", headers=headers, json=body)
                elapsed = (time.perf_counter() - tick) * 1000
                assert response.status_code == 200
                latencies.append(elapsed)
                payload_sizes.append(len(response.request.content))
            body = {"version_id": result["version_id"], "expected_revision": 12}
            first = client.post(url + "/submit", headers=headers, json=body)
            assert first.status_code == 200
            assert client.post(url + "/submit", headers=headers, json=body).json() == first.json()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(writer, fixture) for fixture in fixtures]
            while not all(future.done() for future in futures):
                pool = database.engine.pool
                pool_samples.append(
                    {
                        "checked_out": pool.checkedout(),
                        "checked_in": pool.checkedin(),
                        "size": pool.size(),
                        "overflow": pool.overflow(),
                    }
                )
                with sessions() as session:
                    age = session.scalar(
                        select(func.extract("epoch", func.now() - Job.created_at)).where(
                            Job.id == ai_job_id
                        )
                    )
                    queue_ages.append(float(age))
                time.sleep(0.02)
            for future in futures:
                future.result()
        assert not release.is_set() and not delay
        duration = time.perf_counter() - start
    finally:
        release.set()
        client.portal.call(runner.stop)
    with sessions() as session:
        for fixture in fixtures:
            sid = UUID(fixture[3]["session_id"])
            row = session.get(CollectionSession, sid)
            assert row.submitted_snapshot is not None
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(AnswerRevision)
                    .where(AnswerRevision.session_id == sid)
                )
                == 12
            )
            assert (
                session.scalar(select(func.count()).select_from(Job).where(Job.target_id == sid))
                == 1
            )
        assert session.get(Job, ai_job_id).state == "succeeded"
    write_metrics(
        output,
        {
            "schema_version": 1,
            "hardware": hardware(),
            "topology": "one Python process; TestClient ASGI portal + embedded runner on same event loop; real PostgreSQL; local rate limiter; no HTTP socket or Valkey",
            "concurrency": 4,
            "writes_per_session": 12,
            "accepted_writes": len(latencies),
            "accepted_submissions": 4,
            "duration_seconds": duration,
            "autosave_latency_ms": {
                "p50": percentile(latencies, 50),
                "p95": percentile(latencies, 95),
            },
            "payload_bytes": {"min": min(payload_sizes), "max": max(payload_sizes)},
            "mock_inference_blocked_seconds": delay[0],
            "ai_job_created_age_seconds_max": max(queue_ages),
            "queue_age_scope": "created age of the single running AI job, includes execution wait",
            "pool_samples": pool_samples,
            "rss_peak_before_bytes": rss_before,
            "rss_peak_after_bytes": peak_rss_bytes(),
            "memory_scope": "process lifetime high-water RSS, includes fixtures/client, excludes PostgreSQL",
        },
    )


def test_job_poll_exception_is_sanitized_and_recovers(monkeypatch, caplog):
    runner = JobRunner(SimpleNamespace(), SimpleNamespace(job_poll_seconds=0.05))
    attempts = []

    async def transient(*args):
        attempts.append(time.perf_counter())
        if len(attempts) == 1:
            raise RuntimeError("synthetic-private-detail")
        runner._stop.set()
        return None

    monkeypatch.setattr(runner, "_db", transient)

    async def exercise():
        await runner.start()
        await asyncio.wait_for(runner._task, timeout=2)
        await runner.stop()

    asyncio.run(exercise())
    assert len(attempts) == 2
    assert attempts[1] - attempts[0] >= 0.04
    assert "Job runner operation failed" in caplog.text
    assert "synthetic-private-detail" not in caplog.text
