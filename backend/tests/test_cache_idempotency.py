import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import UTC, datetime, timedelta
from threading import Event
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest
from pydantic import SecretStr
from redis.exceptions import RedisError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.models import User, Workspace
from app.common.cache import Cache, RateLimiter, canonical_json
from app.common.errors import DomainError
from app.common.idempotency import IdempotencyRecord, execute_idempotent
from app.db import AppMetadata


class Disconnected:
    def get(self, *args):
        raise RedisError("private connection details")

    def set(self, *args, **kwargs):
        raise RedisError("private connection details")

    def eval(self, *args):
        raise RedisError("private connection details")

    def close(self):
        pass


def test_cache_outage_and_fail_closed_rate_limit(settings):
    cache = Cache(settings, client=Disconnected())
    assert cache.get_json("ws", "counts", 1, "private@example.test") is None
    cache.set_json("ws", "counts", 1, "key", {"count": 3}, 60)
    limiter = RateLimiter(settings, client=Disconnected())
    with pytest.raises(DomainError) as caught:
        limiter.check("login", "private@example.test", 3, 60)
    assert (caught.value.code, caught.value.status) == ("RATE_LIMIT_UNAVAILABLE", 503)
    assert caught.value.message == "Please retry later."
    assert "private" not in str(caught.value)
    cache.close()


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), {1: "x"}, {"x": object()}, "x" * 1_048_577]
)
def test_strict_bounded_json(value):
    with pytest.raises(ValueError):
        canonical_json(value)


def test_cache_keys_are_private_and_scoped(settings):
    cache = Cache(settings, namespace="test_unique", client=Disconnected())
    key = cache._key("ws", "stats", 1, "private@example.test")
    assert key.startswith("elseview:test_unique:aggregate:")
    assert "private" not in key
    assert key != cache._key("other", "stats", 1, "private@example.test")
    assert key != cache._key("ws", "stats", 2, "private@example.test")
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})


def test_idempotency_rejects_invalid_input_before_database_access():
    with pytest.raises(DomainError) as caught:
        execute_idempotent(None, uuid4(), uuid4(), "create", "", {}, lambda: None)
    assert caught.value.status == 400
    with pytest.raises(ValueError):
        execute_idempotent(
            None, uuid4(), uuid4(), "create", "key", {"x": float("nan")}, lambda: None
        )
    with pytest.raises(ValueError):
        execute_idempotent(None, uuid4(), uuid4(), "x" * 97, "key", {}, lambda: None)


@pytest.fixture
def real_cache(settings, db_engine):
    if os.environ.get("TEST_ALLOW_DB") != "1":
        pytest.skip("Real cache requires explicit test database opt-in")
    url = urlsplit(os.environ["CACHE_URL"])
    # Dedicated cache database; never flush shared DB0 or unrelated keys.
    settings.cache_url = SecretStr(urlunsplit(url._replace(path="/15", query="")))
    cache = Cache(settings, namespace="test_" + uuid4().hex)
    try:
        yield cache
    finally:
        keys = list(cache.client.scan_iter(match=cache.prefix + "*"))
        if keys:
            cache.client.delete(*keys)
        cache.close()


@pytest.mark.db
@pytest.mark.cache
def test_real_cache_roundtrip_scope_ttl_and_rate_limit(real_cache, settings):
    cache = real_cache
    cache.set_json("ws", "counts", 1, "private@example.test", {"count": 2}, 30)
    assert cache.get_json("ws", "counts", 1, "private@example.test") == {"count": 2}
    assert cache.get_json("other", "counts", 1, "private@example.test") is None
    assert cache.get_json("ws", "counts", 2, "private@example.test") is None
    assert 0 < cache.client.ttl(cache._key("ws", "counts", 1, "private@example.test")) <= 30
    limiter = RateLimiter(settings, namespace=cache.prefix.split(":")[1], client=cache.client)
    limiter.check("login", "192.0.2.1", 2, 30)
    limiter.check("login", "192.0.2.1", 2, 30)
    with pytest.raises(DomainError) as caught:
        limiter.check("login", "192.0.2.1", 2, 30)
    assert caught.value.status == 429
    limiter.check("login", "192.0.2.2", 2, 30)
    for key in cache.client.scan_iter(match=cache.prefix + "rate:*"):
        assert b"192.0.2" not in key
        assert 0 < cache.client.ttl(key) <= 30


@pytest.fixture
def identity(db_engine):
    workspace_id, actor_id = uuid4(), uuid4()
    with Session(db_engine) as session, session.begin():
        session.add(Workspace(id=workspace_id, name="Synthetic idempotency test"))
        session.add(User(id=actor_id, email=f"{actor_id}@example.test", password_hash="synthetic"))
    try:
        yield workspace_id, actor_id
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(
                delete(IdempotencyRecord).where(IdempotencyRecord.workspace_id == workspace_id)
            )
            session.execute(delete(Workspace).where(Workspace.id == workspace_id))
            session.execute(delete(User).where(User.id == actor_id))


@pytest.mark.db
def test_idempotency_replay_conflict_and_rollback(db_engine, identity):
    workspace, actor = identity
    marker = "idem-" + uuid4().hex
    calls = []
    with Session(db_engine) as session:
        with session.begin():

            def callback():
                calls.append(1)
                return 201, {"synthetic": True}

            args = (session, workspace, actor, "create", "key", {"a": 1}, callback)
            assert execute_idempotent(*args) == (201, {"synthetic": True})
            assert execute_idempotent(*args) == (201, {"synthetic": True})
        assert len(calls) == 1
        with session.begin():
            assert execute_idempotent(*args) == (201, {"synthetic": True})
        assert len(calls) == 1
        with pytest.raises(DomainError) as caught, session.begin():
            execute_idempotent(session, workspace, actor, "create", "key", {"a": 2}, callback)
        assert caught.value.status == 409
        with pytest.raises(RuntimeError), session.begin():

            def failing():
                session.add(AppMetadata(key=marker, value={"synthetic": True}, is_synthetic=True))
                session.flush()
                raise RuntimeError("synthetic failure")

            execute_idempotent(session, workspace, actor, "create", "rollback", {}, failing)
        assert session.get(AppMetadata, marker) is None
        assert (
            session.scalar(
                select(func.count())
                .select_from(IdempotencyRecord)
                .where(IdempotencyRecord.workspace_id == workspace)
            )
            == 1
        )


@pytest.mark.db
def test_expired_idempotency_key_rejected_without_repeating_effect(db_engine, identity):
    workspace, actor = identity
    key = "private-key-" + uuid4().hex
    calls = []

    def callback():
        calls.append(1)
        return 201, {"synthetic": True}

    with Session(db_engine) as session, session.begin():
        execute_idempotent(session, workspace, actor, "create", key, {"count": 1}, callback)
        record = session.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.workspace_id == workspace)
        )
        record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        original_hash = record.request_hash
    for payload in ({"count": 1}, {"count": 2}):
        with Session(db_engine) as session:
            with pytest.raises(DomainError) as caught, session.begin():
                execute_idempotent(session, workspace, actor, "create", key, payload, callback)
        error = caught.value
        assert (error.code, error.status) == ("IDEMPOTENCY_KEY_EXPIRED", 409)
        assert error.message == "Idempotency key has expired."
        assert key not in str(error) + error.message
        assert original_hash not in str(error) + error.message
    assert calls == [1]
    with Session(db_engine) as session:
        record = session.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.workspace_id == workspace)
        )
        assert record.request_hash == original_hash
        assert (record.status, record.response) == (201, {"synthetic": True})
        assert record.expires_at < datetime.now(UTC)


@pytest.mark.db
def test_concurrent_idempotency_one_business_effect(db_engine, identity):
    workspace, actor = identity
    entered, second_started, release = Event(), Event(), Event()
    marker = "idem-" + uuid4().hex
    calls = []

    def run(first):
        with Session(db_engine) as session, session.begin():
            if not first:
                second_started.set()

            def callback():
                calls.append(1)
                session.add(AppMetadata(key=marker, value={"synthetic": True}, is_synthetic=True))
                session.flush()
                entered.set()
                assert release.wait(5)
                return 201, {"marker": marker}

            return execute_idempotent(session, workspace, actor, "concurrent", "same", {}, callback)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(run, True)
            try:
                assert entered.wait(5)
                second = pool.submit(run, False)
                assert second_started.wait(5)
                # The second transaction must wait for the uncommitted key;
                # it cannot execute the business callback independently.
                with pytest.raises(TimeoutError):
                    second.result(timeout=0.2)
            finally:
                release.set()
            assert (
                first.result(timeout=10) == second.result(timeout=10) == (201, {"marker": marker})
            )
        assert len(calls) == 1
        with Session(db_engine) as session:
            assert session.get(AppMetadata, marker) is not None
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(AppMetadata).where(AppMetadata.key == marker))
